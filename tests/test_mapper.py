"""Tests for guitar position mapping."""

from clawde.mapper import (
    get_candidates,
    map_notes,
    map_percussive,
    GuitarNote,
    Position,
    TUNINGS,
)
from clawde.transcriber import Note
from clawde.percussive import PercussiveEvent


class TestGetCandidates:
    def test_open_e_string(self):
        """E2 (40) should map to 6th string open."""
        candidates = get_candidates(40, TUNINGS["standard"])
        assert Position(6, 0) in candidates

    def test_middle_c(self):
        """C4 (60) should have multiple positions."""
        candidates = get_candidates(60, TUNINGS["standard"])
        assert len(candidates) >= 2
        # 1st string, fret 8 (64 - 60... wait, 60 - 64 = -4, not valid)
        # 2nd string, fret 1 (60 - 59 = 1)
        assert Position(2, 1) in candidates
        # 3rd string, fret 5 (60 - 55 = 5)
        assert Position(3, 5) in candidates

    def test_out_of_range_high(self):
        """Very high notes should have fewer candidates."""
        candidates = get_candidates(84, TUNINGS["standard"])  # C6
        # 84 - 64 = 20, too high for fret 15
        assert len(candidates) == 0

    def test_out_of_range_low(self):
        """Notes below lowest string should have no candidates."""
        candidates = get_candidates(30, TUNINGS["standard"])
        assert len(candidates) == 0

    def test_drop_d_tuning(self):
        """D2 (38) should map to 6th string open in Drop D."""
        candidates = get_candidates(38, TUNINGS["drop_d"])
        assert Position(6, 0) in candidates

        # In standard tuning, D2 would be 6th string fret 0 doesn't work (40-38=-2)
        candidates_std = get_candidates(38, TUNINGS["standard"])
        assert Position(6, 0) not in candidates_std


class TestMapNotes:
    def test_single_note(self):
        """Single note should get a valid position."""
        notes = [Note(start_time=0.0, end_time=0.5, pitch=60, velocity=80)]
        result = map_notes(notes, "standard")
        assert len(result) == 1
        assert isinstance(result[0], GuitarNote)
        assert result[0].pitch == 60

    def test_open_string_preference(self):
        """Open string should be preferred when available."""
        # E4 (64) = 1st string open
        notes = [Note(start_time=0.0, end_time=0.5, pitch=64, velocity=80)]
        result = map_notes(notes, "standard")
        assert result[0].string == 1
        assert result[0].fret == 0

    def test_simultaneous_notes_different_strings(self):
        """Simultaneous notes should be on different strings."""
        notes = [
            Note(start_time=0.0, end_time=0.5, pitch=40, velocity=80),  # E2
            Note(start_time=0.0, end_time=0.5, pitch=52, velocity=80),  # E3
            Note(start_time=0.0, end_time=0.5, pitch=64, velocity=80),  # E4
        ]
        result = map_notes(notes, "standard")
        strings = {n.string for n in result}
        assert len(strings) == 3  # all on different strings

    def test_sequential_minimizes_movement(self):
        """Sequential notes should minimize fret distance."""
        notes = [
            Note(start_time=0.0, end_time=0.3, pitch=60, velocity=80),  # C4
            Note(start_time=0.5, end_time=0.8, pitch=62, velocity=80),  # D4
            Note(start_time=1.0, end_time=1.3, pitch=64, velocity=80),  # E4
        ]
        result = map_notes(notes, "standard")
        # Should stay in a similar fret area
        frets = [n.fret for n in result]
        max_jump = max(abs(frets[i+1] - frets[i]) for i in range(len(frets)-1))
        assert max_jump <= 5  # reasonable hand movement

    def test_empty_notes(self):
        """Empty input should return empty output."""
        result = map_notes([], "standard")
        assert result == []

    def test_unknown_tuning_raises(self):
        """Unknown tuning should raise ValueError."""
        import pytest
        with pytest.raises(ValueError, match="Unknown tuning"):
            map_notes([], "random_tuning")


class TestMapPercussive:
    def test_body_tap(self):
        events = [PercussiveEvent(time=1.0, category="body_tap", strength=0.9)]
        result = map_percussive(events)
        assert len(result) == 1
        assert result[0].string == 6
        assert result[0].effect == "dead"

    def test_mute(self):
        events = [PercussiveEvent(time=1.0, category="mute", strength=0.7)]
        result = map_percussive(events)
        assert result[0].string == 4
        assert result[0].effect == "palm_mute"

    def test_string_tap(self):
        events = [PercussiveEvent(time=1.0, category="string_tap", strength=0.5)]
        result = map_percussive(events)
        assert result[0].string == 1
        assert result[0].effect == "dead"

    def test_empty_events(self):
        assert map_percussive([]) == []

    def test_velocity_from_strength(self):
        events = [PercussiveEvent(time=0.0, category="body_tap", strength=1.0)]
        result = map_percussive(events)
        assert result[0].velocity == 127
