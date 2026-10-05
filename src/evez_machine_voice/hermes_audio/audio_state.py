from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AudioState(StrEnum):
    UNKNOWN = "UNKNOWN"
    PLANNED = "PLANNED"
    RENDERING = "RENDERING"
    PRODUCED = "PRODUCED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class AudioArtifact:
    state: AudioState
    path: str | None = None
    sha256: str | None = None
    manifest: str | None = None
    error: str | None = None


def planned() -> AudioArtifact:
    return AudioArtifact(AudioState.PLANNED)


def rendering() -> AudioArtifact:
    return AudioArtifact(AudioState.RENDERING)


def produced(path: str, sha256: str, manifest: str | None = None) -> AudioArtifact:
    return AudioArtifact(AudioState.PRODUCED, path=path, sha256=sha256, manifest=manifest)


def failed(error: str) -> AudioArtifact:
    return AudioArtifact(AudioState.FAILED, error=error)
