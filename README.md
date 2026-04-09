# Rocky — AI Voice Assistant

> *"It is 2 AM. You are still running. Noted. What do you need?"*

A fully local, modular AI voice assistant inspired by **JARVIS** and **Rocky from Project Hail Mary**. Runs entirely on your machine — no cloud APIs, no subscriptions, no data leaves your system.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python)
![Ollama](https://img.shields.io/badge/LLM-llama3.2%3A3b-green?style=flat-square)
![Whisper](https://img.shields.io/badge/STT-faster--whisper-orange?style=flat-square)
![TTS](https://img.shields.io/badge/TTS-edge--tts-blueviolet?style=flat-square)
![UI](https://img.shields.io/badge/UI-PyQt6-purple?style=flat-square)

---

### 🧬 Current Evolution: Phase 11-13 (The Architect)
*   **Autonomous Web Agent (Playwright)**: Rocky now has a literal browser "hand." He can research live topics, bypass bot checks, and summarize findings from the live web.
*   **Work Shadow Context**: Intent intelligence that tracks your active window (VS Code, Chrome, etc.). Rocky knows *what* you're working on without being told.
*   **Daily Standup Architect**: Automated work reporting. Rocky analyzes his own activity logs to produce formatted standup reports of your day.
*   **Conversation State Engine**: Advanced state tracking for "Yes/No" confirmations, ensuring Rocky never loses the thread during complex multi-step tasks.
*   **Acoustic Voice Hardening**: Suppression of ambient fan noise and improved VAD (Voice Activity Detection) for high-performance PC environments.

---

### 🚀 Quick Start
1.  **Dependencies**: `python -m pip install -r jarvis/requirements.txt`
2.  **Web Agent Setup**: `python -m playwright install chromium`
3.  **Launch**: `python jarvis/main.py`

---

### 🧠 Core Features
| Capability | Tech | Description |
|---|---|---|
| 🎙️ Voice Detection | `sounddevice` + RMS | Records only when you speak, stops on silence. |
| 🛡️ Sentinel Sandbox | Python AST Allowlist | Secure execution of terminal scripts via AST validation. |
| 🧠 LLM Brain | `llama3.2:3b` | Multi-turn conversation with JSON schema enforcement. |
| 🔊 Local Neural TTS | `Piper` (Local ONNX) | 100% offline neural voice with `edge-tts` fallback. |
| ✨ Voice Emotion | Spectral Analysis | Detects acoustic stress and energy from your voice. |
| 🖥️ Shadow IQ | Window Title Monitoring | Senses when you are coding vs. browsing for context. |
| 👁️ Vision | `pyautogui` + LLaVA | "What's on my screen?" — screenshot analysis. |
| 🛠️ Self-Evolution | Agentic Plugin Maker | Ask Rocky to "evolve" — he writes and installs his own plugins. |
| 🧹 Chaos Fixer | `shutil` | Organizes messy folders (Desktop/Downloads) by context. |
| 🗑️ Data Privacy | `purge_memory()` | Say "Wipe my memory" to instantly delete all local data. |

---

## Project Structure

```
Rocky/
├── jarvis/
│   ├── main.py                 # Entry point — Qt app + voice loop
│   ├── config.py               # All settings in one place
│   │
│   ├── voice/
│   │   ├── input.py            # VAD-based recording + Whisper STT
│   │   ├── output.py           # edge-tts neural voice + SAPI5 fallback
│   │   └── wake_word.py        # openWakeWord background detector
│   │
│   ├── brain/
│   │   ├── llm.py              # Ollama /api/chat — JSON schema enforced
│   │   ├── emotion.py          # Keyword emotion classifier
│   │   ├── vision.py           # Screenshot → LLaVA analysis
│   │   ├── observer.py         # Passive active-window monitoring
│   │   ├── file_rag.py         # Local document ingestion + RAG
│   │   └── prompt.txt          # Rocky's personality prompt
│   │
│   ├── utils/
│   │   ├── intent.py           # Keyword-based intent routing
│   │   └── parser.py           # JSON extraction with repair + fallback
│   │
│   ├── actions/
│   │   ├── executor.py         # Routes intent → action module
│   │   ├── system.py           # App launcher, navigation, system control
│   │   ├── weather.py          # wttr.in live weather
│   │   ├── reminders.py        # Threading-based reminder system
│   │   ├── terminal.py         # Agentic script generation + execution
│   │   └── plugins_manager.py  # Dynamic plugin loader
│   │
│   ├── memory/
│   │   ├── memory.json         # Short-term preferences & habits
│   │   ├── memory_manager.py   # Atomic read/write
│   │   ├── vector_db.py        # ChromaDB semantic memory
│   │   └── chroma_db/          # Persistent vector store
│   │
│   ├── ui/
│   │   ├── main_window.py      # JARVIS HUD — waveform, info bar, typing
│   │   ├── signals.py          # Qt signals for thread-safe updates
│   │   └── styles.qss          # Iron Man Mark 85 stylesheet
│   │
│   └── requirements.txt
│
├── plugins/                    # Drop custom extensions here
│   └── web_research.py         # Autonomous web research plugin
│
└── README.md
```

---

## Setup

### Prerequisites
- Python 3.10+
- [Ollama](https://ollama.com) installed and running
- Windows 10/11

### 1. Clone the repo
```bash
git clone https://github.com/Sathvik-Nagesh/Rocky-AI-Agent
cd Rocky
```

### 2. Create a virtual environment
```bash
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r jarvis/requirements.txt
```

### 4. Pull the LLM models
```bash
ollama pull llama3.2:3b        # Main brain
ollama pull llava:7b           # Optional: vision capabilities
```

### 5. Start Ollama
```bash
ollama serve
```

### 6. Run Rocky
```bash
cd jarvis
python main.py
```

---

## Configuration

All settings are in `jarvis/config.py`:

```python
MODEL_NAME         = "llama3.2:3b"        # LLM model
WHISPER_MODEL_SIZE = "base.en"            # STT accuracy vs speed
EDGE_TTS_VOICE     = "en-US-AndrewNeural" # Neural voice
EDGE_TTS_RATE      = "+15%"               # Speaking speed
ENABLE_WAKE_WORD   = False                # "Hey Jarvis" trigger
VAD_SILENCE_TIMEOUT = 1.5                 # Seconds of silence to stop recording
LLM_TEMPERATURE    = 0.72                 # Creativity level
```

### Available Voices
| Voice | Style |
|---|---|
| `en-US-AndrewNeural` | Confident, calm, masculine (default) |
| `en-US-GuyNeural` | Natural American male |
| `en-GB-RyanNeural` | British / JARVIS-style |
| `en-US-ChristopherNeural` | Deep, authoritative |

---

## Voice Commands

| Say | What happens |
|---|---|
| `"Open YouTube"` | Opens youtube.com directly |
| `"Open Chrome"` | Launches Google Chrome |
| `"Play some music"` | Launches Apple Music |
| `"Search for black holes"` | Google search |
| `"Find out about SpaceX"` | **Autonomous web research** — reads articles aloud |
| `"What's on my screen?"` | **Vision** — analyzes screenshot |
| `"What's the weather?"` | Live weather from wttr.in |
| `"Remind me in 10 minutes"` | Timed voice reminder |
| `"Learn my files"` | **Ingests** your Documents folder into memory |
| `"Clean up my downloads"` | **Agentic terminal** — writes + runs a script |
| `"What can you do?"` | Lists capabilities |
| `"Forget everything"` | Clears all memory |
| `"Goodbye"` | Shuts down |

---

## Architecture

```
[Microphone]
     │
     ▼
[VAD Listener] ──RMS──► [UI Waveform]
     │
     ▼ transcribed text
[Intent Detector] ─── plugin check ──► [Plugin Manager]
     │                  vision check ──► [Vision / LLaVA]
     │
     ├── Keyword match ──► [Executor] ──► [Actions]
     │                     [LLM]        (speak first, act in background)
     │
     └── Chat ──► [LLM + Document RAG + Semantic Memory]
                       │
                       ▼
                 [Parser] → [edge-tts] → [Speaker]
                       │
                       ▼
              [ChromaDB + memory.json]

[AppObserver] ──────────► passive nudges ──► [UI Info Bar]
```

---

## Memory System

### Short-term (memory.json)
Preferences, habits, emotion, last 10 conversation turns. Atomic writes prevent corruption.

### Long-term (ChromaDB)
Every conversation is vector-embedded. When you ask a question, Rocky semantically retrieves only the most relevant 2-3 past memories — infinite history without slowing down.

### Document RAG
Say *"Learn my files"* — Rocky ingests your `Documents` folder. Then ask questions: *"What was the deadline in that proposal?"*

---

## Plugin System

Drop a `.py` file in the `plugins/` directory:

```python
# plugins/my_plugin.py
KEYWORDS = ["turn on lights", "lights on"]

def execute(query: str) -> str:
    # Your smart home / API code here
    return "Lights turned on."
```

Rocky auto-loads it on startup and routes matching queries to your function.

---

## Requirements

```
faster-whisper        # Local speech-to-text
sounddevice           # Mic recording + VAD
numpy / scipy         # Audio processing
requests              # API calls
pywin32               # SAPI5 fallback TTS
PyQt6                 # JARVIS HUD
edge-tts              # Microsoft Neural TTS
pygame-ce             # Audio playback
chromadb              # Vector semantic memory
pyautogui             # Screenshot capture
pygetwindow           # Active window monitoring
beautifulsoup4        # Web scraping
duckduckgo-search     # Private web search
```

---

## License

MIT — do whatever you want with it.

---

*Built with Python, running entirely locally. Zero cloud dependency. Your data never leaves your machine.*
