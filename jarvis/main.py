"""
Rocky — Phase 10 Voice Assistant with JARVIS HUD.

Phase 10 additions:
  - Self-Evolution: Rocky writes and hot-reloads his own plugins
  - Voice Emotion: acoustic fatigue/stress detection from speech
  - Negation-safe intent detection ("I am not asleep" no longer triggers sleep)
  - Dangerous action confirmation gate (shutdown/restart/sleep require "yes")
  - Expanded prompt personality and vocabulary
"""

import sys
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import logging
import random
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QThread, pyqtSignal, QObject, QTimer

from config import ENABLE_WAKE_WORD
from voice.input import listen
from voice.output import speak
from voice.wake_word import WakeWordDetector
from brain.llm import generate_response
from brain.emotion import detect_emotion
from brain.observer import AppObserver
from brain.file_rag import query_documents
from brain.clipboard_manager import ClipboardManager
from brain.self_repair import self_repair, diagnose
from brain.self_evolve import generate_plugin, save_plugin
from brain.voice_emotion import analyze_voice_features, get_voice_insight
from brain.git_architect import summarize_repo_changes, audit_file
from utils.parser import parse_llm_response
from utils.intent import detect_intent
from utils.system_stats import get_system_stats
from utils.exporter import export_history
from utils.finance_tracker import query_finance
from actions.executor import execute_action
from actions.reminders import set_reminder
from actions.terminal import generate_script, execute_script
from actions.spotify_control import spotify_control
from actions.process_control import describe_top_processes, kill_process_by_name, is_system_stressed
from actions.chaos_fixer import organize_folder
from memory.memory_manager import (
    load_memory, add_to_history, save_memory,
    set_preference, update_habit, set_emotion,
    purge_memory
)
from memory.vector_db import vector_memory
from ui.main_window import RockyWindow
from ui.signals import RockySignals

logging.basicConfig(
    level=logging.WARNING,          # ← Changed INFO→WARNING to reduce log noise per turn
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("rocky.log", encoding="utf-8"),
    ],
)

# 4 workers: LLM, action, clipboard analysis, file ingest can all overlap
_pool = ThreadPoolExecutor(max_workers=4)

# ── Constants ──────────────────────────────────────────────────────────────────

_HELP_TEXT = (
    "I can open apps, play music, search or research the web, read your screen, "
    "check weather, set reminders, search your files, track expenses, "
    "run scripts, monitor your system, analyse your clipboard, and hold a conversation. "
    "Ask away."
)

_RESET_PHRASES = ("forget everything", "clear memory", "reset memory", "start fresh")

_GREETINGS = {
    "late_night": [
        "Past midnight. You are still running. Noted. What do you need?",
        "It is very late. Your persistence is admirable. What do you need?",
    ],
    "morning": [
        "Morning. Systems online. What do we have today?",
        "Morning. All modules cleared diagnostics. Ready.",
    ],
    "afternoon": [
        "Afternoon. Initialized and standing by.",
        "Afternoon. Systems nominal. What is the task?",
    ],
    "evening": [
        "Evening. Online and standing by.",
        "Evening. Ready for operations. What do you need?",
    ],
    "late_evening": [
        "Late evening. Still here. What do you need?",
        "Getting late. But I do not sleep. What do you need?",
    ],
}

_CLIP_MESSAGES = {
    "stack_trace": "I noticed you copied a stack trace. Want me to analyse it?",
    "url":         "You copied a URL. Want a quick summary of that page?",
    "code":        "You copied a code block. Want me to review it?",
    "long_text":   "You copied a long block of text. Want me to summarise it?",
}


def _get_greeting() -> str:
    hour = datetime.now().hour
    if hour < 5:   return random.choice(_GREETINGS["late_night"])
    if hour < 12:  return random.choice(_GREETINGS["morning"])
    if hour < 17:  return random.choice(_GREETINGS["afternoon"])
    if hour < 21:  return random.choice(_GREETINGS["evening"])
    return random.choice(_GREETINGS["late_evening"])


def _proactive_check(memory: dict) -> str | None:
    habits = memory.get("habits", {})
    if habits.get("gym_skipped", 0) >= 3:
        return "Gym skipped three times. Pattern forming. Correction suggested."
    if habits.get("working_late", 0) >= 2:
        return "Working late again. Sleep is not optional."
    return None


