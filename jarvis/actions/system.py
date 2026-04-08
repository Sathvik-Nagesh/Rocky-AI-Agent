import os
import subprocess
import webbrowser
import logging

# ── Known website navigation map ──────────────────────────────────────────────
WEBSITE_MAP = {
    "youtube":    "https://www.youtube.com",
    "google":     "https://www.google.com",
    "github":     "https://www.github.com",
    "netflix":    "https://www.netflix.com",
    "spotify":    "https://open.spotify.com",
    "twitter":    "https://www.twitter.com",
    "instagram":  "https://www.instagram.com",
    "reddit":     "https://www.reddit.com",
    "gmail":      "https://mail.google.com",
    "outlook":    "https://outlook.live.com",
    "linkedin":   "https://www.linkedin.com",
    "amazon":     "https://www.amazon.in",
    "flipkart":   "https://www.flipkart.com",
    "chatgpt":    "https://chat.openai.com",
    "whatsapp":   "https://web.whatsapp.com",
    "maps":       "https://maps.google.com",
    "drive":      "https://drive.google.com",
    "notion":     "https://www.notion.so",
    "figma":      "https://www.figma.com",
}

# ── App launcher commands ──────────────────────────────────────────────────────
_APP_COMMANDS = {
    "chrome":      ["cmd", "/c", "start", "chrome"],
    "notepad":     ["cmd", "/c", "start", "notepad"],
    "calculator":  ["cmd", "/c", "start", "calc"],
    "explorer":    ["cmd", "/c", "start", "explorer"],
    "settings":    ["cmd", "/c", "start", "ms-settings:"],
    "vscode":      ["cmd", "/c", "start", "code"],
    "word":        ["cmd", "/c", "start", "winword"],
    "excel":       ["cmd", "/c", "start", "excel"],
    "paint":       ["cmd", "/c", "start", "mspaint"],
    "terminal":    ["cmd", "/c", "start", "wt"],
    "task_manager":["cmd", "/c", "start", "taskmgr"],
    "control":     ["cmd", "/c", "start", "control"],
}

def open_app(app_name: str):
    """Launch an application by keyword."""
    name = (app_name or "").lower().strip()

    # Apple Music — try multiple methods
    if name in ("apple_music", "apple music", "music"):
        _open_apple_music()
        return

    # Spotify
    if name == "spotify":
        _run(["cmd", "/c", "start", "spotify:"])
        return

    cmd = _APP_COMMANDS.get(name)
    if cmd:
        print(f"[ACTION] Opening {name}")
        _run(cmd)
    else:
        # Last resort: try Windows start
        print(f"[ACTION] Attempting start {name}")
        _run(["cmd", "/c", "start", name])

def _open_apple_music():
    """Try multiple methods to open Apple Music on Windows."""
    print("[ACTION] Opening Apple Music")
    attempts = [
        # Windows Store app protocol
        lambda: _run(["cmd", "/c", "start", "ms-appx://content/"]),
        # Shell app folder launch
        lambda: subprocess.Popen(
            ["explorer.exe", r"shell:AppsFolder\AppleInc.AppleMusicWin_nzyj5cx40ttqa!App"],
            shell=False
        ),
        # iTunes fallback
        lambda: _run(["cmd", "/c", "start", "itunes:"]),
        # Open Apple Music website
        lambda: webbrowser.open("https://music.apple.com"),
    ]
    for attempt in attempts:
        try:
            attempt()
            return
        except Exception:
            continue
    logging.warning("Could not open Apple Music via any method — opening web fallback")
    webbrowser.open("https://music.apple.com")

def navigate_to(url: str):
    """Open a URL directly in the default browser."""
    # Resolve shorthand names
    shorthand = url.lower().strip().rstrip("/").replace("https://www.", "").replace("http://", "")
    if shorthand in WEBSITE_MAP:
        url = WEBSITE_MAP[shorthand]
    elif not url.startswith("http"):
        url = "https://" + url
    print(f"[ACTION] Navigating to {url}")
    webbrowser.open(url)

def play_music(app_name: str):
    open_app(app_name or "apple_music")

def system_control(action: str):
    action = (action or "").lower().strip()
    print(f"[ACTION] System control: {action}")
    _sys_map = {
        "shutdown":    ["cmd", "/c", "shutdown /s /t 5"],
        "restart":     ["cmd", "/c", "shutdown /r /t 5"],
        "reboot":      ["cmd", "/c", "shutdown /r /t 5"],
        "lock":        ["rundll32.exe", "user32.dll,LockWorkStation"],
        "sleep":       ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"],
        "volume_up":   ["nircmd.exe", "changesysvolume", "6553"],
        "volume_down": ["nircmd.exe", "changesysvolume", "-6553"],
        "mute":        ["nircmd.exe", "mutesysvolume", "1"],
        "unmute":      ["nircmd.exe", "mutesysvolume", "0"],
    }
    cmd = _sys_map.get(action)
    if cmd:
        _run(cmd)
    else:
        logging.warning(f"Unknown system action: {action}")

def search_web(query: str):
    if query:
        # Check if query is actually a website name
        q_lower = query.lower().strip()
        if q_lower in WEBSITE_MAP:
            navigate_to(WEBSITE_MAP[q_lower])
            return
        print(f"[ACTION] Searching: {query}")
        webbrowser.open(f"https://www.google.com/search?q={query}")

def open_downloads():
    _open_folder("Downloads")

def open_documents():
    _open_folder("Documents")

def open_desktop():
    _open_folder("Desktop")

def _open_folder(name: str):
    path = os.path.join(os.path.expanduser("~"), name)
    print(f"[ACTION] Opening {name} folder")
    os.startfile(path)

def find_file(filename: str) -> list:
    print(f"[ACTION] Searching for file: {filename}")
    home    = os.path.expanduser("~")
    matches = []
    for root, _, files in os.walk(home):
        for f in files:
            if filename.lower() in f.lower():
                matches.append(os.path.join(root, f))
        if len(matches) >= 5:
            break
    if matches:
        os.startfile(os.path.dirname(matches[0]))
    return matches

def _run(cmd: list):
    try:
        subprocess.Popen(cmd, shell=False,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        logging.error(f"Failed to run {cmd}: {e}")
