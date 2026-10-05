#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from evez_machine_voice.hermes_audio.conductor import advance_conductor, state_from_dict, write_conductor_step
from evez_machine_voice.hermes_audio.session_ledger import append_record, read_records


def main() -> int:
    parser = argparse.ArgumentParser(description="Advance a persistent Hermes conversation soundtrack session.")
    parser.add_argument("response")
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--session-dir", default="data/hermes/sessions")
    parser.add_argument("--duration", type=int, default=30)
    parser.add_argument("--energy", type=float, default=0.55)
    parser.add_argument("--surrealism", type=float, default=0.70)
    parser.add_argument("--theme")
    parser.add_argument("--performance-kind", choices=["vocaloid", "cinematic", "rap", "beatbox", "rasp", "sustain"])
    parser.add_argument("--seed", type=int)
    args = parser.parse_args()

    session_dir = Path(args.session_dir).expanduser() / args.session_id
    records = read_records(session_dir)
    previous_state = None

    if records:
        state_path = session_dir / f"turn-{records[-1].turn_index:04d}-state.json"
        previous_state = state_from_dict(json.loads(state_path.read_text(encoding="utf-8")))

    step = advance_conductor(
        args.response,
        session_id=args.session_id,
        previous_state=previous_state,
        duration_seconds=args.duration,
        energy=args.energy,
        surrealism=args.surrealism,
        explicit_theme=args.theme,
        performance_kind=args.performance_kind,
        seed=args.seed,
    )
    paths = write_conductor_step(step, session_dir)

    record = append_record(
        session_dir,
        session_id=args.session_id,
        turn_index=step.state.turn_index,
        state_sha256=step.state.state_sha256,
        scene_sha256=step.scene.scene_sha256,
        plan_sha256=step.performance_plan.plan_sha256,
        source_sha256=step.performance_plan.source_sha256,
        events=step.events,
    )

    print(json.dumps({
        "session_id": args.session_id,
        "turn_index": step.state.turn_index,
        "state_sha256": step.state.state_sha256,
        "events": list(step.events),
        "theme": step.state.theme,
        "bpm": step.state.bpm,
        "key": step.state.key,
        "scale": step.state.scale,
        "motif_id": step.state.motif.motif_id,
        "scene_sha256": step.scene.scene_sha256,
        "plan_sha256": step.performance_plan.plan_sha256,
        "session_record_sha256": record.record_sha256,
        "artifacts": paths,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
