"""ASCII guitar tablature renderer."""

from __future__ import annotations

from clawde.mapper import GuitarNote

# Standard string labels (high to low for display)
STRING_LABELS = {1: "e", 2: "B", 3: "G", 4: "D", 5: "A", 6: "E"}

# Time quantization: subdivide each beat into slots
SLOTS_PER_BEAT = 4  # sixteenth notes
CHARS_PER_SLOT = 1
MEASURES_PER_LINE = 4
BEATS_PER_MEASURE = 4  # assume 4/4 time


def render(
    notes: list[GuitarNote],
    bpm: float = 120.0,
    title: str = "",
    tuning: str = "standard",
) -> str:
    """Render guitar notes as ASCII tablature.

    Args:
        notes: List of GuitarNote with string/fret assignments.
        bpm: Beats per minute for time quantization.
        title: Song title for header.
        tuning: Tuning name for header.

    Returns:
        ASCII tablature string.
    """
    if not notes:
        return _header(title, tuning, bpm) + "\n(no notes detected)\n"

    # Calculate timing
    beat_duration = 60.0 / bpm
    slot_duration = beat_duration / SLOTS_PER_BEAT
    slots_per_measure = BEATS_PER_MEASURE * SLOTS_PER_BEAT
    slots_per_line = slots_per_measure * MEASURES_PER_LINE

    # Find total duration
    max_time = max(n.time + n.duration for n in notes)
    total_slots = int(max_time / slot_duration) + 1

    # Build grid: string -> list of slot characters
    grid: dict[int, list[str]] = {}
    for s in range(1, 7):
        grid[s] = ["-"] * total_slots

    # Place notes on grid
    for note in notes:
        slot = int(note.time / slot_duration)
        if 0 <= slot < total_slots and 1 <= note.string <= 6:
            if note.effect == "dead":
                fret_str = "x"
            elif note.effect == "palm_mute":
                fret_str = "M"
            else:
                fret_str = str(note.fret)
            grid[note.string][slot] = fret_str
            # Two-digit frets take an extra slot
            if len(fret_str) > 1 and slot + 1 < total_slots:
                grid[note.string][slot + 1] = ""

    # Render output
    lines = [_header(title, tuning, bpm), ""]

    for line_start in range(0, total_slots, slots_per_line):
        line_end = min(line_start + slots_per_line, total_slots)

        for string_num in range(1, 7):  # high e to low E
            label = STRING_LABELS[string_num]
            chars = []
            for slot in range(line_start, line_end):
                ch = grid[string_num][slot]
                chars.append(ch)
                # Add measure bar
                if (slot + 1) % slots_per_measure == 0 and slot + 1 < line_end:
                    chars.append("|")

            line = f"{label}|{''.join(chars)}|"
            lines.append(line)

        lines.append("")  # blank line between tab lines

    return "\n".join(lines)


def _header(title: str, tuning: str, bpm: float) -> str:
    parts = ["Clawde - Audio to Fingerstyle Tab"]
    parts.append("=" * len(parts[0]))
    info = []
    if title:
        info.append(f"File: {title}")
    info.append(f"Tuning: {tuning.replace('_', ' ').title()}")
    info.append(f"BPM: ~{int(bpm)}")
    parts.append(" | ".join(info))
    return "\n".join(parts)
