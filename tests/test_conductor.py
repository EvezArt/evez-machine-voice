from pathlib import Path
import json

from evez_machine_voice.hermes_audio.conductor import advance_conductor, semantic_events, write_conductor_step, state_from_dict
from evez_machine_voice.hermes_audio.session_ledger import append_record, verify_chain


def test_semantic_events_are_deterministic():
    events = semantic_events("We found a strange contradiction in the runtime. Is it actually fixed?")
    assert events == ("REVEAL", "CONTRADICTION", "QUESTION", "TECHNICAL", "UNCANNY")


def test_conductor_is_continuous():
    first = advance_conductor(
        "We found the evidence.",
        session_id="test",
        seed=7,
        duration_seconds=20,
    )
    second = advance_conductor(
        "But the system warns about a breach.",
        session_id="test",
        previous_state=first.state,
        seed=7,
        duration_seconds=20,
    )
    assert first.state.turn_index == 0
    assert second.state.turn_index == 1
    assert second.state.previous_state_sha256 == first.state.state_sha256
    assert second.state.motif.parent_motif_id == first.state.motif.motif_id
    assert second.performance_plan.key == first.performance_plan.key


def test_conductor_round_trips_state(tmp_path: Path):
    step = advance_conductor("The architecture is technically complete.", session_id="roundtrip", seed=3)
    paths = write_conductor_step(step, tmp_path)
    saved = json.loads(Path(paths["state"]).read_text())
    state = state_from_dict(saved)
    assert state == step.state


def test_session_ledger_verifies_and_detects_tamper(tmp_path: Path):
    step = advance_conductor("The contradiction is resolved.", session_id="ledger", seed=9)
    append_record(
        tmp_path,
        session_id="ledger",
        turn_index=0,
        state_sha256=step.state.state_sha256,
        scene_sha256=step.scene.scene_sha256,
        plan_sha256=step.performance_plan.plan_sha256,
        source_sha256=step.performance_plan.source_sha256,
        events=step.events,
        recorded_at="2026-10-05T00:00:00+00:00",
    )
    assert verify_chain(tmp_path)["ok"] is True

    path = tmp_path / "session-ledger.jsonl"
    tampered = path.read_text().replace('"turn_index":0', '"turn_index":9', 1)
    path.write_text(tampered)
    result = verify_chain(tmp_path)
    assert result["ok"] is False
    assert result["problems"]
