from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any

from .performance import PerformanceKind
from .score_compiler import PerformancePlan, compile_performance
from .scene_director import HermesScene, direct_scene
from .theme import THEMES, Theme, select_theme


SEMANTIC_EVENTS = (
    "REVEAL",
    "CONTRADICTION",
    "DANGER",
    "HUMOR",
    "QUESTION",
    "REFLECTION",
    "TECHNICAL",
    "RESOLUTION",
    "UNCANNY",
)


@dataclass(frozen=True)
class Motif:
    motif_id: str
    intervals: tuple[int, ...]
    source_sha256: str
    parent_motif_id: str | None
    variation_index: int


@dataclass(frozen=True)
class ConductorState:
    version: str
    session_id: str
    turn_index: int
    state_sha256: str
    previous_state_sha256: str | None
    theme: str
    bpm: int
    key: str
    scale: str
    tension: float
    density: float
    brightness: float
    surrealism: float
    motif: Motif
    last_performance_kind: str
    cumulative_seconds: int


@dataclass(frozen=True)
class ConductorStep:
    state: ConductorState
    events: tuple[str, ...]
    scene: HermesScene
    performance_plan: PerformancePlan
    rationale: dict[str, Any]


def _hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def semantic_events(text: str) -> tuple[str, ...]:
    lower = text.lower()
    rules = (
        ("REVEAL", ("found", "discover", "revealed", "turns out", "actually", "evidence shows", "proof")),
        ("CONTRADICTION", ("contradiction", "however", "but ", "yet ", "conflict", "inconsistent")),
        ("DANGER", ("danger", "attack", "breach", "urgent", "threat", "risk", "failure", "warning")),
        ("HUMOR", ("lol", "lmao", "haha", "joke", "funny", "absurd", "shitpost")),
        ("QUESTION", ("?", "why ", "how ", "what ", "who ", "where ", "when ")),
        ("REFLECTION", ("remember", "memory", "grief", "reflect", "history", "past", "meaning")),
        ("TECHNICAL", ("code", "system", "architecture", "deploy", "runtime", "api", "database", "build", "engine")),
        ("RESOLUTION", ("resolved", "confirmed", "verified", "done", "shipped", "complete", "fixed")),
        ("UNCANNY", ("surreal", "dream", "strange", "impossible", "liminal", "alien", "uncanny", "reality")),
    )
    found: list[str] = []
    for event, needles in rules:
        if any(needle in lower for needle in needles):
            found.append(event)
    return tuple(found[:6])


def _event_delta(events: tuple[str, ...]) -> tuple[float, float, float, float]:
    tension = density = brightness = surrealism = 0.0
    for event in events:
        if event == "REVEAL":
            tension += 0.16
            density += 0.08
            brightness += 0.08
        elif event == "CONTRADICTION":
            tension += 0.13
            density += 0.04
        elif event == "DANGER":
            tension += 0.22
            density += 0.12
        elif event == "HUMOR":
            tension -= 0.10
            brightness += 0.10
        elif event == "QUESTION":
            tension += 0.04
            density += 0.03
        elif event == "REFLECTION":
            tension -= 0.12
            density -= 0.05
            brightness -= 0.08
        elif event == "TECHNICAL":
            density += 0.07
            brightness += 0.03
        elif event == "RESOLUTION":
            tension -= 0.22
            density -= 0.10
            brightness += 0.05
        elif event == "UNCANNY":
            tension += 0.08
            surrealism += 0.16
    return tension, density, brightness, surrealism


def _clamp(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 4)


def _choose_theme(text: str, previous: ConductorState | None) -> Theme:
    fresh = select_theme(text)
    if previous is None:
        return fresh
    prev = THEMES.get(previous.theme, fresh)
    event_set = set(semantic_events(text))
    if "DANGER" in event_set or "REVEAL" in event_set or "UNCANNY" in event_set:
        return fresh
    return prev


def _key_for_seed(seed: int, current_key: str | None) -> str:
    keys = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
    if current_key in keys:
        return current_key
    return keys[seed % len(keys)]


