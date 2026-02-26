"""
Healthcare Voice Agent — FastAPI Backend

Endpoints:
  POST /api/process-audio   — Receives audio blob, returns MP3 response
  POST /api/process-text    — Text-in / text-out (for testing without mic)
  GET  /api/health          — Health check
  GET  /api/session/{id}    — Retrieve session conversation history
  DELETE /api/session/{id}  — Clear session history
"""
import io
import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from agent_router import _session_histories, process_request
from config import settings
from models.schemas import ProcessResponse, TextRequest
from stt import transcribe_audio
from tts import synthesize_speech

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Healthcare Voice Agent starting up (env=%s)", settings.app_env)
    logger.info("Google Calendar: %s", "enabled" if settings.use_google_calendar else "in-memory demo")
    yield
    logger.info("Healthcare Voice Agent shutting down")


app = FastAPI(
    title="Healthcare Voice Agent",
    version="1.0.0",
    description="Voice-driven healthcare admin assistant — POC",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-User-Text", "X-Response-Text", "X-Session-Id", "X-Intent", "X-Goal-Achieved"],
)


# ─── Audio pipeline endpoint ──────────────────────────────────────────────────

@app.post("/api/process-audio", summary="Process voice input, return voice response")
async def process_audio(
    audio: UploadFile = File(..., description="Audio file (webm, mp4, wav, mp3)"),
    session_id: str = Form(default=""),
):
    """
    Full voice pipeline:
      audio → Whisper STT → LangGraph agent → Claude response → OpenAI TTS → MP3
    """
    if not session_id:
        session_id = str(uuid.uuid4())

    logger.info("[%s] Received audio: %s (%s)", session_id, audio.filename, audio.content_type)

    try:
        audio_bytes = await audio.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Empty audio file")

        # Step 2: STT
        user_text = await transcribe_audio(audio_bytes, audio.filename or "audio.webm")
        if not user_text:
            return StreamingResponse(
                io.BytesIO(await synthesize_speech("I didn't catch that. Could you please repeat?")),
                media_type="audio/mpeg",
                headers={
                    "X-User-Text": "",
                    "X-Response-Text": "I didn't catch that. Could you please repeat?",
                    "X-Session-Id": session_id,
                    "X-Intent": "unknown",
                    "X-Goal-Achieved": "false",
                },
            )

        # Steps 3–8: Intent → Agent → Response
        response_text = await process_request(user_text, session_id)

        # Step 8: TTS
        audio_out = await synthesize_speech(response_text)

        return StreamingResponse(
            io.BytesIO(audio_out),
            media_type="audio/mpeg",
            headers={
                "X-User-Text": user_text[:500],           # header size limit guard
                "X-Response-Text": response_text[:500],
                "X-Session-Id": session_id,
                "X-Goal-Achieved": "true",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[%s] Audio pipeline error: %s", session_id, e)
        error_audio = await synthesize_speech(
            "I'm sorry, I encountered a technical error. Please try again."
        )
        return StreamingResponse(
            io.BytesIO(error_audio),
            media_type="audio/mpeg",
            headers={
                "X-User-Text": "",
                "X-Response-Text": "Technical error",
                "X-Session-Id": session_id,
                "X-Goal-Achieved": "false",
            },
        )


# ─── Text-mode endpoint (for testing) ────────────────────────────────────────

@app.post("/api/process-text", response_model=ProcessResponse, summary="Text-in / text-out (test mode)")
async def process_text(request: TextRequest):
    """Bypass STT/TTS — useful for testing the intent/agent pipeline."""
    session_id = request.session_id or str(uuid.uuid4())
    logger.info("[%s] Text request: %s", session_id, request.text)

    response_text = await process_request(request.text, session_id)

    return ProcessResponse(
        session_id=session_id,
        user_text=request.text,
        response_text=response_text,
        goal_achieved=True,
    )


# ─── Health & session management ─────────────────────────────────────────────

@app.get("/api/health", summary="Health check")
async def health():
    return {
        "status": "ok",
        "env": settings.app_env,
        "google_calendar": settings.use_google_calendar,
        "version": "1.0.0",
    }


@app.get("/api/session/{session_id}", summary="Get conversation history for a session")
async def get_session(session_id: str):
    history = _session_histories.get(session_id, [])
    return {"session_id": session_id, "turns": len(history) // 2, "history": history}


@app.delete("/api/session/{session_id}", summary="Clear session conversation history")
async def clear_session(session_id: str):
    _session_histories.pop(session_id, None)
    return {"session_id": session_id, "cleared": True}
