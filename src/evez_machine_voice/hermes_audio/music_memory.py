from __future__ import annotations

import hashlib
import json
import math
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

try:
    import librosa
except ImportError:  # pragma: no cover
    librosa = None


@dataclass(frozen=True)
class TrackFingerprint:
    path: str
    sha256: str
    duration_seconds: float
    bpm: float | None
    key: str | None
    mode: str | None
    rms_db: float | None
    spectral_centroid_hz: float | None
    spectral_bandwidth_hz: float | None
    zero_crossing_rate: float | None
    pulse_density: float | None


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def _ffprobe_duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


def _nearest_pitch_name(value: float) -> str:
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    return names[int(round(value)) % 12]


def estimate_key(y, sr: int) -> tuple[str | None, str | None]:
    if librosa is None:
        return None, None

    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    if chroma.size == 0:
        return None, None

    major = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
    minor = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]

    scores = []
    vector = chroma.mean(axis=1)
    for tonic in range(12):
        maj = sum(vector[(i + tonic) % 12] * major[i] for i in range(12))
        min_ = sum(vector[(i + tonic) % 12] * minor[i] for i in range(12))
        scores.append((maj, _nearest_pitch_name(tonic), "major"))
        scores.append((min_, _nearest_pitch_name(tonic), "minor"))

    _, key, mode = max(scores, key=lambda item: item[0])
    return key, mode


def fingerprint(path: Path) -> TrackFingerprint:
    if librosa is None:
        raise RuntimeError("Install the optional audio dependencies with: pip install -e '.[audio]'")

    y, sr = librosa.load(path, sr=None, mono=True)
    duration = float(len(y) / sr) if len(y) else _ffprobe_duration(path)

    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    tempo_value = float(tempo[0]) if hasattr(tempo, "__len__") else float(tempo)

    rms = librosa.feature.rms(y=y)
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
    bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)
    zcr = librosa.feature.zero_crossing_rate(y)

    rms_mean = float(rms.mean())
    rms_db = 20.0 * math.log10(max(rms_mean, 1e-9))
    pulse_density = float(max(0.0, min(1.0, tempo_value / 180.0)))

    key, mode = estimate_key(y, sr)

    return TrackFingerprint(
        path=str(path),
        sha256=sha256_file(path),
        duration_seconds=round(duration, 3),
        bpm=round(tempo_value, 3) if tempo_value else None,
        key=key,
        mode=mode,
        rms_db=round(rms_db, 3),
        spectral_centroid_hz=round(float(centroid.mean()), 3),
        spectral_bandwidth_hz=round(float(bandwidth.mean()), 3),
        zero_crossing_rate=round(float(zcr.mean()), 6),
        pulse_density=round(pulse_density, 4),
    )


def scan_library(root: Path) -> list[TrackFingerprint]:
    supported = {".wav", ".flac", ".mp3", ".m4a", ".ogg", ".aac"}
    tracks = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix.lower() in supported:
            try:
                tracks.append(fingerprint(path))
            except Exception as exc:
                print(f"SKIP {path}: {exc}")
    return tracks


def save_index(tracks: list[TrackFingerprint], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "tracks": [asdict(track) for track in tracks],
    }
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_index(index_path: Path) -> list[TrackFingerprint]:
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    return [TrackFingerprint(**item) for item in payload.get("tracks", [])]


def select_palette(
    tracks: list[TrackFingerprint],
    bpm: float,
    mode: str | None,
    energy: float,
    surrealism: float,
    limit: int = 5,
) -> list[TrackFingerprint]:
    if not tracks:
        return []

    target_rms = -24.0 + (energy * 18.0)
    target_centroid = 1800.0 + (surrealism * 4200.0)

    def score(track: TrackFingerprint) -> float:
        tempo = 1.0 - min(abs((track.bpm or bpm) - bpm) / 80.0, 1.0)
        tonal = 1.0 if (mode is None or track.mode == mode) else 0.25
        loud = 1.0 - min(abs((track.rms_db or target_rms) - target_rms) / 24.0, 1.0)
        bright = 1.0 - min(abs((track.spectral_centroid_hz or target_centroid) - target_centroid) / 5000.0, 1.0)
        return 0.40 * tempo + 0.25 * tonal + 0.15 * loud + 0.20 * bright

    return sorted(tracks, key=score, reverse=True)[:limit]


def palette_prompt(tracks: list[TrackFingerprint]) -> str:
    if not tracks:
        return "original cinematic palette with no external musical fingerprint"

    fragments = []
    for track in tracks:
        fragments.append(
            f"BPM {track.bpm or 'unknown'}, {track.key or 'unknown'} {track.mode or ''}, "
            f"brightness {track.spectral_centroid_hz or 'unknown'}Hz, "
            f"bandwidth {track.spectral_bandwidth_hz or 'unknown'}Hz, "
            f"pulse density {track.pulse_density or 'unknown'}"
        )
    return " | ".join(fragments)
