"""Claude API-based tab refinement for musical quality."""

from __future__ import annotations

import json
import os
from dataclasses import asdict

from clawde.mapper import GuitarNote

SYSTEM_PROMPT = """You are a fingerstyle guitar arrangement expert. You receive a machine-generated guitar tab (as a JSON list of notes) and refine it for musical quality.

Each note has: time, duration, string (1=high e, 6=low E), fret, pitch, velocity, effect (null/"dead"/"palm_mute").

Rules:
1. Remove excessive percussive notes (effect="dead" or "palm_mute") that disrupt the musical flow. Keep only those that add rhythmic value.
2. When melody is absent, ensure the most prominent musical line is on high strings (1-2).
3. Remove notes that create unplayable stretches (fret distance > 5 between simultaneous notes).
4. Ensure bass notes (strings 5-6) provide a solid foundation - don't remove bass on beat 1 and 3.
5. Remove duplicate/redundant notes that muddy the sound.
6. Keep the arrangement playable for an intermediate fingerstyle guitarist.

Return ONLY a valid JSON array of refined notes with the same field structure. No explanation."""

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
