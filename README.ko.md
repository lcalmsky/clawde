<p align="center">
  <img src="https://img.shields.io/badge/python-3.10--3.12-blue" alt="Python">
  <img src="https://img.shields.io/badge/version-0.4.0-green" alt="Version">
  <img src="https://img.shields.io/badge/license-MIT-yellow" alt="License">
  <img src="https://img.shields.io/badge/MCP-server-purple" alt="MCP">
  <img src="https://img.shields.io/badge/tests-66%20passed-brightgreen" alt="Tests">
</p>

# Clawde 🎸

**오디오를 핑거스타일 기타 타브악보로 변환**

아무 노래나 넣으면 연주 가능한 핑거스타일 기타 탭으로 변환. 소스 분리(demucs), 피치 감지(basic-pitch), AI 교정(Claude API) 기반.

[English](README.md)

## 출력 예시

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

## 동작 원리

```
mp3/mp4/wav
    |
    v
[demucs]  -----> 보컬 / 베이스 / 드럼 / 기타     (소스 분리)
    |
    v
[basic-pitch] -> 각 stem별 MIDI 노트               (피치 감지)
    |
    v
[arranger] ----> 멜로디(1-2번줄) + 베이스(5-6번줄)  (역할별 배치)
                 + 하모니(3-4번줄) + 퍼커시브
    |
    v
[refiner] -----> Claude API 음악적 교정             (AI 후처리)
    |
    v
[output] ------> ASCII 탭 + GuitarPro (.gp5)
```

## 설치

```bash
git clone https://github.com/lcalmsky/clawde.git
cd clawde

# 기본 설치 (소스 분리 없음)
uv sync

# 전체 설치 (demucs 소스 분리 포함 - 권장)
uv sync --extra full

# 시스템 요구사항
brew install ffmpeg   # macOS
```

## 사용법

### CLI

```bash
# 기본 변환 (소스 분리 + AI 교정)
uv run clawde convert song.mp3

# 옵션 지정
uv run clawde convert song.mp4 --tuning drop_d --format both --output ./tabs/ --bpm 116

# 레거시 모드 (소스 분리 없이)
uv run clawde convert song.mp3 --no-separate

# AI 교정 건너뛰기
uv run clawde convert song.mp3 --no-refine
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
| `--tuning` | standard, drop_d, open_g, dadgad | standard |
| `--format` | ascii, gp, both | both |
| `--bpm` | 숫자 | 자동 감지 |
| `--no-separate` | 플래그 | off |
| `--no-refine` | 플래그 | off |

### 환경변수

| 변수 | 설명 |
|------|------|
| `ANTHROPIC_API_KEY` | AI 교정용 Claude API 키 (선택) |

## 출력

- **ASCII tab** - 터미널에 바로 출력
- **GuitarPro (.gp5)** - TuxGuitar/GuitarPro에서 열어서 편집/재생

## 테스트

```bash
uv run pytest        # 66개 테스트
uv run pytest -v     # 상세 출력
```

## 로드맵

- [x] **v0.1** - basic-pitch 오디오→탭 파이프라인
- [x] **v0.2** - librosa 퍼커시브 감지 + BPM 자동 감지
- [x] **v0.3** - demucs 소스 분리 + 역할별 편곡
- [x] **v0.4** - Claude API 후처리 교정
- [ ] **v0.5** - MIDI 출력 (pyguitarpro 제한 우회), 인터랙티브 편집

## 한계

- 화음 보이싱 정확도는 basic-pitch에 의존
- 소스 분리 품질은 demucs에 의존
- GuitarPro 출력은 8분음표 양자화 (pyguitarpro 제한)
- AI 교정은 Anthropic API 키 필요
- 어쿠스틱/핑거스타일 소스에서 최적 결과
