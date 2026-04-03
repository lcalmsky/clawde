"""Tests for Claude API refiner module."""

import json
from unittest.mock import patch, MagicMock

from clawde.mapper import GuitarNote
from clawde.refiner import _split_by_time, refine


def _note(time, string=1, fret=5, effect=None):
    return GuitarNote(time=time, duration=0.5, string=string, fret=fret,
                      pitch=60, velocity=80, effect=effect)


class TestSplitByTime:
    def test_single_chunk(self):
        notes = [_note(0.0), _note(1.0), _note(2.0)]
        chunks = _split_by_time(notes, 30.0)
        assert len(chunks) == 1
        assert len(chunks[0]) == 3

    def test_multiple_chunks(self):
        notes = [_note(0.0), _note(10.0), _note(35.0), _note(40.0)]
        chunks = _split_by_time(notes, 30.0)
        assert len(chunks) == 2

    def test_empty(self):
        assert _split_by_time([], 30.0) == []


class TestRefine:
    def test_no_api_key_returns_original(self):
        notes = [_note(0.0)]
        with patch.dict("os.environ", {}, clear=True):
            result = refine(notes)
        assert result == notes

    def test_empty_notes_returns_empty(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test"}):
            result = refine([])
        assert result == []

    def test_successful_refinement(self):
        mock_anthropic = MagicMock()
        notes = [_note(0.0, string=1, fret=5), _note(0.0, string=6, fret=0, effect="dead")]

        refined = [{"time": 0.0, "duration": 0.5, "string": 1, "fret": 5,
                     "pitch": 60, "velocity": 80, "effect": None}]
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(refined))]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.Anthropic.return_value = mock_client

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test"}), \
             patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            result = refine(notes)

        assert len(result) == 1
        assert result[0].effect is None

    def test_api_error_returns_original(self):
        mock_anthropic = MagicMock()
        notes = [_note(0.0)]
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("API error")
        mock_anthropic.Anthropic.return_value = mock_client

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test"}), \
             patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            result = refine(notes)

        assert result == notes
