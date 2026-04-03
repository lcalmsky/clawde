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
) -> str:
    """Convert an audio file to fingerstyle guitar tablature.

    Analyzes mp3/mp4/wav files and generates guitar tab notation.
    Outputs ASCII tab for quick viewing and/or GuitarPro (.gp5) files for editing.

    Args:
        file_path: Path to the audio file (mp3, mp4, wav, flac, ogg).
        tuning: Guitar tuning - "standard", "drop_d", "open_g", or "dadgad".
        output_format: Output format - "ascii" (text only), "gp" (GuitarPro only), or "both".
        output_dir: Directory to save GuitarPro files.
        bpm: Override tempo detection. Leave empty for default (~120 BPM).
    """
    result = convert(
        file_path=file_path,
        tuning=tuning,
        output_format=output_format,
        output_dir=output_dir,
        bpm=bpm,
    )

    parts = []

    if result.ascii_tab:
        parts.append(result.ascii_tab)

    parts.append(f"\nNotes detected: {result.note_count}")
    parts.append(f"Duration: {result.duration_seconds:.1f}s")

    if result.gp_path:
        parts.append(f"GuitarPro file saved: {result.gp_path}")

    return "\n".join(parts)


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
