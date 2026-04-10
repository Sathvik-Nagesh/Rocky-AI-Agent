import pygetwindow as gw
import pyautogui
import pyperclip
import logging
import time

def sniff_active_terminal() -> str:
    """Attempt to capture the content of the currently focused terminal window."""
    try:
        active = gw.getActiveWindow()
        if not active: return ""
        
        # Check if the active window looks like a terminal
        title = active.title.lower()
        if any(kw in title for kw in ["terminal", "powershell", "cmd", "bash", "zsh", "vcode"]):
            print(f"[OMNISCIENCE] Focused on: {title}. Scraping buffer...")
            
            # Use Keyboard shortcuts to Copy-All (Ctrl+A, Ctrl+C)
            # Warning: This is disruptive, so we only do it if explicitly asked or during a crash loop.
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.1)
            pyautogui.hotkey('ctrl', 'c')
            time.sleep(0.1)
            # Deselect
            pyautogui.press('right')
            
            buffer = pyperclip.paste()
            return buffer[-2000:] # Return last 2k chars
    except Exception as e:
        logging.error(f"Omniscience sniff failed: {e}")
        
    return ""

def analyze_cli_error(buffer: str) -> str:
    """Analyze terminal buffer for common CLI errors."""
    low = buffer.lower()
    if "error:" in low or "failed" in low or "exception" in low or "traceback" in low:
        from brain.llm import generate_response
        prompt = f"Analyze this terminal buffer and provide a 1-sentence fix for the error seen at the bottom:\n{buffer}"
        return generate_response(prompt, [])
    return ""
