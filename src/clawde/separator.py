"""Audio source separation using demucs."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


@dataclass
class StemPaths:
    """Paths to separated audio stems."""
    vocals: Path
    bass: Path
    drums: Path
    other: Path


def _cache_key(wav_path: Path) -> str:
    """Generate cache key from file path and modification time."""
    stat = wav_path.stat()
    raw = f"{wav_path.resolve()}:{stat.st_size}:{stat.st_mtime}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def separate(wav_path: str | Path, output_dir: str | Path) -> StemPaths:
    """Separate audio into 4 stems using demucs htdemucs model.

    Raises ImportError if demucs/torch is not installed.
    """
    import torch  # noqa: F401 - verify torch available
    from demucs.separate import load_track, get_model_from_args, apply_model, get_parser

    wav_path = Path(wav_path)
    output_dir = Path(output_dir)
    cache_dir = output_dir / f"stems_{_cache_key(wav_path)}"

    # Check cache
    expected = StemPaths(
        vocals=cache_dir / "vocals.wav",
        bass=cache_dir / "bass.wav",
        drums=cache_dir / "drums.wav",
        other=cache_dir / "other.wav",
    )
    if all(p.exists() for p in [expected.vocals, expected.bass, expected.drums, expected.other]):
        return expected

    cache_dir.mkdir(parents=True, exist_ok=True)

    # Load model
    parser = get_parser()
    args = parser.parse_args(["-n", "htdemucs", str(wav_path)])
    model = get_model_from_args(args)

    # Load and process audio
    wav = load_track(str(wav_path), model.audio_channels, model.samplerate)
    ref = wav.mean(0)
    wav = (wav - ref.mean()) / ref.std()

    # Apply model
    sources = apply_model(model, wav[None], device="cpu", shifts=1, split=True, overlap=0.25, progress=True)
    sources = sources * ref.std() + ref.mean()

    # Save stems using soundfile (avoids torchcodec dependency)
    import soundfile as sf
    import numpy as np

    source_names = model.sources  # ['drums', 'bass', 'other', 'vocals']
    for i, name in enumerate(source_names):
        stem_path = cache_dir / f"{name}.wav"
        audio_np = sources[0, i].cpu().numpy().T  # (channels, samples) → (samples, channels)
        sf.write(str(stem_path), audio_np, model.samplerate)

    return expected
