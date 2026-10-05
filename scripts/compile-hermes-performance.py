#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path

from evez_machine_voice.hermes_audio.score_compiler import (
    compile_performance,
    write_plan,
)


def main():
    parser = argparse.ArgumentParser(description="Compile an EVEZ/Hermes response into a reproducible performance plan.")
    parser.add_argument("text")
    parser.add_argument("--kind", choices=["vocaloid", "cinematic", "rap", "beatbox", "rasp", "sustain"])
    parser.add_argument("--theme")
    parser.add_argument("--bpm", type=int)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--json", type=Path, default=Path("data/hermes/performance-plan.json"))
    parser.add_argument("--midi", type=Path, default=Path("data/hermes/performance-plan.mid"))
    args = parser.parse_args()

    plan = compile_performance(
        args.text,
        kind=args.kind,
        explicit_theme=args.theme,
        bpm=args.bpm,
        seed=args.seed,
    )
    outputs = write_plan(plan, args.json, args.midi)

    print("Hermes performance plan")
    print("  plan:", plan.plan_sha256)
    print("  kind:", plan.performance_kind)
    print("  theme:", plan.theme)
    print("  tempo:", plan.bpm)
    print("  key:", plan.key, plan.scale)
    print("  sections:", ", ".join(s["name"] for s in plan.sections))
    print("  JSON:", outputs["json"])
    print("  MIDI:", outputs["midi"])


if __name__ == "__main__":
    main()
