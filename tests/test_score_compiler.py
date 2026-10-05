from pathlib import Path
import json

from evez_machine_voice.hermes_audio.score_compiler import (
    compile_performance,
    write_midi,
    write_plan,
)


def test_compile_is_deterministic():
    a = compile_performance("The contradiction survived the fire.", seed=42)
    b = compile_performance("The contradiction survived the fire.", seed=42)
    assert a.plan_sha256 == b.plan_sha256
    assert a.notes == b.notes
    assert a.percussion == b.percussion


def test_different_seed_changes_plan():
    a = compile_performance("The contradiction survived the fire.", seed=1)
    b = compile_performance("The contradiction survived the fire.", seed=2)
    assert a.plan_sha256 != b.plan_sha256


def test_rap_generates_percussion():
    plan = compile_performance("write bars and flow over the beat", kind="rap", seed=11)
    assert plan.performance_kind == "rap"
    assert len(plan.percussion) > 0


def test_beatbox_generates_percussion_events():
    plan = compile_performance("kick snare boots and cats", kind="beatbox", seed=7)
    assert plan.performance_kind == "beatbox"
    assert all(36 <= p.drum <= 42 for p in plan.percussion)


def test_midi_written(tmp_path: Path):
    plan = compile_performance("sing this refrain with a rising hook", kind="vocaloid", seed=9)
    midi = tmp_path / "test.mid"
    write_midi(plan, midi)
    data = midi.read_bytes()
    assert data[:4] == b"MThd"
    assert len(data) > 20


def test_json_plan_written(tmp_path: Path):
    plan = compile_performance("a strange liminal answer", seed=3)
    out = tmp_path / "plan.json"
    write_plan(plan, out)
    saved = json.loads(out.read_text())
    assert saved["plan_sha256"] == plan.plan_sha256


def test_key_and_scale_overrides_are_honored():
    plan = compile_performance(
        "sing a continuous harmonic motif",
        seed=12,
        key="F#",
        scale="dorian",
    )
    assert plan.key == "F#"
    assert plan.scale == "dorian"
