"""Tests for percussive event detection module."""

import numpy as np

from clawde.percussive import _classify_onset, PercussiveEvent


class TestClassifyOnset:
    def _make_mel_freqs(self):
        return np.linspace(0, 11025, 128)

    def test_low_energy_dominant_is_body_tap(self):
        mel_freqs = self._make_mel_freqs()
        mel_spec = np.zeros((128, 10))
        # Put energy only in low band (<300Hz)
        low_mask = mel_freqs < 300
        mel_spec[low_mask, 5] = 10.0

        result = _classify_onset(mel_spec, 22050, 5, mel_freqs)
        assert result == "body_tap"

    def test_high_energy_dominant_is_string_tap(self):
        mel_freqs = self._make_mel_freqs()
        mel_spec = np.zeros((128, 10))
        # Put energy only in high band (>2kHz)
        high_mask = mel_freqs >= 2000
        mel_spec[high_mask, 5] = 10.0

        result = _classify_onset(mel_spec, 22050, 5, mel_freqs)
        assert result == "string_tap"

    def test_mid_energy_dominant_is_mute(self):
        mel_freqs = self._make_mel_freqs()
        mel_spec = np.zeros((128, 10))
        # Put energy in mid band (300-2000Hz)
        mid_mask = (mel_freqs >= 300) & (mel_freqs < 2000)
        mel_spec[mid_mask, 5] = 10.0

        result = _classify_onset(mel_spec, 22050, 5, mel_freqs)
        assert result == "mute"

    def test_empty_spectrum_is_mute(self):
        mel_freqs = self._make_mel_freqs()
        mel_spec = np.zeros((128, 10))

        result = _classify_onset(mel_spec, 22050, 5, mel_freqs)
        assert result == "mute"

    def test_out_of_bounds_frame_is_mute(self):
        mel_freqs = self._make_mel_freqs()
        mel_spec = np.zeros((128, 10))

        result = _classify_onset(mel_spec, 22050, 99, mel_freqs)
        assert result == "mute"


class TestPercussiveEvent:
    def test_dataclass_fields(self):
        event = PercussiveEvent(time=1.0, category="body_tap", strength=0.8)
        assert event.time == 1.0
        assert event.category == "body_tap"
        assert event.strength == 0.8
