from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SessionRecord:
    version: str
    session_id: str
    turn_index: int
    recorded_at: str
    parent_record_sha256: str | None
    state_sha256: str
    scene_sha256: str
    plan_sha256: str
    source_sha256: str
    events: tuple[str, ...]
    audio: dict[str, Any] | None
    record_sha256: str


def _hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _ledger_path(session_dir: Path) -> Path:
    return session_dir / "session-ledger.jsonl"


def read_records(session_dir: Path) -> list[SessionRecord]:
    path = _ledger_path(session_dir)
    if not path.exists():
        return []

    records: list[SessionRecord] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        records.append(
            SessionRecord(
                version=payload["version"],
                session_id=payload["session_id"],
                turn_index=int(payload["turn_index"]),
                recorded_at=payload["recorded_at"],
                parent_record_sha256=payload.get("parent_record_sha256"),
                state_sha256=payload["state_sha256"],
                scene_sha256=payload["scene_sha256"],
                plan_sha256=payload["plan_sha256"],
                source_sha256=payload["source_sha256"],
                events=tuple(payload.get("events", [])),
                audio=payload.get("audio"),
                record_sha256=payload["record_sha256"],
            )
        )
    return records


def append_record(
    session_dir: Path,
    *,
    session_id: str,
    turn_index: int,
    state_sha256: str,
    scene_sha256: str,
    plan_sha256: str,
    source_sha256: str,
    events: tuple[str, ...],
    audio: dict[str, Any] | None = None,
    recorded_at: str | None = None,
) -> SessionRecord:
    session_dir.mkdir(parents=True, exist_ok=True)
    existing = read_records(session_dir)

    if existing and existing[-1].session_id != session_id:
        raise ValueError("session directory belongs to a different session_id")
    expected_turn = existing[-1].turn_index + 1 if existing else 0
    if turn_index != expected_turn:
        raise ValueError(f"turn index mismatch: expected {expected_turn}, got {turn_index}")

    parent = existing[-1].record_sha256 if existing else None
    timestamp = recorded_at or datetime.now(timezone.utc).isoformat()

    canonical = {
        "version": "evez-hermes-session/v1",
        "session_id": session_id,
        "turn_index": turn_index,
        "recorded_at": timestamp,
        "parent_record_sha256": parent,
        "state_sha256": state_sha256,
        "scene_sha256": scene_sha256,
        "plan_sha256": plan_sha256,
        "source_sha256": source_sha256,
        "events": list(events),
        "audio": audio,
    }
    record_sha = _hash(canonical)

    record = SessionRecord(
        version="evez-hermes-session/v1",
        session_id=session_id,
        turn_index=turn_index,
        recorded_at=timestamp,
        parent_record_sha256=parent,
        state_sha256=state_sha256,
        scene_sha256=scene_sha256,
        plan_sha256=plan_sha256,
        source_sha256=source_sha256,
        events=events,
        audio=audio,
        record_sha256=record_sha,
    )

    with _ledger_path(session_dir).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(asdict(record), sort_keys=True, separators=(",", ":")) + "\n")

    manifest = session_dir / "session-manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "version": "evez-hermes-session-manifest/v1",
                "session_id": session_id,
                "turn_count": len(existing) + 1,
                "head_record_sha256": record_sha,
                "head_state_sha256": state_sha256,
                "turns": [
                    {
                        "turn_index": r.turn_index,
                        "scene_sha256": r.scene_sha256,
                        "plan_sha256": r.plan_sha256,
                        "state_sha256": r.state_sha256,
                        "record_sha256": r.record_sha256,
                    }
                    for r in [*existing, record]
                ],
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    return record


def verify_chain(session_dir: Path) -> dict[str, Any]:
    records = read_records(session_dir)
    problems: list[str] = []

    expected_parent: str | None = None
    for index, record in enumerate(records):
        if record.turn_index != index:
            problems.append(f"turn index {record.turn_index} at position {index}")
        if record.parent_record_sha256 != expected_parent:
            problems.append(
                f"turn {record.turn_index}: parent {record.parent_record_sha256!r} != {expected_parent!r}"
            )

        canonical = {
            "version": record.version,
            "session_id": record.session_id,
            "turn_index": record.turn_index,
            "recorded_at": record.recorded_at,
            "parent_record_sha256": record.parent_record_sha256,
            "state_sha256": record.state_sha256,
            "scene_sha256": record.scene_sha256,
            "plan_sha256": record.plan_sha256,
            "source_sha256": record.source_sha256,
            "events": list(record.events),
            "audio": record.audio,
        }
        if _hash(canonical) != record.record_sha256:
            problems.append(f"turn {record.turn_index}: record hash mismatch")

        expected_parent = record.record_sha256

    return {
        "ok": not problems,
        "turn_count": len(records),
        "head_record_sha256": records[-1].record_sha256 if records else None,
        "problems": problems,
    }
