from __future__ import annotations

import json
import os
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests


class ACEStepAPIError(RuntimeError):
    pass


class ACEStepClient:
    """Client for the documented ACE-Step 1.5 local HTTP API."""

    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        self.base_url = (base_url or os.getenv("EVEZ_ACESTEP_URL", "http://127.0.0.1:8001")).rstrip("/") + "/"
        self.api_key = api_key or os.getenv("ACESTEP_API_KEY")
        self.timeout = float(os.getenv("EVEZ_ACESTEP_TIMEOUT", "30"))
        self.poll_seconds = float(os.getenv("EVEZ_ACESTEP_POLL_SECONDS", "2"))

    def _headers(self) -> dict[str, str]:
        if self.api_key:
            return {"Authorization": f"Bearer {self.api_key}"}
        return {}

    def submit(
        self,
        *,
        prompt: str,
        lyrics: str = "",
        bpm: int | None = None,
        key_scale: str = "",
        duration: float = 20,
        model: str | None = None,
        reference_audio: Path | None = None,
        thinking: bool = True,
        seed: int | None = None,
    ) -> str:
        payload = {
            "prompt": prompt,
            "lyrics": lyrics,
            "thinking": thinking,
            "audio_format": "wav",
            "audio_duration": duration,
            "key_scale": key_scale,
        }
        if bpm is not None:
            payload["bpm"] = int(bpm)
        if model:
            payload["model"] = model
        if seed is not None:
            payload["use_random_seed"] = False
            payload["seed"] = int(seed)

        if reference_audio:
            with reference_audio.open("rb") as fh:
                files = {"reference_audio": (reference_audio.name, fh, "audio/wav")}
                response = requests.post(
                    urljoin(self.base_url, "release_task"),
                    data={str(k): str(v) for k, v in payload.items()},
                    files=files,
                    headers=self._headers(),
                    timeout=self.timeout,
                )
        else:
            response = requests.post(
                urljoin(self.base_url, "release_task"),
                json=payload,
                headers=self._headers(),
                timeout=self.timeout,
            )

        response.raise_for_status()
        body = response.json()
        if body.get("code") != 200 or not body.get("data", {}).get("task_id"):
            raise ACEStepAPIError(json.dumps(body))
        return str(body["data"]["task_id"])

    def wait_for_audio(self, task_id: str, output: Path, timeout: float = 900) -> Path:
        deadline = time.monotonic() + timeout
        output.parent.mkdir(parents=True, exist_ok=True)

        while time.monotonic() < deadline:
            response = requests.post(
                urljoin(self.base_url, "query_result"),
                json={"task_id_list": [task_id]},
                headers=self._headers(),
                timeout=self.timeout,
            )
            response.raise_for_status()
            body = response.json()
            rows = body.get("data") or []
            if rows:
                row = rows[0]
                status = int(row.get("status", 0))
                if status == 2:
                    raise ACEStepAPIError(str(row))
                if status == 1:
                    result = json.loads(row.get("result") or "[]")
                    if not result:
                        raise ACEStepAPIError("ACE-Step succeeded with no result metadata")
                    audio_path = result[0].get("file")
                    if not audio_path:
                        raise ACEStepAPIError("ACE-Step result has no file path")
                    parsed = urlparse(audio_path)
                    if parsed.scheme in {"http", "https"}:
                        audio_url = audio_path
                    else:
                        audio_url = urljoin(self.base_url, audio_path.lstrip("/"))
                    audio_response = requests.get(
                        audio_url,
                        headers=self._headers(),
                        timeout=max(self.timeout, 60),
                    )
                    audio_response.raise_for_status()
                    output.write_bytes(audio_response.content)
                    return output
            time.sleep(self.poll_seconds)

        raise TimeoutError(f"ACE-Step task {task_id} did not finish before timeout")
