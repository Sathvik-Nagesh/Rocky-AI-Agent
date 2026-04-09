"""
Self-Repair Logic.
Rocky reads his own rocky.log, detects recurring errors,
and automatically adjusts internal settings to self-correct.
"""

import os
import re
import logging
from collections import Counter

LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "rocky.log")


def _tail(path: str, lines: int = 200) -> list[str]:
    """Read the last N lines of a file efficiently."""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.readlines()[-lines:]
    except FileNotFoundError:
        return []


def diagnose() -> dict:
    """
    Analyse the log for common failure patterns.
    Returns a dict with detected issues and recommended actions.
    """
    tail = _tail(LOG_FILE)
    issues = {}

    # Count JSON parse failures
    json_fails = sum(1 for l in tail if "Failed strict JSON" in l or "parse JSON" in l.lower())
    if json_fails >= 3:
        issues["json_parse"] = json_fails

    # Count LLM request failures
    llm_fails = sum(1 for l in tail if "LLM request failed" in l)
    if llm_fails >= 2:
        issues["llm_connection"] = llm_fails

    # Count voice loop errors
    voice_errs = sum(1 for l in tail if "Voice loop error" in l)
    if voice_errs >= 2:
        issues["voice_loop"] = voice_errs

    # Count recording errors
    rec_errs = sum(1 for l in tail if "Recording/transcription error" in l)
    if rec_errs >= 2:
        issues["recording"] = rec_errs

    return issues


def self_repair() -> str:
    """
    Detect issues from logs and return a report of what was fixed.
    In critical cases, automatically adjusts config values at runtime.
    """
    import config

    issues = diagnose()
    if not issues:
        return "Diagnostics clean. All systems nominal."

    report_parts = []

    if "json_parse" in issues:
        count = issues["json_parse"]
        # Lower temperature slightly to make the LLM more deterministic
        old_temp = config.LLM_TEMPERATURE
        config.LLM_TEMPERATURE = max(0.3, old_temp - 0.1)
        report_parts.append(
            f"JSON parse failures detected ({count}x). "
            f"Reduced LLM temperature from {old_temp:.2f} to {config.LLM_TEMPERATURE:.2f} for more precise output."
        )

    if "llm_connection" in issues:
        count = issues["llm_connection"]
        report_parts.append(
            f"LLM connection failures ({count}x). "
            "Verify Ollama is running: open a terminal and run `ollama serve`."
        )

    if "voice_loop" in issues:
        count = issues["voice_loop"]
        report_parts.append(
            f"Voice loop exceptions detected ({count}x). "
            "Check rocky.log for the specific exception trace."
        )

    if "recording" in issues:
        count = issues["recording"]
        report_parts.append(
            f"Recording errors ({count}x). "
            "Check microphone permissions and sounddevice installation."
        )

    full_report = " | ".join(report_parts)
    logging.info(f"[SELF-REPAIR] {full_report}")
    return full_report
