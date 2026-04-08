import tempfile
import os
import time
import logging
import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write as wav_write
from faster_whisper import WhisperModel
from config import WHISPER_MODEL_SIZE, RECORDING_DURATION_SECONDS, RECORDING_SAMPLE_RATE

print(f"--- Loading Whisper model '{WHISPER_MODEL_SIZE}' (first time may download) ---")
try:
    _model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
    print("--- Whisper model ready ---")
except Exception as e:
    logging.error(f"Whisper model failed to load: {e}")
    _model = None

def listen(on_level=None) -> str:
    """
    Record from the microphone and return transcribed text.

    Args:
        on_level: Optional callable(float) — called ~20x/sec during recording
                  with RMS 0.0–1.0 so the UI waveform can react to real mic input.
    Returns:
        Transcribed string, or empty string on failure.
    """
    if _model is None:
        logging.error("Whisper model not loaded.")
        return ""

    fs       = RECORDING_SAMPLE_RATE
    duration = RECORDING_DURATION_SECONDS
    print(f"\n[LISTENING] Recording for {duration}s... (Speak now)")

    frames: list[np.ndarray] = []
    temp_path = None

    try:
        # Use a streaming InputStream so we can compute RMS in real time
        # while also collecting frames for Whisper transcription.
        def _callback(indata: np.ndarray, frame_count, time_info, status):
            frames.append(indata.copy())
            if on_level:
                rms = float(np.sqrt(np.mean(indata ** 2)))
                on_level(min(1.0, rms * 25))  # scale to 0–1

        with sd.InputStream(samplerate=fs, channels=1, dtype="float32",
                            blocksize=1024, callback=_callback):
            time.sleep(duration)

        if not frames:
            return ""

        print("[PROCESS] Transcribing...")
        recording = np.concatenate(frames, axis=0)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name
            wav_write(temp_path, fs, recording)

        segments, _ = _model.transcribe(temp_path, beam_size=5)
        return " ".join(seg.text for seg in segments).strip()

    except Exception as e:
        logging.error(f"Recording/transcription error: {e}")
        return ""
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
        # Signal waveform to idle
        if on_level:
            on_level(0.0)
