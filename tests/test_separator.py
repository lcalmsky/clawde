"""Tests for audio source separation module."""

from pathlib import Path

from clawde.separator import StemPaths, _cache_key


class TestStemPaths:
    def test_dataclass_fields(self):
        stems = StemPaths(
            vocals=Path("/tmp/vocals.wav"),
            bass=Path("/tmp/bass.wav"),
            drums=Path("/tmp/drums.wav"),
            other=Path("/tmp/other.wav"),
        )
        assert stems.vocals == Path("/tmp/vocals.wav")
        assert stems.bass == Path("/tmp/bass.wav")
        assert stems.drums == Path("/tmp/drums.wav")
        assert stems.other == Path("/tmp/other.wav")


class TestCacheKey:
    def test_same_file_same_key(self, tmp_path):
        f = tmp_path / "test.wav"
        f.write_bytes(b"fake audio")
        key1 = _cache_key(f)
        key2 = _cache_key(f)
        assert key1 == key2

    def test_different_files_different_keys(self, tmp_path):
        f1 = tmp_path / "a.wav"
        f2 = tmp_path / "b.wav"
        f1.write_bytes(b"audio1")
        f2.write_bytes(b"audio2")
        assert _cache_key(f1) != _cache_key(f2)
