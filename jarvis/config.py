# Configuration settings for Rocky (Jarvis + Rocky) Assistant

# --- Ollama settings ---
OLLAMA_API_BASE = "http://localhost:11434"
OLLAMA_API_CHAT = f"{OLLAMA_API_BASE}/api/chat"       # multi-turn chat endpoint
OLLAMA_API_GEN  = f"{OLLAMA_API_BASE}/api/generate"   # legacy, kept for reference

# llama3.2:3b — instruction-following, fast, fits in 4GB VRAM, reliable JSON
MODEL_NAME = "llama3.2:3b"

# --- Whisper settings ---
# "tiny.en" = fastest, "base.en" = balanced, "small.en" = most accurate
WHISPER_MODEL_SIZE = "base.en"

# --- Recording settings ---
RECORDING_DURATION_SECONDS = 5
RECORDING_SAMPLE_RATE = 16000

# --- TTS settings ---
# edge-tts voices (primary): change to any Microsoft Neural voice
#   en-US-AndrewNeural      — confident, calm, masculine (Rocky's voice)
#   en-US-GuyNeural         — natural American male
#   en-GB-RyanNeural        — British / JARVIS-style
#   en-US-ChristopherNeural — deeper, more authoritative
EDGE_TTS_VOICE = "en-US-AndrewNeural"
EDGE_TTS_RATE  = "+15%"      # speaking pace: "+0%" = default, "+15%" = slightly faster

# SAPI5 fallback (when offline / edge-tts unreachable)
TTS_RATE   = 3    # -10 (slow) to 10 (fast)
TTS_VOLUME = 100  # 0–100

# --- Wake word ---
# True  = say "Hey Rocky" before each command (saves CPU)
# False = always-listening mode (best for testing)
ENABLE_WAKE_WORD = False

# --- LLM generation options ---
LLM_NUM_PREDICT = 150   # max response tokens — prevents truncation
LLM_NUM_CTX     = 2048  # context window — llama3.2 handles 2k well
LLM_TEMPERATURE = 0.72
