from pathlib import Path

from evez_machine_voice.hermes_audio.audio_jobs import AudioJobStore
from evez_machine_voice.hermes_audio.audio_state import AudioState


def test_audio_job_state_transitions_persist(tmp_path: Path):
    store = AudioJobStore(tmp_path)
    job = store.create(
        guide_audio="/tmp/guide.wav",
        performance_kind="vocaloid",
        output_name="hermes.wav",
    )
    assert job.state == AudioState.PLANNED

    rendering = store.update(job, AudioState.RENDERING)
    assert store.get(job.job_id).state == AudioState.RENDERING

    produced = store.update(
        rendering,
        AudioState.PRODUCED,
        output_path="/tmp/hermes.wav",
        manifest_path="/tmp/hermes.wav.manifest.json",
        sha256="abc123",
    )
    loaded = store.get(job.job_id)
    assert loaded.state == AudioState.PRODUCED
    assert loaded.output_path == "/tmp/hermes.wav"
    assert loaded.sha256 == "abc123"