def _motif(
    source_sha256: str,
    *,
    previous: ConductorState | None,
    variation_index: int,
) -> Motif:
    parent = previous.motif if previous else None
    basis = f"{source_sha256}:{parent.motif_id if parent else 'ROOT'}:{variation_index}"
    digest = hashlib.sha256(basis.encode("utf-8")).digest()

    if parent:
        intervals = list(parent.intervals)
        slot = digest[0] % len(intervals)
        delta = (digest[1] % 3) - 1
        intervals[slot] = max(-4, min(4, intervals[slot] + delta))
        variation = tuple(intervals)
        parent_id = parent.motif_id
    else:
        choices = (-3, -2, -1, 0, 1, 2, 3)
        variation = tuple(choices[digest[i] % len(choices)] for i in range(4))
        parent_id = None

    motif_id = hashlib.sha256(
        json.dumps(
            {
                "intervals": variation,
                "source_sha256": source_sha256,
                "parent_motif_id": parent_id,
                "variation_index": variation_index,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()[:16]

    return Motif(
        motif_id=motif_id,
        intervals=variation,
        source_sha256=source_sha256,
        parent_motif_id=parent_id,
        variation_index=variation_index,
    )


def advance_conductor(
    response_text: str,
    *,
    session_id: str,
    previous_state: ConductorState | None = None,
    duration_seconds: int = 30,
    energy: float = 0.55,
    surrealism: float = 0.70,
    explicit_theme: str | None = None,
    performance_kind: PerformanceKind | None = None,
    seed: int | None = None,
) -> ConductorStep:
    source_sha256 = hashlib.sha256(response_text.encode("utf-8")).hexdigest()
    events = semantic_events(response_text)
    theme = THEMES[explicit_theme] if explicit_theme in THEMES else _choose_theme(response_text, previous_state)

    base_tension = previous_state.tension if previous_state else energy
    base_density = previous_state.density if previous_state else 0.42
    base_brightness = previous_state.brightness if previous_state else 0.52
    base_surrealism = previous_state.surrealism if previous_state else surrealism

    dt, dd, db, ds = _event_delta(events)
    tension = _clamp(base_tension * 0.72 + energy * 0.18 + dt * 0.55)
    density = _clamp(base_density * 0.78 + dd * 0.60)
    brightness = _clamp(base_brightness * 0.82 + db * 0.70)
    surreal = _clamp(base_surrealism * 0.82 + surrealism * 0.18 + ds * 0.45)

    seed_base = seed if seed is not None else int(source_sha256[:8], 16)
    key = _key_for_seed(seed_base, previous_state.key if previous_state else None)
    scale = previous_state.scale if previous_state else theme.mode

    # Major semantic turns may change the harmonic color while preserving the key.
    if {"REVEAL", "RESOLUTION"} & set(events):
        scale = theme.mode

    bpm = int(max(40, min(200, theme.bpm + round((tension - 0.5) * 28))))
    kind = performance_kind

    performance_plan = compile_performance(
        response_text,
        kind=kind,
        explicit_theme=theme.name,
        bpm=bpm,
        seed=seed_base,
        key=key,
        scale=scale,
    )

    if kind is None:
        kind = performance_plan.performance_kind

    scene = direct_scene(
        response_text,
        duration_seconds=duration_seconds,
        energy=energy,
        surrealism=surreal,
        explicit_theme=theme.name,
        performance_kind=kind,
        seed=seed_base,
        key=performance_plan.key,
        scale=performance_plan.scale,
    )

    motif = _motif(
        source_sha256,
        previous=previous_state,
        variation_index=(previous_state.turn_index + 1) if previous_state else 0,
    )
    turn_index = (previous_state.turn_index + 1) if previous_state else 0
    previous_hash = previous_state.state_sha256 if previous_state else None
    cumulative = (previous_state.cumulative_seconds if previous_state else 0) + duration_seconds

    canonical = {
        "version": "evez-hermes-conductor/v1",
        "session_id": session_id,
        "turn_index": turn_index,
        "previous_state_sha256": previous_hash,
        "theme": theme.name,
        "bpm": bpm,
        "key": performance_plan.key,
        "scale": performance_plan.scale,
        "tension": tension,
        "density": density,
        "brightness": brightness,
        "surrealism": surreal,
        "motif": asdict(motif),
        "last_performance_kind": kind,
        "cumulative_seconds": cumulative,
        "source_sha256": source_sha256,
    }
    state_hash = _hash(canonical)

    state = ConductorState(
        version="evez-hermes-conductor/v1",
        session_id=session_id,
        turn_index=turn_index,
        state_sha256=state_hash,
        previous_state_sha256=previous_hash,
        theme=theme.name,
        bpm=bpm,
        key=performance_plan.key,
        scale=performance_plan.scale,
        tension=tension,
        density=density,
        brightness=brightness,
        surrealism=surreal,
        motif=motif,
        last_performance_kind=kind,
        cumulative_seconds=cumulative,
    )

    rationale = {
        "events": list(events),
        "theme_reason": "explicit" if explicit_theme in THEMES else ("continuity" if previous_state else "semantic"),
        "continuity": {
            "preserved_key": previous_state.key if previous_state else None,
            "preserved_motif": previous_state.motif.motif_id if previous_state else None,
            "previous_state_sha256": previous_hash,
        },
        "metrics": {
            "tension": tension,
            "density": density,
            "brightness": brightness,
            "surrealism": surreal,
        },
    }

    return ConductorStep(state, events, scene, performance_plan, rationale)


def state_from_dict(payload: dict[str, Any]) -> ConductorState:
    motif = payload["motif"]
    return ConductorState(
        version=payload["version"],
        session_id=payload["session_id"],
        turn_index=int(payload["turn_index"]),
        state_sha256=payload["state_sha256"],
        previous_state_sha256=payload.get("previous_state_sha256"),
        theme=payload["theme"],
        bpm=int(payload["bpm"]),
        key=payload["key"],
        scale=payload["scale"],
        tension=float(payload["tension"]),
        density=float(payload["density"]),
        brightness=float(payload["brightness"]),
        surrealism=float(payload["surrealism"]),
        motif=Motif(
            motif_id=motif["motif_id"],
            intervals=tuple(int(x) for x in motif["intervals"]),
            source_sha256=motif["source_sha256"],
            parent_motif_id=motif.get("parent_motif_id"),
            variation_index=int(motif["variation_index"]),
        ),
        last_performance_kind=payload["last_performance_kind"],
        cumulative_seconds=int(payload["cumulative_seconds"]),
    )


def write_conductor_step(step: ConductorStep, directory) -> dict[str, str]:
    directory.mkdir(parents=True, exist_ok=True)
    state_path = directory / f"turn-{step.state.turn_index:04d}-state.json"
    scene_path = directory / f"turn-{step.state.turn_index:04d}-scene.json"
    plan_path = directory / f"turn-{step.state.turn_index:04d}-plan.json"
    summary_path = directory / f"turn-{step.state.turn_index:04d}.json"

    state_path.write_text(json.dumps(asdict(step.state), indent=2, sort_keys=True), encoding="utf-8")
    scene_path.write_text(json.dumps(asdict(step.scene), indent=2, sort_keys=True), encoding="utf-8")
    plan_path.write_text(json.dumps(asdict(step.performance_plan), indent=2, sort_keys=True), encoding="utf-8")
    summary_path.write_text(
        json.dumps(
            {
                "version": "evez-hermes-conductor-step/v1",
                "state": asdict(step.state),
                "events": list(step.events),
                "scene_sha256": step.scene.scene_sha256,
                "plan_sha256": step.performance_plan.plan_sha256,
                "rationale": step.rationale,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    return {
        "state": str(state_path),
        "scene": str(scene_path),
        "plan": str(plan_path),
        "summary": str(summary_path),
    }
