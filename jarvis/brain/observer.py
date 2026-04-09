"""
Contextual App Intelligence — Passive Observation.

Monitors the user's active window in a background thread.
If the user stares at the same app for too long (e.g., VS Code with an error),
Rocky can proactively offer help or suggest a break.
"""

import threading
import time
import logging
from datetime import datetime

try:
    import pygetwindow as gw
    _GW_AVAILABLE = True
except ImportError:
    _GW_AVAILABLE = False
    logging.warning("pygetwindow not installed. Passive observation disabled.")


class AppObserver:
    """Background daemon that tracks app usage patterns."""

    # How many seconds on the same window before Rocky comments
    STALE_THRESHOLD   = 600   # 10 minutes
    CHECK_INTERVAL    = 15    # poll every 15 seconds
    CODING_APPS       = {"code", "visual studio", "pycharm", "intellij", "sublime", "cursor"}
    BROWSER_APPS      = {"chrome", "firefox", "edge", "brave", "opera"}

    def __init__(self, on_observation=None):
        """
        Args:
            on_observation: callable(str) — called from bg thread when Rocky has something to say.
        """
        self._on_observation = on_observation
        self._stop           = threading.Event()
        self._thread         = None
        self._last_title     = ""
        self._same_since     = time.time()
        self._last_nudge     = 0.0   # prevent spam

    def start(self):
        if not _GW_AVAILABLE:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._observe_loop, daemon=True)
        self._thread.start()
        logging.info("AppObserver started.")

    def stop(self):
        self._stop.set()

    def get_active_app(self) -> str:
        """Returns the title of the currently focused window."""
        if not _GW_AVAILABLE:
            return ""
        try:
            win = gw.getActiveWindow()
            return win.title if win else ""
        except Exception:
            return ""

    def _observe_loop(self):
        while not self._stop.is_set():
            try:
                title = self.get_active_app().lower()
                now   = time.time()

                if title != self._last_title:
                    self._last_title = title
                    self._same_since = now
                else:
                    elapsed = now - self._same_since
                    # Only nudge once per 20 minutes
                    if elapsed > self.STALE_THRESHOLD and (now - self._last_nudge > 1200):
                        observation = self._generate_observation(title, elapsed)
                        if observation and self._on_observation:
                            self._on_observation(observation)
                            self._last_nudge = now

            except Exception as e:
                logging.debug(f"AppObserver error: {e}")

            self._stop.wait(self.CHECK_INTERVAL)

    def _generate_observation(self, title: str, elapsed: float) -> str | None:
        minutes = int(elapsed / 60)
        hour    = datetime.now().hour

        # Late night coding
        if hour >= 0 and hour < 5:
            if any(app in title for app in self.CODING_APPS):
                return f"You have been coding for {minutes} minutes. It is past midnight. Rest is a variable you are ignoring."
            return f"Same window for {minutes} minutes at this hour. Consider sleeping."

        # Long coding session
        if any(app in title for app in self.CODING_APPS):
            if "error" in title or "exception" in title or "traceback" in title:
                return f"You have been staring at what appears to be an error for {minutes} minutes. Want me to take a look?"
            return f"Coding for {minutes} minutes straight. A short break improves cognitive output by 15 percent. Is science."

        # Doomscrolling
        if any(app in title for app in self.BROWSER_APPS):
            if minutes > 20:
                return f"You have been browsing for {minutes} minutes. Interesting data, or are you avoiding something?"

        return None
