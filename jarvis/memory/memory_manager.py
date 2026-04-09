"""
Memory manager with in-memory cache.

Performance fix:
  - `load_memory()` now caches to an in-memory dict
  - Cache is only invalidated when `save_memory()` is called
  - Eliminates repeated JSON disk reads during a single conversation turn
"""

import json
import os
import threading

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "memory.json")

_EMPTY = lambda: {"user_preferences": {}, "habits": {}, "history": [], "last_emotion": "neutral"}

_cache: dict | None = None
_cache_lock = threading.Lock()


def load_memory() -> dict:
    """Load memory from cache (fast path) or disk (cold start)."""
    global _cache
    if _cache is not None:
        return _cache
    with _cache_lock:
        if _cache is not None:  # double-check after acquiring lock
            return _cache
        if not os.path.exists(MEMORY_FILE):
            _cache = _EMPTY()
            return _cache
        try:
            with open(MEMORY_FILE, "r") as f:
                _cache = json.load(f)
        except (json.JSONDecodeError, IOError):
            _cache = _EMPTY()
    return _cache


def save_memory(memory: dict):
    """Atomic write to disk + invalidate cache."""
    global _cache
    tmp = MEMORY_FILE + ".tmp"
    with _cache_lock:
        try:
            with open(tmp, "w") as f:
                json.dump(memory, f, indent=2)
            os.replace(tmp, MEMORY_FILE)
            _cache = memory  # update cache with what we wrote
        except Exception as e:
            print(f"[MEMORY] Save failed: {e}")
            try:
                os.remove(tmp)
            except FileNotFoundError:
                pass


def add_to_history(user: str, assistant: str):
    mem = load_memory()
    mem["history"].append({"user": user, "assistant": assistant})
    mem["history"] = mem["history"][-10:]  # keep last 10 turns
    save_memory(mem)


def set_preference(key: str, value):
    mem = load_memory()
    mem.setdefault("user_preferences", {})[key] = value
    save_memory(mem)


def update_habit(key: str):
    mem = load_memory()
    mem.setdefault("habits", {})[key] = mem["habits"].get(key, 0) + 1
    save_memory(mem)


def set_emotion(emotion: str):
    mem = load_memory()
    mem["last_emotion"] = emotion
    save_memory(mem)

def purge_memory():
    """Wipes the short-term JSON memory and drops the ChromaDB collection."""
    global _cache
    import shutil
    with _cache_lock:
        try:
            if os.path.exists(MEMORY_FILE):
                os.remove(MEMORY_FILE)
            _cache = _EMPTY()
        except Exception as e:
            print(f"[MEMORY] Purge JSON failed: {e}")
