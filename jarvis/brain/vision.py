"""
Vision capabilities via PyAutoGUI and LLaVA / Llama3.2-Vision running locally.
Takes a screenshot, encodes it to base64, and prompts the vision LLM.
"""

import os
import base64
import requests
import pyautogui
from io import BytesIO

# Make sure the user runs `ollama pull llava:7b` for this to work natively
VISION_MODEL = "llava:7b" 

def _capture_screen_base64() -> str:
    """Takes a screenshot, saves to buffer, returns base64."""
    img = pyautogui.screenshot()
    
    # Scale down the image heavily to save VRAM and processing time during inference
    img.thumbnail((800, 800))
    
    buffered = BytesIO()
    img.save(buffered, format="JPEG", quality=85)
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def analyze_screen(prompt: str = "What's on this screen? Summarize briefly.") -> str:
    """Sends current screen to local vision LLM."""
    b64_image = _capture_screen_base64()
    
    payload = {
        "model": VISION_MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt,
                "images": [b64_image]
            }
        ],
        "stream": False
    }

    print(f"\n[VISION] Analyzing screenshot using {VISION_MODEL}...")
    try:
        resp = requests.post("http://localhost:11434/api/chat", json=payload, timeout=90)
        resp.raise_for_status()
        return resp.json().get("message", {}).get("content", "").strip()
    except Exception as e:
        print(f"[VISION ERROR] {e}")
        return "Cannot process visual data right now. Either the LLM is busy or llava is not pulled."
