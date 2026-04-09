# Configuration settings for Rocky (Jarvis + Rocky) Assistant

# --- Ollama settings ---
OLLAMA_API_BASE = "http://localhost:11434"
OLLAMA_API_CHAT = f"{OLLAMA_API_BASE}/api/chat"       # multi-turn chat endpoint
OLLAMA_API_GEN  = f"{OLLAMA_API_BASE}/api/generate"   # legacy, kept for reference

# llama3.2:3b — instruction-following, fast, fits in 4GB VRAM, reliable JSON
MODEL_NAME = "llama3.2:3b"

# --- Whisper settings ---
# "tiny" / "base" / "small" (multilingual) 
# Note: dropping the '.en' suffix enables multi-language support.
WHISPER_MODEL_SIZE = "base"

# --- Recording settings ---
RECORDING_DURATION_SECONDS = 5
RECORDING_SAMPLE_RATE = 16000

# --- Voice Activity Detection (VAD) ---
VAD_ENERGY_THRESHOLD = 0.035     # Raised from 0.015 to ignore fan noise
VAD_SILENCE_TIMEOUT  = 1.1       # Shortened from 1.5 to stop faster
VAD_MAX_DURATION     = 12.0      # Hard limit on recording length

# --- TTS settings ---
# Piper TTS (Local Neural Voice) - Fast, GPU accelerated, 100% offline
ENABLE_PIPER_TTS = True
PIPER_VOICE_MODEL = "en_GB-alan-medium" # Jarvis-style British Male
# Options: "en_GB-alan-medium", "en_US-kusal-medium", "en_US-ryan-high"

# edge-tts voices (fallback to Microsoft Neural voice over internet):
EDGE_TTS_VOICE = "en-US-AndrewNeural"
EDGE_TTS_RATE  = "+15%"      # speaking pace: "+0%" = default, "+15%" = slightly faster

# SAPI5 fallback (when offline / edge-tts reachable)
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
