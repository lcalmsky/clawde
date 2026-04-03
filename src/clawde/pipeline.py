"""Pipeline orchestration: audio file → guitar tablature."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from clawde.audio import ensure_wav
from clawde.transcriber import transcribe
from clawde.mapper import map_notes
from clawde.tab_ascii import render as render_ascii
from clawde.tab_gp import generate as generate_gp


@dataclass
class TabResult:
    """Result of tablature conversion."""
    ascii_tab: str | None
    gp_path: Path | None
    note_count: int
    duration_seconds: float


def convert(
    file_path: str | Path,
    tuning: str = "standard",
    output_format: str = "both",
    output_dir: str | Path = ".",
    bpm: float | None = None,
) -> TabResult:
    """Convert an audio file to guitar tablature.

    Args:
        file_path: Path to audio file (mp3/mp4/wav).
        tuning: Guitar tuning name.
        output_format: "ascii", "gp", or "both".
        output_dir: Directory for GuitarPro file output.
        bpm: Override BPM detection. If None, defaults to 120.

    Returns:
        TabResult with ASCII tab and/or GP file path.
    """
    file_path = Path(file_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Ensure wav format
    wav_path = ensure_wav(file_path)

    # Step 2: Transcribe audio to MIDI notes
    notes = transcribe(wav_path)

    if not notes:
        return TabResult(
            ascii_tab="(no notes detected)" if output_format != "gp" else None,
            gp_path=None,
            note_count=0,
            duration_seconds=0.0,
        )

    # Step 3: Map to guitar positions
    estimated_bpm = bpm or 120.0
    guitar_notes = map_notes(notes, tuning=tuning)
    duration = max(n.end_time for n in notes)

    # Step 4: Generate output
    ascii_tab = None
    gp_path = None
    title = file_path.stem

    if output_format in ("ascii", "both"):
        ascii_tab = render_ascii(
            guitar_notes,
            bpm=estimated_bpm,
            title=title,
            tuning=tuning,
        )

    if output_format in ("gp", "both"):
        gp_file = output_dir / f"{title}.gp5"
        gp_path = generate_gp(
            guitar_notes,
            output_path=gp_file,
            bpm=estimated_bpm,
            title=title,
            tuning=tuning,
        )

    return TabResult(
        ascii_tab=ascii_tab,
        gp_path=gp_path,
        note_count=len(guitar_notes),
        duration_seconds=duration,
    )
