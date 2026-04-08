"""
LLM interface using Ollama /api/chat with native JSON enforcement.
llama3.2:3b supports "format":"json" — this eliminates missing-JSON warnings.
"""

import os
import requests
import logging
import time
from config import OLLAMA_API_CHAT, MODEL_NAME, LLM_NUM_PREDICT, LLM_NUM_CTX, LLM_TEMPERATURE

def _read_system_prompt() -> str:
    path = os.path.join(os.path.dirname(__file__), "prompt.txt")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception as e:
        logging.error(f"Failed to read prompt.txt: {e}")
        return 'You are Rocky, a voice assistant. Always respond in valid JSON: {"intent":"chat","action":null,"response":"..."}'

SYSTEM_PROMPT = _read_system_prompt()

def generate_response(user_input: str, history: list[dict] | None = None) -> str:
    """
    Send user_input to Ollama /api/chat with conversation history.
    Uses "format":"json" to enforce structured output at the API level.
    """
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

    for turn in (history or [])[-5:]:
        messages.append({"role": "user",      "content": str(turn.get("user", ""))})
        messages.append({"role": "assistant", "content": str(turn.get("assistant", ""))})

    messages.append({"role": "user", "content": user_input})

    payload = {
        "model":    MODEL_NAME,
        "messages": messages,
        "stream":   False,
        "format":   {
            "type": "object",
            "properties": {
                "intent": {"type": "string"},
                "action": {"type": ["string", "null"]},
                "response": {"type": "string"},
            },
            "required": ["intent", "action", "response"],
        },
        "options": {
            "num_predict": LLM_NUM_PREDICT,
            "num_ctx":     LLM_NUM_CTX,
            "temperature": LLM_TEMPERATURE,
        }
    }

    retries = 2
    for attempt in range(retries + 1):
        try:
            resp = requests.post(OLLAMA_API_CHAT, json=payload, timeout=60)
            resp.raise_for_status()
            text = resp.json().get("message", {}).get("content", "").strip()
            if text:
                return text
            logging.warning(f"Empty LLM response (attempt {attempt+1})")
        except Exception as e:
            logging.error(f"LLM request failed (attempt {attempt+1}): {e}")
        if attempt < retries:
            time.sleep(0.4)

    return '{"intent":"chat","action":null,"response":"Systems struggling. Try again, yes?"}'
