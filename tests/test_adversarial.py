from pathlib import Path

from evez_machine_voice.hermes_audio.adversarial import audit_bundle
from evez_machine_voice.hermes_audio.score_compiler import compile_performance


def test_adversarial_gate_passes_replayable_plan():
    text = "The system found the contradiction and shipped the fix."
    plan = compile_performance(text, seed=17)
    payload = {
        "plan_sha256": plan.plan_sha256,
        "source_sha256": plan.source_sha256,
        "theme": plan.theme,
        "bpm": plan.bpm,
        "key": plan.key,
        "scale": plan.scale,
        "performance_kind": plan.performance_kind,
        "seed": plan.seed,
    }
    report = audit_bundle(response_text=text, plan_payload=payload)
    assert report.verdict == "PASS"
    assert all(f.verdict == "PASS" for f in report.findings)


def test_adversarial_gate_rejects_fake_produced_audio(tmp_path: Path):
    fake = tmp_path / "missing.wav"
    report = audit_bundle(
        response_text="A render exists.",
        audio_artifact={
            "state": "PRODUCED",
            "path": str(fake),
            "sha256": "definitely-not-real",
            "manifest": str(tmp_path / "missing.json"),
        },
    )
    assert report.verdict == "FAIL"
    assert any(f.code == "PRODUCED_EXISTS" for f in report.findings)


def test_adversarial_gate_rejects_hash_mismatch(tmp_path: Path):
    audio = tmp_path / "audio.bin"
    audio.write_bytes(b"actual bytes")
    report = audit_bundle(
        response_text="A render exists.",
        audio_artifact={
            "state": "PRODUCED",
            "path": str(audio),
            "sha256": "0000000000000000000000000000000000000000000000000000000000000000",
            "manifest": str(tmp_path / "missing.json"),
        },
    )
    assert report.verdict == "FAIL"
    assert any(f.code == "OUTPUT_HASH" for f in report.findings)


def test_adversarial_gate_rejects_unstable_plan():
    text = "The system is technically complete."
    plan = compile_performance(text, seed=2)
    payload = {
        "plan_sha256": "tampered",
        "source_sha256": plan.source_sha256,
        "theme": plan.theme,
        "bpm": plan.bpm,
        "key": plan.key,
        "scale": plan.scale,
        "performance_kind": plan.performance_kind,
        "seed": plan.seed,
    }
    report = audit_bundle(response_text=text, plan_payload=payload)
    assert report.verdict == "FAIL"
    assert any(f.code == "PLAN_REPLAY" for f in report.findings)
