from __future__ import annotations
import os
import subprocess
from pathlib import Path
from .config import SETTINGS
from .theme import musical_prompt, select_theme, Theme

class MusicEngine:
    def compose(self, response_text: str, theme_name: str | None = None, duration: int = 20, energy: float = 0.55, surrealism: float = 0.70, source_audio: str | None = None, rights_asserted: bool = False) -> tuple[Path, Theme]:
        if source_audio and not rights_asserted:
            raise PermissionError("Source remix mode requires explicit rights_asserted=true")
        theme = select_theme(response_text, theme_name)
        prompt = musical_prompt(theme, response_text, energy, surrealism)
        out = SETTINGS.output_dir / f"score-{theme.name}-{os.getpid()}.wav"
        # ACE-Step command-line flags can differ across releases. Keep the adapter isolated.
        cmd = [SETTINGS.ace_step_cmd, "--prompt", prompt, "--duration", str(duration), "--output", str(out)]
        if source_audio:
            cmd += ["--source_audio", source_audio]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(result.stderr[-5000:] or "ACE-Step failed")
        if not out.exists():
            raise RuntimeError("ACE-Step returned success but no output file was created")
        return out, theme
