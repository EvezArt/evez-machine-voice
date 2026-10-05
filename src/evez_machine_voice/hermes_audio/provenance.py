from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def write_manifest(
    output_audio: Path,
    *,
    pipeline: str,
    inputs: dict[str, Any],
    models: dict[str, Any],
    params: dict[str, Any],
    rights_state: str,
    evidence_state: str = "PRODUCED",
) -> Path:
    manifest = output_audio.with_suffix(output_audio.suffix + ".manifest.json")
    payload = {
        "schema": "evez-hermes-audio-manifest/v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "pipeline": pipeline,
        "output": {
            "path": str(output_audio),
            "sha256": sha256_file(output_audio) if output_audio.exists() else None,
        },
        "inputs": inputs,
        "models": models,
        "params": params,
        "rights_state": rights_state,
        "evidence_state": evidence_state,
    }
    manifest.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return manifest
