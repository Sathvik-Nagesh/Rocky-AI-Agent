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

def open_app(app_name: str, query: str = None):
    """Launch an application by keyword, optionally searching for a query or incognito mode."""
    name = (app_name or "").lower().strip()
    
    # Handle incognito requests
    is_incognito = "incognito" in name or (query and "incognito" in query.lower())

    # Chrome / Browser
    if "chrome" in name or "google" in name or "browser" in name:
        print(f"[ACTION] Opening Chrome {'Incognito' if is_incognito else ''}")
        if is_incognito:
            _run(["cmd", "/c", "start", "chrome", "--incognito", query or "https://www.google.com"])
        elif query:
            search_q = query.lower().replace("search", "").replace("for", "").strip()
            webbrowser.open(f"https://www.google.com/search?q={search_q}")
        else:
            _run(["cmd", "/c", "start", "chrome"])
        return

    # Special protocol handling for UWP/System apps
    protocol_map = {
        "settings": "ms-settings:",
        "calculator": "calc",
        "task_manager": "taskmgr",
        "explorer": "explorer",
        "notepad": "notepad",
        "paint": "mspaint",
        "control": "control",
        "terminal": "wt", 
    }

    # Apple Music
    if name in ("apple_music", "apple music", "music"):
        _open_apple_music(query)
        return

    # YouTube / YouTube Music
    if "youtube" in name:
        print(f"[ACTION] Opening YouTube {'Music' if 'music' in name else ''}")
        if query:
            search_q = query.lower().replace("play", "").replace("start", "").replace("on youtube", "").replace("music", "").strip()
            url = f"https://music.youtube.com/search?q={search_q}" if "music" in name else f"https://www.youtube.com/results?search_query={search_q}"
            webbrowser.open(url)
        else:
            webbrowser.open("https://music.youtube.com" if "music" in name else "https://www.youtube.com")
        return

    # Spotify
    if name == "spotify":
        print("[ACTION] Opening Spotify")
        if query:
            search_q = query.lower().replace("play", "").replace("on spotify", "").strip()
            _run(["cmd", "/c", "start", f"spotify:search:{search_q}"])
        else:
            _run(["cmd", "/c", "start", "spotify:"])
        return

    # Preferred: check protocol map first
    target = protocol_map.get(name)
    if target:
        print(f"[ACTION] Opening {name} via {target}")
        _run(target)
        return

    # Check command map
    cmd = _APP_COMMANDS.get(name)
    if cmd:
        print(f"[ACTION] Opening {name}")
        _run(cmd)
    else:
        # Last resort: try Windows start directly on the name
        print(f"[ACTION] Attempting start {name}")
        _run(name)

def _open_apple_music(query: str = None):
    """Try multiple methods to open Apple Music on Windows. No broken ms-appx links."""
    print("[ACTION] Opening Apple Music")
    
    # If query exists, we usually have to use web for search results reliably
    if query:
        search_q = query.replace("play", "").replace("apple music", "").strip()
        webbrowser.open(f"https://music.apple.com/search?term={search_q}")
        return

    # 1. Try modern Windows Store Package ID via Shell...
    ids = [
        r"AppleInc.AppleMusicWin_nzyj5cx40ttqa!App",
        r"AppleInc.iTunes_nzyj5cx40ttqa!iTunes"
    ]
    
    for package_id in ids:
        try:
            subprocess.Popen(["explorer.exe", f"shell:AppsFolder\\{package_id}"])
            return
        except Exception:
            continue

    # 2. Try protocol handler
    try:
        _run(["cmd", "/c", "start", "musics:"]) # Apple Music protocol
        return
    except Exception:
        pass

    # 3. Web Fallback
    logging.warning("Local Apple Music app not found — opening web player")
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

def play_music(app_name: str, query: str = None):
    open_app(app_name or "apple_music", query=query)

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

def _run(cmd: str | list):
    """Execute a command string or list with the most robust Windows handler."""
    try:
        import os
        if isinstance(cmd, str):
            # os.startfile is best for apps, protocols, and files on Windows
            os.startfile(cmd)
        else:
            # shell=True required for builtins like 'start' to work reliably
            subprocess.Popen(cmd, shell=True, 
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        logging.error(f"Failed to run {cmd}: {e}")

def get_active_work_context() -> str:
    """Detect active window and return its title + suspected task context."""
    try:
        active = pygetwindow.getActiveWindow()
        if not active: return "Unknown task."
        title = active.title
        if "visual studio code" in title.lower():
            # Try to extract the filename from the title
            filename = title.split("-")[0].strip()
            return f"Coding in VS Code: {filename}"
        elif "chrome" in title.lower() or "edge" in title.lower():
            return f"Browsing: {title}"
        return f"Working in: {title}"
    except Exception:
        return "Focusing on current workspace."

def generate_daily_standup() -> str:
    """Summarize system usage, git activity, and file changes for a status report."""
    context = load_memory()
    history = context.get("history", [])
    
    # Analyze recent actions
    actions = [h for h in history if h.get("intent") and h["intent"] != "chat"]
    app_usage = {}
    for a in actions:
        name = a.get("action", "unknown")
        app_usage[name] = app_usage.get(name, 0) + 1
    
    top_apps = sorted(app_usage.items(), key=lambda x: x[1], reverse=True)[:3]
    apps_str = ", ".join([f"{a[0]}" for a in top_apps])
    
    report = f"Daily Standup Architect Report:\n"
    report += f"- Primary focus: {apps_str if apps_str else 'General research'}\n"
    report += f"- Total tasks automated by Rocky today: {len(actions)}\n"
    report += f"- Recent work folder: {os.path.basename(os.getcwd())}\n"
    report += "Ready to push these updates or export for your team."
    return report