def _update_memory(user_input: str, intent: str, action: str | None):
    low = user_input.lower()
    if intent == "play_music" and action:
        set_preference("music_app", action)
    if "gym" in low and any(w in low for w in ("skip", "skipped", "missed", "didn't go")):
        update_habit("gym_skipped")
    if any(p in low for p in ("working late", "staying up", "up late")):
        update_habit("working_late")


def _respond(sig: RockySignals, user_input: str, response_text: str):
    """Central respond: print, emit to HUD, store to memory."""
    if not response_text:
        return
    print(f"ROCKY : {response_text}")
    sig.ai_text.emit(response_text)
    add_to_history(user_input, response_text)
    # Only embed non-trivial exchanges in vector DB
    if len(user_input) > 15:
        vector_memory.add_memory(user_input, response_text)


# ── Voice worker ───────────────────────────────────────────────────────────────

class VoiceWorker(QObject):
    finished = pyqtSignal()

    def __init__(self, signals: RockySignals):
        super().__init__()
        self._sig             = signals
        self._speak_lock      = threading.Lock()
        self._pending_script  = None   # agentic terminal confirmation
        self._pending_kill    = None   # process terminator confirmation
        self._pending_sys     = None   # dangerous system_control confirmation
        self._pending_plugin  = None   # self-evolution plugin confirmation
        self._clipboard_queue = []     # pending clipboard observations

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

        # Vision / plugins return their own text directly
        if intent_name in ("vision", "plugin_action"):
            action_result = execute_action(intent)
            response_text = action_result or "Processing complete."
            _respond(self._sig, user_input, response_text)
            self._sig.info_text.emit(response_text[:90])
            self._safe_speak(response_text)
            return

        # Generate spoken text, then fire action in background
        raw           = generate_response(user_input, history)
        parsed        = parse_llm_response(raw)
        response_text = intent.get("response_override") or parsed.get("response", "Executing.")

        _respond(self._sig, user_input, response_text)
        _pool.submit(lambda: (execute_action(intent), _update_memory(user_input, intent_name, action_name)))
        self._safe_speak(response_text)

    def _handle_chat(self, user_input: str, history: list) -> str:
        # Enrich with document RAG for question-like inputs
        doc_context = query_documents(user_input, top_k=2) if "?" in user_input or len(user_input) > 30 else []
        if doc_context:
            enriched = f"[File context: {' | '.join(doc_context[:2])}]\n{user_input}"
        else:
            enriched = user_input

        raw    = generate_response(enriched, history)
        parsed = parse_llm_response(raw)

        llm_intent = parsed.get("intent", "chat")
        if llm_intent and llm_intent != "chat":
            _pool.submit(execute_action, parsed)
            _update_memory(user_input, llm_intent, parsed.get("action"))

        return parsed.get("response", "")

    def _handle_terminal(self, user_input: str):
        self._sig.ai_text.emit("Generating script. Stand by.")
        self._safe_speak("Generating script. Stand by.")
        result      = generate_script(user_input)
        explanation = result.get("explanation", "Script generated.")
        code        = result.get("code", "")
        if not code:
            _respond(self._sig, user_input, explanation)
            self._safe_speak(explanation)
            return
        self._pending_script = result
        self._sig.info_text.emit(f"Script ready: {explanation}")
        confirm_msg = f"{explanation}. Say proceed to execute or cancel to abort."
        _respond(self._sig, user_input, confirm_msg)
        self._safe_speak(confirm_msg)

    # ── Main loop ─────────────────────────────────────────────────────────────
    def run(self):
        self._sig.status_changed.emit("IDLE")

        # Run self-repair on startup silently — log results but don't speak unless issues found
        startup_issues = diagnose()
        if startup_issues:
            repair_report = self_repair()
            logging.warning(f"[STARTUP] Self-repair: {repair_report}")

        greeting = _get_greeting()
        self._sig.ai_text.emit(greeting)
        self._safe_speak(greeting)
        print(f"\n[ROCKY] Phase 9 Active — say 'goodbye' to exit.\n")

        # ── Background services ───────────────────────────────────────────────

        # Clipboard manager — pushes type+text to a queue, Rocky picks up between turns
        def _on_clip(clip_type: str, text: str):
            msg = _CLIP_MESSAGES.get(clip_type)
            if msg:
                self._clipboard_queue.append((msg, text))
                self._sig.info_text.emit(f"📋 {msg}")
        clipboard_mgr = ClipboardManager(on_clipboard_event=_on_clip)
        clipboard_mgr.start()

        # Passive app observer with desktop notifications
        try:
            from plyer import notification as _notif

            def _notify(msg: str):
                try:
                    _notif.notify(title="Rocky", message=msg, app_name="Rocky", timeout=5)
                except Exception:
                    pass
        except ImportError:
            _notify = lambda _: None

        def _on_obs(msg: str):
            self._sig.observation.emit(msg)
            self._sig.info_text.emit(msg)
            _notify(msg)

        observer = AppObserver(on_observation=_on_obs)
        observer.start()

        wake = WakeWordDetector()
        if ENABLE_WAKE_WORD:
            wake.start()

        # ── Main conversation loop ────────────────────────────────────────────
        while True:
            try:
                # Flush any clipboard observation before next listen cycle
                if self._clipboard_queue:
                    clip_msg, clip_text = self._clipboard_queue.pop(0)
                    self._sig.ai_text.emit(clip_msg)
                    self._safe_speak(clip_msg)
                    # Store in context so Rocky knows what was copied
                    add_to_history("(clipboard)", clip_text[:200])

                # Wake word gate
                if ENABLE_WAKE_WORD:
                    self._sig.status_changed.emit("STANDBY")
                    if not wake.wait_for_wake():
                        continue
                    self._safe_speak("Yes?")

                # Listen
                self._sig.status_changed.emit("LISTENING")
                user_input, raw_audio = listen(on_level=lambda lvl: self._sig.wave_tick.emit(lvl))
                self._sig.status_changed.emit("IDLE")

                if not user_input or not user_input.strip():
                    continue

                # Voice emotion analysis (runs on the recorded audio, lightweight)
                if raw_audio is not None:
                    voice_analysis = analyze_voice_features(raw_audio)
                    voice_insight = get_voice_insight(voice_analysis)
                    if voice_insight:
                        self._sig.info_text.emit(f"🎤 {voice_analysis['label'].title()}")
                        # Don't interrupt every time — only proactively speak if exhausted
                        if voice_analysis["label"] == "exhausted":
                            self._sig.ai_text.emit(voice_insight)
                            self._safe_speak(voice_insight)

                self._sig.user_text.emit(user_input)
                print(f"USER : {user_input}")
                low = user_input.lower()

                # ── Pending confirmations ─────────────────────────────────────
                if self._pending_script:
                    if any(w in low for w in ("proceed", "yes", "do it", "execute", "run it")):
                        script = self._pending_script
                        self._pending_script = None
                        output = execute_script(script.get("code", ""), script.get("language", "python"))
                        resp = f"Done. Output: {output[:120]}"
                        _respond(self._sig, user_input, resp)
                        self._sig.info_text.emit(output[:90])
                        self._safe_speak(resp)
                        continue
                    elif any(w in low for w in ("cancel", "no", "abort", "stop")):
                        self._pending_script = None
                        resp = "Script cancelled."
                        _respond(self._sig, user_input, resp)
                        self._safe_speak(resp)
                        continue

                if self._pending_kill:
                    if any(w in low for w in ("yes", "do it", "kill it", "terminate", "proceed")):
                        proc_name = self._pending_kill
                        self._pending_kill = None
                        result = kill_process_by_name(proc_name)
                        _respond(self._sig, user_input, result)
                        self._safe_speak(result)
                        continue
                    else:
                        self._pending_kill = None
                        resp = "Termination cancelled."
                        _respond(self._sig, user_input, resp)
                        self._safe_speak(resp)
                        continue

                if self._pending_sys:
                    if any(w in low for w in ("yes", "confirm", "do it", "proceed", "go ahead")):
                        action = self._pending_sys
                        self._pending_sys = None
                        execute_action({"intent": "system_control", "action": action})
                        resp = f"{action.title()} confirmed. Executing."
                        _respond(self._sig, user_input, resp)
                        self._safe_speak(resp)
                        continue
                    else:
                        self._pending_sys = None
                        resp = "Action cancelled. Systems unchanged."
                        _respond(self._sig, user_input, resp)
                        self._safe_speak(resp)
                        continue

                if self._pending_plugin:
                    if any(w in low for w in ("yes", "save it", "proceed", "do it", "confirm")):
                        plugin = self._pending_plugin
                        self._pending_plugin = None
                        result = save_plugin(plugin["filename"], plugin["code"])
                        _respond(self._sig, user_input, result)
                        self._safe_speak(result)
                        continue
                    else:
                        self._pending_plugin = None
                        resp = "Plugin discarded."
                        _respond(self._sig, user_input, resp)
                        self._safe_speak(resp)
                        continue

                # ── Hard commands ─────────────────────────────────────────────
                if any(kw in low for kw in ("shut down rocky", "goodbye", "exit rocky")):
                    self._safe_speak("Shutting down. Optimal choice.")
                    clipboard_mgr.stop()
                    observer.stop()
                    wake.stop()
                    break

                if any(kw in low for kw in ("export conversation", "save log", "export history")):
                    res = export_history()
                    self._sig.info_text.emit(res)
                    _respond(self._sig, user_input, res)
                    self._safe_speak(res)
                    continue

                if any(kw in low for kw in ("skip track", "next song", "previous track",
                                             "pause spotify", "resume spotify", "volume to")):
                    res = spotify_control(low)
                    _respond(self._sig, user_input, res)
                    self._safe_speak(res)
                    continue

                if any(kw in low for kw in ("diagnose", "self repair", "run diagnostics",
                                             "check yourself", "fix yourself")):
                    res = self_repair()
                    _respond(self._sig, user_input, res)
                    self._sig.info_text.emit(res[:90])
                    self._safe_speak(res)
                    continue

                if any(kw in low for kw in ("who is using my ram", "what's using my cpu",
                                             "system is slow", "why is my computer lagging",
                                             "top processes")):
                    res = describe_top_processes()
                    _respond(self._sig, user_input, res)
                    self._safe_speak(res)
                    # Ask if they want to kill the top culprit
                    stressed, reason = is_system_stressed()
                    if stressed:
                        parts = res.split(":")
                        if len(parts) > 1:
                            proc_name = parts[1].strip().split(" ")[0]
                            self._pending_kill = proc_name
                            follow = f"{reason}. Say yes to terminate {proc_name} or no to leave it."
                            self._sig.ai_text.emit(follow)
                            self._safe_speak(follow)
                    continue

                if any(kw in low for kw in ("terminate", "kill process", "close process")):
                    # Extract process name from command: "kill chrome" → "chrome"
                    import re
                    m = re.search(r'(kill|terminate|close)\s+(\w+)', low)
                    if m:
                        proc_name = m.group(2)
                        self._pending_kill = proc_name
                        confirm = f"About to kill {proc_name}. Say yes to proceed or no to cancel."
                        _respond(self._sig, user_input, confirm)
                        self._safe_speak(confirm)
                    else:
                        resp = "Which process should I terminate? Name the app."
                        _respond(self._sig, user_input, resp)
                        self._safe_speak(resp)
                    continue

                if any(kw in low for kw in ("how much did i spend", "total expenses",
                                             "spending this", "finance", "expense breakdown")):
                    res = query_finance(user_input)
                    _respond(self._sig, user_input, res)
                    self._sig.info_text.emit(res[:90])
                    self._safe_speak(res)
                    continue

                if any(p in low for p in _RESET_PHRASES):
                    save_memory({"user_preferences": {}, "habits": {}, "history": [], "last_emotion": "neutral"})
                    resp = "Memory cleared. Starting fresh."
                    self._sig.ai_text.emit(resp)
                    self._safe_speak(resp)
                    continue

                if any(p in low for p in ("what can you do", "help", "capabilities")):
                    self._sig.ai_text.emit(_HELP_TEXT)
                    self._safe_speak(_HELP_TEXT)
                    continue

                # ── Self-Evolution: "I need a new capability to..." ───────────
                if any(t in low for t in ("create a plugin", "make a new capability",
                                           "i need a new feature", "build me a plugin",
                                           "teach yourself", "learn to",
                                           "make yourself able to", "evolve")):
                    self._sig.ai_text.emit("Generating a new plugin. Stand by.")
                    self._safe_speak("Generating a new plugin. Stand by.")
                    result = generate_plugin(user_input)
                    if "error" in result:
                        _respond(self._sig, user_input, result["error"])
                        self._safe_speak(result["error"])
                    else:
                        self._pending_plugin = result
                        preview = f"Plugin ready: {result['filename']}. Keywords: {', '.join(result['keywords'][:3])}. Say yes to save or no to discard."
                        _respond(self._sig, user_input, preview)
                        self._sig.info_text.emit(f"Plugin: {result['filename']}")
                        self._safe_speak(preview)
                    continue

                if any(t in low for t in ("purge memory", "wipe memory", "erase my data", "delete memory")):
                    purge_memory()
                    vector_memory.clear()
                    resp = "Memory wiped. I have no recollection of past events."
                    _respond(self._sig, user_input, resp)
                    self._safe_speak(resp)
                    continue

                if any(t in low for t in ("clean up my desktop", "organize my desktop", "fix my desktop")):
                    folder = os.path.join(os.path.expanduser("~"), "Desktop")
                    res = organize_folder(folder)
                    _respond(self._sig, user_input, res)
                    self._safe_speak(res)
                    continue

                if any(t in low for t in ("clean up my downloads", "organize my downloads", "fix my downloads")):
                    folder = os.path.join(os.path.expanduser("~"), "Downloads")
                    res = organize_folder(folder)
                    _respond(self._sig, user_input, res)
                    self._safe_speak(res)
                    continue

                if any(t in low for t in ("audit file", "audit the file", "audit code in")):
                    import re
                    m = re.search(r"audit\s+(?:file|the file|code in)\s+([a-zA-Z0-9_\-\.]+)", low)
                    if m:
                        filename = m.group(1).strip()
                        self._sig.ai_text.emit(f"Auditing {filename}...")
                        res = audit_file(filename)
                        _respond(self._sig, user_input, res)
                        self._safe_speak(res)
                    else:
                        resp = "Which file should I audit? Please provide the filename."
                        _respond(self._sig, user_input, resp)
                        self._safe_speak(resp)
                    continue

                if any(t in low for t in ("what changed in git", "git status", "repo status", "summarize my changes")):
                    self._sig.ai_text.emit("Analyzing git diff...")
                    res = summarize_repo_changes()
                    _respond(self._sig, user_input, res)
                    self._sig.info_text.emit(res[:90])
                    self._safe_speak(res)
                    continue

                if any(t in low for t in ("run a script", "write a script", "execute code")):
                    self._handle_terminal(user_input)
                    continue

                if any(t in low for t in ("learn my files", "ingest my", "read my folder",
                                           "scan my documents", "index my files")):
                    from brain.file_rag import ingest_folder
                    folder = os.path.join(os.path.expanduser("~"), "Documents")
                    self._sig.info_text.emit(f"Ingesting: {folder}")
                    self._safe_speak("Scanning your documents folder. This may take a moment.")
                    stats = _pool.submit(ingest_folder, folder).result()
                    resp = f"Ingested {stats.get('files_processed', 0)} files, {stats.get('chunks_added', 0)} chunks stored."
                    _respond(self._sig, user_input, resp)
                    self._sig.info_text.emit(resp)
                    self._safe_speak(resp)
                    continue

                # ── Emotion + Memory ──────────────────────────────────────────
                set_emotion(detect_emotion(user_input))
                memory  = load_memory()
                history = memory.get("history", [])

                # ── Intent detect → handle ────────────────────────────────────
                self._sig.status_changed.emit("THINKING")
                keyword_intent = detect_intent(user_input)

                if keyword_intent and keyword_intent["intent"] == "reminder":
                    self._handle_reminder(user_input, keyword_intent)
                    continue

                if keyword_intent:
                    # ── Dangerous action gate ─────────────────────────────────
                    if keyword_intent.get("needs_confirmation"):
                        action = keyword_intent["action"]
                        self._pending_sys = action
                        confirm = f"{action.title()} requested. Are you sure? Say yes to confirm."
                        _respond(self._sig, user_input, confirm)
                        self._safe_speak(confirm)
                        continue

                    self._handle_keyword_intent(user_input, keyword_intent, history)
                else:
                    response_text = self._handle_chat(user_input, history)
                    _respond(self._sig, user_input, response_text)
                    self._safe_speak(response_text)

                # Proactive habit check every turn (lightweight dict lookup)
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

    # Stats timer lives on the Qt main thread — no leaked daemon threads
    def _update_stats():
        stats = get_system_stats()
        signals.info_text.emit(stats)
        
        # Thermal UI Glitch
        from actions.process_control import is_system_stressed
        stressed, _ = is_system_stressed()
        window.set_stressed(stressed)

    stats_timer = QTimer()
    stats_timer.timeout.connect(_update_stats)
    stats_timer.start(12_000)   # every 12 seconds, non-blocking

    thread = QThread()
    worker = VoiceWorker(signals)
    worker.moveToThread(thread)

    thread.started.connect(worker.run)
    worker.finished.connect(thread.quit)
    worker.finished.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)
    worker.finished.connect(app.quit)
    worker.finished.connect(stats_timer.stop)
    thread.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
