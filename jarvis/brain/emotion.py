"""Lightweight keyword-based emotion detector."""

_EMOTION_WORDS = {
    "low":     ["sad", "tired", "exhausted", "depressed", "upset", "down", "drained", "lonely", "miserable"],
    "high":    ["happy", "excited", "great", "amazing", "awesome", "fantastic", "wonderful", "pumped"],
    "angry":   ["angry", "frustrated", "furious", "annoyed", "pissed", "mad", "irritated"],
    "anxious": ["anxious", "stressed", "nervous", "worried", "overwhelmed", "panic"],
}

def detect_emotion(user_input: str) -> str:
    """Returns one of: 'low', 'high', 'angry', 'anxious', 'neutral'."""
    lowered = user_input.lower()
    for emotion, words in _EMOTION_WORDS.items():
        if any(w in lowered for w in words):
            return emotion
    return "neutral"
