#!/usr/bin/env python3

from pathlib import Path
import argparse

from evez_machine_voice.hermes_audio.music_memory import scan_library, save_index


def main():
    parser = argparse.ArgumentParser(description="Build a local EVEZ musical fingerprint index.")
    parser.add_argument("library", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    tracks = scan_library(args.library.expanduser().resolve())
    save_index(tracks, args.output.expanduser().resolve())
    print(f"indexed {len(tracks)} tracks -> {args.output}")


if __name__ == "__main__":
    main()
