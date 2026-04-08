"""
Keyword-based intent detector — fast, reliable, runs before LLM.
Order is critical: specific patterns first, generic search last.
"""
import re
from actions.system import WEBSITE_MAP

def detect_intent(text: str) -> dict | None:
    lowered = text.lower().strip()

    # ── Website navigation (must be before search) ────────────────────────────
    # "open youtube" / "go to youtube" / "take me to youtube"
    _nav_triggers = ("open", "go to", "take me to", "navigate to", "launch", "visit")
    for trigger in _nav_triggers:
        if trigger in lowered:
            for site, url in WEBSITE_MAP.items():
                if site in lowered:
                    return {"intent": "navigate", "action": url}

    # "youtube.com" typed / "open youtube.com"
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

    # ── System control ────────────────────────────────────────────────────────
    _sys = {
        "shutdown":    ["shut down", "shutdown", "power off", "turn off the computer"],
        "restart":     ["restart", "reboot", "restart the computer"],
        "lock":        ["lock", "lock the screen", "lock screen"],
        "sleep":       ["sleep", "go to sleep", "hibernate"],
        "volume_up":   ["volume up", "turn up the volume", "louder", "increase volume"],
        "volume_down": ["volume down", "lower the volume", "lower volume", "quieter", "turn it down"],
        "mute":        ["mute", "silence"],
        "unmute":      ["unmute"],
    }
    for action_key, kws in _sys.items():
        if any(kw in lowered for kw in kws):
            return {"intent": "system_control", "action": action_key}

    # ── Weather ────────────────────────────────────────────────────────────────
    if any(t in lowered for t in ["weather", "temperature", "how hot", "how cold", "forecast", "raining"]):
        match = re.search(r"(?:weather|temperature|forecast)\s+(?:in|for|at)\s+([\w\s]+?)(?:\?|$|,)", lowered)
        location = match.group(1).strip() if match else "auto"
        return {"intent": "weather", "action": location}

    # ── Reminders ─────────────────────────────────────────────────────────────
    if re.search(r"\bremind\b|\bset.{0,10}reminder\b", lowered):
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
            # If the query is a known site name, navigate there instead
            if query in WEBSITE_MAP:
                return {"intent": "navigate", "action": WEBSITE_MAP[query]}
            return {"intent": "search", "action": query}

    return None
