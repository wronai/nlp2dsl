"""
Audio Parser — Speech-to-Text via Deepgram HTTP API.

Integruje STT (Speech-to-Text) w Conversation Loop:
  1. Użytkownik wysyła audio w /chat/start lub /chat/message
  2. STT → transcript → NLP Parser/Mapper → DSL/UI form
  3. Odpowiedź jako tekst (lub TTS w przyszłości)

Konfiguracja (env vars):
  DEEPGRAM_API_KEY  — klucz API Deepgram (wymagany)
  DEEPGRAM_MODEL    — model STT (default: nova-3-general)
  DEEPGRAM_LANGUAGE — język (default: pl)
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import httpx

log = logging.getLogger("nlp.audio")

# ── Deepgram Config ───────────────────────────────────────────

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
DEEPGRAM_MODEL = os.getenv("DEEPGRAM_MODEL", "nova-3-general")
DEEPGRAM_LANGUAGE = os.getenv("DEEPGRAM_LANGUAGE", "pl")
DEEPGRAM_API_URL = "https://api.deepgram.com/v1/listen"


# ── STT Functions ─────────────────────────────────────────────


async def stt_audio(audio_bytes: bytes, language: str = None) -> Optional[str]:
    """
    Transcribe audio bytes to text using Deepgram HTTP API.
    
    Args:
        audio_bytes: Audio data (WAV, MP3, M4A, etc.)
        language: Language code (default: pl)
    
    Returns:
        Transcribed text or None if failed
    """
    if not DEEPGRAM_API_KEY:
        log.warning("DEEPGRAM_API_KEY not set, STT disabled")
        return None
    
    lang = language or DEEPGRAM_LANGUAGE
    
    try:
        # Build URL with query params
        url = f"{DEEPGRAM_API_URL}?model={DEEPGRAM_MODEL}&language={lang}&smart_format=true&punctuate=true"
        
        headers = {
            "Authorization": f"Token {DEEPGRAM_API_KEY}",
            "Content-Type": "audio/*",  # Auto-detect format
        }
        
        # Transcribe
        log.info("Transcribing audio (%d bytes, lang=%s)", len(audio_bytes), lang)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, content=audio_bytes)
            
            if response.status_code != 200:
                log.error("Deepgram API error: %d - %s", response.status_code, response.text)
                return None
            
            data = response.json()
        
        # Extract transcript
        if "results" in data:
            channels = data["results"].get("channels", [])
            if channels:
                alternatives = channels[0].get("alternatives", [])
                if alternatives:
                    transcript = alternatives[0].get("transcript", "")
                    if transcript:
                        log.info("Transcription complete: %d chars", len(transcript))
                        return transcript
        
        log.warning("No transcript in response")
        return None
        
    except Exception as e:
        log.exception("STT transcription failed: %s", e)
        return None


async def stt_file(file_path: str, language: str = None) -> Optional[str]:
    """
    Transcribe audio file to text using Deepgram.
    
    Args:
        file_path: Path to audio file
        language: Language code (default: pl)
    
    Returns:
        Transcribed text or None if failed
    """
    try:
        with open(file_path, "rb") as f:
            audio_bytes = f.read()
        return await stt_audio(audio_bytes, language)
    except Exception as e:
        log.exception("Failed to read audio file: %s", e)
        return None


def is_stt_available() -> bool:
    """Check if STT is available (Deepgram configured)."""
    return DEEPGRAM_API_KEY is not None and DEEPGRAM_API_KEY != ""


# ── Streaming STT (placeholder - requires WebSocket) ────────────────

class StreamingSTT:
    """
    Real-time streaming STT via Deepgram WebSocket.
    Placeholder - requires WebSocket implementation.
    """
    
    def __init__(self, language: str = None):
        self.language = language or DEEPGRAM_LANGUAGE
        self.transcript_buffer = []
        log.warning("StreamingSTT not fully implemented - use stt_audio for batch processing")
    
    async def start(self):
        """Start streaming connection."""
        log.warning("StreamingSTT.start() not implemented")
        return False
    
    async def send_audio(self, audio_chunk: bytes):
        """Send audio chunk to streaming connection."""
        # Fallback: batch process
        transcript = await stt_audio(audio_chunk, self.language)
        if transcript:
            self.transcript_buffer.append(transcript)
    
    async def get_transcript(self) -> str:
        """Get accumulated transcript."""
        return " ".join(self.transcript_buffer)
    
    async def stop(self) -> str:
        """Stop streaming and return final transcript."""
        return " ".join(self.transcript_buffer)
