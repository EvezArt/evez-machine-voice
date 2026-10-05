from pathlib import Path
import json
import zipfile

from evez_machine_voice.hermes_audio.album import export_album
from evez_machine_voice.hermes_audio.conductor import advance_conductor
from evez_machine_voice.hermes_audio.session_ledger import append_record
from evez_machine_voice.hermes_audio.conductor import write_conductor_step


def test_album_export_is_control_only_without_audio(tmp_path: Path):
    session_dir = tmp_path / "session"
    step = advance_conductor("A surreal technical reveal.", session_id="album", seed=5)
    write_conductor_step(step, session_dir)
    append_record(
        session_dir,
        session_id="album",
        turn_index=0,
        state_sha256=step.state.state_sha256,
        scene_sha256=step.scene.scene_sha256,
        plan_sha256=step.performance_plan.plan_sha256,
        source_sha256=step.performance_plan.source_sha256,
        events=step.events,
        recorded_at="2026-10-05T00:00:00+00:00",
    )

    result = export_album(session_dir, session_dir / "album")
    assert result["verified"] is True
    assert result["control_only"] is True
    assert Path(result["json"]).exists()
    assert Path(result["zip"]).exists()

    saved = json.loads(Path(result["json"]).read_text())
    assert saved["track_count"] == 1
    with zipfile.ZipFile(result["zip"]) as archive:
        assert "ALBUM.json" in archive.namelist()
