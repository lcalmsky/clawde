"""Percussive event detection using librosa HPSS + onset detection."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class PercussiveEvent:
    """A percussive hit detected from audio."""
    time: float           # seconds
    category: str         # "body_tap" | "mute" | "string_tap"
    strength: float       # 0.0-1.0

# Frequency band boundaries for classification (Hz)
LOW_BAND_MAX = 300
MID_BAND_MAX = 2000

# Minimum onset strength to keep (relative to max)
MIN_STRENGTH_RATIO = 0.1


def _classify_onset(mel_spec: np.ndarray, sr: int, frame_idx: int,
                    mel_freqs: np.ndarray) -> str:
    """Classify a percussive onset by frequency band energy."""
    if frame_idx >= mel_spec.shape[1]:
        return "mute"

    spectrum = mel_spec[:, frame_idx]

    low_mask = mel_freqs < LOW_BAND_MAX
    mid_mask = (mel_freqs >= LOW_BAND_MAX) & (mel_freqs < MID_BAND_MAX)
    high_mask = mel_freqs >= MID_BAND_MAX

    low_energy = float(np.sum(spectrum[low_mask])) if np.any(low_mask) else 0.0
    mid_energy = float(np.sum(spectrum[mid_mask])) if np.any(mid_mask) else 0.0
    high_energy = float(np.sum(spectrum[high_mask])) if np.any(high_mask) else 0.0

    total = low_energy + mid_energy + high_energy
    if total == 0:
        return "mute"

    low_ratio = low_energy / total
    high_ratio = high_energy / total

    if low_ratio > 0.5:
        return "body_tap"
    elif high_ratio > 0.4:
        return "string_tap"
    else:
        return "mute"


def detect_percussive(wav_path: str | Path) -> list[PercussiveEvent]:
    """Detect percussive events from an audio file.

    Uses HPSS to isolate percussive component, then onset detection
    and spectral analysis for classification.
    """
    import librosa  # lazy: heavy dependency

    y, sr = librosa.load(str(wav_path), sr=22050)

    # Separate harmonic and percussive components
    _, y_perc = librosa.effects.hpss(y)

    # Detect onsets in percussive signal
    onset_env = librosa.onset.onset_strength(y=y_perc, sr=sr)
    onset_frames = librosa.onset.onset_detect(
        y=y_perc, sr=sr, onset_envelope=onset_env, backtrack=False,
    )
    onset_times = librosa.frames_to_time(onset_frames, sr=sr)

    if len(onset_frames) == 0:
        return []

    # Compute mel spectrogram of percussive component for classification
    mel_spec = librosa.feature.melspectrogram(y=y_perc, sr=sr, n_mels=128)
    mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)
    # Shift to positive range for energy comparison
    mel_spec_pos = mel_spec_db - mel_spec_db.min()
    mel_freqs = librosa.mel_frequencies(n_mels=128, fmin=0, fmax=sr / 2)

    # Compute strengths from onset envelope
    max_strength = onset_env.max() if onset_env.max() > 0 else 1.0

    events = []
    for frame, time in zip(onset_frames, onset_times):
        strength = float(onset_env[frame] / max_strength) if frame < len(onset_env) else 0.0

        if strength < MIN_STRENGTH_RATIO:
            continue

        category = _classify_onset(mel_spec_pos, sr, frame, mel_freqs)

        events.append(PercussiveEvent(
            time=float(time),
            category=category,
            strength=round(strength, 3),
        ))

    return events
