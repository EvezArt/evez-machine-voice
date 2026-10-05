from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import subprocess
from dataclasses import asdict
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from .adversarial import audit_bundle
from .album import export_album
from .audio_jobs import AudioJobStore
from .audio_state import AudioState
from .config import SETTINGS
from .conductor import advance_conductor, state_from_dict, write_conductor_step
from .mix import mix
from .music import MusicEngine
from .music_memory import load_index
from .orchestrator import generate_score
from .performance import PRESETS, PerformanceKind, PerformanceSpec, make_prompt
from .provenance import write_manifest
from .score_compiler import compile_performance, write_plan
from .scene_director import direct_scene, write_scene
from .session_ledger import append_record, read_records, verify_chain
from .voice_clone import VoiceClone

app = FastAPI(title="EVEZ Hermes Audio", version="0.5.0")
voice = VoiceClone()
music = MusicEngine()
job_store = AudioJobStore(SETTINGS.output_dir / "jobs")


class HermesRequest(BaseModel):
    response_text: str = Field(min_length=1, max_length=20000)
    voice: str = "steven"
    voice_style: str = "cinematic"
    music: bool = True
    theme: str | None = None
    duration_seconds: int = Field(default=20, ge=5, le=600)
    energy: float = Field(default=0.55, ge=0, le=1)
    surrealism: float = Field(default=0.70, ge=0, le=1)
    source_audio: str | None = None
    rights_asserted: bool = False
    performance_kind: PerformanceKind | None = None
    guide_audio: str | None = None


class PerformanceRequest(BaseModel):
    guide_audio: str = Field(min_length=1)
    performance_kind: PerformanceKind = "vocaloid"
    output_name: str = "hermes-performance.wav"


class PerformanceJobRequest(BaseModel):
    guide_audio: str = Field(min_length=1)
    performance_kind: PerformanceKind = "vocaloid"
    output_name: str = "hermes-performance.wav"


class SceneRequest(BaseModel):
    response_text: str = Field(min_length=1, max_length=20000)
    duration_seconds: int = Field(default=30, ge=5, le=600)
    energy: float = Field(default=0.55, ge=0, le=1)
    surrealism: float = Field(default=0.70, ge=0, le=1)
    theme: str | None = None
    performance_kind: PerformanceKind | None = None
    seed: int | None = None


class PerformancePlanRequest(BaseModel):
    response_text: str = Field(min_length=1, max_length=20000)
    performance_kind: PerformanceKind | None = None
    theme: str | None = None
    bpm: int | None = Field(default=None, ge=40, le=240)
    seed: int | None = None


class ConductorRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128, pattern=r"[A-Za-z0-9_.-]+")
    response_text: str = Field(min_length=1, max_length=20000)
    duration_seconds: int = Field(default=30, ge=5, le=600)
    energy: float = Field(default=0.55, ge=0, le=1)
    surrealism: float = Field(default=0.70, ge=0, le=1)
    theme: str | None = None
    performance_kind: PerformanceKind | None = None
    seed: int | None = None


class SessionExportRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128, pattern=r"[A-Za-z0-9_.-]+")


class AuditRequest(BaseModel):
    response_text: str = Field(min_length=1, max_length=20000)
    plan: dict | None = None
    audio_artifact: dict | None = None
    session_verification: dict | None = None


class ScoreRequest(BaseModel):
    response_text: str = Field(min_length=1, max_length=20000)
    lyrics: str = ""
    theme: str | None = None
    duration_seconds: int = Field(default=30, ge=10, le=600)
    energy: float = Field(default=0.55, ge=0, le=1)
    surrealism: float = Field(default=0.70, ge=0, le=1)
    seed: int | None = None


def auth(token: str | None):
    if SETTINGS.token and not hmac.compare_digest(token or "", SETTINGS.token):
        raise HTTPException(401, "invalid audio token")


