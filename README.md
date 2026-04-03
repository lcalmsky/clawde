# Clawde 🎸

Audio to fingerstyle guitar tablature converter.
MCP server + CLI tool powered by Spotify's basic-pitch.

[한국어](README.ko.md)

## Setup

```bash
# Install dependencies (requires Python 3.10-3.12)
uv sync

# System requirement: ffmpeg
brew install ffmpeg   # macOS
```

## Usage

### CLI

```bash
# Basic conversion
uv run clawde convert song.mp3

# With options
uv run clawde convert song.mp4 --tuning drop_d --format both --output ./tabs/ --bpm 116
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
| tuning | standard, drop_d, open_g, dadgad | standard |
| format | ascii, gp, both | both |
| bpm | any number | 120 |

## Output

- **ASCII tab** - printed to terminal
- **GuitarPro (.gp5)** - open in TuxGuitar/GuitarPro for editing and playback

## How It Works

```
mp3/mp4/wav
    → [audio.py] extract wav (ffmpeg)
    → [transcriber.py] audio to MIDI notes (basic-pitch ONNX)
    → [mapper.py] MIDI pitch to guitar position (string, fret)
    → [tab_ascii.py] ASCII tab / [tab_gp.py] GuitarPro file
```

## Tests

```bash
uv run pytest
```

## Limitations (v0.1)

- Chord voicing accuracy depends on basic-pitch
- No percussive elements (planned for v0.2)
- No slide/hammer-on/pull-off detection
- Designed as an "arrangement starting point", not a perfect score

## Roadmap

- **v0.2** - librosa onset detection, percussive classification
- **v0.3** - Claude interactive arrangement (tuning conversion, difficulty adjustment)
