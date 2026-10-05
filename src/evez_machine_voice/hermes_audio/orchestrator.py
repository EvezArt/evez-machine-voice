from __future__ import annotations

from pathlib import Path

from .acestep_api import ACEStepClient
from .music_memory import TrackFingerprint, palette_prompt, select_palette
from .performance import PRESETS, PerformanceKind
from .provenance import sha256_text, write_manifest
from .theme import select_theme


def infer_performance_kind(text: str) -> PerformanceKind:
    lower = text.lower()
    if any(x in lower for x in ("beatbox", "boots and cats", "percussion", "kick", "snare")):
        return "beatbox"
    if any(x in lower for x in ("rasp", "growl", "grit", "shout", "feral")):
        return "rasp"
    if any(x in lower for x in ("bar", "rhyme", "flow", "rap", "verse")):
        return "rap"
    if any(x in lower for x in ("sing", "melody", "chorus", "refrain")):
        return "vocaloid"
    if any(x in lower for x in ("remember", "grief", "reflect", "memory")):
        return "sustain"
    return "cinematic"


def build_music_context(
    response_text: str,
    tracks: list[TrackFingerprint],
    energy: float,
    surrealism: float,
):
    theme = select_theme(response_text)
    bpm = theme.bpm
    palette = select_palette(tracks, bpm=bpm, mode="minor", energy=energy, surrealism=surrealism)
    return theme, palette


def build_score_prompt(
    response_text: str,
    theme,
    palette: list[TrackFingerprint],
    energy: float,
    surrealism: float,
) -> str:
    fingerprint_context = palette_prompt(palette)
    return (
        f"Original cinematic score for a spoken or sung response. "
        f"Theme: {theme.name}. Tempo: {theme.bpm} BPM. Mode: {theme.mode}. "
        f"Texture: {theme.texture}. Arrangement: {theme.arrangement}. "
        f"Energy {energy:.2f}; surrealism {surrealism:.2f}. "
        f"Private musical-memory descriptors: {fingerprint_context}. "
        f"Response semantics: {response_text[:1600]}. "
        f"Create a new composition. Do not reproduce a source melody."
    )


def generate_score(
    response_text: str,
    tracks: list[TrackFingerprint],
    output_dir: Path,
    energy: float,
    surrealism: float,
    *,
    lyrics: str = "",
    seed: int | None = None,
) -> dict:
    theme, palette = build_music_context(response_text, tracks, energy, surrealism)
    prompt = build_score_prompt(response_text, theme, palette, energy, surrealism)

    client = ACEStepClient()
    output = output_dir / f"score-{theme.name}-{abs(hash(prompt))}.wav"
    task_id = client.submit(
        prompt=prompt,
        lyrics=lyrics,
        bpm=theme.bpm,
        key_scale=f"{theme.mode}",
        duration=30,
        thinking=True,
        seed=seed,
    )
    client.wait_for_audio(task_id, output)

    manifest = write_manifest(
        output,
        pipeline="hermes-score",
        inputs={
            "response_sha256": sha256_text(response_text),
            "lyrics_sha256": sha256_text(lyrics) if lyrics else None,
            "fingerprint_paths": [t.path for t in palette],
        },
        models={
            "music_backend": "ACE-Step 1.5 local API",
            "task_id": task_id,
        },
        params={
            "theme": theme.name,
            "bpm": theme.bpm,
            "mode": theme.mode,
            "energy": energy,
            "surrealism": surrealism,
        },
        rights_state="FINGERPRINT_ONLY_ORIGINAL_GENERATION",
    )

    return {
        "audio": str(output),
        "manifest": str(manifest),
        "theme": theme.name,
        "bpm": theme.bpm,
        "mode": theme.mode,
        "task_id": task_id,
    }
