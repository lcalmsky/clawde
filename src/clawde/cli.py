"""CLI interface for Clawde."""

from __future__ import annotations

import click

from clawde.pipeline import convert


@click.group()
@click.version_option()
def main():
    """Clawde - Audio to fingerstyle guitar tablature converter."""


@main.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--tuning", "-t", default="standard",
              type=click.Choice(["standard", "drop_d", "open_g", "dadgad"]),
              help="Guitar tuning.")
@click.option("--format", "-f", "output_format", default="both",
              type=click.Choice(["ascii", "gp", "both"]),
              help="Output format.")
@click.option("--output", "-o", "output_dir", default=".",
              type=click.Path(), help="Output directory for GP files.")
@click.option("--bpm", type=float, default=None,
              help="Override BPM (default: auto-detect).")
@click.option("--no-separate", is_flag=True, default=False,
              help="Disable source separation (use v0.2 legacy mode).")
def convert_cmd(file_path, tuning, output_format, output_dir, bpm, no_separate):
    """Convert an audio file to guitar tablature."""
    mode = "legacy" if no_separate else "source separation"
    click.echo(f"Processing: {file_path}")
    bpm_info = f"BPM: {bpm}" if bpm else "BPM: auto-detect"
    click.echo(f"Tuning: {tuning} | Format: {output_format} | {bpm_info} | Mode: {mode}")
    click.echo()

    result = convert(
        file_path=file_path,
        tuning=tuning,
        output_format=output_format,
        output_dir=output_dir,
        bpm=bpm,
        separate_sources=not no_separate,
    )

    if result.ascii_tab:
        click.echo(result.ascii_tab)

    click.echo()
    click.echo(f"Detected BPM: {result.detected_bpm}")
    click.echo(f"Notes detected: {result.note_count}")
    click.echo(f"Duration: {result.duration_seconds:.1f}s")

    if result.gp_path:
        click.echo(f"GuitarPro file: {result.gp_path}")


if __name__ == "__main__":
    main()
