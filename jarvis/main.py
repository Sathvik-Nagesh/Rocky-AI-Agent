"""
Rocky — Phase 4 voice assistant with JARVIS HUD.

Threading model:
  Main thread  → Qt event loop (UI)
  VoiceWorker  → QThread running the voice loop
  WakeWord     → daemon thread inside WakeWordDetector
  InputStream  → sounddevice daemon thread, emits RMS via on_level callback
"""

import sys
import os
import logging
import random
import threading
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QThread, pyqtSignal, QObject

from config import ENABLE_WAKE_WORD
from voice.input import listen
from voice.output import speak
from voice.wake_word import WakeWordDetector
from brain.llm import generate_response
from brain.emotion import detect_emotion
from utils.parser import parse_llm_response
from utils.intent import detect_intent
from actions.executor import execute_action
from actions.reminders import set_reminder
from memory.memory_manager import (
    load_memory, add_to_history,
    set_preference, update_habit, set_emotion,
)
from ui.main_window import RockyWindow
from ui.signals import RockySignals

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("rocky.log", encoding="utf-8"),
    ],
)

_pool = ThreadPoolExecutor(max_workers=2)

# ── Helpers ────────────────────────────────────────────────────────────────────

_HELP_TEXT = (
    "I can open apps, play Apple Music, search the web, check the weather, "
    "set reminders, open your folders, and hold a conversation. Ask away."
)

_RESET_PHRASES = ("forget everything", "clear memory", "reset memory", "start fresh")

def _proactive_check(memory: dict) -> str | None:
    habits = memory.get("habits", {})
    if habits.get("gym_skipped", 0) >= 3:
        return "Gym skipped three times now. Pattern is forming. Correction suggested, yes?"
    if habits.get("working_late", 0) >= 2:
        return "Working late again. Sleep is not optional. Recommend rest."
    if random.random() < 0.05:
        return "You are quiet. Everything functioning well?"
    return None

def _update_memory(user_input: str, intent: str, action: str | None):
    low = user_input.lower()
    if intent == "play_music" and action:
        set_preference("music_app", action)
    if "gym" in low and any(w in low for w in ("skip", "skipped", "missed", "didn't go")):
        update_habit("gym_skipped")
    if any(p in low for p in ("working late", "staying up", "up late")):
        update_habit("working_late")

# ── Voice worker ───────────────────────────────────────────────────────────────

