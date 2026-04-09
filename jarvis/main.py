"""
Rocky — Phase 7 Voice Assistant with JARVIS HUD.

Architecture:
  Main thread   → Qt event loop (UI)
  VoiceWorker   → QThread (voice loop, LLM, actions)
  AppObserver   → daemon thread (passive window monitoring)
  WakeWord      → daemon thread (openWakeWord)
  InputStream   → sounddevice daemon thread (RMS → waveform)
"""

import sys
import os
import logging
import random
import threading
from datetime import datetime
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
from brain.observer import AppObserver
from brain.file_rag import query_documents
from utils.parser import parse_llm_response
from utils.intent import detect_intent
from utils.system_stats import get_system_stats
from utils.exporter import export_history
from actions.executor import execute_action
from actions.reminders import set_reminder
from actions.terminal import generate_script, execute_script
from actions.spotify_control import spotify_control
from memory.memory_manager import (
    load_memory, add_to_history, save_memory,
    set_preference, update_habit, set_emotion,
)
from memory.vector_db import vector_memory
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

_pool = ThreadPoolExecutor(max_workers=3)

# ── Helpers ────────────────────────────────────────────────────────────────────

_HELP_TEXT = (
    "Open apps, play music, search the web, read your screen, "
    "research topics, check weather, set reminders, search your files, "
    "run scripts, and hold a conversation. Ask away."
)

_RESET_PHRASES = ("forget everything", "clear memory", "reset memory", "start fresh")

_GREETINGS = {
    "late_night": [
        "Past midnight. You are still running. Noted. What do you need?",
        "It is very late. Your persistence is... admirable. What do you need?",
    ],
    "morning": [
        "Morning. Systems online. What do we have today?",
        "Morning. All modules cleared diagnostics. Ready.",
    ],
    "afternoon": [
        "Afternoon. All modules initialized. Ready when you are.",
        "Afternoon. Systems nominal. What is the task?",
    ],
    "evening": [
        "Evening. Online and standing by. What do you need?",
        "Evening. Ready for operations. What do you need?",
    ],
    "late_evening": [
        "Late evening. Still here. What do you need?",
        "Getting late. But I do not sleep. What do you need?",
    ],
}


def _get_greeting() -> str:
    hour = datetime.now().hour
    if 0 <= hour < 5:
        return random.choice(_GREETINGS["late_night"])
    elif hour < 12:
        return random.choice(_GREETINGS["morning"])
    elif hour < 17:
        return random.choice(_GREETINGS["afternoon"])
    elif hour < 21:
        return random.choice(_GREETINGS["evening"])
    else:
        return random.choice(_GREETINGS["late_evening"])


def _proactive_check(memory: dict) -> str | None:
    habits = memory.get("habits", {})
    if habits.get("gym_skipped", 0) >= 3:
        return "Gym skipped three times now. Pattern is forming. Correction suggested."
    if habits.get("working_late", 0) >= 2:
        return "Working late again. Sleep is not optional. Recommend rest."
    return None


def _update_memory(user_input: str, intent: str, action: str | None):
    low = user_input.lower()
    if intent == "play_music" and action:
        set_preference("music_app", action)
    if "gym" in low and any(w in low for w in ("skip", "skipped", "missed", "didn't go")):
        update_habit("gym_skipped")
    if any(p in low for p in ("working late", "staying up", "up late")):
        update_habit("working_late")


def _respond(sig, user_input: str, response_text: str):
    """Central respond helper — print, emit, store, speak."""
    if not response_text:
        return
    print(f"ROCKY : {response_text}")
    sig.ai_text.emit(response_text)
    add_to_history(user_input, response_text)
    vector_memory.add_memory(user_input, response_text)


# ── Voice worker ───────────────────────────────────────────────────────────────

