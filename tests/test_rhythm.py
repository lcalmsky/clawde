"""Tests for rhythm (BPM detection) module."""

from unittest.mock import patch, MagicMock
import numpy as np

from clawde.rhythm import detect_bpm, FALLBACK_BPM


class TestDetectBpm:
    @patch.dict("sys.modules", {"librosa": MagicMock()})
    def test_normal_bpm(self):
        import sys
        mock_librosa = sys.modules["librosa"]
        mock_librosa.load.return_value = (np.zeros(22050), 22050)
        mock_librosa.beat.beat_track.return_value = (np.array([116.0]), np.array([0]))

        result = detect_bpm("test.wav")
        assert result == 116.0

    @patch.dict("sys.modules", {"librosa": MagicMock()})
    def test_scalar_tempo(self):
        import sys
        mock_librosa = sys.modules["librosa"]
        mock_librosa.load.return_value = (np.zeros(22050), 22050)
        mock_librosa.beat.beat_track.return_value = (130.0, np.array([0]))

        result = detect_bpm("test.wav")
        assert result == 130.0

    @patch.dict("sys.modules", {"librosa": MagicMock()})
    def test_too_low_bpm_returns_fallback(self):
        import sys
        mock_librosa = sys.modules["librosa"]
        mock_librosa.load.return_value = (np.zeros(22050), 22050)
        mock_librosa.beat.beat_track.return_value = (np.array([10.0]), np.array([0]))

        result = detect_bpm("test.wav")
        assert result == FALLBACK_BPM

    @patch.dict("sys.modules", {"librosa": MagicMock()})
    def test_too_high_bpm_returns_fallback(self):
        import sys
        mock_librosa = sys.modules["librosa"]
        mock_librosa.load.return_value = (np.zeros(22050), 22050)
        mock_librosa.beat.beat_track.return_value = (np.array([300.0]), np.array([0]))

        result = detect_bpm("test.wav")
        assert result == FALLBACK_BPM
