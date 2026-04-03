"""BPM auto-detection using librosa."""

from __future__ import annotations

from pathlib import Path

MIN_BPM = 40.0
MAX_BPM = 240.0
FALLBACK_BPM = 120.0


def detect_bpm(wav_path: str | Path) -> float:
    """Detect BPM from an audio file.

    Returns fallback 120.0 if detection fails or result is out of range.
    """
    import librosa  # lazy: heavy dependency

    y, sr = librosa.load(str(wav_path), sr=22050)
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)

    bpm = float(tempo) if not hasattr(tempo, '__len__') else float(tempo[0])

    if MIN_BPM <= bpm <= MAX_BPM:
        return round(bpm, 1)
    return FALLBACK_BPM
