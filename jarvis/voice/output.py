import logging
import win32com.client
from config import TTS_RATE, TTS_VOLUME

class _VoiceOutput:
    """Singleton SAPI5 voice engine. Initialized once, reused forever."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            try:
                cls._instance._speaker = win32com.client.Dispatch("SAPI.SpVoice")
                cls._instance._speaker.Rate = TTS_RATE
                cls._instance._speaker.Volume = TTS_VOLUME
                logging.info("SAPI5 voice engine initialized.")
            except Exception as e:
                logging.error(f"SAPI5 init failed: {e}")
                cls._instance._speaker = None
        return cls._instance

    def speak(self, text: str):
        """Blocking speech — waits for full playback before returning."""
        if not self._speaker:
            logging.warning("TTS engine unavailable.")
            return
        try:
            self._speaker.Speak(text)
        except Exception as e:
            logging.error(f"TTS error: {e}")

# Module-level singleton
_engine = _VoiceOutput()

def speak(text: str):
    """Public speak function used throughout the app."""
    _engine.speak(text)