class VoiceWorker(QObject):
    finished = pyqtSignal()

    def __init__(self, signals: RockySignals):
        super().__init__()
        self._sig        = signals
        self._speak_lock = threading.Lock()

    # ── Speech ────────────────────────────────────────────────────────────────
    def _safe_speak(self, text: str):
        with self._speak_lock:
            self._sig.status_changed.emit("SPEAKING")
            speak(text)
            self._sig.status_changed.emit("IDLE")

    # ── Intent handlers ───────────────────────────────────────────────────────
    def _handle_reminder(self, user_input: str, intent: dict):
        confirmation = set_reminder(user_input, self._safe_speak)
        self._sig.ai_text.emit(confirmation)
        add_to_history(user_input, confirmation)
        self._safe_speak(confirmation)

    def _handle_keyword_intent(self, user_input: str, intent: dict, history: list):
        intent_name = intent["intent"]
        action_name = intent.get("action")

        # Parallel: fire action + generate spoken reply simultaneously
        action_f = _pool.submit(execute_action, intent)
        llm_f    = _pool.submit(generate_response, user_input, history)

        action_result = action_f.result()
        raw           = llm_f.result()
        parsed        = parse_llm_response(raw)
        response_text = action_result or parsed.get("response", "Understood. Executing now.")

        _update_memory(user_input, intent_name, action_name)
        return response_text

    def _handle_chat(self, user_input: str, history: list) -> str:
        raw    = generate_response(user_input, history)
        parsed = parse_llm_response(raw)

        # Honour any intent the LLM may have detected
        llm_intent = parsed.get("intent", "chat")
        if llm_intent and llm_intent != "chat":
            execute_action(parsed)
            _update_memory(user_input, llm_intent, parsed.get("action"))

        return parsed.get("response", "")

    # ── Main loop ─────────────────────────────────────────────────────────────
    def run(self):
        self._sig.status_changed.emit("IDLE")

        # Time-aware greeting
        from datetime import datetime
        hour = datetime.now().hour
        if 0 <= hour < 5:
            greeting = "It is past midnight. You are still running. Noted. What do you need?"
        elif hour < 12:
            greeting = "Morning. Systems online. What do we have today?"
        elif hour < 17:
            greeting = "Afternoon. All modules initialized. Ready when you are."
        elif hour < 21:
            greeting = "Evening. Online and standing by. What do you need?"
        else:
            greeting = "Late evening. Still here. What do you need?"

        self._sig.ai_text.emit(greeting)
        self._safe_speak(greeting)
        print(f"\n[ROCKY] Active — say 'goodbye' to exit.\n")

        wake = WakeWordDetector()
        if ENABLE_WAKE_WORD:
            wake.start()

        while True:
            try:
                # ── Wake word gate ────────────────────────────────────────────
                if ENABLE_WAKE_WORD:
                    self._sig.status_changed.emit("STANDBY")
                    if not wake.wait_for_wake():
                        continue
                    self._safe_speak("Yes?")

                # ── Listen (real RMS → waveform) ──────────────────────────────
                self._sig.status_changed.emit("LISTENING")
                user_input = listen(
                    on_level=lambda lvl: self._sig.wave_tick.emit(lvl)
                )
                self._sig.status_changed.emit("IDLE")

                if not user_input or not user_input.strip():
                    continue

                self._sig.user_text.emit(user_input)
                print(f"USER : {user_input}")

                low = user_input.lower()

                # ── Special commands ──────────────────────────────────────────
                if any(kw in low for kw in ("shut down", "goodbye", "exit rocky")):
                    self._safe_speak("Shutting down. Optimal choice, yes?")
                    wake.stop()
                    break

                if any(p in low for p in _RESET_PHRASES):
                    from memory.memory_manager import save_memory
                    save_memory({"user_preferences": {}, "habits": {}, "history": [], "last_emotion": "neutral"})
                    resp = "Memory cleared. Starting fresh, curious."
                    self._sig.ai_text.emit(resp)
                    self._safe_speak(resp)
                    continue

                if any(p in low for p in ("what can you do", "what do you do", "help", "capabilities")):
                    self._sig.ai_text.emit(_HELP_TEXT)
                    self._safe_speak(_HELP_TEXT)
                    continue

                # ── Emotion + Memory ──────────────────────────────────────────
                set_emotion(detect_emotion(user_input))
                memory  = load_memory()
                history = memory.get("history", [])

                # ── Intent detection ──────────────────────────────────────────
                self._sig.status_changed.emit("THINKING")
                print("ROCKY : Thinking...")

                keyword_intent = detect_intent(user_input)

                if keyword_intent and keyword_intent["intent"] == "reminder":
                    self._handle_reminder(user_input, keyword_intent)
                    continue

                if keyword_intent:
                    response_text = self._handle_keyword_intent(user_input, keyword_intent, history)
                else:
                    response_text = self._handle_chat(user_input, history)

                # ── Respond ───────────────────────────────────────────────────
                if response_text:
                    print(f"ROCKY : {response_text}")
                    self._sig.ai_text.emit(response_text)
                    add_to_history(user_input, response_text)
                    self._safe_speak(response_text)

                # ── Proactive ─────────────────────────────────────────────────
                proactive = _proactive_check(memory)
                if proactive:
                    self._sig.ai_text.emit(proactive)
                    self._safe_speak(proactive)

            except Exception as e:
                logging.error(f"Voice loop error: {e}", exc_info=True)
                self._sig.status_changed.emit("IDLE")

        self.finished.emit()


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Rocky")

    signals = RockySignals()

    window = RockyWindow(signals)
    window.show()

    thread = QThread()
    worker = VoiceWorker(signals)
    worker.moveToThread(thread)

    thread.started.connect(worker.run)
    worker.finished.connect(thread.quit)
    worker.finished.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)
    worker.finished.connect(app.quit)
    thread.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
