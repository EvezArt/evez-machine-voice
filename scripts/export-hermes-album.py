#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from evez_machine_voice.hermes_audio.album import export_album


def main() -> int:
    parser = argparse.ArgumentParser(description="Export a Hermes conversation session as a provenance-aware album bundle.")
    parser.add_argument("session_dir")
    parser.add_argument("--output-dir")
    args = parser.parse_args()

    session_dir = Path(args.session_dir).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else session_dir / "album"
    result = export_album(session_dir, output_dir)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
