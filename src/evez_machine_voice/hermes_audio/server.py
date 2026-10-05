from __future__ import annotations

import hmac
import os
import subprocess
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from .config import SETTINGS
from .mix import mix
from .music import MusicEngine
from .music_memory import load_index
from .orchestrator import generate_score
from .performance import PRESETS, PerformanceKind, PerformanceSpec, make_prompt
from .provenance import write_manifest
from .score_compiler import compile_performance, write_plan
from .voice_clone import VoiceClone

app = FastAPI(title="EVEZ Hermes Audio", version="0.3.0")
voice = VoiceClone()
music = MusicEngine()


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


class PerformancePlanRequest(BaseModel):
    response_text: str = Field(min_length=1, max_length=20000)
    performance_kind: PerformanceKind | None = None
    theme: str | None = None
    bpm: int | None = Field(default=None, ge=40, le=240)
    seed: int | None = None


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

    script = Path(
        os.getenv(
            "EVEZ_HERMES_PERFORMANCE_SCRIPT",
            str(Path(__file__).resolve().parents[4] / "scripts" / "hermes-vocal-performance.sh"),
        )
    )
    if not script.exists():
        raise HTTPException(500, "Hermes performance script is not installed")

    output = SETTINGS.output_dir / req.output_name
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
