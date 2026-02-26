"""Speech-to-Text using OpenAI Whisper API."""
import io
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


async def transcribe_audio(audio_bytes: bytes, filename: str = "audio.webm") -> str:
    """
    Transcribe audio bytes to text using OpenAI Whisper.

    Args:
        audio_bytes: Raw audio bytes (webm, mp4, wav, mp3 supported)
        filename: Original filename with extension (used to hint MIME type)

    Returns:
        Transcribed text string
    """
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is not configured")

    logger.info("Transcribing audio (%d bytes, %s)", len(audio_bytes), filename)

    client = _get_client()
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = filename  # Whisper uses filename extension for format detection

    transcript = await client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
        language="en",
        response_format="text",
    )

    text = transcript.strip() if isinstance(transcript, str) else transcript.text.strip()
    logger.info("Transcription result: %s", text)
    return text