class VoiceWorker(QObject):
    finished = pyqtSignal()

    def __init__(self, signals: RockySignals):
        super().__init__()
        self._sig        = signals
        self._speak_lock = threading.Lock()
        self._pending_script = None  # For agentic terminal confirmation

    # ── Speech ────────────────────────────────────────────────────────────────
    def _safe_speak(self, text: str):
        with self._speak_lock:
            self._sig.status_changed.emit("SPEAKING")
            speak(text)
            self._sig.status_changed.emit("IDLE")

    # ── Intent handlers ───────────────────────────────────────────────────────

    def _handle_reminder(self, user_input: str, intent: dict):
        confirmation = set_reminder(user_input, self._safe_speak)
        _respond(self._sig, user_input, confirmation)
        self._safe_speak(confirmation)

    def _handle_keyword_intent(self, user_input: str, intent: dict, history: list):
        intent_name = intent["intent"]
        action_name = intent.get("action")

        # Special: vision and plugin intents may produce their own response text
        if intent_name in ("vision", "plugin_action"):
            action_result = execute_action(intent)
            response_text = action_result or "Processing complete."
            _respond(self._sig, user_input, response_text)
            self._sig.info_text.emit(response_text[:80])
            self._safe_speak(response_text)
            return

        # Generate spoken text via LLM (quick because schemas are enforced)
        raw    = generate_response(user_input, history)
        parsed = parse_llm_response(raw)
        response_text = intent.get("response_override") or parsed.get("response", "Executing.")

        # Speak FIRST, then execute action in background
        _respond(self._sig, user_input, response_text)
        _pool.submit(lambda: (execute_action(intent), _update_memory(user_input, intent_name, action_name)))
        self._safe_speak(response_text)

    def _handle_chat(self, user_input: str, history: list) -> str:
        # Inject document context if a question is being asked
        doc_context = query_documents(user_input, top_k=2)
        if doc_context:
            enriched = f"[Document context: {' | '.join(doc_context[:2])}]\n{user_input}"
        else:
            enriched = user_input

        raw    = generate_response(enriched, history)
        parsed = parse_llm_response(raw)

        # Execute any LLM-detected intent
        llm_intent = parsed.get("intent", "chat")
        if llm_intent and llm_intent != "chat":
            _pool.submit(execute_action, parsed)
            _update_memory(user_input, llm_intent, parsed.get("action"))

        return parsed.get("response", "")

    def _handle_terminal(self, user_input: str):
        """Let Rocky write a script and ask for confirmation."""
        self._sig.ai_text.emit("Generating script. Stand by.")
        self._safe_speak("Generating script. Stand by.")

        result = generate_script(user_input)
        explanation = result.get("explanation", "Script generated.")
        code        = result.get("code", "")

        if not code:
            _respond(self._sig, user_input, explanation)
            self._safe_speak(explanation)
            return

        # Show the script info and ask for permission
        self._pending_script = result
        self._sig.info_text.emit(f"Script ready: {explanation}")
        confirm_msg = f"{explanation} Say 'proceed' to execute or 'cancel' to abort."
        _respond(self._sig, user_input, confirm_msg)
        self._safe_speak(confirm_msg)

    # ── Main loop ─────────────────────────────────────────────────────────────
    def run(self):
        self._sig.status_changed.emit("IDLE")

        greeting = _get_greeting()
        self._sig.ai_text.emit(greeting)
        self._safe_speak(greeting)
        print(f"\n[ROCKY] Active — say 'goodbye' to exit.\n")

        def _update_stats():
            if not getattr(self, "_active", True): return
            stats = get_system_stats()
            self._sig.info_text.emit(stats)
            threading.Timer(10, _update_stats).start()

        stats_timer = threading.Timer(2, _update_stats)
        stats_timer.start()

        # Start passive observer
        from plyer import notification
        def _on_obs(msg):
            self._sig.observation.emit(msg)
            self._sig.info_text.emit(msg)
            try:
                notification.notify(title="Rocky Observation", message=msg, app_name="Rocky", timeout=5)
            except: pass

        observer = AppObserver(on_observation=_on_obs)
        observer.start()

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

                # ── Listen ────────────────────────────────────────────────────
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

                # ── Pending script confirmation ───────────────────────────────
                if self._pending_script:
                    if any(w in low for w in ("proceed", "yes", "do it", "execute", "run it")):
                        script = self._pending_script
                        self._pending_script = None
                        output = execute_script(script.get("code", ""), script.get("language", "python"))
                        resp = f"Script executed. Output: {output[:120]}"
                        _respond(self._sig, user_input, resp)
                        self._sig.info_text.emit(output[:80])
                        self._safe_speak(resp)
                        continue
                    elif any(w in low for w in ("cancel", "no", "abort", "stop")):
                        self._pending_script = None
                        resp = "Script cancelled. Noted."
                        _respond(self._sig, user_input, resp)
                        self._safe_speak(resp)
                        continue

                # ── Special commands ──────────────────────────────────────────
                if any(kw in low for kw in ("shut down", "goodbye", "exit rocky")):
                    self._safe_speak("Shutting down. Optimal choice.")
                    observer.stop()
                    wake.stop()
                    stats_timer.cancel()
                    break

                if any(kw in low for kw in ("export conversation", "save log", "export history")):
                    res = export_history()
                    self._sig.ai_text.emit(res)
                    self._safe_speak(res)
                    continue

                if any(kw in low for kw in ("skip track", "next song", "spotify next", "volume to")):
                    res = spotify_control(low)
                    self._sig.ai_text.emit(res)
                    self._safe_speak(res)
                    continue

                if any(p in low for p in _RESET_PHRASES):
                    save_memory({"user_preferences": {}, "habits": {}, "history": [], "last_emotion": "neutral"})
                    resp = "Memory cleared. Starting fresh."
                    self._sig.ai_text.emit(resp)
                    self._safe_speak(resp)
                    continue

                if any(p in low for p in ("what can you do", "what do you do", "help", "capabilities")):
                    self._sig.ai_text.emit(_HELP_TEXT)
                    self._safe_speak(_HELP_TEXT)
                    continue

                # ── Terminal commands ─────────────────────────────────────────
                if any(t in low for t in ("run a script", "write a script",
                                           "clean up my", "organize my",
                                           "sort my files", "execute code")):
                    self._handle_terminal(user_input)
                    continue

                # ── Ingest files ──────────────────────────────────────────────
                if any(t in low for t in ("learn my files", "ingest my", "read my folder",
                                           "scan my documents", "index my files")):
                    from brain.file_rag import ingest_folder
                    # Default to Documents folder
                    folder = os.path.join(os.path.expanduser("~"), "Documents")
                    self._sig.info_text.emit(f"Ingesting: {folder}")
                    self._safe_speak("Scanning your documents folder. This may take a moment.")

                    stats = _pool.submit(ingest_folder, folder).result()
                    resp = f"Ingested {stats.get('files_processed', 0)} files, {stats.get('chunks_added', 0)} data chunks stored."
                    _respond(self._sig, user_input, resp)
                    self._sig.info_text.emit(resp)
                    self._safe_speak(resp)
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
                    self._handle_keyword_intent(user_input, keyword_intent, history)
                else:
                    response_text = self._handle_chat(user_input, history)
                    _respond(self._sig, user_input, response_text)
                    self._safe_speak(response_text)

                # ── Proactive check ───────────────────────────────────────────
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
    window  = RockyWindow(signals)
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
