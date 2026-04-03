<p align="center">
  <img src="https://img.shields.io/badge/python-3.10--3.12-blue" alt="Python">
  <img src="https://img.shields.io/badge/version-0.4.0-green" alt="Version">
  <img src="https://img.shields.io/badge/license-MIT-yellow" alt="License">
  <img src="https://img.shields.io/badge/MCP-server-purple" alt="MCP">
  <img src="https://img.shields.io/badge/tests-66%20passed-brightgreen" alt="Tests">
</p>

# Clawde 🎸

**Audio to fingerstyle guitar tablature converter.**

Turn any song into a playable fingerstyle guitar tab. Powered by source separation (demucs), pitch detection (basic-pitch), and AI refinement (Claude API).

[한국어](README.ko.md)

## Example Output

```
Clawde - Audio to Fingerstyle Tab
=================================
File: demo | Tuning: Standard | BPM: ~116

e|---0---0---2---|---0-------2---|---0---0---2---|---------------|
B|-----3---0-----|-----2---0-----|-----3---0-----|-------3---0---|
G|---2-----------|---------------|---2-----------|---2-----------|
D|---------------|---0-----------|---------------|---------------|
A|-2---------0---|0---------2---|-2-------------|---0-----------|
E|---------------|-----------2---|---------------|-------------2-|
```

## How It Works

```
mp3/mp4/wav
    |
    v
[demucs]  -----> vocals / bass / drums / other   (source separation)
    |
    v
[basic-pitch] -> MIDI notes per stem              (pitch detection)
    |
    v
[arranger] ----> melody(1-2) + bass(5-6)          (role-based mapping)
                 + harmony(3-4) + percussion
    |
    v
[refiner] -----> Claude API musical refinement    (AI post-processing)
    |
    v
[output] ------> ASCII tab + GuitarPro (.gp5)
```

## Setup

```bash
git clone https://github.com/lcalmsky/clawde.git
cd clawde

# Basic install (no source separation)
uv sync

# Full install (with demucs source separation - recommended)
uv sync --extra full

# System requirement
brew install ffmpeg   # macOS
```

## Usage

### CLI

```bash
# Basic conversion (source separation + AI refinement)
uv run clawde convert song.mp3

# With options
uv run clawde convert song.mp4 --tuning drop_d --format both --output ./tabs/ --bpm 116

# Legacy mode (no source separation)
uv run clawde convert song.mp3 --no-separate

# Skip AI refinement
uv run clawde convert song.mp3 --no-refine
```

### MCP Server (Claude Code)

Add to `~/.claude/.mcp.json`:

```json
{
  "clawde": {
    "command": "uv",
    "args": ["--directory", "/path/to/clawde", "run", "clawde-server"]
  }
}
```

Then in Claude Code:
> "Convert song.mp3 to guitar tab"

### Options

| Option | Values | Default |
|--------|--------|---------|
| `--tuning` | standard, drop_d, open_g, dadgad | standard |
| `--format` | ascii, gp, both | both |
| `--bpm` | any number | auto-detect |
| `--no-separate` | flag | off |
| `--no-refine` | flag | off |

### Environment

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Claude API key for AI refinement (optional) |

## Output

- **ASCII tab** - printed to terminal
- **GuitarPro (.gp5)** - open in TuxGuitar/GuitarPro for editing and playback

## Architecture

| Module | Role |
|--------|------|
| `audio.py` | ffmpeg audio extraction (mp4 -> wav) |
| `separator.py` | demucs 4-stem source separation |
| `transcriber.py` | basic-pitch ONNX pitch detection |
| `percussive.py` | HPSS + onset detection for percussive events |
| `rhythm.py` | librosa BPM auto-detection |
| `mapper.py` | MIDI pitch -> guitar position (string, fret) |
| `arranger.py` | Role-based arrangement with priority merge |
| `refiner.py` | Claude API musical refinement |
| `tab_ascii.py` | ASCII tab renderer |
| `tab_gp.py` | GuitarPro file generator |
| `pipeline.py` | Pipeline orchestration |
| `cli.py` | Click CLI |
| `server.py` | FastMCP server |

## Tests

```bash
uv run pytest        # 66 tests
uv run pytest -v     # verbose
```

## Roadmap

- [x] **v0.1** - basic-pitch audio-to-tab pipeline
- [x] **v0.2** - librosa percussive detection + auto BPM
- [x] **v0.3** - demucs source separation + role-based arrangement
- [x] **v0.4** - Claude API post-processing refinement
- [ ] **v0.5** - MIDI output (bypass pyguitarpro limitations), interactive editing

## Limitations

- Chord voicing accuracy depends on basic-pitch
- Source separation quality depends on demucs
- 8th-note quantization in GuitarPro output (pyguitarpro limitation)
- AI refinement requires Anthropic API key
- Best results with acoustic/fingerstyle source material
