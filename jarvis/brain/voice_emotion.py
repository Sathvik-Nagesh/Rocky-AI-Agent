"""
Emotional Speech Analysis — Tiredness / Stress Detection from voice.

Uses audio features (RMS energy, zero-crossing rate, spectral centroid)
to estimate the speaker's fatigue level from speech patterns.

This is a lightweight, local, zero-dependency approach (numpy only).
No ML model required — uses simple acoustic heuristics:
  - Low energy + low pitch variance → tired
  - High energy + high pitch variance → agitated/stressed
  - Monotone + slow speech rate → exhausted
"""

import numpy as np
import logging


def analyze_voice_features(audio_data: np.ndarray, sample_rate: int = 16000) -> dict:
    """
    Analyze raw audio samples for emotional markers.
    Returns dict with energy, pitch_variance, speech_rate, and a label.
    """
    if audio_data is None or len(audio_data) == 0:
        return {"label": "unknown", "confidence": 0.0}

    audio = audio_data.astype(np.float32)
    if np.max(np.abs(audio)) > 0:
        audio = audio / np.max(np.abs(audio))

    # ── RMS Energy ────────────────────────────────────────────────────────────
    rms = float(np.sqrt(np.mean(audio ** 2)))

    # ── Zero-Crossing Rate (proxy for speech energy/agitation) ────────────────
    zcr = float(np.mean(np.abs(np.diff(np.sign(audio)))) / 2.0)

    # ── Spectral Centroid (brightness/pitch proxy) ────────────────────────────
    fft_vals = np.abs(np.fft.rfft(audio))
    freqs    = np.fft.rfftfreq(len(audio), d=1.0 / sample_rate)
    if np.sum(fft_vals) > 0:
        spectral_centroid = float(np.sum(freqs * fft_vals) / np.sum(fft_vals))
    else:
        spectral_centroid = 0.0

    # ── Speech Rate Proxy (voiced segments / total duration) ──────────────────
    frame_len  = int(0.025 * sample_rate)
    num_frames = max(1, len(audio) // frame_len)
    voiced_frames = 0
    for i in range(num_frames):
        frame = audio[i * frame_len : (i + 1) * frame_len]
        if len(frame) > 0 and np.sqrt(np.mean(frame ** 2)) > 0.02:
            voiced_frames += 1
    speech_ratio = voiced_frames / num_frames

    # ── Emotion Classification (heuristic thresholds) ─────────────────────────
    label = "neutral"
    confidence = 0.5

    if rms < 0.08 and spectral_centroid < 800 and speech_ratio < 0.5:
        label = "exhausted"
        confidence = 0.75
    elif rms < 0.12 and spectral_centroid < 1200:
        label = "tired"
        confidence = 0.65
    elif rms > 0.3 and zcr > 0.15:
        label = "agitated"
        confidence = 0.7
    elif rms > 0.25 and spectral_centroid > 2500:
        label = "stressed"
        confidence = 0.65
    elif rms > 0.15 and spectral_centroid > 1500:
        label = "energetic"
        confidence = 0.6

    return {
        "label":       label,
        "confidence":  round(confidence, 2),
        "rms":         round(rms, 4),
        "zcr":         round(zcr, 4),
        "centroid":    round(spectral_centroid, 1),
        "speech_ratio": round(speech_ratio, 2),
    }


def get_voice_insight(analysis: dict) -> str | None:
    """
    Turn voice analysis into a Rocky-style spoken observation.
    Returns None if the user sounds normal (no intervention needed).
    """
    label = analysis.get("label", "neutral")
    conf  = analysis.get("confidence", 0)

    if conf < 0.6:
        return None   # Not confident enough to intervene

    insights = {
        "exhausted": "Your vocal patterns indicate significant fatigue. Rest is not optional at this point. Shutting down recommendations in progress.",
        "tired":     "Your voice energy is lower than baseline. You sound tired. Consider a break.",
        "agitated":  "Elevated vocal frequency detected. You appear agitated. Perhaps a different approach to the current problem.",
        "stressed":  "Your speech patterns suggest stress. Deep breath recommended. The problem will not solve faster with cortisol.",
        "energetic": None,  # No need to intervene when the user is doing well
    }

    return insights.get(label)
