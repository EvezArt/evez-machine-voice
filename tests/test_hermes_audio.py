from evez_machine_voice.hermes_audio.performance import PRESETS, preset
from evez_machine_voice.hermes_audio.theme import THEMES, select_theme
from evez_machine_voice.hermes_audio.music_memory import TrackFingerprint, palette_prompt, select_palette


def test_all_performance_presets_exist():
    expected = {"vocaloid", "cinematic", "rap", "beatbox", "rasp", "sustain"}
    assert expected.issubset(PRESETS)


def test_surreal_routes_to_surreal():
    assert select_theme("an uncanny liminal impossible reality") == THEMES["surreal"]


def test_rap_preset_has_high_cadence():
    assert preset("rap").cadence > 0.8


def test_palette_prompt_is_deterministic():
    track = TrackFingerprint(
        path="song.wav",
        sha256="abc",
        duration_seconds=100,
        bpm=100,
        key="A",
        mode="minor",
        rms_db=-10,
        spectral_centroid_hz=3200,
        spectral_bandwidth_hz=2500,
        zero_crossing_rate=0.04,
        pulse_density=0.55,
    )
    assert "BPM 100" in palette_prompt([track])


def test_palette_selects_closest_tempo():
    tracks = [
        TrackFingerprint("slow.wav", "a", 10, 70, "A", "minor", -12, 1500, 2000, 0.03, 0.39),
        TrackFingerprint("match.wav", "b", 101, 120, "A", "minor", -12, 2800, 2200, 0.03, 0.56),
        TrackFingerprint("fast.wav", "c", 10, 180, "C", "major", -12, 5000, 3000, 0.07, 1.0),
    ]
    chosen = select_palette(tracks, bpm=120, mode="minor", energy=0.7, surrealism=0.5, limit=1)
    assert chosen[0].path == "match.wav"
