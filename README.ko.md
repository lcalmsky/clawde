# Clawde 🎸

오디오를 핑거스타일 기타 타브악보로 변환하는 도구.
Spotify basic-pitch 기반 MCP 서버 + CLI.

[English](README.md)

## 설치

```bash
# 의존성 설치 (Python 3.10-3.12 필요)
uv sync

# 시스템 요구사항: ffmpeg
brew install ffmpeg   # macOS
```

## 사용법

### CLI

```bash
# 기본 변환
uv run clawde convert song.mp3

# 옵션 지정
uv run clawde convert song.mp4 --tuning drop_d --format both --output ./tabs/ --bpm 116
```

### MCP 서버 (Claude Code)

`~/.claude/.mcp.json`에 추가:

```json
{
  "clawde": {
    "command": "uv",
    "args": ["--directory", "/path/to/clawde", "run", "clawde-server"]
  }
}
```

Claude Code에서:
> "song.mp3 파일로 타브악보 만들어줘"

### 옵션

| 옵션 | 값 | 기본값 |
|------|-----|--------|
| tuning | standard, drop_d, open_g, dadgad | standard |
| format | ascii, gp, both | both |
| bpm | 숫자 | 120 |

## 출력

- **ASCII tab** - 터미널에 바로 출력
- **GuitarPro (.gp5)** - TuxGuitar/GuitarPro에서 열어서 편집/재생

## 동작 원리

```
mp3/mp4/wav
    → [audio.py] wav 추출 (ffmpeg)
    → [transcriber.py] 오디오 → MIDI 노트 (basic-pitch ONNX)
    → [mapper.py] MIDI pitch → 기타 포지션 (줄, 프렛)
    → [tab_ascii.py] ASCII 탭 / [tab_gp.py] GuitarPro 파일
```

## 테스트

```bash
uv run pytest
```

## 한계 (v0.1)

- 화음 보이싱 정확도는 basic-pitch에 의존
- 퍼커시브 요소 미지원 (v0.2 예정)
- 슬라이드/해머온/풀오프 구분 불가
- "편곡 시작점"용, 완벽한 악보가 아님

## 로드맵

- **v0.2** - librosa 온셋 감지, 퍼커시브 분류
- **v0.3** - Claude 인터랙티브 편곡 (튜닝 변환, 난이도 조절)
