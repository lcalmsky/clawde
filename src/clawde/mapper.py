"""MIDI note to guitar position mapping."""

from __future__ import annotations

from dataclasses import dataclass
from typing import NamedTuple

from clawde.transcriber import Note
from clawde.percussive import PercussiveEvent


# Guitar tunings: (string_6, string_5, string_4, string_3, string_2, string_1)
# Values are MIDI pitch numbers for open strings
TUNINGS: dict[str, tuple[int, ...]] = {
    "standard":  (40, 45, 50, 55, 59, 64),  # E A D G B e
    "drop_d":    (38, 45, 50, 55, 59, 64),  # D A D G B e
    "open_g":    (38, 43, 50, 55, 59, 62),  # D G D G B D
    "dadgad":    (38, 45, 50, 55, 57, 62),  # D A D G A D
}

MAX_FRET = 15
SIMULTANEOUS_THRESHOLD_MS = 30  # notes within 30ms are "simultaneous"
OPEN_STRING_BONUS = -2          # prefer open strings in distance calculation


class Position(NamedTuple):
    string: int   # 6 (low E) to 1 (high e)
    fret: int     # 0 to MAX_FRET


@dataclass
class GuitarNote:
    """A note mapped to a guitar position."""
    time: float
    duration: float
    string: int
    fret: int
    pitch: int
    velocity: int
    effect: str | None = None  # None, "dead", "palm_mute"


def get_candidates(pitch: int, tuning: tuple[int, ...]) -> list[Position]:
    """Get all possible guitar positions for a MIDI pitch."""
    candidates = []
    for string_idx, open_pitch in enumerate(tuning):
        fret = pitch - open_pitch
        if 0 <= fret <= MAX_FRET:
            string_num = 6 - string_idx  # convert to 6=low, 1=high
            candidates.append(Position(string_num, fret))
    return candidates


def _position_cost(pos: Position, prev_fret: int | None) -> float:
    """Calculate cost of choosing a position given previous fret."""
    cost = 0.0

    # Prefer open strings
    if pos.fret == 0:
        cost += OPEN_STRING_BONUS

    # Minimize hand movement from previous position
    if prev_fret is not None and prev_fret > 0:
        cost += abs(pos.fret - prev_fret)

    # Slight preference for lower positions (more common in fingerstyle)
    cost += pos.fret * 0.1

    return cost


def _group_simultaneous(notes: list[Note]) -> list[list[Note]]:
    """Group notes that sound simultaneously."""
    if not notes:
        return []

    groups: list[list[Note]] = []
    current_group: list[Note] = [notes[0]]

    for note in notes[1:]:
        time_diff_ms = (note.start_time - current_group[0].start_time) * 1000
        if time_diff_ms <= SIMULTANEOUS_THRESHOLD_MS:
            current_group.append(note)
        else:
            groups.append(current_group)
            current_group = [note]

    groups.append(current_group)
    return groups


def _assign_simultaneous(
    notes: list[Note],
    tuning: tuple[int, ...],
    prev_fret: int | None,
) -> list[GuitarNote]:
    """Assign positions to simultaneously sounding notes.

    Ensures each note goes to a different string.
    Uses backtracking to find the best assignment.
    """
    if len(notes) == 1:
        candidates = get_candidates(notes[0].pitch, tuning)
        if not candidates:
            return []
        best = min(candidates, key=lambda p: _position_cost(p, prev_fret))
        return [GuitarNote(
            time=notes[0].start_time,
            duration=notes[0].duration,
            string=best.string,
            fret=best.fret,
            pitch=notes[0].pitch,
            velocity=notes[0].velocity,
        )]

    # Get candidates for each note
    all_candidates = [get_candidates(n.pitch, tuning) for n in notes]

    # Filter notes that have no candidates
    valid = [(n, c) for n, c in zip(notes, all_candidates) if c]
    if not valid:
        return []

    # Sort by fewest candidates first (most constrained)
    valid.sort(key=lambda x: len(x[1]))

    # Greedy assignment with string conflict avoidance
    used_strings: set[int] = set()
    result: list[GuitarNote] = []

    for note, candidates in valid:
        available = [p for p in candidates if p.string not in used_strings]
        if not available:
            available = candidates  # fallback: allow string reuse

        best = min(available, key=lambda p: _position_cost(p, prev_fret))
        used_strings.add(best.string)
        result.append(GuitarNote(
            time=note.start_time,
            duration=note.duration,
            string=best.string,
            fret=best.fret,
            pitch=note.pitch,
            velocity=note.velocity,
        ))

    return result


