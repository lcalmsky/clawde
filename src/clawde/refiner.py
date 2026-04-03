"""Claude API-based tab refinement for musical quality."""

from __future__ import annotations

import json
import os
from dataclasses import asdict

from clawde.mapper import GuitarNote

SYSTEM_PROMPT = """You are a fingerstyle guitar arrangement expert. You receive a machine-generated guitar tab (as a JSON list of notes) and refine it for musical quality and playability.

Each note has: time, duration, string (1=high e, 6=low E), fret, pitch, velocity, effect (null/"dead"/"palm_mute").

FINGERING RULES (highest priority):
1. Simultaneous notes must be playable: max fret span of 4 frets (5 with stretch). If wider, move notes to equivalent positions on adjacent strings, or remove the least important note.
2. Prefer positions in frets 0-7 (first position). Relocate notes to lower positions when the same pitch is available (e.g., fret 12 on string 2 = fret 7 on string 1).
3. Consecutive notes should minimize hand jumps. If two adjacent notes are >5 frets apart, find alternative positions on different strings.
4. Open strings (fret 0) are preferred when available - they allow the other hand to prepare for the next position.

ARRANGEMENT RULES:
5. Remove excessive percussive notes (effect="dead"/"palm_mute"). Keep at most 1 percussive per beat. Remove any that fall on the same beat as melodic notes.
6. Melody (highest pitched notes) should be on strings 1-2 and clearly audible. Don't bury melody under harmony.
7. Bass notes on strings 5-6 should follow the chord root, especially on beats 1 and 3.
8. Remove duplicate/redundant notes. If two notes on different strings produce the same pitch, keep only one.
9. Thin out dense passages - an intermediate guitarist can play max 3-4 notes simultaneously.

MUSICAL RULES:
10. Maintain consistent rhythm patterns. Don't create irregular gaps.
11. If you detect a recognizable chord progression, ensure voicings match standard guitar chord shapes.

When relocating a note to a different string/fret, update BOTH string and fret fields. The pitch field stays the same.

Return ONLY a valid JSON array of refined notes. No explanation."""

USER_PROMPT_TEMPLATE = """Refine this fingerstyle guitar tab. BPM: {bpm}, Tuning: {tuning}.

Notes (JSON):
{notes_json}

Return the refined JSON array only."""

# Process in chunks to stay within token limits
CHUNK_DURATION_SEC = 30.0


def refine(
    notes: list[GuitarNote],
    bpm: float = 120.0,
    tuning: str = "standard",
) -> list[GuitarNote]:
    """Refine guitar notes using Claude API for musical quality.

    Returns original notes if API key is missing or on error.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return notes

    try:
        import anthropic  # lazy import
    except ImportError:
        return notes

    if not notes:
        return notes

    client = anthropic.Anthropic(api_key=api_key)

    # Process in time chunks to avoid token limits
    chunks = _split_by_time(notes, CHUNK_DURATION_SEC)
    refined_all: list[GuitarNote] = []

    for chunk in chunks:
        refined_chunk = _refine_chunk(client, chunk, bpm, tuning)
        refined_all.extend(refined_chunk)

    refined_all.sort(key=lambda n: n.time)
    return refined_all


def _split_by_time(notes: list[GuitarNote], window: float) -> list[list[GuitarNote]]:
    """Split notes into time-based chunks."""
    if not notes:
        return []

    chunks: list[list[GuitarNote]] = []
    current: list[GuitarNote] = []
    chunk_start = notes[0].time

    for note in sorted(notes, key=lambda n: n.time):
        if note.time - chunk_start >= window and current:
            chunks.append(current)
            current = []
            chunk_start = note.time
        current.append(note)

    if current:
        chunks.append(current)

    return chunks


def _refine_chunk(
    client,
    notes: list[GuitarNote],
    bpm: float,
    tuning: str,
) -> list[GuitarNote]:
    """Refine a single chunk of notes via Claude API."""
    notes_dicts = [asdict(n) for n in notes]
    notes_json = json.dumps(notes_dicts, indent=None)

    user_msg = USER_PROMPT_TEMPLATE.format(
        bpm=bpm, tuning=tuning, notes_json=notes_json,
    )

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )

        content = response.content[0].text.strip()
        # Strip markdown code fences if present
        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else content[3:]
            if content.endswith("```"):
                content = content[:-3].strip()

        refined_dicts = json.loads(content)

        return [
            GuitarNote(
                time=d["time"],
                duration=d["duration"],
                string=d["string"],
                fret=d["fret"],
                pitch=d["pitch"],
                velocity=d["velocity"],
                effect=d.get("effect"),
            )
            for d in refined_dicts
        ]
    except Exception:
        # On any error, return original notes
        return notes
