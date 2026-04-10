import tempfile
import os
import time
import logging
import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write as wav_write
from faster_whisper import WhisperModel
from config import (
    WHISPER_MODEL_SIZE, RECORDING_SAMPLE_RATE,
    VAD_ENERGY_THRESHOLD, VAD_SILENCE_TIMEOUT, VAD_MAX_DURATION
)

print(f"--- Loading Whisper model '{WHISPER_MODEL_SIZE}' (first time may download) ---")
try:
    _model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
    print("--- Whisper model ready ---")
except Exception as e:
    logging.error(f"Whisper model failed to load: {e}")
    _model = None

def listen(on_level=None) -> tuple[str, np.ndarray | None]:
    """
    Record from the microphone dynamically until silence is detected.
    Returns (transcribed_text, raw_audio_ndarray).
    The raw audio is passed to voice emotion analysis.
    """
    if _model is None:
        logging.error("Whisper model not loaded.")
        return "", None

    fs = RECORDING_SAMPLE_RATE
    frames: list[np.ndarray] = []
    temp_path = None

    # Acoustic Shield: Auto-calibrate noise floor
    noise_samples = []
    dynamic_threshold = VAD_ENERGY_THRESHOLD

    # VAD state control
    speaking_started = False
    silence_start_time = None
    start_time = time.time()
    
    print("\n[LISTENING] Waiting for speech...")

    try:
        def _callback(indata: np.ndarray, frame_count, time_info, status):
            nonlocal speaking_started, silence_start_time, dynamic_threshold
            if status:
                logging.warning(status)
            
            # Record frame (Scale check for noise floor)
            rms = float(np.sqrt(np.mean(indata ** 2)))
            
            if not speaking_started and len(noise_samples) < 10:
                noise_samples.append(rms)
                if len(noise_samples) == 10:
                    avg_noise = sum(noise_samples) / 10
                    dynamic_threshold = max(VAD_ENERGY_THRESHOLD, avg_noise * 1.5)
                    print(f"  [ACOUSTIC SHIELD] Noise floor calibrated. Threshold: {dynamic_threshold:.4f}")

            frames.append(indata.copy())
            
            if on_level:
                on_level(min(1.0, rms * 25))

            current_time = time.time()
            if rms > dynamic_threshold:
                if not speaking_started:
                    print("  [VAD] Speech detected. Recording...")
                    speaking_started = True
                silence_start_time = None
            else:
                if speaking_started and silence_start_time is None:
                    silence_start_time = current_time

        with sd.InputStream(samplerate=fs, channels=1, dtype="float32",
                            blocksize=1024, callback=_callback):
            while True:
                time.sleep(0.05)   # Pre-Reflex: High frequency check
                now = time.time()
                
                # Check 1: We've been recording for way too long (hard stop)
                if now - start_time > VAD_MAX_DURATION:
                    print("  [VAD] Max duration reached.")
                    break
                
                # Check 2: We started speaking, and have now been silent beyond the timeout
                if speaking_started and silence_start_time is not None:
                    if now - silence_start_time > VAD_SILENCE_TIMEOUT:
                        print("  [VAD] Silence detected. Stopping.")
                        break

        if not frames or not speaking_started:
            return "", None

        print("[PROCESS] Transcribing...")
        recording = np.concatenate(frames, axis=0)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name
            wav_write(temp_path, fs, recording)

        segments, _ = _model.transcribe(temp_path, beam_size=5)
        text = " ".join(seg.text for seg in segments).strip()
        return text, recording

    except Exception as e:
        logging.error(f"Recording/transcription error: {e}")
        return "", None
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        if on_level:
            on_level(0.0)
