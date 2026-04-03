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
SLOTS_PER_BEAT = 4
SLOTS_PER_MEASURE = BEATS_PER_MEASURE * SLOTS_PER_BEAT


def _quantize_slot(time_sec: float, slot_duration_sec: float) -> int:
    return round(time_sec / slot_duration_sec)


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
    track.channel.instrument = 25
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

    # Quantize notes to eighth-note grid (8 beats per measure)
    eighth_duration_sec = beat_duration_sec / 2
    EIGHTHS_PER_MEASURE = BEATS_PER_MEASURE * 2  # 8

    beat_grid: dict[int, list[GuitarNote]] = {}
    for note in notes:
        beat_idx = round(note.time / eighth_duration_sec)
        beat_grid.setdefault(beat_idx, []).append(note)

    # Ensure enough measures
    while len(song.measureHeaders) < num_measures:
        header = guitarpro.models.MeasureHeader()
        header.tempo = int(bpm)
        song.measureHeaders.append(header)

    while len(track.measures) < num_measures:
        measure_header = song.measureHeaders[len(track.measures)]
        measure = guitarpro.models.Measure(track, measure_header)
        track.measures.append(measure)

    # Fill each measure with exactly 8 eighth-note beats
    EIGHTHS_PER_MEASURE = BEATS_PER_MEASURE * 2

    for m_idx in range(num_measures):
        measure = track.measures[m_idx]
        voice = measure.voices[0]
        voice.beats = []

        for beat_in_measure in range(EIGHTHS_PER_MEASURE):
            abs_beat = m_idx * EIGHTHS_PER_MEASURE + beat_in_measure

            gp_duration = guitarpro.models.Duration()
            gp_duration.value = 8  # eighth note

            if abs_beat in beat_grid:
                beat = guitarpro.models.Beat(voice, duration=gp_duration)

                # Deduplicate by string (keep first per string)
                seen_strings: set[int] = set()
                for gnote in beat_grid[abs_beat]:
                    if gnote.string in seen_strings:
                        continue
                    seen_strings.add(gnote.string)

                    gp_note = guitarpro.models.Note(beat)
                    gp_note.string = gnote.string
                    gp_note.value = gnote.fret
                    gp_note.velocity = guitarpro.models.Velocities.forte

                    if gnote.effect == "dead":
                        gp_note.type = guitarpro.models.NoteType.dead
                    elif gnote.effect == "palm_mute":
                        gp_note.effect.palmMute = True

                    beat.notes.append(gp_note)

                voice.beats.append(beat)
            else:
                beat = guitarpro.models.Beat(
                    voice, duration=gp_duration,
                    status=guitarpro.models.BeatStatus.rest,
                )
                voice.beats.append(beat)

    guitarpro.write(song, str(output_path))
    return output_path
