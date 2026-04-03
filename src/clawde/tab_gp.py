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

# Valid slot counts and their GP duration values
# Each entry: (slot_count, gp_duration_value, is_dotted)
VALID_DURATIONS = [
    (16, 1, False),   # whole
    (12, 2, True),    # dotted half
    (8,  2, False),   # half
    (6,  4, True),    # dotted quarter
    (4,  4, False),   # quarter
    (3,  8, True),    # dotted eighth
    (2,  8, False),   # eighth
    (1,  16, False),  # sixteenth
]


def _decompose_slots(n_slots: int) -> list[tuple[int, int, bool]]:
    """Decompose a slot count into valid GP durations.

    Returns list of (slot_count, gp_duration_value, is_dotted).
    E.g., 5 slots → [(4, 4, False), (1, 16, False)] (quarter + 16th)
    """
    result = []
    remaining = n_slots
    for slot_count, dur_value, is_dotted in VALID_DURATIONS:
        while remaining >= slot_count:
            result.append((slot_count, dur_value, is_dotted))
            remaining -= slot_count
    return result


def _quantize_slot(time_sec: float, slot_duration_sec: float) -> int:
    return round(time_sec / slot_duration_sec)


def _note_duration_slots(note_duration_sec: float, slot_duration_sec: float) -> int:
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
    note_durations: dict[int, int] = {}

    for note in notes:
        slot = _quantize_slot(note.time, slot_duration_sec)
        slot = min(slot, total_slots - 1)
        grid.setdefault(slot, []).append(note)
        dur_slots = _note_duration_slots(note.duration, slot_duration_sec)
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
        pos = 0

        while pos < SLOTS_PER_MEASURE:
            abs_slot = slot_offset + pos

            if abs_slot in grid:
                # Note beat - use only the first valid duration chunk,
                # tie the rest as sustained
                dur_slots = note_durations[abs_slot]
                dur_slots = min(dur_slots, SLOTS_PER_MEASURE - pos)
                chunks = _decompose_slots(dur_slots)
                if not chunks:
                    chunks = [(1, 16, False)]

                gnotes_for_slot = grid[abs_slot]

                for i, (chunk_slots, dur_value, is_dotted) in enumerate(chunks):
                    gp_duration = guitarpro.models.Duration()
                    gp_duration.value = dur_value
                    gp_duration.isDotted = is_dotted

                    beat = guitarpro.models.Beat(voice, duration=gp_duration)

                    if i == 0:
                        # First chunk: place the actual notes
                        for gnote in gnotes_for_slot:
                            gp_note = guitarpro.models.Note(beat)
                            gp_note.string = gnote.string
                            gp_note.value = gnote.fret
                            gp_note.velocity = guitarpro.models.Velocities.forte

                            if gnote.effect == "dead":
                                gp_note.type = guitarpro.models.NoteType.dead
                            elif gnote.effect == "palm_mute":
                                gp_note.effect.palmMute = True

                            beat.notes.append(gp_note)
                    else:
                        # Continuation chunks: rest (simpler than tied notes)
                        beat.status = guitarpro.models.BeatStatus.rest

                    voice.beats.append(beat)
                    pos += chunk_slots
            else:
                # Rest: find how many slots until next note or measure end
                rest_slots = 1
                while (pos + rest_slots < SLOTS_PER_MEASURE
                       and (slot_offset + pos + rest_slots) not in grid):
                    rest_slots += 1

                # Decompose rest into valid durations
                chunks = _decompose_slots(rest_slots)
                if not chunks:
                    chunks = [(1, 16, False)]

                for chunk_slots, dur_value, is_dotted in chunks:
                    gp_duration = guitarpro.models.Duration()
                    gp_duration.value = dur_value
                    gp_duration.isDotted = is_dotted

                    beat = guitarpro.models.Beat(voice, duration=gp_duration,
                                                 status=guitarpro.models.BeatStatus.rest)
                    voice.beats.append(beat)
                    pos += chunk_slots

    guitarpro.write(song, str(output_path))
    return output_path
