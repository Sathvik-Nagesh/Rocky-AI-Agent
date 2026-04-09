"""
Intent detector — Phase 10: context-aware, negation-safe, confirmation-gated.

Key fixes from Phase 9:
  - NEGATION GUARD: "I am not asleep" no longer triggers sleep mode.
    All system-control and destructive keywords now require either:
      a) A trigger verb ("put", "set", "turn", "go to", "make it") before the keyword, OR
      b) The keyword to NOT be preceded by negation words ("not", "don't", "no", "isn't", "never").
  - DANGEROUS ACTION CONFIRMATION: shutdown, restart, sleep return a special
    "needs_confirmation" flag so main.py can ask "Are you sure?" before executing.
  - PRIORITY ORDER: Plugins → Vision → Website nav → App open → Music →
    System (with guards) → Weather → Reminders → Files → Search (last).
"""

import re
from actions.system import WEBSITE_MAP

# Words that negate the following keyword
_NEGATION = {"not", "don't", "dont", "no", "never", "isn't", "isnt", "wasn't", "wasnt",
             "can't", "cant", "shouldn't", "shouldnt", "won't", "wont", "without", "ain't"}

# Actions that require explicit confirmation before executing
_DANGEROUS_ACTIONS = {"shutdown", "restart", "sleep"}


def _has_negation_before(text: str, keyword: str) -> bool:
    """Check if any negation word appears within 4 words before the keyword."""
    idx = text.find(keyword)
    if idx < 0:
        return False
    # Get the 4 words before the keyword position
    before = text[:idx].split()[-4:]
    return bool(_NEGATION & set(before))


def _has_trigger_verb(text: str, keyword: str) -> bool:
    """Check if a system-control trigger verb appears before the keyword."""
    triggers = ("put", "set", "make", "switch to", "go to", "turn on", "turn off",
                "enable", "activate", "initiate", "do a", "please")
    idx = text.find(keyword)
    if idx < 0:
        return False
    before = text[:idx].strip()
    return any(t in before for t in triggers)


