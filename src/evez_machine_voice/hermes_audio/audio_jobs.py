from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from .audio_state import AudioState


@dataclass(frozen=True)
class AudioJob:
    version: str
    job_id: str
    state: AudioState
    created_at: str
    updated_at: str
    guide_audio: str
    performance_kind: str
    output_name: str
    output_path: str | None = None
    manifest_path: str | None = None
    sha256: str | None = None
    error: str | None = None


class AudioJobStore:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, job_id: str) -> Path:
        return self.root / f"{job_id}.json"

    def create(self, *, guide_audio: str, performance_kind: str, output_name: str) -> AudioJob:
        now = datetime.now(timezone.utc).isoformat()
        job = AudioJob(
            version="evez-hermes-audio-job/v1",
            job_id=uuid.uuid4().hex,
            state=AudioState.PLANNED,
            created_at=now,
            updated_at=now,
            guide_audio=guide_audio,
            performance_kind=performance_kind,
            output_name=output_name,
        )
        self.save(job)
        return job

    def get(self, job_id: str) -> AudioJob:
        payload = json.loads(self._path(job_id).read_text(encoding="utf-8"))
        return AudioJob(
            version=payload["version"],
            job_id=payload["job_id"],
            state=AudioState(payload["state"]),
            created_at=payload["created_at"],
            updated_at=payload["updated_at"],
            guide_audio=payload["guide_audio"],
            performance_kind=payload["performance_kind"],
            output_name=payload["output_name"],
            output_path=payload.get("output_path"),
            manifest_path=payload.get("manifest_path"),
            sha256=payload.get("sha256"),
            error=payload.get("error"),
        )

    def save(self, job: AudioJob) -> AudioJob:
        target = self._path(job.job_id)
        temp = target.with_suffix(".tmp")
        temp.write_text(json.dumps(asdict(job), indent=2, sort_keys=True), encoding="utf-8")
        temp.replace(target)
        return job

    def update(self, job: AudioJob, state: AudioState, **changes) -> AudioJob:
        updated = AudioJob(
            version=job.version,
            job_id=job.job_id,
            state=state,
            created_at=job.created_at,
            updated_at=datetime.now(timezone.utc).isoformat(),
            guide_audio=job.guide_audio,
            performance_kind=job.performance_kind,
            output_name=job.output_name,
            output_path=changes.get("output_path", job.output_path),
            manifest_path=changes.get("manifest_path", job.manifest_path),
            sha256=changes.get("sha256", job.sha256),
            error=changes.get("error"),
        )
        return self.save(updated)

    def payload(self, job: AudioJob) -> dict:
        result = asdict(job)
        result["state"] = job.state.value
        return result
