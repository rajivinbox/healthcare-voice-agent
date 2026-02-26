"""Speech-to-Text using ElevenLabs Scribe API."""
import io
import logging
from elevenlabs import AsyncElevenLabs
from config import settings

logger = logging.getLogger(__name__)
_client: AsyncElevenLabs | None = None


def _get_client() -> AsyncElevenLabs:
    global _client
    if _client is None:
        _client = AsyncElevenLabs(api_key=settings.elevenlabs_api_key)
    return _client


async def transcribe_audio(audio_bytes: bytes, filename: str = "audio.webm") -> str:
    """
    Transcribe audio bytes to text using ElevenLabs Scribe.

    Args:
        audio_bytes: Raw audio bytes (webm, mp4, wav, mp3 supported)
        filename: Original filename with extension (used to hint MIME type)

    Returns:
        Transcribed text string
    """
    if not settings.elevenlabs_api_key:
        raise ValueError("ELEVENLABS_API_KEY is not configured")

    logger.info("Transcribing audio (%d bytes, %s)", len(audio_bytes), filename)

    client = _get_client()
    audio_file = ("audio.webm", io.BytesIO(audio_bytes), "audio/webm")

    result = await client.speech_to_text.convert(
        file=audio_file,
        model_id="scribe_v1",
        language_code="en",
    )

    text = result.text.strip() if result.text else ""
    logger.info("Transcription result: %s", text)
    return text
