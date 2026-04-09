"""
Wolfram Alpha Genius Mode.
Instead of a generic web search, queries Wolfram Alpha for exact, factual answers.
Handles math, science, dates, geography, unit conversion — anything Wolfram knows.
"""

import logging

KEYWORDS = [
    "calculate", "what is the square root", "convert",
    "how many", "solve", "formula for", "equal to",
    "distance from", "population of", "capital of",
    "wolfram", "exact answer", "compute"
]

_app = None

def _get_app():
    global _app
    if _app:
        return _app
    import wolframalpha
    import os
    api_key = os.getenv("WOLFRAM_APP_ID", "")
    if not api_key:
        return None
    _app = wolframalpha.Client(api_key)
    return _app

def execute(query: str) -> str:
    """Query Wolfram Alpha and return the most relevant plaintext answer."""
    client = _get_app()
    if not client:
        return (
            "Wolfram Alpha not configured. "
            "Set the WOLFRAM_APP_ID environment variable with your free API key from developer.wolframalpha.com."
        )
    
    # Strip trigger keywords so only the real question goes to Wolfram
    clean = query
    for kw in ("wolfram", "calculate", "compute", "solve", "exact answer"):
        clean = clean.replace(kw, "").strip()

    try:
        res = client.query(clean)
        # Walk pods in order of relevance — prefer 'Result' or 'Decimal approximation'
        priority_pods = ("Result", "Decimal approximation", "Value", "Solution")
        for pod_name in priority_pods:
            try:
                answer = next(res.results).text
                if answer:
                    return f"Wolfram says: {answer}"
            except StopIteration:
                pass

        # Fallback to first available textual result
        for pod in res.pods:
            for sub in pod.subpods:
                if sub.plaintext and len(sub.plaintext.strip()) > 1:
                    return f"Wolfram says: {sub.plaintext.strip()}"

        return "Wolfram found no definitive answer for that. Try rephrasing."
    except Exception as e:
        logging.error(f"[Wolfram] Query failed: {e}")
        return "Wolfram Alpha query failed. Check your network or API key."
