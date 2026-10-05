from __future__ import annotations

import hashlib
import json
import math
import re
import struct
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .performance import Expression, PerformanceKind, PRESETS
from .theme import THEMES, Theme, select_theme


SCALES: dict[str, tuple[int, ...]] = {
    "major": (0, 2, 4, 5, 7, 9, 11),
    "minor": (0, 2, 3, 5, 7, 8, 10),
    "dorian": (0, 2, 3, 5, 7, 9, 10),
    "aeolian": (0, 2, 3, 5, 7, 8, 10),
    "harmonic_minor": (0, 2, 3, 5, 7, 8, 11),
    "phrygian": (0, 1, 3, 5, 7, 8, 10),
}


@dataclass(frozen=True)
class NoteEvent:
    bar: int
    beat: float
    duration: float
    midi: int
    velocity: int
    lyric: str
    articulation: str


@dataclass(frozen=True)
class ExpressionEvent:
    bar: int
    beat: float
    energy: float
    breath: float
    vibrato: float
    rasp: float
    grit: float
    fry: float


@dataclass(frozen=True)
class PercussionEvent:
    bar: int
    beat: float
    drum: int
    velocity: int
    syllable: str


@dataclass(frozen=True)
class PerformancePlan:
    version: str
    plan_sha256: str
    source_sha256: str
    theme: str
    bpm: int
    key: str
    scale: str
    performance_kind: str
    lyrics: list[str]
    notes: list[NoteEvent]
    expressions: list[ExpressionEvent]
    percussion: list[PercussionEvent]
    sections: list[dict[str, Any]]
    seed: int


KEY_ROOTS = {
    "C": 60,
    "C#": 61,
    "Db": 61,
    "D": 62,
    "D#": 63,
    "Eb": 63,
    "E": 64,
    "F": 65,
    "F#": 66,
    "Gb": 66,
    "G": 67,
    "G#": 68,
    "Ab": 68,
    "A": 69,
    "A#": 70,
    "Bb": 70,
    "B": 71,
}


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _seed(source_sha256: str, explicit_seed: int | None) -> int:
    if explicit_seed is not None:
        return int(explicit_seed) & 0xFFFFFFFF
    return int(source_sha256[:8], 16)


