"""Tests for role-based arrangement module."""

from clawde.arranger import _priority_merge, _group_by_time, ArrangementConfig
from clawde.mapper import GuitarNote


def _note(time, string, fret=5, effect=None):
    return GuitarNote(time=time, duration=0.5, string=string, fret=fret,
                      pitch=60, velocity=80, effect=effect)


class TestGroupByTime:
    def test_single_note(self):
        groups = _group_by_time([_note(0.0, 1)])
        assert len(groups) == 1
        assert len(groups[0]) == 1

    def test_simultaneous_grouped(self):
        notes = [_note(0.0, 1), _note(0.01, 2), _note(0.02, 3)]
        groups = _group_by_time(notes)
        assert len(groups) == 1
        assert len(groups[0]) == 3

    def test_separate_groups(self):
        notes = [_note(0.0, 1), _note(1.0, 2)]
        groups = _group_by_time(notes)
        assert len(groups) == 2

    def test_empty(self):
        assert _group_by_time([]) == []


class TestPriorityMerge:
    def test_melody_wins_over_harmony(self):
        melody = [_note(0.0, 1)]
        harmony = [_note(0.0, 1)]  # same string conflict
        result = _priority_merge(melody, [], harmony, [])
        assert len(result) == 1
        assert result[0] is melody[0]

    def test_all_roles_fit(self):
        melody = [_note(0.0, 1)]
        bass = [_note(0.0, 6)]
        harmony = [_note(0.0, 3)]
        perc = [_note(0.0, 4, effect="dead")]
        result = _priority_merge(melody, bass, harmony, perc)
        assert len(result) == 4

    def test_six_string_limit(self):
        melody = [_note(0.0, 1), _note(0.0, 2)]
        bass = [_note(0.0, 5), _note(0.0, 6)]
        harmony = [_note(0.0, 3), _note(0.0, 4)]
        perc = [_note(0.0, 4, effect="dead")]  # conflicts with harmony
        result = _priority_merge(melody, bass, harmony, perc, max_simultaneous=6)
        assert len(result) == 6

    def test_exceeds_limit_removes_low_priority(self):
        # 7 notes on different strings - percussive should be dropped
        melody = [_note(0.0, 1)]
        bass = [_note(0.0, 6)]
        harmony = [_note(0.0, 2), _note(0.0, 3), _note(0.0, 4), _note(0.0, 5)]
        perc = [_note(0.0, 4, effect="dead")]  # string 4 already taken by harmony
        result = _priority_merge(melody, bass, harmony, perc, max_simultaneous=6)
        # melody(1) + bass(1) + harmony(4) = 6, perc conflicts on string 4
        assert len(result) == 6
        strings = {n.string for n in result}
        assert 1 in strings  # melody kept
        assert 6 in strings  # bass kept

    def test_empty_stems(self):
        result = _priority_merge([], [], [], [])
        assert result == []

    def test_only_melody(self):
        melody = [_note(0.0, 1), _note(0.5, 2)]
        result = _priority_merge(melody, [], [], [])
        assert len(result) == 2


class TestArrangementConfig:
    def test_defaults(self):
        cfg = ArrangementConfig()
        assert cfg.melody_strings == (1, 2)
        assert cfg.bass_strings == (5, 6)
        assert cfg.harmony_strings == (3, 4)
        assert cfg.max_simultaneous == 6
