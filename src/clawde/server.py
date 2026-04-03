"""MCP server for Clawde - audio to guitar tab conversion."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from clawde.pipeline import convert

mcp = FastMCP("clawde")


@mcp.tool()
def audio_to_tab(
    file_path: str,
    tuning: str = "standard",
    output_format: str = "both",
    output_dir: str = ".",
    bpm: float | None = None,
    separate_sources: bool = True,
) -> str:
    """Convert an audio file to fingerstyle guitar tablature.

    Uses source separation (demucs) to split vocals/bass/drums/other,
    then arranges each part onto appropriate guitar strings for fingerstyle.

    Args:
        file_path: Path to the audio file (mp3, mp4, wav, flac, ogg).
        tuning: Guitar tuning - "standard", "drop_d", "open_g", or "dadgad".
        output_format: Output format - "ascii" (text only), "gp" (GuitarPro only), or "both".
        output_dir: Directory to save GuitarPro files.
        bpm: Override tempo detection. Leave empty for auto-detect.
        separate_sources: Use demucs source separation. Set false for legacy mode.
    """
    result = convert(
        file_path=file_path,
        tuning=tuning,
        output_format=output_format,
        output_dir=output_dir,
        bpm=bpm,
        separate_sources=separate_sources,
    )

    parts = []

    if result.ascii_tab:
        parts.append(result.ascii_tab)

    parts.append(f"\nDetected BPM: {result.detected_bpm}")
    parts.append(f"Notes detected: {result.note_count}")
    parts.append(f"Duration: {result.duration_seconds:.1f}s")

    if result.gp_path:
        parts.append(f"GuitarPro file saved: {result.gp_path}")

    return "\n".join(parts)


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
