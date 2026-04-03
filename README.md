# Clawde 🎸

Audio to fingerstyle guitar tablature converter.
MCP server + CLI tool powered by Spotify's basic-pitch.

## Setup

```bash
cd ~/git-repo/clawde

# Install dependencies
uv sync

# System requirement: ffmpeg
brew install ffmpeg
```

## Usage

### CLI

```bash
# Basic conversion
uv run clawde convert song.mp3

# With options
uv run clawde convert song.mp4 --tuning drop_d --format both --output ./tabs/
```

### MCP Server (Claude Code)

Add to `~/.claude/.mcp.json`:

```json
{
  "clawde": {
    "command": "uv",
    "args": ["--directory", "~/git-repo/clawde", "run", "clawde-server"]
  }
}
```

Then in Claude Code:
> "song.mp3 파일로 타브악보 만들어줘"

### Options

| Option | Values | Default |
|--------|--------|---------|
| tuning | standard, drop_d, open_g, dadgad | standard |
| format | ascii, gp, both | both |
| bpm | any number | 120 (auto) |

## Output

- **ASCII tab**: terminal에 바로 출력
- **GuitarPro (.gp5)**: TuxGuitar/GuitarPro에서 열어서 편집/재생

## Tests

```bash
uv run pytest
```

## Limitations (v0.1)

- 화음 보이싱 정확도는 basic-pitch에 의존
- 퍼커시브 요소 미지원 (v0.2 예정)
- 슬라이드/해머온/풀오프 구분 불가
- "편곡 시작점"용, 완벽한 악보 X
