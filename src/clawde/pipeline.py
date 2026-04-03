"""Pipeline orchestration: audio file → guitar tablature."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from clawde.audio import ensure_wav
from clawde.transcriber import transcribe
from clawde.mapper import map_notes, map_percussive
from clawde.percussive import detect_percussive
from clawde.rhythm import detect_bpm
from clawde.tab_ascii import render as render_ascii
from clawde.tab_gp import generate as generate_gp

OVERLAP_THRESHOLD_MS = 80  # melodic note wins if percussive is within this range


@dataclass
class TabResult:
    """Result of tablature conversion."""
    ascii_tab: str | None
    gp_path: Path | None
    note_count: int
    duration_seconds: float
    detected_bpm: float


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
        bpm: Override BPM detection. If None, auto-detect with librosa.

    Returns:
        TabResult with ASCII tab and/or GP file path.
    """
    file_path = Path(file_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Ensure wav format
    wav_path = ensure_wav(file_path)

    # Step 2: Auto-detect BPM (or use override)
    detected_bpm = detect_bpm(wav_path)
    effective_bpm = bpm or detected_bpm

    # Step 3: Transcribe audio to MIDI notes
    notes = transcribe(wav_path)

    # Step 4: Detect percussive events
    perc_events = detect_percussive(wav_path)

    # Step 5: Map to guitar positions
    guitar_notes = map_notes(notes, tuning=tuning) if notes else []
    perc_notes = map_percussive(perc_events)

    # Step 6: Merge melodic + percussive, removing overlaps
    merged = _merge_notes(guitar_notes, perc_notes)

    if not merged:
        return TabResult(
            ascii_tab="(no notes detected)" if output_format != "gp" else None,
            gp_path=None,
            note_count=0,
            duration_seconds=0.0,
            detected_bpm=effective_bpm,
        )

    duration = max(n.time + n.duration for n in merged)

    # Step 7: Generate output
    ascii_tab = None
    gp_path = None
    title = file_path.stem

    if output_format in ("ascii", "both"):
        ascii_tab = render_ascii(
            merged,
            bpm=effective_bpm,
            title=title,
            tuning=tuning,
        )

    if output_format in ("gp", "both"):
        gp_file = output_dir / f"{title}.gp5"
        gp_path = generate_gp(
            merged,
            output_path=gp_file,
            bpm=effective_bpm,
            title=title,
            tuning=tuning,
        )

    return TabResult(
        ascii_tab=ascii_tab,
        gp_path=gp_path,
        note_count=len(merged),
        duration_seconds=duration,
        detected_bpm=effective_bpm,
    )


def _merge_notes(melodic, percussive):
    """Merge melodic and percussive notes. Melodic wins on overlap."""
    if not percussive:
        return melodic
    if not melodic:
        return percussive

    # Build lookup: (quantized_time, string) pairs used by melodic notes
    melodic_slots = set()
    for n in melodic:
        t = round(n.time, 2)
        melodic_slots.add(t)
        # Also block nearby times
        melodic_slots.add(round(t - 0.05, 2))
        melodic_slots.add(round(t + 0.05, 2))

    filtered_perc = []
    for p in percussive:
        pt = round(p.time, 2)
        # Skip percussive if a melodic note is within threshold
        too_close = any(
            abs(p.time - mt) * 1000 <= OVERLAP_THRESHOLD_MS
            for mt in melodic_slots
        )
        if not too_close:
            filtered_perc.append(p)

    merged = melodic + filtered_perc
    merged.sort(key=lambda n: n.time)
    return merged
