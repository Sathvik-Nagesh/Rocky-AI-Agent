"""
Spotify Control via Spotipy.
Requires SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, and SPOTIPY_REDIRECT_URI.
"""

import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import logging

# 🛡️ SECURITY: No hardcoded fallbacks to prevent accidental commits of keys
CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:8888/callback")

_sp = None

def _get_spotify():
    global _sp
    if _sp: return _sp
    
    if not CLIENT_ID or not CLIENT_SECRET:
        return None
        
    try:
        scope = "user-modify-playback-state user-read-playback-state"
        _sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            redirect_uri=REDIRECT_URI,
            scope=scope
        ))
        return _sp
    except Exception as e:
        logging.error(f"Spotify Auth failed: {e}")
        return None

def spotify_control(command: str) -> str:
    """High-level Spotify controller."""
    sp = _get_spotify()
    if not sp:
        return "Spotify not configured. Please set your credentials in brain/spotify_control.py."

    cmd = command.lower()
    try:
        if "skip" in cmd or "next" in cmd:
            sp.next_track()
            return "Skipped to the next track."
        elif "back" in cmd or "previous" in cmd:
            sp.previous_track()
            return "Going back."
        elif "pause" in cmd or "stop" in cmd:
            sp.pause_playback()
            return "Spotify paused."
        elif "play" in cmd or "resume" in cmd:
            sp.start_playback()
            return "Resuming Spotify."
        elif "volume" in cmd:
            # Simple volume extraction "volume to 50"
            import re
            m = re.search(r'(\d+)', cmd)
            if m:
                vol = int(m.group(1))
                sp.volume(min(100, max(0, vol)))
                return f"Volume set to {vol}%."
        return "Spotify command not recognized."
    except Exception as e:
        return f"Spotify error: {e}"
