"""
tools/whisper_local_provider.py

Default speech-to-text backend: the pip `openai-whisper` package running
fully locally — no API key needed. Trade-off, stated plainly: this pulls
in `torch` (large) and requires a system `ffmpeg` binary pip cannot
install (see requirements-transcription.txt) — heavier than this
project's usual "runs offline out of the box" bar, but it's what was
asked for as the default so a doctor's consultation audio never has to
leave the machine.
"""

from __future__ import annotations

from pathlib import Path

from tools.speech_to_text import SpeechToTextProvider
from utils.exceptions import TranscriptionError
from utils.logger import get_logger

logger = get_logger(__name__)


class WhisperLocalProvider(SpeechToTextProvider):
    def __init__(self, model_size: str = "base") -> None:
        self._model_size = model_size
        self._model = None  # lazy-loaded on first transcribe() call

    @property
    def name(self) -> str:
        return f"whisper_local:{self._model_size}"

    def _load_model(self):
        if self._model is not None:
            return self._model
        try:
            import whisper  # local import: optional, heavy dependency
        except ImportError as exc:
            raise TranscriptionError(
                "The 'openai-whisper' package isn't installed. Run: "
                "pip install -r requirements-transcription.txt "
                "(also requires a system ffmpeg binary — see that file)."
            ) from exc

        logger.info("Loading local Whisper model '%s' (first use, may take a while)...", self._model_size)
        self._model = whisper.load_model(self._model_size)
        return self._model

    def transcribe(self, audio_path: str | Path) -> str:
        path = Path(audio_path)
        if not path.exists():
            raise TranscriptionError(f"Audio file not found: {path}")

        model = self._load_model()
        try:
            result = model.transcribe(str(path))
        except Exception as exc:
            raise TranscriptionError(
                f"Local Whisper transcription failed for {path.name}: {exc}. "
                "If this mentions ffmpeg, install it as a system binary (not via pip)."
            ) from exc

        text = (result.get("text") or "").strip()
        if not text:
            raise TranscriptionError(f"Whisper produced no text for {path.name} — check the audio isn't silent/corrupt.")
        logger.info("Transcribed %s: %d characters", path.name, len(text))
        return text
