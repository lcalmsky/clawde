"""Tests for GuitarPro file generation."""

import tempfile
from pathlib import Path

import guitarpro

from clawde.mapper import GuitarNote
from clawde.tab_gp import generate


class TestGenerate:
    def test_creates_file(self):
        """Should create a .gp5 file."""
        notes = [GuitarNote(time=0.0, duration=0.5, string=1, fret=0, pitch=64, velocity=80)]
        with tempfile.TemporaryDirectory() as tmpdir:
            path = generate(notes, Path(tmpdir) / "test.gp5")
            assert path.exists()
            assert path.suffix == ".gp5"

    def test_adds_suffix(self):
        """Should add .gp5 suffix if missing."""
        notes = [GuitarNote(time=0.0, duration=0.5, string=1, fret=0, pitch=64, velocity=80)]
        with tempfile.TemporaryDirectory() as tmpdir:
            path = generate(notes, Path(tmpdir) / "test")
            assert path.suffix == ".gp5"

    def test_readable_after_write(self):
        """Generated file should be readable by pyguitarpro."""
        notes = [
            GuitarNote(time=0.0, duration=0.5, string=6, fret=0, pitch=40, velocity=80),
            GuitarNote(time=0.5, duration=0.5, string=1, fret=0, pitch=64, velocity=80),
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            path = generate(notes, Path(tmpdir) / "test.gp5", title="Test Song")
            song = guitarpro.parse(str(path))
            assert song.title == "Test Song"
            assert len(song.tracks) >= 1

    def test_empty_notes(self):
        """Should create a valid file even with no notes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = generate([], Path(tmpdir) / "empty.gp5")
            assert path.exists()
            song = guitarpro.parse(str(path))
            assert song is not None

    def test_tuning_applied(self):
        """Should apply the specified tuning."""
        notes = [GuitarNote(time=0.0, duration=0.5, string=1, fret=0, pitch=64, velocity=80)]
        with tempfile.TemporaryDirectory() as tmpdir:
            path = generate(notes, Path(tmpdir) / "test.gp5", tuning="drop_d")
            song = guitarpro.parse(str(path))
            # 6th string in drop D should be 38
            strings = song.tracks[0].strings
            assert strings[-1].value == 38  # lowest string

    def test_dead_note_type(self):
        """Dead note effect should set NoteType.dead."""
        notes = [GuitarNote(time=0.0, duration=0.05, string=6, fret=0, pitch=0, velocity=80, effect="dead")]
        with tempfile.TemporaryDirectory() as tmpdir:
            path = generate(notes, Path(tmpdir) / "dead.gp5")
            song = guitarpro.parse(str(path))
            track = song.tracks[0]
            # Find the first non-rest beat
            for measure in track.measures:
                for beat in measure.voices[0].beats:
                    if beat.notes:
                        assert beat.notes[0].type == guitarpro.models.NoteType.dead
                        return
            assert False, "No notes found"

    def test_palm_mute_effect(self):
        """Palm mute effect should set palmMute on note effect."""
        notes = [GuitarNote(time=0.0, duration=0.05, string=4, fret=0, pitch=0, velocity=80, effect="palm_mute")]
        with tempfile.TemporaryDirectory() as tmpdir:
            path = generate(notes, Path(tmpdir) / "mute.gp5")
            song = guitarpro.parse(str(path))
            track = song.tracks[0]
            for measure in track.measures:
                for beat in measure.voices[0].beats:
                    if beat.notes:
                        assert beat.notes[0].effect.palmMute is True
                        return
            assert False, "No notes found"
