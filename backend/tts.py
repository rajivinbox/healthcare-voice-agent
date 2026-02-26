"""Text-to-Speech using OpenAI TTS API."""
import logging
from openai import AsyncOpenAI
from config import settings

logger = logging.getLogger(__name__)
_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


async def synthesize_speech(
    text: str,
    voice: str = "nova",
    speed: float = 1.0,
) -> bytes:
    """
    Convert text to speech audio bytes using OpenAI TTS.

    Args:
        text: Text to synthesize
        voice: OpenAI voice ID — alloy | echo | fable | onyx | nova | shimmer
        speed: Speech speed multiplier (0.25–4.0)

    Returns:
        MP3 audio bytes
    """
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is not configured")

    logger.info("Synthesizing speech for text (%d chars)", len(text))

    client = _get_client()
    response = await client.audio.speech.create(
        model="tts-1",
        voice=voice,
        input=text,
        speed=speed,
        response_format="mp3",
    )

    audio_bytes = response.content
    logger.info("TTS produced %d bytes of audio", len(audio_bytes))
    return audio_bytes
