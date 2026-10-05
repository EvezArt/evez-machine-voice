from __future__ import annotations
import subprocess
from pathlib import Path

def mix(voice: Path, score: Path, output: Path, music_db: float = -18.0) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-i", str(voice), "-i", str(score),
        "-filter_complex",
        f"[1:a]volume={music_db}dB,aloop=loop=-1:size=2000000000[bg];[0:a][bg]amix=inputs=2:duration=first:dropout_transition=2, loudnorm=I=-15:TP=-1.5:LRA=11[out]",
        "-map", "[out]", "-ar", "48000", "-ac", "2", str(output),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-5000:])
    return output
