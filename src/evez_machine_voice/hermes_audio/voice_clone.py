from __future__ import annotations
import os
import subprocess
from pathlib import Path
from .config import SETTINGS

class VoiceClone:
    """Zero-shot reference-conditioned synthesis for the owner's voice."""
    def reference(self, voice_id: str) -> Path:
        path = SETTINGS.voice_dir / voice_id / "reference.wav"
        if not path.exists():
            raise FileNotFoundError(f"Missing private voice reference: {path}")
        return path

    def speak(self, text: str, voice_id: str = "steven", style: str = "neutral", ref_text: str | None = None) -> Path:
        ref = self.reference(voice_id)
        out = SETTINGS.output_dir / f"voice-{voice_id}-{os.getpid()}.wav"
        styled = text if style == "neutral" else f"{style}. {text}"
        cmd = [
            SETTINGS.f5tts_bin, "--model", "F5TTS_v1_Base",
            "--ref_audio", str(ref), "--ref_text", ref_text or "",
            "--gen_text", styled,
            "--output_dir", str(SETTINGS.output_dir), "--output_file", out.name,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(result.stderr[-5000:] or "F5-TTS failed")
        if not out.exists():
            raise RuntimeError("F5-TTS returned success but no output file was created")
        return out
