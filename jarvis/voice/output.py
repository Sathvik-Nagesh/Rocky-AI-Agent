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

from config import TTS_RATE, TTS_VOLUME, EDGE_TTS_VOICE, EDGE_TTS_RATE, ENABLE_PIPER_TTS, PIPER_VOICE_MODEL

# ── Global Emotion Context ─────────────────────────────────────────────────────
# This allows the voice to react to the HUD state in App.tsx
_current_emotion = "neutral"

def set_voice_emotion(emotion: str):
    global _current_emotion
    _current_emotion = emotion

def _get_emotion_modifiers():
    """Adjusts rate and volume based on detected sentiment."""
    if _current_emotion == "stressed":
        return {"rate": 20, "volume": 100} # Urgent
    if _current_emotion == "productive":
        return {"rate": 10, "volume": 90}  # Efficient
    if _current_emotion == "alert":
        return {"rate": 0, "volume": 100}   # Authoritative
    return {"rate": 0, "volume": 90}       # Neutral

# ── Piper TTS ──────────────────────────────────────────────────────────────────
_piper_voice = None
_piper_lock = threading.Lock()

def _ensure_piper():
    global _piper_voice
    if _piper_voice:
        return True
    with _piper_lock:
        if _piper_voice:
            return True
        try:
            import piper
            onnx, config_json = get_piper_model(PIPER_VOICE_MODEL)
            if onnx and config_json:
                _piper_voice = piper.PiperVoice.load(onnx, config_json)
                logging.info(f"Piper neural voice loaded: {PIPER_VOICE_MODEL}")
                return True
        except Exception as e:
            logging.error(f"Piper TTS init failed: {e}")
    return False

def _piper_speak(text: str):
    import wave
    import pygame
    tmp_path = None
    try:
        if not _ensure_piper():
            raise RuntimeError("Piper voice model unavailable")

        # Use NamedTemporaryFile to avoid mkstemp descriptor race conditions
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
            tmp_path = tf.name
            tf.close()
        
        with wave.open(tmp_path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(_piper_voice.config.sample_rate)
            _piper_voice.synthesize(text, w)

        if os.path.getsize(tmp_path) <= 44:
            logging.debug("Piper generated an empty audio payload (ONNX model incompatibility).")
            raise RuntimeError("Piper generated an empty audio payload (ONNX model incompatibility).")

        if not _ensure_pygame():
            raise RuntimeError("pygame not available")

        pygame.mixer.music.load(tmp_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.wait(40)

    except Exception as e:
        logging.error(f"Piper playback failed: {e} - falling back to edge-tts")
        _edge_speak(text)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass

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
    
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tf:
        tmp_path = tf.name
        tf.close()
        
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
        import pythoncom
        pythoncom.CoInitialize()  # Ensure thread safety for COM object
        sp = win32com.client.Dispatch("SAPI.SpVoice")
        mods = _get_emotion_modifiers()
        sp.Rate   = TTS_RATE + mods["rate"]
        sp.Volume = mods["volume"]
        sp.Speak(text)
    except Exception as e:
        logging.error(f"SAPI5 fallback also failed: {e}")

# ── Public API ─────────────────────────────────────────────────────────────────
def speak(text: str):
    """Speak text locally — prioritize Piper, fallback to SAPI5 (100% Offline)."""
    if not text or not text.strip():
        return
        
    print(f"[VOICE] Aura: {_current_emotion} | Rocky: {text}")
    
    # ── RVC Bridge Injection ──────────────────────────────────────────
    # If a local RVC server is detected, we would route the audio there
    # for voice conversion (e.g. to a JARVIS voice).
    # ──────────────────────────────────────────────────────────────────
    
    if ENABLE_PIPER_TTS:
        _piper_speak(text)
    else:
        _sapi5_speak(text)
