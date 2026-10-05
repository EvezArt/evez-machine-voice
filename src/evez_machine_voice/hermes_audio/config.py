import os
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Settings:
    voice_dir: Path = Path(os.getenv("EVEZ_HERMES_VOICE_DIR", "./data/hermes/voices"))
    output_dir: Path = Path(os.getenv("EVEZ_HERMES_OUTPUT_DIR", "./data/hermes/output"))
    f5tts_bin: str = os.getenv("EVEZ_F5TTS_BIN", "f5-tts_infer-cli")
    ace_step_cmd: str = os.getenv("EVEZ_ACE_STEP_CMD", "acestep")
    token: str | None = os.getenv("EVEZ_HERMES_AUDIO_TOKEN")
    default_voice: str = os.getenv("EVEZ_HERMES_VOICE", "steven")

SETTINGS = Settings()
SETTINGS.voice_dir.mkdir(parents=True, exist_ok=True)
SETTINGS.output_dir.mkdir(parents=True, exist_ok=True)
