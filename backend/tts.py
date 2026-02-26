"""Text-to-Speech using ElevenLabs API."""
import logging
from elevenlabs import AsyncElevenLabs
from config import settings

logger = logging.getLogger(__name__)
_client: AsyncElevenLabs | None = None

# Default voice — "Rachel" is a clear, professional female voice
# Browse voices at: elevenlabs.io/voice-library
DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"   # Rachel


def _get_client() -> AsyncElevenLabs:
    global _client
    if _client is None:
        _client = AsyncElevenLabs(api_key=settings.elevenlabs_api_key)
    return _client


async def synthesize_speech(
    text: str,
    voice_id: str = DEFAULT_VOICE_ID,
    model_id: str = "eleven_turbo_v2_5",
) -> bytes:
    """
    Convert text to speech audio bytes using ElevenLabs.

    Args:
        text: Text to synthesize
        voice_id: ElevenLabs voice ID (default: Rachel)
        model_id: Model to use — eleven_turbo_v2_5 (fast) or eleven_multilingual_v2 (quality)

    Returns:
        MP3 audio bytes
    """
    if not settings.elevenlabs_api_key:
        raise ValueError("ELEVENLABS_API_KEY is not configured")

    logger.info("Synthesizing speech for text (%d chars)", len(text))

    client = _get_client()
    audio_generator = await client.text_to_speech.convert(
        voice_id=voice_id,
        text=text,
        model_id=model_id,
        output_format="mp3_44100_128",
    )

    # Collect streamed chunks into a single bytes object
    audio_bytes = b"".join([chunk async for chunk in audio_generator])
    logger.info("TTS produced %d bytes of audio", len(audio_bytes))
    return audio_bytes