def detect_intent(text: str) -> dict | None:
    lowered = text.lower().strip()

    # ── Plugins (Dynamic Extensions) ──────────────────────────────────────────
    from actions.plugins_manager import run_plugin
    plugin_res = run_plugin(lowered)
    if plugin_res is not None:
        return {"intent": "plugin_action", "action": lowered, "response_override": plugin_res}

    # ── Vision / Screen context ───────────────────────────────────────────────
    _vision_phrases = [
        "what's on my screen", "what is on my screen", "look at my screen",
        "read my screen", "analyze my screen", "what do you see",
        "describe my screen", "screenshot"
    ]
    if any(t in lowered for t in _vision_phrases):
        return {"intent": "vision", "action": lowered}

    # ── Website navigation (must be before search) ────────────────────────────
    _nav_triggers = ("open", "go to", "take me to", "navigate to", "launch", "visit")
    for trigger in _nav_triggers:
        if trigger in lowered:
            for site, url in WEBSITE_MAP.items():
                if site in lowered:
                    return {"intent": "navigate", "action": url}

    # "youtube.com" / "open youtube.com"
    url_match = re.search(r"([\w-]+\.(com|org|net|io|co|in|dev))", lowered)
    if url_match:
        domain = url_match.group(0)
        root   = domain.split(".")[0]
        url    = WEBSITE_MAP.get(root, f"https://www.{domain}")
        return {"intent": "navigate", "action": url}

    # ── Open desktop app ──────────────────────────────────────────────────────
    _open_triggers = {"open", "launch", "start", "run", "bring up", "pull up"}
    _apps = {
        "chrome":       ["chrome", "google chrome", "browser"],
        "notepad":      ["notepad", "text editor"],
        "apple_music":  ["apple music"],
        "spotify":      ["spotify"],
        "calculator":   ["calculator", "calc"],
        "explorer":     ["file explorer"],
        "settings":     ["settings", "control panel"],
        "vscode":       ["vs code", "visual studio code", "vscode"],
        "word":         ["microsoft word", "ms word"],
        "excel":        ["excel", "spreadsheet"],
        "paint":        ["paint", "mspaint"],
        "terminal":     ["terminal", "command prompt", "cmd", "powershell"],
        "task_manager": ["task manager"],
        "discord":      ["discord"],
        "telegram":     ["telegram"],
        "slack":        ["slack"],
        "zoom":         ["zoom"],
        "steam":        ["steam"],
        "obs":          ["obs", "obs studio"],
        "blender":      ["blender"],
        "vlc":          ["vlc", "media player"],
    }
    words = set(lowered.split())
    if _open_triggers & words:
        for app_key, keywords in _apps.items():
            if any(kw in lowered for kw in keywords):
                return {"intent": "open_app", "action": app_key}

    # ── Play music ────────────────────────────────────────────────────────────
    if re.search(r"\b(play|start|put on|turn on)\b.{0,15}\b(music|song|track|playlist)\b", lowered):
        return {"intent": "play_music", "action": "apple_music"}
    if any(kw in lowered for kw in ["music please", "some music", "play something"]):
        return {"intent": "play_music", "action": "apple_music"}

    # ── System control (NEGATION-SAFE + CONFIRMATION-GATED) ───────────────────
    _sys = {
        "shutdown":    ["shut down the computer", "shutdown my pc", "power off my computer",
                        "turn off the computer", "turn off my pc", "shut down my computer"],
        "restart":     ["restart the computer", "restart my pc", "reboot the computer",
                        "reboot my computer", "restart my system"],
        "lock":        ["lock the screen", "lock my screen", "lock my computer", "lock screen",
                        "lock my pc"],
        "sleep":       ["put computer to sleep", "put my pc to sleep", "go to sleep mode",
                        "sleep mode", "hibernate my computer", "hibernate my pc"],
        "volume_up":   ["volume up", "turn up the volume", "louder", "increase volume",
                        "raise the volume"],
        "volume_down": ["volume down", "lower the volume", "lower volume", "quieter",
                        "turn it down", "decrease volume", "reduce volume"],
        "mute":        ["mute the sound", "mute audio", "mute everything", "mute my computer"],
        "unmute":      ["unmute", "unmute audio", "unmute sound"],
    }

    for action_key, phrases in _sys.items():
        for phrase in phrases:
            if phrase in lowered:
                # Check negation — "don't shut down" / "I am not sleeping"
                if _has_negation_before(lowered, phrase):
                    break  # Skip this entire action_key, fall through to chat

                result = {"intent": "system_control", "action": action_key}

                # Gate dangerous actions behind confirmation
                if action_key in _DANGEROUS_ACTIONS:
                    result["needs_confirmation"] = True

                return result

    # Volume shorthand — only if the user is clearly commanding (not just mentioning)
    if "volume" in lowered and ("up" in lowered or "louder" in lowered or "increase" in lowered):
        return {"intent": "system_control", "action": "volume_up"}
    if "volume" in lowered and ("down" in lowered or "quieter" in lowered or "lower" in lowered or "decrease" in lowered):
        return {"intent": "system_control", "action": "volume_down"}

    # Standalone "mute" — but ONLY if it looks like a command, not conversation
    if re.search(r"^(please\s+)?mute\b", lowered):
        return {"intent": "system_control", "action": "mute"}
    if re.search(r"^(please\s+)?unmute\b", lowered):
        return {"intent": "system_control", "action": "unmute"}

    # ── Weather ────────────────────────────────────────────────────────────────
    if any(t in lowered for t in ["weather", "temperature outside", "how hot is it",
                                   "how cold is it", "forecast", "is it raining"]):
        match = re.search(r"(?:weather|temperature|forecast)\s+(?:in|for|at)\s+([\w\s]+?)(?:\?|$|,)", lowered)
        location = match.group(1).strip() if match else "auto"
        return {"intent": "weather", "action": location}

    # ── Reminders ─────────────────────────────────────────────────────────────
    if re.search(r"\bremind\b|\bset.{0,10}reminder\b|\bset.{0,10}alarm\b|\bwake me\b", lowered):
        return {"intent": "reminder", "action": text}

    # ── File operations ───────────────────────────────────────────────────────
    if "downloads" in lowered and any(t in lowered for t in ["open", "show", "go to", "my"]):
        return {"intent": "file_operation", "action": "downloads"}
    if "documents" in lowered and any(t in lowered for t in ["open", "show", "go to", "my"]):
        return {"intent": "file_operation", "action": "documents"}
    if "desktop" in lowered and any(t in lowered for t in ["open", "show", "go to", "my"]):
        return {"intent": "file_operation", "action": "desktop"}

    find_match = re.search(
        r"(?:find|locate|search for)\s+(?:a\s+)?file\s+(?:named|called)?\s+(.+?)(?:\?|$)",
        lowered
    )
    if find_match:
        return {"intent": "file_operation", "action": f"find:{find_match.group(1).strip()}"}

    # ── Web search — LAST, most generic ──────────────────────────────────────
    _search_ptns = [
        r"search (?:for|google for|on google for|the internet for|online for)\s+(.+)",
        r"look up\s+(.+)",
        r"(?:find|google)\s+(?:information|info|articles?|news|videos?)?\s+(?:about|on|for)?\s+(.+)",
    ]
    for pat in _search_ptns:
        m = re.search(pat, lowered)
        if m:
            query = m.group(1).strip().rstrip("?. ")
            if query in WEBSITE_MAP:
                return {"intent": "navigate", "action": WEBSITE_MAP[query]}
            return {"intent": "search", "action": query}

    return None
