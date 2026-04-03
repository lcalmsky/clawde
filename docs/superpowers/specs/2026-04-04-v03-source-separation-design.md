# v0.3 Source Separation + Role-Based Arrangement Design

## Context

v0.2까지는 전체 오디오를 basic-pitch에 통째로 넘겨서 모든 악기가 섞인 노트를 추출했다. 보컬+드럼+베이스+신스가 전부 "기타 노트"로 변환되어 정확도가 낮았다.

핑거스타일은 한 기타로 멜로디(보컬) + 베이스 + 리듬(드럼) + 하모니를 모두 연주하는 장르다. 따라서 소스를 분리한 뒤 각 역할을 기타의 적절한 줄에 배치해야 한다.

## 접근법

demucs(htdemucs 모델)로 4-stem 분리 후 각 stem을 역할별로 트랜스크립션하고, 우선순위 기반으로 기타 한 악보에 병합한다.

## 새 모듈

### `separator.py` - 소스 분리

```python
@dataclass
class StemPaths:
    vocals: Path
    bass: Path
    drums: Path
    other: Path

def separate(wav_path: Path, output_dir: Path) -> StemPaths
```

- demucs htdemucs 모델 사용 (4-stem)
- lazy import (torch 무거움)
- 분리된 각 stem을 output_dir에 wav로 저장
- 캐싱: 같은 입력 파일이면 재분리하지 않음 (파일명+mtime 기반)

### `arranger.py` - 역할별 편곡

```python
@dataclass
class ArrangementConfig:
    melody_strings: tuple[int, ...] = (1, 2)
    bass_strings: tuple[int, ...] = (5, 6)
    harmony_strings: tuple[int, ...] = (3, 4)
    max_simultaneous: int = 6

def arrange(stems: StemPaths, tuning: str, bpm: float,
            config: ArrangementConfig | None = None) -> list[GuitarNote]
```

처리 흐름:
1. vocals stem → `transcribe()` → `map_notes_constrained(preferred_strings=(1,2))` → 멜로디
2. bass stem → `transcribe()` → `map_notes_constrained(preferred_strings=(5,6))` → 베이스
3. drums stem → `detect_percussive()` → `map_percussive()` → 퍼커시브
4. other stem → `transcribe()` → `map_notes_constrained(preferred_strings=(3,4))` → 하모니
5. 우선순위 병합 (아래 참조)

### 우선순위 병합 알고리즘

동시 발음 그룹(30ms 이내) 기준:
1. 멜로디 노트 배치 (최우선)
2. 베이스 노트 배치 (사용된 줄 제외)
3. 하모니 노트 배치 (사용된 줄 제외)
4. 퍼커시브 노트 배치 (사용된 줄 제외)
5. 총 노트 수 > 6이면 역순으로(퍼커시브→하모니→베이스) 제거

줄 충돌 해결: 같은 줄에 두 노트가 배치되면, 우선순위가 낮은 노트를 다른 빈 줄로 이동하거나 제거.

## 기존 모듈 수정

### `mapper.py`

새 함수 추가:

```python
def map_notes_constrained(
    notes: list[Note],
    tuning: str = "standard",
    preferred_strings: tuple[int, ...] = (),
) -> list[GuitarNote]
```

- `preferred_strings`에 지정된 줄에 우선 배치
- 불가능한 경우(프렛 범위 초과)에만 다른 줄 허용
- 기존 `map_notes()`는 그대로 유지 (하위 호환)

### `pipeline.py`

```python
def convert(
    file_path, tuning, output_format, output_dir,
    bpm=None,
    separate_sources=True,   # 새 옵션: demucs 분리 사용 여부
) -> TabResult
```

- `separate_sources=True` (기본): separator → arranger 경로
- `separate_sources=False`: 기존 v0.2 경로 (전체 오디오 → transcribe → map)

### `cli.py`

- `--no-separate` 플래그 추가 (demucs 없이 v0.2 방식 사용)

## 의존성

```toml
[project.optional-dependencies]
full = ["demucs>=4.0"]
```

기본 설치(`uv sync`)에는 demucs 미포함. `uv sync --extra full`로 설치.
demucs 미설치 상태에서 `--no-separate` 없이 실행하면 안내 메시지 출력 후 v0.2 fallback.

## 테스트

- `test_separator.py`: demucs mock, StemPaths 생성/캐싱 검증
- `test_arranger.py`:
  - 역할별 줄 배치 검증
  - 6줄 제한 검증 (우선순위 순 제거)
  - 줄 충돌 해결 검증
  - 빈 stem 처리 (예: 보컬 없는 곡)
- `test_mapper.py`: `map_notes_constrained` 줄 제약 + fallback 테스트
- 통합: 실제 mp3로 `--no-separate` vs 기본 비교

## 검증

1. `uv run pytest` 전체 통과
2. 핑거스타일 커버 mp3로 CLI 실행 (소스 분리 모드)
3. GP 파일에서 멜로디(고음줄) + 베이스(저음줄) 분리 확인
4. `--no-separate`로 v0.2 호환 동작 확인
5. demucs 미설치 시 graceful fallback 확인
