"""
Qt signals used to relay voice-loop updates (from QThread) to the UI.
Always update Qt widgets from the main thread — never directly from worker threads.
"""
from PyQt6.QtCore import QObject, pyqtSignal


class RockySignals(QObject):
    status_changed = pyqtSignal(str)     # "LISTENING" / "THINKING" / "SPEAKING" / "IDLE"
    user_text      = pyqtSignal(str)     # transcribed speech
    ai_text        = pyqtSignal(str)     # Rocky's response
    wave_tick      = pyqtSignal(float)   # 0.0–1.0 audio activity level
    info_text      = pyqtSignal(str)     # dynamic info bar (weather, vision summary, etc.)
    observation    = pyqtSignal(str)     # passive app observer nudges
