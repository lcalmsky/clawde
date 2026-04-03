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

OVERLAP_THRESHOLD_MS = 80


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
    separate_sources: bool = True,
) -> TabResult:
    """Convert an audio file to guitar tablature.

    Args:
        file_path: Path to audio file (mp3/mp4/wav).
        tuning: Guitar tuning name.
        output_format: "ascii", "gp", or "both".
        output_dir: Directory for GuitarPro file output.
        bpm: Override BPM detection. If None, auto-detect.
        separate_sources: Use demucs source separation for better accuracy.
    """
    file_path = Path(file_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    wav_path = ensure_wav(file_path)
    detected_bpm = detect_bpm(wav_path)
    effective_bpm = bpm or detected_bpm

    if separate_sources:
        guitar_notes = _convert_separated(wav_path, tuning, output_dir)
    else:
        guitar_notes = _convert_legacy(wav_path, tuning)

    if not guitar_notes:
        return TabResult(
            ascii_tab="(no notes detected)" if output_format != "gp" else None,
            gp_path=None,
            note_count=0,
            duration_seconds=0.0,
            detected_bpm=effective_bpm,
        )

    duration = max(n.time + n.duration for n in guitar_notes)

    ascii_tab = None
    gp_path = None
    title = file_path.stem

    if output_format in ("ascii", "both"):
        ascii_tab = render_ascii(
            guitar_notes, bpm=effective_bpm, title=title, tuning=tuning,
        )

    if output_format in ("gp", "both"):
        gp_file = output_dir / f"{title}.gp5"
        gp_path = generate_gp(
            guitar_notes, output_path=gp_file, bpm=effective_bpm,
            title=title, tuning=tuning,
        )

    return TabResult(
        ascii_tab=ascii_tab,
        gp_path=gp_path,
        note_count=len(guitar_notes),
        duration_seconds=duration,
        detected_bpm=effective_bpm,
    )


def _convert_separated(wav_path: Path, tuning: str, output_dir: Path) -> list:
    """v0.3 path: demucs separation → role-based arrangement."""
    try:
        from clawde.separator import separate
        from clawde.arranger import arrange
    except ImportError:
        import click
        click.echo("demucs not installed. Install with: uv sync --extra full")
        click.echo("Falling back to legacy mode (no source separation).")
        return _convert_legacy(wav_path, tuning)

    stems = separate(wav_path, output_dir)
    return arrange(stems, tuning=tuning)


def _convert_legacy(wav_path: Path, tuning: str) -> list:
    """v0.2 path: whole-audio transcription + percussive detection."""
    notes = transcribe(wav_path)
    perc_events = detect_percussive(wav_path)

    guitar_notes = map_notes(notes, tuning=tuning) if notes else []
    perc_notes = map_percussive(perc_events)

    return _merge_notes(guitar_notes, perc_notes)


def _merge_notes(melodic, percussive):
    """Merge melodic and percussive notes. Melodic wins on overlap."""
    if not percussive:
        return melodic
    if not melodic:
        return percussive

    melodic_slots = set()
    for n in melodic:
        t = round(n.time, 2)
        melodic_slots.add(t)
        melodic_slots.add(round(t - 0.05, 2))
        melodic_slots.add(round(t + 0.05, 2))

    filtered_perc = []
    for p in percussive:
        too_close = any(
            abs(p.time - mt) * 1000 <= OVERLAP_THRESHOLD_MS
            for mt in melodic_slots
        )
        if not too_close:
            filtered_perc.append(p)

    merged = melodic + filtered_perc
    merged.sort(key=lambda n: n.time)
    return merged
