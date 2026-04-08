"""
Reminder system using threading.Timer.

Reminders fire a voice callback after a delay parsed from the user's utterance.
Stored in memory so they survive if needed; timers are in-process only.
"""
import re
import threading
import logging
from typing import Callable

# Holds active timers so they can be cancelled if needed
_active_timers: list[threading.Timer] = []

def _parse_delay_seconds(text: str) -> int | None:
    """
    Parse natural language duration from text.
    Supports: 'in 5 minutes', 'in 2 hours', 'in 30 seconds'.
    Returns seconds as int, or None if unparsable.
    """
    lowered = text.lower()
    match = re.search(r"in\s+(\d+)\s+(second|minute|hour)s?", lowered)
    if not match:
        return None
    amount = int(match.group(1))
    unit   = match.group(2)
    return {"second": amount, "minute": amount * 60, "hour": amount * 3600}[unit]

def _parse_message(text: str) -> str:
    """Extract what to remind about — text after 'to' or 'about'."""
    lowered = text.lower()
    for keyword in ("to remind me to", "remind me to", "remind me about", "to"):
        idx = lowered.find(keyword)
        if idx != -1:
            chunk = text[idx + len(keyword):].strip()
            # Strip trailing time phrase
            chunk = re.sub(r"\s+in\s+\d+\s+\w+s?\.?$", "", chunk, flags=re.IGNORECASE)
            return chunk.strip(" .")
    return "something important"

def set_reminder(user_input: str, speak_callback: Callable[[str], None]) -> str:
    """
    Parse `user_input` for a delay + message, then fire speak_callback after the delay.
    Returns a human-readable confirmation string.
    """
    delay = _parse_delay_seconds(user_input)
    if delay is None:
        return "Could not parse reminder time. Try saying 'in 5 minutes'."

    message = _parse_message(user_input)

    def _fire():
        speak_callback(f"Reminder: {message}.")

    timer = threading.Timer(delay, _fire)
    timer.daemon = True
    timer.start()
    _active_timers.append(timer)

    minutes = delay // 60
    seconds = delay % 60
    time_str = f"{minutes} minute{'s' if minutes != 1 else ''}" if minutes else f"{seconds} second{'s' if seconds != 1 else ''}"
    logging.info(f"Reminder set: '{message}' in {delay}s")
    return f"Reminder set for {time_str}: {message}."
