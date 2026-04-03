"""Tests for ASCII tab rendering."""

from clawde.mapper import GuitarNote
from clawde.tab_ascii import render


class TestRender:
    def test_empty_notes(self):
        """Empty notes should show 'no notes detected'."""
        result = render([])
        assert "no notes detected" in result

    def test_header_includes_info(self):
        """Header should include title, tuning, and BPM."""
        notes = [GuitarNote(time=0.0, duration=0.5, string=1, fret=0, pitch=64, velocity=80)]
        result = render(notes, bpm=120.0, title="test_song", tuning="standard")
        assert "Clawde" in result
        assert "test_song" in result
        assert "Standard" in result
        assert "120" in result

    def test_single_note_renders(self):
        """A single note should appear in the tab."""
        notes = [GuitarNote(time=0.0, duration=0.5, string=1, fret=5, pitch=69, velocity=80)]
        result = render(notes, bpm=120.0)
        assert "5" in result

    def test_open_string_note(self):
        """Open string note should show 0."""
        notes = [GuitarNote(time=0.0, duration=0.5, string=1, fret=0, pitch=64, velocity=80)]
        result = render(notes, bpm=120.0)
        assert "0" in result

    def test_six_strings_present(self):
        """All six string labels should appear."""
        notes = [GuitarNote(time=0.0, duration=0.5, string=1, fret=0, pitch=64, velocity=80)]
        result = render(notes, bpm=120.0)
        for label in ["e|", "B|", "G|", "D|", "A|", "E|"]:
            assert label in result

    def test_multiple_notes_timing(self):
        """Notes at different times should be at different positions."""
        notes = [
            GuitarNote(time=0.0, duration=0.25, string=1, fret=0, pitch=64, velocity=80),
            GuitarNote(time=0.5, duration=0.25, string=1, fret=3, pitch=67, velocity=80),
        ]
        result = render(notes, bpm=120.0)
        lines = result.split("\n")
        e_line = [l for l in lines if l.startswith("e|")]
        assert len(e_line) > 0
        # Both 0 and 3 should appear
        assert "0" in e_line[0]
        assert "3" in e_line[0]
