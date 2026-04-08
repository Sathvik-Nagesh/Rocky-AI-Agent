import json
import os
import logging

_DIR = os.path.dirname(os.path.abspath(__file__))
MEMORY_FILE = os.path.join(_DIR, "memory.json")

_DEFAULTS = {
    "user_preferences": {},
    "habits": {},
    "history": [],
    "last_emotion": "neutral",
}

def load_memory() -> dict:
    if not os.path.exists(MEMORY_FILE):
        return dict(_DEFAULTS)
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            for key, default in _DEFAULTS.items():
                data.setdefault(key, default)
            return data
    except (json.JSONDecodeError, IOError) as e:
        logging.error(f"Memory load failed: {e}. Resetting.")
        return dict(_DEFAULTS)

def save_memory(memory: dict):
    """Atomic write: write to .tmp first, then rename — crash-safe."""
    dir_ = os.path.dirname(MEMORY_FILE)
    try:
        import tempfile
        with tempfile.NamedTemporaryFile("w", dir=dir_, delete=False,
                                         suffix=".tmp", encoding="utf-8") as f:
            json.dump(memory, f, indent=2)
            tmp_path = f.name
        os.replace(tmp_path, MEMORY_FILE)  # atomic on Windows + POSIX
    except IOError as e:
        logging.error(f"Memory save failed: {e}")

def add_to_history(user: str, assistant: str):
    memory = load_memory()
    memory["history"].append({"user": user, "assistant": assistant})
    memory["history"] = memory["history"][-10:]
    save_memory(memory)

def update_habit(key: str, increment: int = 1):
    memory = load_memory()
    memory["habits"][key] = memory["habits"].get(key, 0) + increment
    save_memory(memory)

def set_preference(key: str, value):
    memory = load_memory()
    memory["user_preferences"][key] = value
    save_memory(memory)

def get_preference(key: str, default=None):
    return load_memory()["user_preferences"].get(key, default)

def set_emotion(emotion: str):
    memory = load_memory()
    memory["last_emotion"] = emotion
    save_memory(memory)

def build_context_string(memory: dict) -> str:
    """Compact context string injected into the LLM prompt."""
    prefs   = memory.get("user_preferences", {})
    habits  = memory.get("habits", {})
    history = memory.get("history", [])
    emotion = memory.get("last_emotion", "neutral")

    recent = "\n".join(
        f"  U: {h['user']}\n  R: {h['assistant']}"
        for h in history[-3:]
    ) or "  None yet."

    pref_str  = ", ".join(f"{k}={v}" for k, v in prefs.items())  or "None"
    habit_str = ", ".join(f"{k}={v}" for k, v in habits.items()) or "None"

    return (
        f"Preferences: {pref_str}\n"
        f"Habits: {habit_str}\n"
        f"Last detected emotion: {emotion}\n"
        f"Recent:\n{recent}"
    )
