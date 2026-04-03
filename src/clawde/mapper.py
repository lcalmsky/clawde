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

    # Slight preference for lower positions
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


MAX_HAND_SPAN = 4  # max fret distance for simultaneous notes (realistic finger span)


def _group_hand_position(positions: list[Position]) -> int:
    """Get the central fret of a group of positions (hand position)."""
    frets = [p.fret for p in positions if p.fret > 0]
    return round(sum(frets) / len(frets)) if frets else 0


def _stretch_penalty(positions: list[Position]) -> float:
    """Penalize hand stretches beyond comfortable range (4 frets max)."""
    frets = [p.fret for p in positions if p.fret > 0]
    if len(frets) < 2:
        return 0.0
    span = max(frets) - min(frets)
    if span <= MAX_HAND_SPAN:
        return 0.0
    # Physically impossible stretches get extreme penalty
    return (span - MAX_HAND_SPAN) * 50.0


def _enumerate_group_assignments(
    notes: list[Note],
    tuning: tuple[int, ...],
    preferred: tuple[int, ...] = (),
    max_assignments: int = 20,
) -> list[list[Position]]:
    """Enumerate possible position assignments for a simultaneous group.

    Returns up to max_assignments candidate assignments (each is a list of Positions).
    """
    all_candidates = [get_candidates(n.pitch, tuning) for n in notes]
    valid = [(i, c) for i, c in enumerate(all_candidates) if c]
    if not valid:
        return []

    # For single note, return all candidates as single-element lists
    if len(valid) == 1:
        idx, candidates = valid[0]
        return [[p] for p in candidates[:max_assignments]]

    # For multiple notes, generate assignments avoiding string conflicts
    # Use iterative approach with pruning
    assignments: list[list[Position]] = [[]]
    for idx, candidates in valid:
        new_assignments = []
        for partial in assignments:
            used = {p.string for p in partial}
            for c in candidates:
                if c.string not in used:
                    new_assignments.append(partial + [c])
        # Prune to keep manageable
        if len(new_assignments) > max_assignments * 3:
            new_assignments.sort(key=lambda a: _stretch_penalty(a))
            new_assignments = new_assignments[:max_assignments * 3]
        assignments = new_assignments

    if not assignments:
        # Fallback: allow string conflicts
        assignments = [[]]
        for idx, candidates in valid:
            new_assignments = []
            for partial in assignments:
                for c in candidates[:3]:
                    new_assignments.append(partial + [c])
            assignments = new_assignments[:max_assignments]

    # Score and return top assignments
    def score(a):
        s = _stretch_penalty(a)
        for p in a:
            if preferred and p.string in preferred:
                s -= 3.0
            if p.fret == 0:
                s -= 1.0
        return s

    assignments.sort(key=score)
    return assignments[:max_assignments]


def _assignment_cost(
    positions: list[Position],
    prev_hand: int | None,
    preferred: tuple[int, ...] = (),
) -> float:
    """Total cost of a group assignment given previous hand position."""
    cost = _stretch_penalty(positions)

    for p in positions:
        if p.fret == 0:
            cost += OPEN_STRING_BONUS
        if preferred and p.string in preferred:
            cost -= 3.0
        cost += p.fret * 0.05

    # Hand movement cost
    hand = _group_hand_position(positions)
    if prev_hand is not None and prev_hand > 0 and hand > 0:
        cost += abs(hand - prev_hand) * 0.8

    return cost


def map_notes(notes: list[Note], tuning: str = "standard") -> list[GuitarNote]:
    """Map MIDI notes to guitar positions using DP optimization.

    Finds globally optimal fingering by considering hand position
    transitions across all note groups.
    """
    return _map_notes_dp(notes, tuning, preferred_strings=())


PREFERRED_STRING_BONUS = -5


def map_notes_constrained(
    notes: list[Note],
    tuning: str = "standard",
    preferred_strings: tuple[int, ...] = (),
) -> list[GuitarNote]:
    """Map MIDI notes with preferred string constraints using DP."""
    return _map_notes_dp(notes, tuning, preferred_strings)


def _map_notes_dp(
    notes: list[Note],
    tuning: str,
    preferred_strings: tuple[int, ...],
) -> list[GuitarNote]:
    """DP-based note mapping that minimizes total hand movement + stretch."""
    if tuning not in TUNINGS:
        raise ValueError(f"Unknown tuning: {tuning}. Available: {list(TUNINGS.keys())}")
    if not notes:
        return []

    tuning_pitches = TUNINGS[tuning]
    groups = _group_simultaneous(notes)

    # Generate candidate assignments for each group
    group_candidates: list[list[list[Position]]] = []
    for group in groups:
        assignments = _enumerate_group_assignments(
            group, tuning_pitches, preferred_strings,
        )
        if not assignments:
            group_candidates.append([[]])
        else:
            group_candidates.append(assignments)

    n_groups = len(groups)
    if n_groups == 0:
        return []

    # DP: dp[i][j] = min cost to reach group i with assignment j
    # For efficiency, limit candidates per group
    MAX_CANDS = 10
    for i in range(n_groups):
        group_candidates[i] = group_candidates[i][:MAX_CANDS]

    dp = [{} for _ in range(n_groups)]
    parent = [{} for _ in range(n_groups)]

    # Initialize first group
    for j, assignment in enumerate(group_candidates[0]):
        cost = _assignment_cost(assignment, None, preferred_strings)
        dp[0][j] = cost
        parent[0][j] = -1

    # Fill DP table
    for i in range(1, n_groups):
        for j, assignment in enumerate(group_candidates[i]):
            best_cost = float('inf')
            best_prev = -1

            for k in dp[i - 1]:
                prev_assignment = group_candidates[i - 1][k]
                prev_hand = _group_hand_position(prev_assignment)
                transition_cost = dp[i - 1][k] + _assignment_cost(
                    assignment, prev_hand, preferred_strings,
                )
                if transition_cost < best_cost:
                    best_cost = transition_cost
                    best_prev = k

            dp[i][j] = best_cost
            parent[i][j] = best_prev

    # Backtrack to find optimal path
    if not dp[n_groups - 1]:
        return []

    best_last = min(dp[n_groups - 1], key=dp[n_groups - 1].get)
    path = [0] * n_groups
    path[n_groups - 1] = best_last
    for i in range(n_groups - 2, -1, -1):
        path[i] = parent[i + 1][path[i + 1]]

    # Build result
    result: list[GuitarNote] = []
    for i, group in enumerate(groups):
        assignment = group_candidates[i][path[i]]
        valid_notes = [n for n in group if get_candidates(n.pitch, tuning_pitches)]

        for note, pos in zip(valid_notes, assignment):
            result.append(GuitarNote(
                time=note.start_time,
                duration=note.duration,
                string=pos.string,
                fret=pos.fret,
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