def _session_dir(session_id: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", session_id):
        raise HTTPException(400, "invalid session_id")
    return SETTINGS.output_dir / "sessions" / session_id


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_output_name(name: str) -> str:
    safe = Path(name).name
    if safe != name or safe in {"", ".", ".."}:
        raise HTTPException(400, "output_name must be a simple file name")
    return safe


def _performance_script() -> Path:
    return Path(
        os.getenv(
            "EVEZ_HERMES_PERFORMANCE_SCRIPT",
            str(Path(__file__).resolve().parents[4] / "scripts" / "hermes-vocal-performance.sh"),
        )
    )


def _artifact_payload(
    state: str,
    *,
    path: Path | None = None,
    sha256: str | None = None,
    manifest: Path | None = None,
    error: str | None = None,
) -> dict:
    return {
        "state": state,
        "path": str(path) if path else None,
        "sha256": sha256,
        "manifest": str(manifest) if manifest else None,
        "error": error,
    }


def _run_audio_job(job_id: str) -> None:
    job = job_store.get(job_id)
    job = job_store.update(job, AudioState.RENDERING)

    guide = Path(job.guide_audio).expanduser().resolve()
    script = _performance_script()

    if not guide.exists() or not guide.is_file():
        job_store.update(job, AudioState.FAILED, error="guide audio not found")
        return
    if not script.exists():
        job_store.update(job, AudioState.FAILED, error="Hermes performance script is not installed")
        return

    output = SETTINGS.output_dir / job.output_name
    cmd = ["bash", str(script), str(guide), str(output), job.performance_kind]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        job_store.update(
            job,
            AudioState.FAILED,
            error=result.stderr[-5000:] or "performance rendering failed",
        )
        return

    try:
        manifest = write_manifest(
            output,
            pipeline=f"hermes-performance:{job.performance_kind}",
            inputs={"guide_audio": str(guide)},
            models={"voice_conversion": "RVC local"},
            params={"preset": job.performance_kind},
            rights_state="OWNER_PERFORMANCE_INPUT",
        )
        sha256 = _file_sha256(output)
    except Exception as exc:
        job_store.update(job, AudioState.FAILED, error=f"manifest/fingerprint failed: {exc}")
        return

    job_store.update(
        job,
        AudioState.PRODUCED,
        output_path=str(output),
        manifest_path=str(manifest),
        sha256=sha256,
    )


def memory_tracks():
    index = Path(os.getenv("EVEZ_MUSIC_MEMORY_INDEX", "data/hermes/music-memory.json"))
    if not index.exists():
        return []
    try:
        return load_index(index)
    except Exception as exc:
        raise HTTPException(500, f"invalid music-memory index: {exc}") from exc


@app.get("/health")
def health():
    return {
        "ok": True,
        "service": "evez-hermes-audio",
        "voice": SETTINGS.default_voice,
        "performance_presets": list(PRESETS),
        "music_memory": len(memory_tracks()),
    }


@app.post("/v1/hermes/respond")
def respond(req: HermesRequest, x_hermes_audio_token: str | None = Header(default=None)):
    auth(x_hermes_audio_token)

    if req.performance_kind and req.guide_audio:
        return render_performance(
            PerformanceRequest(
                guide_audio=req.guide_audio,
                performance_kind=req.performance_kind,
                output_name=f"hermes-{req.performance_kind}.wav",
            )
        )

    voice_path = voice.speak(req.response_text, req.voice, req.voice_style)
    if not req.music:
        return {"voice": str(voice_path), "score": None, "mix": None}

    score_path, theme = music.compose(
        req.response_text,
        req.theme,
        req.duration_seconds,
        req.energy,
        req.surrealism,
        req.source_audio,
        req.rights_asserted,
    )
    mix_path = SETTINGS.output_dir / f"hermes-{theme.name}-{voice_path.stem}.wav"
    mix(voice_path, score_path, mix_path)
    return {
        "voice": str(voice_path),
        "score": str(score_path),
        "mix": str(mix_path),
        "theme": theme.name,
        "bpm": theme.bpm,
        "mode": theme.mode,
    }


@app.post("/v1/hermes/scene")
def scene(req: SceneRequest, x_hermes_audio_token: str | None = Header(default=None)):
    auth(x_hermes_audio_token)
    rendered = direct_scene(
        req.response_text,
        duration_seconds=req.duration_seconds,
        energy=req.energy,
        surrealism=req.surrealism,
        explicit_theme=req.theme,
        performance_kind=req.performance_kind,
        seed=req.seed,
    )
    output = SETTINGS.output_dir / f"scene-{rendered.scene_sha256[:16]}.json"
    write_scene(rendered, output)
    return {
        "scene_sha256": rendered.scene_sha256,
        "source_sha256": rendered.source_sha256,
        "theme": rendered.theme,
        "bpm": rendered.bpm,
        "key": rendered.key,
        "scale": rendered.scale,
        "vocal_mode": rendered.vocal_mode,
        "arc": rendered.arc,
        "sections": [asdict(s) for s in rendered.sections],
        "mix_plan": rendered.mix_plan,
        "output": str(output),
    }


@app.post("/v1/hermes/conductor/step")
def conductor_step(req: ConductorRequest, x_hermes_audio_token: str | None = Header(default=None)):
    auth(x_hermes_audio_token)
    session_dir = _session_dir(req.session_id)
    records = read_records(session_dir)
    previous_state = None

    if records:
        state_path = session_dir / f"turn-{records[-1].turn_index:04d}-state.json"
        if not state_path.exists():
            raise HTTPException(500, "session ledger exists but latest state artifact is missing")
        try:
            previous_state = state_from_dict(json.loads(state_path.read_text(encoding="utf-8")))
        except Exception as exc:
            raise HTTPException(500, f"invalid conductor state: {exc}") from exc

    step = advance_conductor(
        req.response_text,
        session_id=req.session_id,
        previous_state=previous_state,
        duration_seconds=req.duration_seconds,
        energy=req.energy,
        surrealism=req.surrealism,
        explicit_theme=req.theme,
        performance_kind=req.performance_kind,
        seed=req.seed,
    )

    paths = write_conductor_step(step, session_dir)
    audit_report = audit_bundle(
        response_text=req.response_text,
        plan_payload=asdict(step.performance_plan),
        session_verification=verify_chain(session_dir),
    )
    if audit_report.verdict == "FAIL":
        raise HTTPException(500, f"conductor truth gate failed: {audit_report.audit_sha256}")

    record = append_record(
        session_dir,
        session_id=req.session_id,
        turn_index=step.state.turn_index,
        state_sha256=step.state.state_sha256,
        scene_sha256=step.scene.scene_sha256,
        plan_sha256=step.performance_plan.plan_sha256,
        source_sha256=step.performance_plan.source_sha256,
        events=step.events,
        audit_sha256=audit_report.audit_sha256,
        audit_verdict=audit_report.verdict,
    )

    return {
        "session_id": req.session_id,
        "turn_index": step.state.turn_index,
        "state": asdict(step.state),
        "events": list(step.events),
        "scene": {
            "scene_sha256": step.scene.scene_sha256,
            "theme": step.scene.theme,
            "bpm": step.scene.bpm,
            "key": step.scene.key,
            "scale": step.scene.scale,
            "vocal_mode": step.scene.vocal_mode,
            "output": paths["scene"],
        },
        "performance_plan": {
            "plan_sha256": step.performance_plan.plan_sha256,
            "kind": step.performance_plan.performance_kind,
            "bpm": step.performance_plan.bpm,
            "key": step.performance_plan.key,
            "scale": step.performance_plan.scale,
            "output": paths["plan"],
        },
        "rationale": step.rationale,
        "audit": asdict(audit_report),
        "session_record_sha256": record.record_sha256,
    }


@app.post("/v1/hermes/performance-job")
def performance_job(
    req: PerformanceJobRequest,
    background_tasks: BackgroundTasks,
    x_hermes_audio_token: str | None = Header(default=None),
):
    auth(x_hermes_audio_token)
    output_name = _safe_output_name(req.output_name)
    guide = Path(req.guide_audio).expanduser().resolve()
    if not guide.exists() or not guide.is_file():
        raise HTTPException(404, "guide audio not found")

    job = job_store.create(
        guide_audio=str(guide),
        performance_kind=req.performance_kind,
        output_name=output_name,
    )
    background_tasks.add_task(_run_audio_job, job.job_id)
    return job_store.payload(job)


@app.get("/v1/hermes/performance-job/{job_id}")
def performance_job_status(job_id: str, x_hermes_audio_token: str | None = Header(default=None)):
    auth(x_hermes_audio_token)
    try:
        job = job_store.get(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(404, "audio job not found") from exc
    return job_store.payload(job)


@app.get("/v1/hermes/session/verify/{session_id}")
def session_verify(session_id: str, x_hermes_audio_token: str | None = Header(default=None)):
    auth(x_hermes_audio_token)
    return verify_chain(_session_dir(session_id))


@app.post("/v1/hermes/session/export")
def session_export(req: SessionExportRequest, x_hermes_audio_token: str | None = Header(default=None)):
    auth(x_hermes_audio_token)
    session_dir = _session_dir(req.session_id)
    if not (session_dir / "session-ledger.jsonl").exists():
        raise HTTPException(404, "session not found")
    return export_album(session_dir, session_dir / "album")


@app.post("/v1/hermes/audit")
def audit(req: AuditRequest, x_hermes_audio_token: str | None = Header(default=None)):
    auth(x_hermes_audio_token)
    report = audit_bundle(
        response_text=req.response_text,
        plan_payload=req.plan,
        audio_artifact=req.audio_artifact,
        session_verification=req.session_verification,
    )
    return asdict(report)


@app.post("/v1/hermes/performance-plan")
def performance_plan(req: PerformancePlanRequest, x_hermes_audio_token: str | None = Header(default=None)):
    auth(x_hermes_audio_token)
    plan = compile_performance(
        req.response_text,
        kind=req.performance_kind,
        explicit_theme=req.theme,
        bpm=req.bpm,
        seed=req.seed,
    )
    json_path = SETTINGS.output_dir / f"plan-{plan.plan_sha256[:16]}.json"
    midi_path = SETTINGS.output_dir / f"plan-{plan.plan_sha256[:16]}.mid"
    outputs = write_plan(plan, json_path, midi_path)
    return {
        "plan_sha256": plan.plan_sha256,
        "source_sha256": plan.source_sha256,
        "theme": plan.theme,
        "kind": plan.performance_kind,
        "bpm": plan.bpm,
        "key": plan.key,
        "scale": plan.scale,
        "sections": plan.sections,
        "note_count": len(plan.notes),
        "percussion_count": len(plan.percussion),
        "outputs": outputs,
    }


@app.post("/v1/hermes/score")
def score(req: ScoreRequest, x_hermes_audio_token: str | None = Header(default=None)):
    auth(x_hermes_audio_token)
    return generate_score(
        req.response_text,
        memory_tracks(),
        SETTINGS.output_dir,
        req.energy,
        req.surrealism,
        lyrics=req.lyrics,
        seed=req.seed,
        explicit_theme=req.theme,
        duration=req.duration_seconds,
    )


@app.post("/v1/hermes/performance")
def render_performance(
    req: PerformanceRequest,
    x_hermes_audio_token: str | None = Header(default=None),
):
    auth(x_hermes_audio_token)

    guide = Path(req.guide_audio).expanduser().resolve()
    if not guide.exists() or not guide.is_file():
        raise HTTPException(404, "guide audio not found")

    script = _performance_script()
    if not script.exists():
        raise HTTPException(500, "Hermes performance script is not installed")

    output = SETTINGS.output_dir / _safe_output_name(req.output_name)
    cmd = ["bash", str(script), str(guide), str(output), req.performance_kind]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)

    if result.returncode != 0:
        raise HTTPException(500, result.stderr[-5000:] or "performance rendering failed")

    manifest = write_manifest(
        output,
        pipeline=f"hermes-performance:{req.performance_kind}",
        inputs={"guide_audio": str(guide)},
        models={"voice_conversion": "RVC local"},
        params={"preset": req.performance_kind},
        rights_state="OWNER_PERFORMANCE_INPUT",
    )

    return {
        "performance": str(output),
        "manifest": str(manifest),
        "kind": req.performance_kind,
        "audio_artifact": _artifact_payload(
            "PRODUCED",
            path=output,
            sha256=_file_sha256(output),
            manifest=manifest,
        ),
        "stdout": result.stdout[-2000:],
    }


@app.get("/v1/hermes/performance/profile/{kind}")
def performance_profile(kind: PerformanceKind):
    expression = PRESETS[kind]
    return {
        "kind": kind,
        "expression": expression.__dict__,
        "prompt": make_prompt(
            PerformanceSpec(
                kind=kind,
                lyrics="",
                bpm=101,
                key="A",
                scale="harmonic_minor",
                expression=expression,
            )
        ),
    }


def main():
    import uvicorn
    uvicorn.run("evez_machine_voice.hermes_audio.server:app", host="0.0.0.0", port=9113)
