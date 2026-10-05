from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any

from .performance import PerformanceKind
from .score_compiler import compile_performance
from .theme import Theme, select_theme


@dataclass(frozen=True)
class SceneCue:
    at_seconds: float
    duration_seconds: float
    kind: str
    intensity: float
    description: str


@dataclass(frozen=True)
class SceneSection:
    name: str
    start_seconds: float
    end_seconds: float
    intensity: float
    vocal_mode: PerformanceKind
    musical_role: str
    cues: list[SceneCue]


@dataclass(frozen=True)
class HermesScene:
    version: str
    scene_sha256: str
    source_sha256: str
    duration_seconds: int
    theme: str
    bpm: int
    key: str
    scale: str
    vocal_mode: PerformanceKind
    arc: list[float]
    sections: list[SceneSection]
    mix_plan: dict[str, Any]


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _mode(text: str) -> PerformanceKind:
    lower = text.lower()
    if any(x in lower for x in ("beatbox", "kick", "snare", "percussion")):
        return "beatbox"
    if any(x in lower for x in ("rap", "rhyme", "bars", "flow", "verse")):
        return "rap"
    if any(x in lower for x in ("rasp", "growl", "grit", "shout", "feral")):
        return "rasp"
    if any(x in lower for x in ("sing", "song", "melody", "chorus", "refrain")):
        return "vocaloid"
    if any(x in lower for x in ("remember", "memory", "grief", "reflect")):
        return "sustain"
    return "cinematic"


def _arc(theme: Theme, energy: float, surrealism: float) -> list[float]:
    base = {
        "investigation": [0.18, 0.25, 0.38, 0.30, 0.58, 0.40],
        "discovery": [0.20, 0.34, 0.52, 0.72, 0.88, 0.66],
        "danger": [0.35, 0.55, 0.72, 0.88, 1.00, 0.76],
        "technical": [0.28, 0.36, 0.48, 0.62, 0.58, 0.42],
        "reflection": [0.42, 0.36, 0.30, 0.46, 0.54, 0.34],
        "surreal": [0.30, 0.52, 0.40, 0.76, 0.46, 0.92],
    }.get(theme.name, [0.3, 0.4, 0.5, 0.6, 0.5, 0.4])
    return [round(max(0.0, min(1.0, v * 0.65 + energy * 0.25 + surrealism * 0.10)), 4) for v in base]


def _cue_kind(theme_name: str, section_index: int, surrealism: float) -> str:
    if section_index == 0:
        return "fade-in"
    if section_index == 4:
        return "impact"
    if section_index == 5:
        return "release"
    if surrealism > 0.75 and section_index % 2:
        return "reality-glitch"
    if theme_name == "danger":
        return "pressure"
    if theme_name == "reflection":
        return "breath"
    return "transition"


def direct_scene(
    response_text: str,
    *,
    duration_seconds: int = 30,
    energy: float = 0.55,
    surrealism: float = 0.70,
    explicit_theme: str | None = None,
    performance_kind: PerformanceKind | None = None,
    seed: int | None = None,
    bpm: int | None = None,
    key: str | None = None,
    scale: str | None = None,
) -> HermesScene:
    source_sha256 = _hash(response_text)
    theme = select_theme(response_text, explicit_theme)
    kind = performance_kind or _mode(response_text)

    plan = compile_performance(
        response_text,
        kind=kind,
        explicit_theme=theme.name,
        bpm=bpm or theme.bpm,
        seed=seed,
        key=key,
        scale=scale,
    )

    arc = _arc(theme, energy, surrealism)
    names = ["OPEN", "BUILD", "TURN", "ASCEND", "IMPACT", "AFTERMATH"]
    segment = duration_seconds / len(names)
    sections = []

    for i, name in enumerate(names):
        start = round(i * segment, 3)
        end = round((i + 1) * segment, 3)
        intensity = arc[i]
        cue_kind = _cue_kind(theme.name, i, surrealism)
        descriptions = {
            "fade-in": "bring the world into focus",
            "transition": "change harmonic or rhythmic layer",
            "reality-glitch": "briefly fracture timing or texture",
            "pressure": "increase low-frequency and transient pressure",
            "breath": "remove layers and expose vocal space",
            "impact": "full arrangement punctuation",
            "release": "remove pressure and leave a tail",
        }
        cue = SceneCue(
            at_seconds=round(start + segment * 0.72, 3),
            duration_seconds=round(min(1.2, segment * 0.16), 3),
            kind=cue_kind,
            intensity=intensity,
            description=descriptions[cue_kind],
        )
        role = "establish" if i == 0 else "develop" if i in (1, 2) else "escalate" if i == 3 else "punctuate" if i == 4 else "resolve"
        sections.append(SceneSection(name, start, end, intensity, kind, role, [cue]))

    mix_plan = {
        "voice_db": 0.0,
        "music_duck_db": -7.0,
        "impact_duck_db": -3.0,
        "voice_presence_hz": [1200, 4200],
        "stereo_width": round(0.75 + surrealism * 0.20, 3),
        "tail_seconds": round(1.2 + surrealism * 2.8, 2),
        "speech_priority": True,
        "music_priority": "secondary",
    }

    canonical = {
        "version": "evez-hermes-scene/v1",
        "source_sha256": source_sha256,
        "duration_seconds": duration_seconds,
        "theme": theme.name,
        "bpm": plan.bpm,
        "key": plan.key,
        "scale": plan.scale,
        "vocal_mode": kind,
        "arc": arc,
        "sections": [asdict(x) for x in sections],
        "mix_plan": mix_plan,
    }
    scene_sha256 = _hash(json.dumps(canonical, sort_keys=True, separators=(",", ":")))

    return HermesScene(
        "evez-hermes-scene/v1",
        scene_sha256,
        source_sha256,
        duration_seconds,
        theme.name,
        plan.bpm,
        plan.key,
        plan.scale,
        kind,
        arc,
        sections,
        mix_plan,
    )


def write_scene(scene: HermesScene, path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(scene), indent=2, sort_keys=True), encoding="utf-8")
    return str(path)
