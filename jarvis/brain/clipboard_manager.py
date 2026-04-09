"""
Autonomous Clipboard Manager.
Monitors the clipboard in a background thread.
If the user copies a stack trace, long URL, code block, or long text,
Rocky proactively offers context-aware assistance.
"""

import threading
import time
import logging

try:
    import pyperclip
    _CLIP_AVAILABLE = True
except ImportError:
    _CLIP_AVAILABLE = False
    logging.warning("pyperclip not installed. Clipboard manager disabled.")

# Minimum chars before Rocky acts on clipboard content
_MIN_LENGTH = 80
_POLL_INTERVAL = 2.5  # seconds


def _is_likely_sensitive(text: str) -> bool:
    """Heuristic to check if text is a password, API key, or token."""
    t = text.strip()
    # Usually sensitive if it's short, no spaces, high entropy, mixed case + numbers + symbols
    if 8 <= len(t) <= 128 and " " not in t:
        import re
        if re.match(r'^[A-Za-z0-9_-]+$', t) and len(t) > 20:
            return True  # Looks like a base64 token or UUID
        has_upper = bool(re.search(r'[A-Z]', t))
        has_lower = bool(re.search(r'[a-z]', t))
        has_num = bool(re.search(r'[0-9]', t))
        has_sym = bool(re.search(r'[^A-Za-z0-9]', t))
        if has_upper and has_lower and has_num and getattr(t, 'isascii', lambda: True)():
            return True # Looks like a generated password
    return False

def _classify(text: str) -> str | None:
    """Classify clipboard content type. Returns action hint or None."""
    t = text.strip()
    if not t or len(t) < _MIN_LENGTH:
        return None

    if _is_likely_sensitive(t):
        return None

    low = t.lower()

    # Stack trace / error detection
    if any(kw in low for kw in ("traceback", "error:", "exception:", "at line", "file \"")):
        return "stack_trace"

    # URL detection
    if t.startswith("http") and len(t) < 500 and " " not in t[:50]:
        return "url"

    # Code detection (heuristic: lots of indentation, brackets, assignment ops)
    code_signals = t.count("    ") + t.count("def ") + t.count("import ") + t.count("{") + t.count("=>")
    if code_signals >= 3:
        return "code"

    # Long block of text (article, document)
    if len(t) > 400:
        return "long_text"

    return None


class ClipboardManager:
    """
    Background thread that watches clipboard.
    Calls `on_clipboard_event(type, text)` when interesting content is detected.
    """
    def __init__(self, on_clipboard_event=None):
        self._callback = on_clipboard_event
        self._stop     = threading.Event()
        self._thread   = None
        self._last     = ""

    def start(self):
        if not _CLIP_AVAILABLE:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        logging.info("ClipboardManager started.")

    def stop(self):
        self._stop.set()

    def _poll_loop(self):
        while not self._stop.is_set():
            try:
                current = pyperclip.paste()
                if current != self._last and current:
                    self._last = current
                    clip_type = _classify(current)
                    if clip_type and self._callback:
                        self._callback(clip_type, current)
            except Exception as e:
                logging.debug(f"[Clipboard] Poll error: {e}")
            self._stop.wait(_POLL_INTERVAL)
