"""
TTS engine for Rocky using edge-tts (Microsoft Neural Voice).

Quality hierarchy:
  1. edge-tts + pygame-ce playback  (best quality, requires internet)
  2. SAPI5 via win32com              (offline fallback)

Voice choices for Rocky's character:
  en-US-AndrewNeural        — confident, masculine, calm
  en-US-GuyNeural           — natural American male
  en-GB-RyanNeural          — British JARVIS-style
  en-US-ChristopherNeural   — deeper, authoritative

Change EDGE_TTS_VOICE in config.py to switch voice.
"""

import asyncio
import os
import tempfile
import threading
import logging

from config import TTS_RATE, TTS_VOLUME, EDGE_TTS_VOICE, EDGE_TTS_RATE

# ── pygame-ce init (done once) ─────────────────────────────────────────────────
_pygame_ready = False
_pygame_lock  = threading.Lock()

def _ensure_pygame():
    global _pygame_ready
    if _pygame_ready:
        return True
    with _pygame_lock:
        if _pygame_ready:
            return True
        try:
            import pygame
            pygame.mixer.init(frequency=48000, size=-16, channels=1, buffer=512)
            _pygame_ready = True
            logging.info("pygame-ce audio mixer initialized.")
            return True
        except Exception as e:
            logging.error(f"pygame-ce init failed: {e}")
            return False

# ── edge-tts async core ────────────────────────────────────────────────────────
async def _edge_generate(text: str) -> str:
    """Generate MP3 via edge-tts, save to temp file, return path."""
    import edge_tts
    communicate = edge_tts.Communicate(text, voice=EDGE_TTS_VOICE, rate=EDGE_TTS_RATE)
    fd, tmp_path = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)
    await communicate.save(tmp_path)
    return tmp_path

def _edge_speak(text: str):
    """Run edge-tts generation + pygame playback synchronously."""
    import pygame
    tmp_path = None
    try:
        loop = asyncio.new_event_loop()
        tmp_path = loop.run_until_complete(_edge_generate(text))
        loop.close()

        if not _ensure_pygame():
            raise RuntimeError("pygame not available")

        pygame.mixer.music.load(tmp_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.wait(40)

    except Exception as e:
        logging.error(f"edge-tts playback failed: {e} — falling back to SAPI5")
        _sapi5_speak(text)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass

# ── SAPI5 fallback ─────────────────────────────────────────────────────────────
def _sapi5_speak(text: str):
    try:
        import win32com.client
        sp = win32com.client.Dispatch("SAPI.SpVoice")
        sp.Rate   = TTS_RATE
        sp.Volume = TTS_VOLUME
        sp.Speak(text)
    except Exception as e:
        logging.error(f"SAPI5 fallback also failed: {e}")

# ── Public API ─────────────────────────────────────────────────────────────────
def speak(text: str):
    """Speak text — tries edge-tts first, then SAPI5."""
    if not text or not text.strip():
        return
    _edge_speak(text)
