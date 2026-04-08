# Rocky — JARVIS-Style Voice Assistant

> *"Hello. You appear functional today. Good sign, yes?"*

A fully offline, modular, production-quality Python voice assistant inspired by JARVIS and Rocky. Runs entirely on your local machine — no cloud APIs, no subscriptions.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python)
![Ollama](https://img.shields.io/badge/LLM-llama3.2%3A3b-green?style=flat-square)
![Whisper](https://img.shields.io/badge/STT-faster--whisper-orange?style=flat-square)
![UI](https://img.shields.io/badge/UI-PyQt6-purple?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-lightgrey?style=flat-square)

---

## Features

| Capability | Tech |
|---|---|
| 🎙️ Speech-to-text | `faster-whisper` (local, offline) |
| 🧠 LLM brain | `llama3.2:3b` via Ollama (local) |
| 🔊 Text-to-speech | Windows SAPI5 via `win32com` |
| 🖥️ JARVIS HUD overlay | PyQt6 — frameless, glassmorphism, always-on-top |
| 🌊 Real mic waveform | Live RMS from `sounddevice.InputStream` |
| 🧠 Memory | JSON-based — preferences, habits, conversation history |
| 😐 Emotion detection | Keyword-based mood classifier → adapts Rocky's tone |
| ⚡ Parallel execution | Action + LLM run simultaneously (no lag) |
| 🔁 Multi-turn context | Proper `/api/chat` message history — real conversation |
| 📂 File operations | Open Downloads, Documents, Desktop, find files |
| 🌤️ Weather | Live via `wttr.in` — no API key needed |
| ⏰ Reminders | Natural language (e.g. "in 5 minutes") |
| 🎙️ Wake word | Optional "Hey Rocky" trigger via `tiny.en` Whisper |
| 🎵 Apple Music | Launch with voice command |

---

## Project Structure

```
Rocky/
├── jarvis/
│   ├── main.py              # Entry point — Qt app + voice loop
│   ├── config.py            # All settings in one place
│   │
│   ├── voice/
│   │   ├── input.py         # Mic recording + Whisper STT + real RMS levels
│   │   ├── output.py        # SAPI5 text-to-speech singleton
│   │   └── wake_word.py     # Background "Hey Rocky" detector
│   │
│   ├── brain/
│   │   ├── llm.py           # Ollama /api/chat — multi-turn conversation
│   │   ├── emotion.py       # Keyword emotion classifier
│   │   └── prompt.txt       # Rocky's system prompt
│   │
│   ├── utils/
│   │   ├── intent.py        # Keyword-based intent routing
│   │   └── parser.py        # JSON extraction with truncation repair
│   │
│   ├── actions/
│   │   ├── executor.py      # Routes intent → action module
│   │   ├── system.py        # App launcher, file ops, system control
│   │   ├── weather.py       # wttr.in live weather
│   │   └── reminders.py     # Threading-based reminder system
│   │
│   ├── memory/
│   │   ├── memory.json      # Persistent memory store
│   │   └── memory_manager.py # Atomic read/write, history, preferences
│   │
│   ├── ui/
│   │   ├── main_window.py   # JARVIS HUD — waveform, status dot, glassmorphism
│   │   ├── signals.py       # Qt signals for thread-safe UI updates
│   │   └── styles.qss       # Stylesheet — electric cyan, dark glass
│   │
│   ├── requirements.txt
│   └── rocky.log            # Auto-generated log file
```

---

## Setup

### Prerequisites
- Python 3.10+
- [Ollama](https://ollama.com) installed and running
- Windows (for SAPI5 TTS and Apple Music support)

### 1. Clone the repo
```bash
git clone https://github.com/Sathvik-Nagesh/Rocky-AI-Agent
cd Jarvis
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

### 4. Pull the LLM model
```bash
ollama pull llama3.2:3b
```

### 5. Start Ollama (in a separate terminal)
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
MODEL_NAME              = "llama3.2:3b"  # Switch to "gemma4" for more creativity
WHISPER_MODEL_SIZE      = "base.en"      # "tiny.en" for speed, "small.en" for accuracy
RECORDING_DURATION_SECONDS = 5           # How long Rocky listens per turn
ENABLE_WAKE_WORD        = False          # Set True to use "Hey Rocky" trigger
LLM_NUM_PREDICT         = 150           # Max response tokens
LLM_TEMPERATURE         = 0.72          # Creativity (0 = robotic, 1 = creative)
```

---

## Voice Commands

| Say | What happens |
|---|---|
| `"Open Chrome"` | Launches Google Chrome |
| `"Open my Downloads"` | Opens Downloads folder |
| `"Play some music"` | Launches Apple Music |
| `"Search for Python tutorials"` | Google search opens in browser |
| `"What's the weather?"` | Fetches live weather from wttr.in |
| `"Remind me in 10 minutes to take a break"` | Sets a timed reminder |
| `"What can you do?"` | Rocky explains his capabilities |
| `"Forget everything"` | Clears conversation memory |
| `"Goodbye"` | Shuts Rocky down |

---

## JARVIS HUD

The overlay window:
- **Frameless + always on top** — sits over any window
- **Glassmorphism** — deep space dark with electric cyan accents
- **Live waveform** — 18 bars driven by real microphone RMS levels
- **Pulsing status dot** — cyan=listening, blue=thinking, green=speaking
- **Fade-in animation** on launch
- **Drag to move** — click anywhere on the panel to reposition

---

## Architecture

```
[Microphone]
     │
     ▼
[voice/input.py] ──RMS──► [UI Waveform]
     │
     ▼ transcribed text
[utils/intent.py]
     │
     ├── Keyword match ──► [actions/executor.py] ──┐
     │                     [brain/llm.py]  ◄────── │ (parallel)
     │                                             ▼
     └── Chat only ───────► [brain/llm.py]   response_text
                                 │                  │
                                 ▼                  ▼
                          [utils/parser.py]   [voice/output.py]
                                 │                  │
                                 ▼                  ▼
                          [memory/ manager]   [SAPI5 TTS]
```

---

## Memory System

Rocky remembers across sessions:

```json
{
  "user_preferences": { "music_app": "apple_music" },
  "habits": { "gym_skipped": 2, "working_late": 1 },
  "last_emotion": "neutral",
  "history": [
    { "user": "hi", "assistant": "Hello. Functioning well." }
  ]
}
```

Writes are **atomic** (temp file → rename) so memory never corrupts on crash.
Last 5 conversation turns are injected directly into the LLM's message history.

---

## What's Coming (Phase 5+)

- [ ] Screen reader — "what's on my screen?"
- [ ] Clipboard integration — "read my clipboard / copy this"
- [ ] System monitor — "what's my CPU usage?"
- [ ] Custom wake word training
- [ ] Plugin system for user-defined actions
- [ ] Multi-language support via Whisper's multilingual models

---

## Requirements

```
faster-whisper     # Local speech-to-text
sounddevice        # Mic recording + real-time RMS
numpy              # Audio processing
scipy              # WAV file writing
requests           # Ollama API + weather
pywin32            # Windows SAPI5 TTS
PyQt6              # JARVIS HUD overlay
```

---

## License

MIT — do whatever you want with it.

---

*Built with Python, running entirely offline. No data leaves your machine.*
