"""Audio to MIDI note transcription using basic-pitch."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

@dataclass
class Note:
    """A detected note from audio."""
    start_time: float   # seconds
    end_time: float     # seconds
    pitch: int          # MIDI pitch (0-127)
    velocity: int       # 0-127

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time


def transcribe(wav_path: str | Path) -> list[Note]:
    """Transcribe audio file to a list of MIDI notes.

    Uses Spotify's basic-pitch for polyphonic pitch detection.
    """
    from basic_pitch.inference import predict  # lazy: heavy dependency
    from basic_pitch import ICASSP_2022_MODEL_PATH

    onnx_path = ICASSP_2022_MODEL_PATH.parent / "nmp.onnx"
    model_output, midi_data, note_events = predict(
        str(wav_path),
        model_or_model_path=onnx_path,
    )

    notes = []
    for start, end, pitch, velocity, _ in note_events:
        notes.append(Note(
            start_time=float(start),
            end_time=float(end),
            pitch=int(pitch),
            velocity=int(min(velocity * 127, 127)),
        ))

    notes.sort(key=lambda n: (n.start_time, n.pitch))
    return notes