def map_notes(notes: list[Note], tuning: str = "standard") -> list[GuitarNote]:
    """Map MIDI notes to guitar positions.

    Args:
        notes: List of transcribed MIDI notes, sorted by start_time.
        tuning: Guitar tuning name.

    Returns:
        List of GuitarNote with string/fret assignments.
    """
    if tuning not in TUNINGS:
        raise ValueError(f"Unknown tuning: {tuning}. Available: {list(TUNINGS.keys())}")

    tuning_pitches = TUNINGS[tuning]
    groups = _group_simultaneous(notes)

    prev_fret: int | None = None
    result: list[GuitarNote] = []

    for group in groups:
        assigned = _assign_simultaneous(group, tuning_pitches, prev_fret)
        result.extend(assigned)

        # Update prev_fret with the highest fret in this group (hand position)
        frets = [g.fret for g in assigned if g.fret > 0]
        if frets:
            prev_fret = max(frets)

    return result


PREFERRED_STRING_BONUS = -5  # strong preference for target strings


def map_notes_constrained(
    notes: list[Note],
    tuning: str = "standard",
    preferred_strings: tuple[int, ...] = (),
) -> list[GuitarNote]:
    """Map MIDI notes with preferred string constraints.

    Like map_notes but strongly prefers placing notes on preferred_strings.
    Falls back to other strings only when preferred ones can't reach the pitch.
    """
    if tuning not in TUNINGS:
        raise ValueError(f"Unknown tuning: {tuning}. Available: {list(TUNINGS.keys())}")

    tuning_pitches = TUNINGS[tuning]
    groups = _group_simultaneous(notes)

    prev_fret: int | None = None
    result: list[GuitarNote] = []

    for group in groups:
        assigned = _assign_constrained(
            group, tuning_pitches, prev_fret, preferred_strings,
        )
        result.extend(assigned)

        frets = [g.fret for g in assigned if g.fret > 0]
        if frets:
            prev_fret = max(frets)

    return result


def _constrained_cost(pos: Position, prev_fret: int | None,
                      preferred: tuple[int, ...]) -> float:
    """Position cost with preferred string bonus."""
    cost = _position_cost(pos, prev_fret)
    if preferred and pos.string in preferred:
        cost += PREFERRED_STRING_BONUS
    return cost


def _assign_constrained(
    notes: list[Note],
    tuning: tuple[int, ...],
    prev_fret: int | None,
    preferred: tuple[int, ...],
) -> list[GuitarNote]:
    """Assign positions with string preference constraints."""
    used_strings: set[int] = set()
    result: list[GuitarNote] = []

    for note in notes:
        candidates = get_candidates(note.pitch, tuning)
        if not candidates:
            continue

        available = [p for p in candidates if p.string not in used_strings]
        if not available:
            available = candidates

        best = min(available, key=lambda p: _constrained_cost(p, prev_fret, preferred))
        used_strings.add(best.string)
        result.append(GuitarNote(
            time=note.start_time,
            duration=note.duration,
            string=best.string,
            fret=best.fret,
            pitch=note.pitch,
            velocity=note.velocity,
        ))

    return result


# Percussive event → guitar string mapping
_PERCUSSIVE_STRING_MAP = {
    "body_tap": 6,     # low E string area
    "mute": 4,         # mid strings
    "string_tap": 1,   # high e string
}

_PERCUSSIVE_EFFECT_MAP = {
    "body_tap": "dead",
    "mute": "palm_mute",
    "string_tap": "dead",
}

PERCUSSIVE_DURATION = 0.05  # short percussive hit


def map_percussive(events: list[PercussiveEvent]) -> list[GuitarNote]:
    """Map percussive events to guitar notes with effects."""
    result = []
    for event in events:
        string = _PERCUSSIVE_STRING_MAP.get(event.category, 4)
        effect = _PERCUSSIVE_EFFECT_MAP.get(event.category, "dead")

        result.append(GuitarNote(
            time=event.time,
            duration=PERCUSSIVE_DURATION,
            string=string,
            fret=0,
            pitch=0,
            velocity=int(event.strength * 127),
            effect=effect,
        ))
    return result
