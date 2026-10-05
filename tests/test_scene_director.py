from pathlib import Path
import json

from evez_machine_voice.hermes_audio.scene_director import direct_scene, write_scene


def test_scene_is_deterministic():
    a = direct_scene("The system wakes up inside the impossible.", seed=123)
    b = direct_scene("The system wakes up inside the impossible.", seed=123)
    assert a.scene_sha256 == b.scene_sha256
    assert a.sections == b.sections


def test_scene_has_six_dramatic_sections():
    scene = direct_scene("The contradiction survived the evidence.", seed=1)
    assert [s.name for s in scene.sections] == ["OPEN", "BUILD", "TURN", "ASCEND", "IMPACT", "AFTERMATH"]


def test_surreal_scene_gets_glitch_cue():
    scene = direct_scene("A strange impossible reality opens.", surrealism=0.95, seed=2)
    assert any(c.kind == "reality-glitch" for s in scene.sections for c in s.cues)


def test_scene_json(tmp_path: Path):
    scene = direct_scene("write a rap about the machine waking up", seed=8)
    output = tmp_path / "scene.json"
    write_scene(scene, output)
    saved = json.loads(output.read_text())
    assert saved["scene_sha256"] == scene.scene_sha256
    assert saved["mix_plan"]["speech_priority"] is True
