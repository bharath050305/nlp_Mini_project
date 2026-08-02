"""
tools/speech_to_text.py

Abstract speech-to-text interface + factory, mirroring `llm/base.py` and
`llm/__init__.py`'s pluggable-provider pattern exactly: the transcript
agent depends only on `SpeechToTextProvider`, never a concrete backend,
so swapping local Whisper for the OpenAI Whisper API is a `.env` change.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class SpeechToTextProvider(ABC):
    """Minimal transcription interface used by agents/transcript_agent.py."""

    @abstractmethod
    def transcribe(self, audio_path: str | Path) -> str:
        """Return the full transcript text for the given audio file."""
        raise NotImplementedError

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError


@lru_cache(maxsize=1)
def get_stt_provider() -> SpeechToTextProvider:
    provider = settings.stt_provider

    if provider == "whisper_local":
        from tools.whisper_local_provider import WhisperLocalProvider

        instance: SpeechToTextProvider = WhisperLocalProvider(settings.whisper_model_size)
    elif provider == "openai_whisper_api":
        from tools.whisper_api_provider import WhisperAPIProvider

        instance = WhisperAPIProvider(settings.openai_api_key or "")
    else:  # pragma: no cover - pydantic Literal already restricts this
        raise ValueError(f"Unknown STT_PROVIDER: {provider}")

    logger.info("Speech-to-text provider initialized: %s", instance.name)
    return instance
