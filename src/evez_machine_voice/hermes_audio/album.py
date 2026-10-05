from __future__ import annotations

import json
import zipfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .session_ledger import read_records, verify_chain


def export_album(session_dir: Path, output_dir: Path) -> dict[str, str | int | bool]:
    session_dir = session_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    records = read_records(session_dir)
    verification = verify_chain(session_dir)
    album_id = records[-1].session_id if records else session_dir.name

    tracks: list[dict[str, Any]] = []
    for record in records:
        turn = session_dir / f"turn-{record.turn_index:04d}"
        track = {
            "track_number": record.turn_index + 1,
            "title": f"Turn {record.turn_index + 1:02d}",
            "turn_index": record.turn_index,
            "scene_sha256": record.scene_sha256,
            "plan_sha256": record.plan_sha256,
            "state_sha256": record.state_sha256,
            "source_sha256": record.source_sha256,
            "events": list(record.events),
            "audio": record.audio,
            "control_artifacts": {
                "summary": str(session_dir / f"turn-{record.turn_index:04d}.json"),
                "scene": str(session_dir / f"turn-{record.turn_index:04d}-scene.json"),
                "plan": str(session_dir / f"turn-{record.turn_index:04d}-plan.json"),
                "state": str(session_dir / f"turn-{record.turn_index:04d}-state.json"),
            },
        }
        if record.audio and record.audio.get("path"):
            audio_path = Path(str(record.audio["path"]))
            track["audio_exists"] = audio_path.exists()
        else:
            track["audio_exists"] = False
        tracks.append(track)

    album = {
        "version": "evez-hermes-album/v1",
        "album_id": album_id,
        "control_only": not any(t["audio_exists"] for t in tracks),
        "verification": verification,
        "track_count": len(tracks),
        "tracks": tracks,
    }

    album_json = output_dir / f"{album_id}-album.json"
    album_json.write_text(json.dumps(album, indent=2, sort_keys=True), encoding="utf-8")

    manifest_path = output_dir / f"{album_id}-album-manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "version": "evez-hermes-album-manifest/v1",
                "album_id": album_id,
                "source_session_dir": str(session_dir),
                "verification": verification,
                "tracks": [
                    {
                        "track_number": t["track_number"],
                        "title": t["title"],
                        "scene_sha256": t["scene_sha256"],
                        "plan_sha256": t["plan_sha256"],
                        "state_sha256": t["state_sha256"],
                    }
                    for t in tracks
                ],
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    zip_path = output_dir / f"{album_id}-album.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in session_dir.glob("turn-*.json"):
            archive.write(path, arcname=path.name)
        ledger = session_dir / "session-ledger.jsonl"
        if ledger.exists():
            archive.write(ledger, arcname=ledger.name)
        session_manifest = session_dir / "session-manifest.json"
        if session_manifest.exists():
            archive.write(session_manifest, arcname=session_manifest.name)
        archive.writestr("ALBUM.json", json.dumps(album, indent=2, sort_keys=True))

    return {
        "album_id": album_id,
        "track_count": len(tracks),
        "control_only": bool(album["control_only"]),
        "verified": bool(verification["ok"]),
        "json": str(album_json),
        "manifest": str(manifest_path),
        "zip": str(zip_path),
    }