def _tokens(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9'!?,.;:-]+", text)


def _intensity(token: str) -> float:
    letters = max(1, sum(c.isalpha() for c in token))
    punctuation = sum(c in "!?!" for c in token)
    upper = sum(c.isupper() for c in token)
    return min(1.0, 0.35 + 0.03 * letters + 0.12 * punctuation + 0.03 * upper)


def _scale_pitch(root: int, scale: tuple[int, ...], degree: int, octave: int = 0) -> int:
    octave_step, index = divmod(degree, len(scale))
    return root + scale[index] + (octave + octave_step) * 12


def _section_plan(tokens: list[str], bars: int) -> list[dict[str, Any]]:
    if not tokens:
        return [{"name": "INTRO", "start_bar": 0, "bars": bars}]

    names = ["INTRO", "VERSE", "LIFT", "HOOK"]
    weights = [0.15, 0.35, 0.20, 0.30]
    raw = [max(1, round(bars * w)) for w in weights]
    while sum(raw) > bars:
        idx = max(range(len(raw)), key=lambda i: raw[i])
        raw[idx] -= 1
    while sum(raw) < bars:
        raw[-1] += 1

    cursor = 0
    sections = []
    for name, length in zip(names, raw):
        sections.append({"name": name, "start_bar": cursor, "bars": length})
        cursor += length
    return sections


def _kind_from_text(text: str, explicit: PerformanceKind | None) -> PerformanceKind:
    if explicit:
        return explicit
    lower = text.lower()
    if any(x in lower for x in ("beatbox", "boots and cats", "kick", "snare", "percussion")):
        return "beatbox"
    if any(x in lower for x in ("rasp", "growl", "grit", "shout", "scream", "feral")):
        return "rasp"
    if any(x in lower for x in ("rap", "rhyme", "bars", "flow", "verse")):
        return "rap"
    if any(x in lower for x in ("sing", "sings", "melody", "chorus", "refrain")):
        return "vocaloid"
    if any(x in lower for x in ("remember", "memory", "grief", "reflection")):
        return "sustain"
    return "cinematic"


def _choose_key_scale(theme: Theme, seed: int) -> tuple[str, str]:
    keys = list(KEY_ROOTS)
    key = keys[seed % len(keys)]
    if theme.name == "discovery":
        scale = "dorian"
    elif theme.name == "danger":
        scale = "phrygian"
    elif theme.name == "reflection":
        scale = "aeolian"
    elif theme.name == "surreal":
        scale = "harmonic_minor"
    else:
        scale = "minor"
    return key, scale


def compile_performance(
    response_text: str,
    *,
    kind: PerformanceKind | None = None,
    explicit_theme: str | None = None,
    bpm: int | None = None,
    seed: int | None = None,
) -> PerformancePlan:
    source_sha256 = _hash_text(response_text)
    actual_seed = _seed(source_sha256, seed)
    theme = select_theme(response_text, explicit_theme)
    performance_kind = _kind_from_text(response_text, kind)
    expression: Expression = PRESETS[performance_kind]
    key, scale_name = _choose_key_scale(theme, actual_seed)
    scale = SCALES[scale_name]

    tokens = _tokens(response_text)
    usable_tokens = tokens[:96]
    beat_bars = max(4, math.ceil(len(usable_tokens) / 4))
    sections = _section_plan(usable_tokens, beat_bars)

    base_bpm = int(bpm or theme.bpm)
    if performance_kind == "rap":
        base_bpm = max(base_bpm, 108)
    if performance_kind == "beatbox":
        base_bpm = max(base_bpm, 120)

    root = KEY_ROOTS[key]
    notes: list[NoteEvent] = []
    expressions: list[ExpressionEvent] = []
    percussion: list[PercussionEvent] = []

    index = 0
    previous_degree = 2
    for bar in range(beat_bars):
        section = next(s for s in sections if s["start_bar"] <= bar < s["start_bar"] + s["bars"])
        section_name = section["name"]

        for slot in range(4):
            if index >= len(usable_tokens):
                break
            token = usable_tokens[index]
            intensity = _intensity(token)

            # Deterministic contour: rises toward the hook, falls into rests,
            # with bounded leaps so the line remains singable.
            seed_byte = actual_seed >> ((index % 4) * 8) & 0xFF
            contour = ((seed_byte + index * 7) % 5) - 2

            if section_name == "INTRO":
                contour -= 1
            elif section_name == "HOOK":
                contour += 1

            desired_degree = previous_degree + contour
            desired_degree = max(0, min(6, desired_degree))
            octave = 0
            if performance_kind == "vocaloid" and section_name == "HOOK":
                octave = 1 if index % 7 == 0 else 0

            midi_note = _scale_pitch(root, scale, desired_degree, octave)

            if token.endswith((".", "!", "?")):
                duration = 1.5 if performance_kind in ("sustain", "vocaloid") else 1.0
                articulation = "release"
            elif performance_kind == "rap":
                duration = 0.45
                articulation = "staccato"
            elif performance_kind == "beatbox":
                duration = 0.20
                articulation = "percussive"
            else:
                duration = 0.75
                articulation = "legato"

            velocity = int(max(36, min(118, 50 + intensity * 55)))
            notes.append(
                NoteEvent(
                    bar=bar,
                    beat=float(slot),
                    duration=duration,
                    midi=midi_note,
                    velocity=velocity,
                    lyric=token,
                    articulation=articulation,
                )
            )

            expressions.append(
                ExpressionEvent(
                    bar=bar,
                    beat=float(slot),
                    energy=min(1.0, expression.energy * (0.75 + 0.35 * intensity)),
                    breath=min(1.0, expression.breath + (0.12 if token.endswith(",") else 0.0)),
                    vibrato=min(1.0, expression.vibrato + (0.18 if duration >= 1.0 else 0.0)),
                    rasp=min(1.0, expression.rasp + (0.12 if "r" in token.lower() else 0.0)),
                    grit=expression.grit,
                    fry=expression.fry,
                )
            )

            if performance_kind == "beatbox":
                drum_cycle = (36, 42, 38, 42)
                percussion.append(
                    PercussionEvent(
                        bar=bar,
                        beat=float(slot),
                        drum=drum_cycle[(index + seed_byte) % len(drum_cycle)],
                        velocity=int(70 + intensity * 45),
                        syllable=("B", "T", "K", "TS")[index % 4],
                    )
                )
            elif performance_kind == "rap":
                if slot in (0, 2):
                    percussion.append(PercussionEvent(bar, float(slot), 36, velocity, "K"))
                if slot in (1, 3):
                    percussion.append(PercussionEvent(bar, float(slot), 42, velocity - 8, "TS"))

            if token.endswith((".", "!", "?")) and slot < 3:
                # Phrase-ending rests are first-class events.
                pass

            previous_degree = desired_degree
            index += 1

    canonical = {
        "version": "evez-performance-plan/v1",
        "source_sha256": source_sha256,
        "theme": theme.name,
        "bpm": base_bpm,
        "key": key,
        "scale": scale_name,
        "performance_kind": performance_kind,
        "lyrics": usable_tokens,
        "notes": [asdict(x) for x in notes],
        "expressions": [asdict(x) for x in expressions],
        "percussion": [asdict(x) for x in percussion],
        "sections": sections,
        "seed": actual_seed,
    }
    plan_sha256 = _hash_text(json.dumps(canonical, sort_keys=True, separators=(",", ":")))

    return PerformancePlan(
        version="evez-performance-plan/v1",
        plan_sha256=plan_sha256,
        source_sha256=source_sha256,
        theme=theme.name,
        bpm=base_bpm,
        key=key,
        scale=scale_name,
        performance_kind=performance_kind,
        lyrics=usable_tokens,
        notes=notes,
        expressions=expressions,
        percussion=percussion,
        sections=sections,
        seed=actual_seed,
    )


def _vlq(value: int) -> bytes:
    value = max(0, int(value))
    buffer = value & 0x7F
    out = []
    while True:
        value >>= 7
        if value:
            buffer <<= 8
            buffer |= ((value & 0x7F) | 0x80)
        else:
            break
    while True:
        out.append(buffer & 0xFF)
        if buffer & 0x80:
            buffer >>= 8
        else:
            break
    return bytes(out)


def _meta(delta: int, payload: bytes) -> bytes:
    return _vlq(delta) + payload


def _midi_track(events: list[tuple[int, int, bytes]]) -> bytes:
    events = sorted(events, key=lambda e: (e[0], e[1]))
    last_tick = 0
    body = bytearray()
    for tick, _, payload in events:
        delta = tick - last_tick
        body.extend(_vlq(delta))
        body.extend(payload)
        last_tick = tick
    body.extend(b"\\x00\\xff\\x2f\\x00")
    return b"MTrk" + struct.pack(">I", len(body)) + body


def write_midi(plan: PerformancePlan, path: Path, ticks_per_beat: int = 480) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tempo = int(60_000_000 / max(1, plan.bpm))

    conductor = [
        (0, 0, b"\\xff\\x51\\x03" + tempo.to_bytes(3, "big")),
        (0, 0, b"\\xff\\x58\\x04\\x04\\x02\\x18\\x08"),
        (0, 0, b"\\xff\\x59\\x02\\x00\\x00"),
    ]

    lead: list[tuple[int, int, bytes]] = []
    drum: list[tuple[int, int, bytes]] = []

    for note in plan.notes:
        start = int((note.bar * 4 + note.beat) * ticks_per_beat)
        end = start + int(note.duration * ticks_per_beat)
        lead.append((start, 1, bytes((0x90, note.midi & 0x7F, note.velocity & 0x7F))))
        lead.append((end, 0, bytes((0x80, note.midi & 0x7F, 0))))

    for hit in plan.percussion:
        start = int((hit.bar * 4 + hit.beat) * ticks_per_beat)
        end = start + max(30, int(0.20 * ticks_per_beat))
        drum.append((start, 1, bytes((0x99, hit.drum & 0x7F, hit.velocity & 0x7F))))
        drum.append((end, 0, bytes((0x89, hit.drum & 0x7F, 0))))

    tracks = [_midi_track(conductor), _midi_track(lead), _midi_track(drum)]
    header = b"MThd" + struct.pack(">IHHH", 6, 1, len(tracks), ticks_per_beat)
    path.write_bytes(header + b"".join(tracks))
    return path


def write_plan(plan: PerformancePlan, json_path: Path, midi_path: Path | None = None) -> dict[str, str]:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(plan)
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    result = {"json": str(json_path)}
    if midi_path:
        result["midi"] = str(write_midi(plan, midi_path))
    return result
