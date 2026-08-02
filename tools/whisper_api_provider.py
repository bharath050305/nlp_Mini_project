"""
tools/whisper_api_provider.py

Speech-to-text via OpenAI's hosted Whisper API — lighter than the local
model (no torch/ffmpeg-heavy local install), opt-in via
STT_PROVIDER=openai_whisper_api, reusing the same openai_api_key already
used by llm/openai_provider.py.
"""

from __future__ import annotations

from pathlib import Path

from tools.speech_to_text import SpeechToTextProvider
from utils.exceptions import TranscriptionError
from utils.logger import get_logger

logger = get_logger(__name__)


class WhisperAPIProvider(SpeechToTextProvider):
    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise TranscriptionError(
                "STT_PROVIDER=openai_whisper_api but OPENAI_API_KEY is empty. "
                "Set it in .env, or switch STT_PROVIDER back to 'whisper_local'."
            )
        try:
            from openai import OpenAI  # local import: optional dependency
        except ImportError as exc:
            raise TranscriptionError(
                "The 'openai' package isn't installed. Run: pip install -r requirements-llm.txt"
            ) from exc

        self._client = OpenAI(api_key=api_key)

    @property
    def name(self) -> str:
        return "openai_whisper_api:whisper-1"

    def transcribe(self, audio_path: str | Path) -> str:
        path = Path(audio_path)
        if not path.exists():
            raise TranscriptionError(f"Audio file not found: {path}")

        try:
            with open(path, "rb") as audio_file:
                response = self._client.audio.transcriptions.create(model="whisper-1", file=audio_file)
        except Exception as exc:
            raise TranscriptionError(f"OpenAI Whisper API call failed for {path.name}: {exc}") from exc

        text = (response.text or "").strip()
        if not text:
            raise TranscriptionError(f"Whisper API produced no text for {path.name}.")
        logger.info("Transcribed %s via OpenAI Whisper API: %d characters", path.name, len(text))
        return text
