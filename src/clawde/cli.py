"""CLI interface for Clawde."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import click

from clawde.mapper import GuitarNote
from clawde.pipeline import convert
from clawde.tab_gp import generate as generate_gp
from clawde.tab_ascii import render as render_ascii


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
              help="Disable source separation (use legacy mode).")
@click.option("--no-refine", is_flag=True, default=False,
              help="Disable Claude API refinement.")
def convert_cmd(file_path, tuning, output_format, output_dir, bpm, no_separate, no_refine):
    """Convert an audio file to guitar tablature."""
    mode = "legacy" if no_separate else "source separation"
    refine_status = "off" if no_refine else "on"
    click.echo(f"Processing: {file_path}")
    bpm_info = f"BPM: {bpm}" if bpm else "BPM: auto-detect"
    click.echo(f"Tuning: {tuning} | Format: {output_format} | {bpm_info} | Mode: {mode} | Refine: {refine_status}")
    click.echo()

    result = convert(
        file_path=file_path,
        tuning=tuning,
        output_format=output_format,
        output_dir=output_dir,
        bpm=bpm,
        separate_sources=not no_separate,
        refine=not no_refine,
    )

    if result.ascii_tab:
        click.echo(result.ascii_tab)

    click.echo()
    click.echo(f"Detected BPM: {result.detected_bpm}")
    click.echo(f"Notes detected: {result.note_count}")
    click.echo(f"Duration: {result.duration_seconds:.1f}s")

    if result.gp_path:
        click.echo(f"GuitarPro file: {result.gp_path}")


@main.command("dump-notes")
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--output", "-o", "output_dir", default=".",
              type=click.Path(), help="Output directory.")
@click.option("--tuning", "-t", default="standard",
              type=click.Choice(["standard", "drop_d", "open_g", "dadgad"]))
@click.option("--bpm", type=float, default=None)
@click.option("--no-separate", is_flag=True, default=False)
def dump_notes_cmd(file_path, output_dir, tuning, bpm, no_separate):
    """Convert audio and dump raw notes as JSON (for manual refinement)."""
    result = convert(
        file_path=file_path,
        tuning=tuning,
        output_format="ascii",
        output_dir=output_dir,
        bpm=bpm,
        separate_sources=not no_separate,
        refine=False,
    )

    # Re-run pipeline internals to get raw notes
    from clawde.audio import ensure_wav
    from clawde.rhythm import detect_bpm
    from clawde.pipeline import _convert_separated, _convert_legacy

    wav_path = ensure_wav(Path(file_path))
    detected_bpm = detect_bpm(wav_path)
    effective_bpm = bpm or detected_bpm

    if not no_separate:
        notes = _convert_separated(wav_path, tuning, Path(output_dir))
    else:
        notes = _convert_legacy(wav_path, tuning)

    stem = Path(file_path).stem
    json_path = Path(output_dir) / f"{stem}_notes.json"
    notes_data = {
        "bpm": effective_bpm,
        "tuning": tuning,
        "notes": [asdict(n) for n in notes],
    }
    json_path.write_text(json.dumps(notes_data, indent=2, ensure_ascii=False))

    click.echo(f"BPM: {effective_bpm}")
    click.echo(f"Notes: {len(notes)}")
    click.echo(f"JSON dumped: {json_path}")


@main.command("load-notes")
@click.argument("json_path", type=click.Path(exists=True))
@click.option("--output", "-o", "output_dir", default=".",
              type=click.Path(), help="Output directory.")
@click.option("--format", "-f", "output_format", default="both",
              type=click.Choice(["ascii", "gp", "both"]))
def load_notes_cmd(json_path, output_dir, output_format):
    """Load refined notes JSON and generate tab output."""
    data = json.loads(Path(json_path).read_text())
    bpm = data["bpm"]
    tuning = data["tuning"]
    notes = [
        GuitarNote(
            time=n["time"], duration=n["duration"],
            string=n["string"], fret=n["fret"],
            pitch=n["pitch"], velocity=n["velocity"],
            effect=n.get("effect"),
        )
        for n in data["notes"]
    ]

    stem = Path(json_path).stem.replace("_notes", "")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if output_format in ("ascii", "both"):
        ascii_tab = render_ascii(notes, bpm=bpm, title=stem, tuning=tuning)
        click.echo(ascii_tab)

    if output_format in ("gp", "both"):
        gp_path = generate_gp(notes, output_dir / f"{stem}.gp5", bpm=bpm, title=stem, tuning=tuning)
        click.echo(f"\nGuitarPro file: {gp_path}")

    click.echo(f"\nNotes: {len(notes)}")


if __name__ == "__main__":
    main()
