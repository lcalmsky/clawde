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
