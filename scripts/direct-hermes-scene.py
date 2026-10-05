#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path

from evez_machine_voice.hermes_audio.scene_director import direct_scene, write_scene


def main():
    parser = argparse.ArgumentParser(description="Compile a Hermes response into a cinematic scene plan.")
    parser.add_argument("text")
    parser.add_argument("--duration", type=int, default=30)
    parser.add_argument("--energy", type=float, default=0.55)
    parser.add_argument("--surrealism", type=float, default=0.70)
    parser.add_argument("--theme")
    parser.add_argument("--kind", choices=["vocaloid", "cinematic", "rap", "beatbox", "rasp", "sustain"])
    parser.add_argument("--seed", type=int)
    parser.add_argument("--output", type=Path, default=Path("data/hermes/scene.json"))
    args = parser.parse_args()

    scene = direct_scene(
        args.text,
        duration_seconds=args.duration,
        energy=args.energy,
        surrealism=args.surrealism,
        explicit_theme=args.theme,
        performance_kind=args.kind,
        seed=args.seed,
    )
    write_scene(scene, args.output)

    print("Hermes Scene Director")
    print("  scene:", scene.scene_sha256)
    print("  theme:", scene.theme)
    print("  vocal:", scene.vocal_mode)
    print("  tempo:", scene.bpm)
    print("  key:", f"{scene.key} {scene.scale}")
    print("  duration:", scene.duration_seconds)
    print("  arc:", " -> ".join(f"{x:.2f}" for x in scene.arc))
    print("  output:", args.output)


if __name__ == "__main__":
    main()
