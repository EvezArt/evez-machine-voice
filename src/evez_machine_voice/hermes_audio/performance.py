from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


PerformanceKind = Literal["vocaloid", "cinematic", "rap", "beatbox", "rasp", "sustain"]


@dataclass(frozen=True)
class Expression:
    pitch_shift: int = 0
    energy: float = 0.70
    breath: float = 0.25
    vibrato: float = 0.20
    rasp: float = 0.00
    grit: float = 0.00
    fry: float = 0.00
    attack: float = 0.50
    legato: float = 0.50
    sustain: float = 0.50
    cadence: float = 0.50
    articulation: float = 0.70
    beatbox: float = 0.00


PRESETS: dict[PerformanceKind, Expression] = {
    "vocaloid": Expression(energy=0.76, breath=0.28, vibrato=0.38, attack=0.56, legato=0.68, sustain=0.68, articulation=0.78),
    "cinematic": Expression(energy=0.65, breath=0.30, vibrato=0.30, attack=0.35, legato=0.82, sustain=0.84, articulation=0.62),
    "rap": Expression(energy=0.86, breath=0.15, attack=0.82, legato=0.28, cadence=0.88, articulation=0.96),
    "beatbox": Expression(energy=0.94, breath=0.12, attack=0.98, articulation=1.00, beatbox=1.00, legato=0.08),
    "rasp": Expression(energy=0.90, breath=0.22, vibrato=0.26, rasp=0.88, grit=0.72, fry=0.42, attack=0.72, sustain=0.72),
    "sustain": Expression(energy=0.73, breath=0.34, vibrato=0.56, rasp=0.18, attack=0.28, legato=0.94, sustain=0.98),
}


@dataclass(frozen=True)
class PerformanceSpec:
    kind: PerformanceKind
    lyrics: str
    bpm: int
    key: str
    scale: str
    expression: Expression
    guide_mode: Literal["recorded", "generated"] = "recorded"
    melody_file: str | None = None


def make_prompt(spec: PerformanceSpec) -> str:
    e = spec.expression
    traits = [
        f"{spec.kind} vocal performance",
        f"{spec.bpm} BPM",
        f"key {spec.key} {spec.scale}",
        f"energy {e.energy:.2f}",
        f"breath {e.breath:.2f}",
        f"vibrato {e.vibrato:.2f}",
        f"rasp {e.rasp:.2f}",
        f"grit {e.grit:.2f}",
        f"fry {e.fry:.2f}",
        f"attack {e.attack:.2f}",
        f"legato {e.legato:.2f}",
        f"sustain {e.sustain:.2f}",
        f"rap cadence {e.cadence:.2f}",
        f"articulation {e.articulation:.2f}",
        f"beatbox {e.beatbox:.2f}",
    ]
    return ", ".join(traits) + f"; lyrics/performance text: {spec.lyrics[:3000]}"


def preset(kind: PerformanceKind) -> Expression:
    return PRESETS[kind]
