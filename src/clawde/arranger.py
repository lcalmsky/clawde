"""Role-based fingerstyle arrangement from separated stems."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from clawde.mapper import GuitarNote, map_notes_constrained, map_percussive
from clawde.percussive import detect_percussive
from clawde.separator import StemPaths
from clawde.transcriber import transcribe, Note


SIMULTANEOUS_THRESHOLD_MS = 30


@dataclass
class ArrangementConfig:
    melody_strings: tuple[int, ...] = (1, 2)
    bass_strings: tuple[int, ...] = (5, 6)
    harmony_strings: tuple[int, ...] = (3, 4)
    max_simultaneous: int = 6


def arrange(
    stems: StemPaths,
    tuning: str = "standard",
    bpm: float = 120.0,
    config: ArrangementConfig | None = None,
) -> list[GuitarNote]:
    """Arrange separated stems into a single fingerstyle guitar part.

    Transcribes each stem with role-appropriate string constraints,
    then merges with priority: melody > bass > harmony > percussive.
    """
    cfg = config or ArrangementConfig()

    # Transcribe each stem
    vocal_notes_raw = transcribe(stems.vocals) if stems.vocals.exists() else []
    other_notes_raw = transcribe(stems.other) if stems.other.exists() else []

    # Dynamic role assignment: when vocals are quiet, promote "other" to melody
    melody_notes, harmony_notes = _dynamic_role_split(
        vocal_notes_raw, other_notes_raw, tuning, cfg,
    )

    bass_notes = _transcribe_stem(stems.bass, tuning, cfg.bass_strings)
    perc_notes = _detect_perc_stem(stems.drums)

    # Merge with priority
    merged = _priority_merge(
        melody_notes, bass_notes, harmony_notes, perc_notes,
        max_simultaneous=cfg.max_simultaneous,
    )

    return merged


# Window size for detecting "vocal silence" (seconds)
SILENCE_WINDOW = 0.5


def _dynamic_role_split(
    vocal_raw: list[Note],
    other_raw: list[Note],
    tuning: str,
    cfg: ArrangementConfig,
) -> tuple[list[GuitarNote], list[GuitarNote]]:
    """Split other stem into melody/harmony based on vocal presence.

    When vocals are active: vocals=melody(high strings), other=harmony(mid strings)
    When vocals are silent: other's highest notes=melody(high strings), rest=harmony
    """
    if not other_raw:
        melody = map_notes_constrained(vocal_raw, tuning, cfg.melody_strings) if vocal_raw else []
        return melody, []

    if not vocal_raw:
        # No vocals at all - other takes melody role entirely
        return map_notes_constrained(other_raw, tuning, cfg.melody_strings), []

    # Build vocal activity timeline: set of time windows where vocals are present
    vocal_times = sorted(set(round(n.start_time / SILENCE_WINDOW) for n in vocal_raw))
    vocal_active = set(vocal_times)

    # Split other_raw into melody-promoted and harmony
    promoted: list[Note] = []
    harmony_raw: list[Note] = []

    for note in other_raw:
        window = round(note.start_time / SILENCE_WINDOW)
        if window not in vocal_active:
            promoted.append(note)
        else:
            harmony_raw.append(note)

    # Map vocals + promoted-other as melody, rest as harmony
    all_melody_raw = vocal_raw + promoted
    all_melody_raw.sort(key=lambda n: (n.start_time, n.pitch))

    melody = map_notes_constrained(all_melody_raw, tuning, cfg.melody_strings)
    harmony = map_notes_constrained(harmony_raw, tuning, cfg.harmony_strings)

    return melody, harmony


def _transcribe_stem(
    stem_path: Path,
    tuning: str,
    preferred_strings: tuple[int, ...],
) -> list[GuitarNote]:
    """Transcribe a single stem and map to constrained guitar positions."""
    if not stem_path.exists():
        return []

    notes = transcribe(stem_path)
    if not notes:
        return []

    return map_notes_constrained(notes, tuning, preferred_strings)


def _detect_perc_stem(drum_path: Path) -> list[GuitarNote]:
    """Detect percussive events from the drum stem."""
    if not drum_path.exists():
        return []

    events = detect_percussive(drum_path)
    return map_percussive(events)


def _group_by_time(notes: list[GuitarNote]) -> list[list[GuitarNote]]:
    """Group notes that sound simultaneously (within threshold)."""
    if not notes:
        return []

    sorted_notes = sorted(notes, key=lambda n: n.time)
    groups: list[list[GuitarNote]] = []
    current: list[GuitarNote] = [sorted_notes[0]]

    for note in sorted_notes[1:]:
        if (note.time - current[0].time) * 1000 <= SIMULTANEOUS_THRESHOLD_MS:
            current.append(note)
        else:
            groups.append(current)
            current = [note]

    groups.append(current)
    return groups


def _priority_merge(
    melody: list[GuitarNote],
    bass: list[GuitarNote],
    harmony: list[GuitarNote],
    percussive: list[GuitarNote],
    max_simultaneous: int = 6,
) -> list[GuitarNote]:
    """Merge notes from all roles with priority-based conflict resolution.

    Priority: melody > bass > harmony > percussive.
    Within each simultaneous group, if total notes > max_simultaneous,
    remove lowest-priority notes first.
    """
    # Tag each note with priority for sorting
    tagged: list[tuple[int, GuitarNote]] = []
    for n in melody:
        tagged.append((0, n))  # highest priority
    for n in bass:
        tagged.append((1, n))
    for n in harmony:
        tagged.append((2, n))
    for n in percussive:
        tagged.append((3, n))  # lowest priority

    all_notes = [n for _, n in tagged]
    priorities = {id(n): p for p, n in tagged}

    groups = _group_by_time(all_notes)
    result: list[GuitarNote] = []

    for group in groups:
        # Sort by priority (lower = higher priority)
        group.sort(key=lambda n: priorities.get(id(n), 99))

        used_strings: set[int] = set()
        kept: list[GuitarNote] = []

        for note in group:
            if len(kept) >= max_simultaneous:
                break
            if note.string in used_strings:
                continue
            used_strings.add(note.string)
            kept.append(note)

        result.extend(kept)

    result.sort(key=lambda n: n.time)
    return result
