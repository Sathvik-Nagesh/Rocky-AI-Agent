import json
import re
import logging

def _repair_json(text: str) -> str:
    """Attempt to close a truncated JSON object by counting braces."""
    depth = 0
    for ch in text:
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
    # Append missing closing braces
    return text + ("}" * max(depth, 0))

def extract_json(text: str) -> dict | None:
    """Try progressive strategies to extract a valid JSON dict."""
    text = text.strip()

    # Strip markdown fencing if present
    if text.startswith("```"):
        text = re.sub(r"^```[a-z]*\n?", "", text).rstrip("`").strip()

    # Strategy 1: direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strategy 2: extract first {...} block (handles extra leading text)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            # Strategy 3: try repairing a truncated JSON
            try:
                repaired = _repair_json(match.group())
                return json.loads(repaired)
            except json.JSONDecodeError:
                pass

    return None

def parse_llm_response(text: str) -> dict:
    """Parse LLM output to dict, with guaranteed fallback."""
    if not text:
        return {"intent": "chat", "response": "Response error. Try again, yes?"}

    data = extract_json(text)
    if data and isinstance(data, dict) and "response" in data:
        return data

    logging.error(f"Failed to parse JSON. Raw: {text[:120]}")
    return {"intent": "chat", "response": "Response error. Try again, yes?"}
