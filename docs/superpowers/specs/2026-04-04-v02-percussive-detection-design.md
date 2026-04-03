# v0.2 Percussive Detection + Auto BPM Design

## Context

v0.1은 basic-pitch로 피치 기반 노트만 추출한다. 핑거스타일 기타의 퍼커시브 요소(바디탭, 스트링 뮤트, 고음줄 탭)는 완전히 무시되며, BPM도 수동 지정이 필요하다.

v0.2는 librosa를 활용해 퍼커시브 이벤트 감지와 BPM 자동 감지를 추가한다.

## 접근법

librosa 단독 사용. HPSS(Harmonic-Percussive Source Separation)로 퍼커시브 신호를 분리하고, 온셋 감지 + 스펙트럼 분석으로 이벤트를 분류한다. BPM은 beat_track으로 감지한다.

대안으로 madmom(RNN 기반)이나 커스텀 CNN을 검토했으나, 의존성 복잡도와 스코프 대비 librosa 단독이 적합하다고 판단.

## 새 모듈

### `percussive.py` - 퍼커시브 이벤트 감지

```python
@dataclass
class PercussiveEvent:
    time: float           # 초
    category: str         # "body_tap" | "mute" | "string_tap"
    strength: float       # 0.0-1.0

def detect_percussive(wav_path: Path) -> list[PercussiveEvent]
```

처리 흐름:
1. `librosa.load()` → 오디오 로드
2. `librosa.effects.hpss()` → harmonic/percussive 분리
3. `librosa.onset.onset_detect(y=percussive)` → 타격 위치 추출
4. 각 온셋 주변 프레임의 mel-spectrogram에서 주파수 대역별 에너지 비율 계산
   - 저역(~300Hz) 우세 → `body_tap`
   - 중역(300-2kHz) 우세 → `mute`
   - 고역(2kHz~) 우세 → `string_tap`
5. 에너지 강도 → strength (정규화)

### `rhythm.py` - BPM 자동 감지

```python
def detect_bpm(wav_path: Path) -> float
```

- `librosa.beat.beat_track()` 사용
- 결과가 비정상적이면(40 미만, 240 초과) fallback 120.0

## 기존 모듈 수정

### `mapper.py`

`GuitarNote`에 `effect` 필드 추가:

```python
@dataclass
class GuitarNote:
    time: float
    duration: float
    string: int
    fret: int
    pitch: int
    velocity: int
    effect: str | None = None  # None, "dead", "palm_mute"
```

새 함수 `map_percussive()` 추가:

| PercussiveEvent.category | string | fret | effect |
|--------------------------|--------|------|--------|
| body_tap | 6 | 0 | dead |
| mute | 이전 포지션 근처 줄 | 0 | palm_mute |
| string_tap | 1 또는 2 | 0 | dead |

### `tab_ascii.py`

- `effect == "dead"` → `x` 렌더링
- `effect == "palm_mute"` → `(x)` 렌더링

### `tab_gp.py`

- `effect == "dead"` → `gp_note.effect.deadNote = True`
- `effect == "palm_mute"` → `gp_note.effect.palmMute = True`

### `pipeline.py`

```
wav → transcriber    → melodic notes     ─┐
    → percussive     → percussive events ─┤→ mapper (병합, 시간순 정렬) → 출력
    → rhythm         → detected BPM      ─┘
```

- `--bpm` CLI 옵션이 있으면 자동 감지를 오버라이드
- percussive 이벤트와 melodic 노트가 30ms 이내에 겹치면 melodic 우선

## 의존성

`pyproject.toml`에 `librosa>=0.10` 추가.

## 테스트

- `test_percussive.py`: HPSS mock으로 분류 로직 검증
- `test_rhythm.py`: beat_track mock으로 BPM 감지 검증
- `test_mapper.py`: 기존 테스트 + percussive 매핑 테스트 추가
- `test_tab_ascii.py`: dead note / palm mute 렌더링 검증
- `test_tab_gp.py`: GP effect 속성 검증
- 통합: v0.1과 동일한 wav로 전체 파이프라인 확인

## 검증 방법

1. `uv run pytest` 전체 통과
2. 퍼커시브 요소가 있는 핑거스타일 mp3로 CLI 실행
3. GP 파일에서 dead note / palm mute 기호 확인
4. BPM 자동 감지 값이 합리적인지 확인
