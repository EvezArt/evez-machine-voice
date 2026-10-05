from __future__ import annotations
import hmac
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from .config import SETTINGS
from .mix import mix
from .music import MusicEngine
from .voice_clone import VoiceClone

app = FastAPI(title="EVEZ Hermes Audio", version="0.1.0")
voice = VoiceClone()
music = MusicEngine()

class HermesRequest(BaseModel):
    response_text: str = Field(min_length=1, max_length=20000)
    voice: str = "steven"
    voice_style: str = "cinematic"
    music: bool = True
    theme: str | None = None
    duration_seconds: int = Field(default=20, ge=5, le=600)
    energy: float = Field(default=0.55, ge=0, le=1)
    surrealism: float = Field(default=0.70, ge=0, le=1)
    source_audio: str | None = None
    rights_asserted: bool = False


def auth(token: str | None):
    if SETTINGS.token and not hmac.compare_digest(token or "", SETTINGS.token):
        raise HTTPException(401, "invalid audio token")

@app.get("/health")
def health():
    return {"ok": True, "service": "evez-hermes-audio", "voice": SETTINGS.default_voice}

@app.post("/v1/hermes/respond")
def respond(req: HermesRequest, x_hermes_audio_token: str | None = Header(default=None)):
    auth(x_hermes_audio_token)
    voice_path = voice.speak(req.response_text, req.voice, req.voice_style)
    if not req.music:
        return {"voice": str(voice_path), "score": None, "mix": None}
    score_path, theme = music.compose(req.response_text, req.theme, req.duration_seconds, req.energy, req.surrealism, req.source_audio, req.rights_asserted)
    mix_path = SETTINGS.output_dir / f"hermes-{theme.name}-{voice_path.stem}.wav"
    mix(voice_path, score_path, mix_path)
    return {"voice": str(voice_path), "score": str(score_path), "mix": str(mix_path), "theme": theme.name, "bpm": theme.bpm, "mode": theme.mode}

def main():
    import uvicorn
    uvicorn.run("evez_machine_voice.hermes_audio.server:app", host="0.0.0.0", port=9113)
