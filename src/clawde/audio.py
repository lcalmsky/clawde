"""Audio extraction and format handling."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


SUPPORTED_EXTENSIONS = {".mp3", ".mp4", ".m4a", ".wav", ".flac", ".ogg"}


def ensure_wav(file_path: str | Path) -> Path:
    """Ensure audio is in wav format. Extract from video if needed.

    Returns path to a wav file. If the input is already wav, returns it as-is.
    For other formats, converts to a temporary wav file.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported format: {suffix}. Supported: {SUPPORTED_EXTENSIONS}")

    if suffix == ".wav":
        return path

    # Convert to wav using ffmpeg
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    out_path = Path(tmp.name)

    cmd = [
        "ffmpeg", "-y",
        "-i", str(path),
        "-vn",              # no video
        "-acodec", "pcm_s16le",
        "-ar", "44100",     # 44.1kHz
        "-ac", "1",         # mono
        str(out_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        out_path.unlink(missing_ok=True)
        raise RuntimeError(f"ffmpeg failed: {result.stderr}")

    return out_path
