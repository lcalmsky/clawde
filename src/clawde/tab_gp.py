"""GuitarPro file generation using pyguitarpro."""

from __future__ import annotations

from pathlib import Path

import guitarpro

from clawde.mapper import GuitarNote

GP_TUNING_MAP = {
    "standard": [64, 59, 55, 50, 45, 40],  # e B G D A E (high to low)
    "drop_d":   [64, 59, 55, 50, 45, 38],
    "open_g":   [62, 59, 55, 50, 43, 38],
    "dadgad":   [62, 57, 55, 50, 45, 38],
}

BEATS_PER_MEASURE = 4
SLOTS_PER_BEAT = 4      # 16th note resolution
SLOTS_PER_MEASURE = BEATS_PER_MEASURE * SLOTS_PER_BEAT  # 16 slots per measure

# Duration value for each slot count (GP uses: 1=whole, 2=half, 4=quarter, etc.)
SLOT_TO_DURATION = {
    16: 1,   # whole
    12: 2,   # dotted half
    8:  2,   # half
    6:  4,   # dotted quarter
    4:  4,   # quarter
    3:  8,   # dotted eighth
    2:  8,   # eighth
    1:  16,  # sixteenth
}

SLOT_TO_DOTTED = {12, 6, 3}


def _quantize_slot(time_sec: float, slot_duration_sec: float) -> int:
    """Quantize a time in seconds to the nearest slot index."""
    return round(time_sec / slot_duration_sec)


def _duration_for_slots(n_slots: int) -> tuple[int, bool]:
    """Get GP duration value and dotted flag for a number of slots.

    Returns the largest fitting duration.
    """
    for slots, dur_value in sorted(SLOT_TO_DURATION.items(), reverse=True):
        if n_slots >= slots:
            return dur_value, slots in SLOT_TO_DOTTED
    return 16, False  # fallback: 16th note


def _note_duration_slots(note_duration_sec: float, slot_duration_sec: float) -> int:
    """Convert note duration in seconds to slot count, minimum 1."""
    return max(1, round(note_duration_sec / slot_duration_sec))


def generate(
    notes: list[GuitarNote],
    output_path: str | Path,
    bpm: float = 120.0,
    title: str = "Clawde Transcription",
    tuning: str = "standard",
) -> Path:
    output_path = Path(output_path)
    if not output_path.suffix:
        output_path = output_path.with_suffix(".gp5")

    song = guitarpro.models.Song()
    song.title = title
    song.tempo = int(bpm)

    track = song.tracks[0]
    track.name = "Fingerstyle Guitar"
    track.channel.instrument = 25  # Acoustic Guitar (steel)
    track.isPercussionTrack = False

    tuning_values = GP_TUNING_MAP.get(tuning, GP_TUNING_MAP["standard"])
    for i, value in enumerate(tuning_values):
        if i < len(track.strings):
            track.strings[i].value = value

    if not notes:
        guitarpro.write(song, str(output_path))
        return output_path

    beat_duration_sec = 60.0 / bpm
    slot_duration_sec = beat_duration_sec / SLOTS_PER_BEAT
    measure_duration_sec = beat_duration_sec * BEATS_PER_MEASURE

    max_time = max(n.time + n.duration for n in notes)
    num_measures = int(max_time / measure_duration_sec) + 1

    # Build slot grid: slot_index -> list of GuitarNote
    total_slots = num_measures * SLOTS_PER_MEASURE
    grid: dict[int, list[GuitarNote]] = {}
    note_durations: dict[int, int] = {}  # slot_index -> duration in slots

    for note in notes:
        slot = _quantize_slot(note.time, slot_duration_sec)
        slot = min(slot, total_slots - 1)
        grid.setdefault(slot, []).append(note)
        dur_slots = _note_duration_slots(note.duration, slot_duration_sec)
        # Use the longest duration if multiple notes on the same slot
        note_durations[slot] = max(note_durations.get(slot, 0), dur_slots)

    # Ensure enough measures
    while len(song.measureHeaders) < num_measures:
        header = guitarpro.models.MeasureHeader()
        header.tempo = int(bpm)
        song.measureHeaders.append(header)

    while len(track.measures) < num_measures:
        measure_header = song.measureHeaders[len(track.measures)]
        measure = guitarpro.models.Measure(track, measure_header)
        track.measures.append(measure)

    # Fill each measure with beats
    for m_idx in range(num_measures):
        measure = track.measures[m_idx]
        voice = measure.voices[0]
        voice.beats = []

        slot_offset = m_idx * SLOTS_PER_MEASURE
        pos = 0  # current position within measure (in slots)

        while pos < SLOTS_PER_MEASURE:
            abs_slot = slot_offset + pos

            if abs_slot in grid:
                # Note beat
                dur_slots = note_durations[abs_slot]
                # Don't exceed measure boundary
                dur_slots = min(dur_slots, SLOTS_PER_MEASURE - pos)
                dur_value, is_dotted = _duration_for_slots(dur_slots)

                gp_duration = guitarpro.models.Duration()
                gp_duration.value = dur_value
                gp_duration.isDotted = is_dotted

                beat = guitarpro.models.Beat(voice, duration=gp_duration)
                for gnote in grid[abs_slot]:
                    gp_note = guitarpro.models.Note(beat)
                    gp_note.string = gnote.string
                    gp_note.value = gnote.fret
                    gp_note.velocity = guitarpro.models.Velocities.forte
                    beat.notes.append(gp_note)

                voice.beats.append(beat)
                pos += dur_slots
            else:
                # Rest: find how many slots until next note or measure end
                rest_slots = 1
                while (pos + rest_slots < SLOTS_PER_MEASURE
                       and (slot_offset + pos + rest_slots) not in grid):
                    rest_slots += 1

                dur_value, is_dotted = _duration_for_slots(rest_slots)

                gp_duration = guitarpro.models.Duration()
                gp_duration.value = dur_value
                gp_duration.isDotted = is_dotted

                beat = guitarpro.models.Beat(voice, duration=gp_duration,
                                             status=guitarpro.models.BeatStatus.rest)
                voice.beats.append(beat)
                pos += rest_slots

    guitarpro.write(song, str(output_path))
    return output_path
