# 페르소나 프로필 구조와 생성 규칙

이 문서는 가상 사용자 프로필의 형식·생성·확장 규칙을 관리한다.
행동 이벤트 계약은 [eventTracking.md](eventTracking.md), 실제 가입·행동 생성과
과거 기록 보존은 [playwrightGuide.md](playwrightGuide.md)를 따른다.
부하 조건과 실측 결과는 [계획](loadTestPlan.md)·[결과](loadTestResult.md)에 있다.

## 현재 데이터와 생성기

- `../syntheticData/personas.json`: 최초 100명을 보존해 총 300명으로 확장한 프로필.
- `../syntheticData/generatePersonas.py`: Python 표준 라이브러리로 프로필 생성·검증.
- 메타데이터: `schema_version=1.1`, `generator_version=1.2`, `seed=42`,
  `synthetic=true`, `count=300`, `expansion_version=append-v1`.
- 프로필 파일에 사람이 추가되는 것과 실제 서비스 회원가입은 별개다.
  생성기는 DB·API에 접근하거나 회원·예매·행동 로그를 생성하지 않는다.

## 프로필 구조

최상위 객체는 `metadata`와 `users` 배열로 구성된다.

| 사용자 필드 | 의미·규칙 |
| --- | --- |
| `id` | 재현 가능한 UUID. 실제 서비스 회원 ID와 같다고 가정하지 않음 |
| `name` | 성 40개·이름 96개의 조합에서 중복 없이 추출. 숫자 접미사 없음 |
| `email` | `persona0001@example.com` 형식의 합성 주소 |
| `mbti` | 16종 중 하나. 실제 성격·취향·구매율을 추정한 값이 아님 |
| `persona` | 아래 5종의 합성 취향 집단 |
| `category_weights` | 6개 카테고리의 양의 정수 점수. 사용자별 합계 100 |
| `preferred_categories` | 점수 상위 두 카테고리 |
| `viewing_style` | 동반 유형·관람 빈도·탐색 성향의 구조화 설정 |
| `bio` | 선호 카테고리와 관람 스타일을 설명하는 한 줄 소개 |

비밀번호·동의값·실제 회원 ID는 프로필에 포함하지 않는다.
가입 실행기가 별도 인증 정보와 프로필 ID ↔ 회원 ID 매핑을 관리한다.

## 취향 집단과 카테고리 점수

카테고리는 콘서트·뮤지컬·스포츠·전시·클래식·연극의 6종이다.
아래는 기본 가중치이며 개인별 점수는 생성기에서 변동·정규화한다.

| 페르소나 | 콘서트 | 뮤지컬 | 스포츠 | 전시 | 클래식 | 연극 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `live_fan` | 40 | 20 | 15 | 10 | 5 | 10 |
| `story_lover` | 10 | 35 | 5 | 10 | 10 | 30 |
| `sports_fan` | 15 | 5 | 55 | 10 | 5 | 10 |
| `art_explorer` | 10 | 10 | 5 | 45 | 20 | 10 |
| `classic_lover` | 10 | 10 | 5 | 20 | 45 | 10 |

MBTI와 페르소나는 독립적으로 균등 배정한다. 모든 MBTI×페르소나 조합의 출현까지
보장하지는 않는다. 점수는 실제 관측 비율이나 결제 확률이 아닌 테스트용 가정이다.

`viewing_style`의 값은 다음과 같다.

| 설정 | 허용 값 |
| --- | --- |
| `companion` | `solo`, `friends`, `partner`, `family` |
| `attendance_frequency` | `occasional`, `monthly`, `frequent` |
| `discovery_style` | `familiar`, `mixed`, `adventurous` |

36가지 조합을 페르소나별로 균등 배정하며 집단 인원이 36명을 넘으면 재사용한다.
관람 빈도와 사이트 방문 횟수는 같은 뜻이 아니다. 방문·구매 수량으로 변환하는 규칙은
실행 도구가 관리하며 `bio` 문장을 파싱해 동작을 결정하지 않는다.

## 생성·확장·재현성

저장소 루트에서 실행한다. CLI 기본값은 100명·시드 42이며 JSON을 표준 출력으로만
내보낸다. 기존 `personas.json`을 자동 갱신하지 않고 `--output` 옵션도 없다.

```powershell
python syntheticData/generatePersonas.py --count 100 --seed 42
python -m unittest discover -s syntheticData -p "test*.py"
```

동일한 Python·생성기 버전·인원·시드에서 같은 결과를 생성한다.
이름 조합에 따라 신규 생성 인원은 최대 3,840명이다.
서로 다른 실행 간 이메일·이름 중복은 보장하지 않으며, 인원을 바꿔 재생성한 결과가
기존 프로필을 그대로 포함한다고 가정하면 안 된다.

기존 프로필을 늘릴 때는 `expand_personas(data, target, seed=42)`와
`../syntheticData/playwright/loadPreparation.py`를 사용한다.
기존 배열·신원을 보존해 신규 프로필만 추가하고, 같은 목표 인원으로 반복해도 추가되지 않는다.
인원을 줄여 기존 사용자를 버리는 요청은 거절한다.
현재 300명 파일을 생성기 `--count 300` 출력으로 덮어쓰지 않는다.

`testGeneratePersonas.py`는 중복·재현성·스타일·소개 일치를,
`testExpandPersonas.py`는 기존 100명 보존·반복 확장·축소 거절을 검사한다.
실제 계정 매핑과 행동 기록 검증은 실행 안내의 별도 검사 대상이다.

## 분석할 때의 한계

프로필의 선호도를 행동 생성 규칙에 넣어 얻은 결과는 해당 규칙의 결과다.
분석 파이프라인 검증에는 사용할 수 있지만 실제 사용자 취향이나 추천 성능을 입증하지 않는다.
프로필 스키마 `1.1`과 행동 이벤트의 정수 `schema_version=1`도 별개다.
