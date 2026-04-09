"""
LLM interface using Ollama /api/chat with native JSON enforcement.

Performance fixes:
  - Semantic memory only queried when query is non-trivial (>20 chars)
  - System prompt cached at module init, not re-read every call
  - Duplicate import time removed
  - Added explicit connection timeout tuning
"""

import os
import requests
import logging
import time
from config import OLLAMA_API_CHAT, MODEL_NAME, LLM_NUM_PREDICT, LLM_NUM_CTX, LLM_TEMPERATURE
from memory.vector_db import vector_memory


def _read_system_prompt() -> str:
    path = os.path.join(os.path.dirname(__file__), "prompt.txt")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception as e:
        logging.error(f"Failed to read prompt.txt: {e}")
        return 'You are Rocky. Respond in JSON: {"intent":"chat","action":null,"response":"..."}'


# Cached once at import — never re-read from disk during runtime
SYSTEM_PROMPT = _read_system_prompt()

# Minimum query length to bother hitting vector DB
_VECTOR_QUERY_MIN_LEN = 20


def generate_response(user_input: str, history: list[dict] | None = None) -> str:
    """
    Send user_input to Ollama /api/chat with conversation history.
    Vector memory is only injected for non-trivial queries (>20 chars).
    """
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Inject last 5 turns of short-term history
    for turn in (history or [])[-5:]:
        messages.append({"role": "user",      "content": str(turn.get("user", ""))})
        messages.append({"role": "assistant", "content": str(turn.get("assistant", ""))})

    # Inject Dynamic Rules (Self-Correction Loop)
    from brain.reflector import get_dynamic_rules
    dynamic_rules = get_dynamic_rules()
    if dynamic_rules:
        messages.append({"role": "system", "content": f"Self-correction rules to follow:\n{dynamic_rules}"})

    # Only query vector DB for substantial inputs — skip for confirmations, short replies
    if len(user_input) > _VECTOR_QUERY_MIN_LEN:
        semantic_context = vector_memory.search_memories(user_input, top_k=2)
        # Also query document RAG for shadow learner context
        from brain.file_rag import query_documents
        doc_context = query_documents(user_input, top_k=2)
        
        combined_context = []
        if semantic_context: combined_context.extend(semantic_context)
        if doc_context: combined_context.extend(doc_context)

        if combined_context:
            messages.append({
                "role": "system",
                "content": f"Relevant past and file context:\n{chr(10).join(combined_context)}"
            })

    messages.append({"role": "user", "content": user_input})

    payload = {
        "model":    MODEL_NAME,
        "messages": messages,
        "stream":   False,
        "format": {
            "type": "object",
            "properties": {
                "intent":   {"type": "string"},
                "action":   {"type": ["string", "null"]},
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
            logging.warning(f"Empty LLM response (attempt {attempt + 1})")
        except Exception as e:
            logging.error(f"LLM request failed (attempt {attempt + 1}): {e}")
        if attempt < retries:
            time.sleep(0.4)

    return '{"intent":"chat","action":null,"response":"Systems struggling. Try again."}'
