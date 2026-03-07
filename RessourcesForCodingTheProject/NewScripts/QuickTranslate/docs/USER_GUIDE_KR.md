# QuickTranslate 사용 가이드

**버전 5.0** | 2026년 3월

---

## QuickTranslate란?

Excel/XML의 번역 수정 사항을 `languagedata_*.xml` 파일에 기록하는 도구입니다. 두 개의 탭으로 구성:

| 탭 | 내용 |
|----|------|
| **Transfer** | 매치 타입, Source/Target 경로, TRANSFER 버튼, 사전 제출 검사, 설정 |
| **Other Tools** | Find Missing Translations, 제외 규칙 |

---

## 1. Excel 파일 준비

### 기본 구성

Row 1 = 헤더 (대소문자 무관, 순서 무관). 데이터는 Row 2부터.

**표준 수정 (가장 일반적):**

```
┌──────────────┬───────────────────────┬───────────────────────┐
│  StringID    │  StrOrigin            │  Correction           │
├──────────────┼───────────────────────┼───────────────────────┤
│  quest_001   │  퀘스트를 완료하세요   │  Complete the quest   │
│  quest_002   │  아이템을 획득하세요   │  Obtain the item      │
│  npc_greet   │  안녕하세요, 모험가!   │  Hello, adventurer!   │
└──────────────┴───────────────────────┴───────────────────────┘
```

**음성 더빙팀 (StringID 대신 EventName 사용):**

```
┌────────────────────────────┬──────────────┬───────────────────┐
│  EventName                 │  DialogVoice │  Correction       │
├────────────────────────────┼──────────────┼───────────────────┤
│  Play_AIDialog_npc01_      │  npc01       │  I have a task.   │
│   quest_greeting           │              │                   │
│  Play_QuestDialog_         │  player      │  What do you need?│
│   player_response_01       │              │                   │
└────────────────────────────┴──────────────┴───────────────────┘
```

EventName → StringID 변환은 자동 (3단계: DialogVoice 접두사 → 키워드 추출 → export 폴더 검색).

**음성 연출 설명이 포함된 표준 수정:**

```
┌──────────┬──────────────┬──────────────┬──────────────┬──────────┐
│ StringID │ StrOrigin    │ Correction   │ DescOrigin   │ Desc     │
├──────────┼──────────────┼──────────────┼──────────────┼──────────┤
│ npc_001  │ 안녕하세요   │ Hello there  │ 밝은 톤으로  │ Bright   │
│          │              │              │              │ tone     │
│ npc_002  │ 감사합니다   │ Thank you    │              │          │
└──────────┴──────────────┴──────────────┴──────────────┴──────────┘
```

DescOrigin/Desc는 선택 사항입니다. Desc가 없는 행은 정상 처리 — Correction만 전송됩니다.

### 허용 헤더명

헤더명은 **대소문자 무관**이며 다음 변형을 허용합니다:

| 열 | 허용 이름 |
|----|-----------|
| StringID | `StringID`, `string_id` |
| StrOrigin | `StrOrigin`, `str_origin` |
| Correction | `Correction`, `Corrected` |
| EventName | `EventName`, `event_name`, `SoundEventName` |
| DialogVoice | `DialogVoice`, `dialog_voice` |
| DescOrigin | `DescOrigin`, `desc_origin` |
| Desc | `Desc`, `DescText`, `desc_text`, `DescCorrection` |

### 열 참조

| 열 | 내용 | 필수 여부 |
|----|------|-----------|
| **StringID** | XML의 고유 ID | Strict / StringID-Only |
| **StrOrigin** | XML의 원본 한국어 (`<br/>` 포함 정확히 복사) | Strict / StrOrigin Only |
| **Correction** | 번역문 — XML에 기록되는 값 | 항상 필수 |
| **EventName** | 사운드 이벤트명 (StringID 대체) | 선택 |
| **DialogVoice** | 성우 접두사 (EventName 해석에 활용) | 선택 |
| **DescOrigin** | 원본 한국어 음성 연출 설명 | 선택 |
| **Desc** | 번역된 음성 연출 설명 — XML에 기록 | 선택 |

### 건너뛰는 경우

- **Correction 열 없음** → 파일 전체 건너뜀
- **Correction에 한국어** → 해당 행 자동 건너뜀 (미번역)
- **빈 Correction** → 해당 행 자동 건너뜀

### 언어별 정리

언어명 폴더에 파일을 배치하면 자동 감지됩니다.

```
MyCorrections/              ← Source로 설정
├── ENG/
│   └── corrections.xlsx
├── FRE/
│   └── corrections.xlsx
└── ZHO_CN/
    └── corrections.xlsx
```

언어 미감지 = 파일 건너뜀. `ENG/`, `FRE/` 등을 사용하거나 파일명에 접미사 추가: `corrections_eng.xlsx`.

---

## 2. 매치 타입

### Strict (기본값 — 가장 안전)

**StringID + StrOrigin + Correction** 필요. ID와 한국어 텍스트 모두 일치해야 함.

실패 선언 전 2단계 캐스케이드:
1. **정규화 매치** — 대소문자 무시 StringID, 정규화된 StrOrigin (HTML 언이스케이프, 공백 정리)
2. **공백 제거 폴백** — 양쪽에서 모든 공백 제거 후 비교

**Fuzzy 옵션:** 캐스케이드 실패 후 Model2Vec 시맨틱 유사도로 가장 가까운 매치 검색.

| 임계값 | 용도 |
|:------:|------|
| 0.95 | 경미한 맞춤법/공백 변경 |
| **0.85** | 기본값 — 범용 표현 변경 |
| 0.80 | 상당한 텍스트 변경 |
| 0.70 | 최대 커버리지 (오탐 위험) |

**적합 대상:** Non-SCRIPT 카테고리 (System/, World/, Platform/). 정밀도가 중요할 때.

### StringID-Only (SCRIPT 카테고리)

**StringID + Correction** 필요. StrOrigin 무시. Dialog/ 및 Sequencer/ 폴더만 처리.

Non-SCRIPT 문자열은 `SKIPPED_NON_SCRIPT`.

**적합 대상:** 음성 더빙 수정. StrOrigin이 길거나 추출 이후 변경된 경우.

### StrOrigin Only (Fan-Out)

**StrOrigin + Correction** 필요. 동일 한국어 텍스트를 공유하는 **모든** 항목에 적용.

```
StrOrigin="확인"인 Excel 1행 → XML 47개 항목 업데이트
```

안전을 위해 "미번역만"이 기본값. "전체 Transfer"는 경고 대화상자 표시.

**적합 대상:** 미번역 UI 라벨, 버튼, 상태 메시지 일괄 채움.

### 비교표

| | Strict | StringID-Only | StrOrigin Only |
|---|:-:|:-:|:-:|
| **정밀도** | 최고 | 중간 | 중간 |
| **Fan-out** | X | X | O |
| **Fuzzy** | O | X | O |
| **Desc Transfer** | O | O | X |
| **기본 범위** | 전체 Transfer | 전체 Transfer | 미번역만 |
| **위험도** | 최저 | 낮음 | 중간 |

---

## 3. TRANSFER 실행

1. **Source** → 수정 파일 폴더 설정
2. **Target** → `languagedata_*.xml`이 있는 LOC 폴더 설정
3. 매치 타입 선택
4. **TRANSFER** 클릭 → 계획 검토 → 확인

### 상태 코드

| 상태 | 의미 |
|------|------|
| `UPDATED` | 적용 완료 |
| `UNCHANGED` | 이미 동일 |
| `NOT_FOUND` | StringID 미존재 |
| `STRORIGIN_MISMATCH` | StringID 존재, 한국어 텍스트 불일치 |
| `SKIPPED_TRANSLATED` | 이미 번역됨 (미번역만 모드) |
| `SKIPPED_NON_SCRIPT` | Dialog/Sequencer에 없음 (StringID-Only) |
| `MISSING EVENTNAME` | EventName → StringID 변환 실패 |
| `RECOVERED_UPDATED` | 복구 패스가 실패 항목 해결 |

### 후처리 (자동)

모든 TRANSFER 후:
1. 모든 줄바꿈을 `<br/>`로 정규화
2. StrOrigin이 비면 Str도 비움 (Golden Rule)
3. "no translation"을 StrOrigin 값으로 교체

### Desc Transfer (음성 연출 설명)

일부 XML 항목에는 `DescOrigin` 속성이 있습니다 — 원본 한국어 음성 연출 설명입니다 (예: "밝은 톤으로", "슬픈 목소리"). 대사 번역 시 이 설명도 함께 번역하면 성우가 의도된 톤을 파악할 수 있습니다.

**Desc 열이 있는 Excel 만드는 방법:**

1. **DescOrigin 가져오기** — 문자열 추출 시 (ExtractAnything 또는 XML에서 복사) `<LocStr>` 요소의 `DescOrigin` 속성값을 가져옵니다. `DescOrigin`이라는 열에 넣으세요.
2. **번역 추가** — 옆에 `Desc` 열을 만들고 번역된 설명을 입력합니다 (예: "Bright tone", "Sad voice").
3. **필요 없으면 비워두기** — 모든 행에 Desc가 필요하지 않습니다. Desc가 없는 행은 정상 처리됩니다 (Correction → Str만 전송).

```
┌──────────┬──────────────┬──────────────┬──────────────┬──────────┐
│ StringID │ StrOrigin    │ Correction   │ DescOrigin   │ Desc     │
├──────────┼──────────────┼──────────────┼──────────────┼──────────┤
│ npc_001  │ 안녕하세요   │ Hello there  │ 밝은 톤으로  │ Bright   │
│          │              │              │              │ tone     │
│ npc_002  │ 감사합니다   │ Thank you    │              │          │
└──────────┴──────────────┴──────────────┴──────────────┴──────────┘
```

**단축:** Excel에 DescOrigin은 있지만 Desc 열이 아직 없으면, QuickTranslate가 Excel 병합 시 Desc 열을 자동 생성합니다 — 나중에 채울 수 있습니다.

**전송 규칙:**

- **Strict 및 StringID-Only만** — StrOrigin Only 모드는 Desc를 전송하지 않음
- **양쪽 조건 필요:** Excel 행에 비어있지 않은 Desc 값이 있고 대상 XML `<LocStr>`에 비어있지 않은 `DescOrigin`이 있어야 함
- **후처리:** Desc에도 동일한 정리 적용 (줄바꿈 정규화, 빈 DescOrigin 처리, "no translation" 교체)
- **유효성 검사 경고:** 소스 파일에 Desc/DescOrigin이 없으면 로그에 경고가 표시되고 Desc 전송이 건너뛰어짐

### 실패 보고서

`Failed Reports/YYMMDD/source_name/` — 재사용 가능한 XML + 3시트 Excel (Summary, Breakdown, Details).

---

## 4. 사전 제출 검사

`languagedata_*.xml` 읽기 전용 스캔. 파일 수정 없음.

### Check Korean

비KOR 파일에서 `Str`에 아직 한국어가 있는 항목. 모든 항목 예외 없이 스캔.

### Check Patterns (5가지 하위 검사)

| 검사 | 내용 |
|------|------|
| **패턴 코드** | Str의 `{code}` 플레이스홀더가 StrOrigin과 일치해야 함 |
| **줄바꿈** | `<br/>`만 허용 — `\n`, `&#10;`, `<BR/>` 등 플래그 |
| **괄호** | `()`, `[]`, `{}` 수가 StrOrigin과 Str 간 일치해야 함 |
| **깨진 XML** | 손상된 `<LocStr>` 요소 (분리된 속성, 깨진 태그) |
| **빈 Str** | Str 비어있지만 StrOrigin에 텍스트 있음 — 누락된 번역 |

### Check Quality (2파트)

- **잘못된 스크립트** — 프랑스어 파일에 키릴 문자, 영어 파일에 CJK 등
- **AI 할루시네이션** — AI 자기 참조 문구, 비정상 길이 비율, 불필요한 `/` 문자

### Check ALL

3가지 검사 순차 실행. **모든 Perforce 제출 전 실행하세요.**

---

## 5. Find Missing Translations (Other Tools 탭)

Source vs Target 비교로 미번역 문자열 탐지. Transfer 탭의 Source/Target 경로 사용.

4가지 매치 모드: StringID+KR Strict (최고속), StringID+KR Fuzzy, KR-only Strict, KR-only Fuzzy.

출력: Excel 보고서 + Close 폴더 (TRANSFER 소스로 재사용 가능).

**Exclude...** 버튼으로 제외할 폴더 설정 (`exclude_rules.json`에 저장).

---

## 6. 설치 & 설정

### 설치

- **Setup:** `QuickTranslate_vX.X.X_Setup.exe` — 실행하면 끝
- **Portable:** zip 압축 해제 후 `QuickTranslate.exe` 실행

### 최초 실행

Settings 섹션 또는 `settings.json` 편집:

```json
{
  "loc_folder": "F:\\perforce\\...\\stringtable\\loc",
  "export_folder": "F:\\perforce\\...\\stringtable\\export__"
}
```

### 생성되는 파일

| 파일 | 용도 |
|------|------|
| `settings.json` | LOC + EXPORT 경로 |
| `exclude_rules.json` | Find Missing 제외 규칙 |
| `presubmission_settings.json` | 검사 설정 |
| `Model2Vec/` | Model2Vec 모델 (fuzzy 매칭) |

---

## 7. 빠른 참조

### 버튼

**Transfer 탭:** TRANSFER, Check Korean, Check Patterns, Check Quality, Check ALL, Open Results, Save Settings, Clear Log, Clear All

**Other Tools 탭:** Find Missing Translations, Exclude...

### 출력 폴더

| 폴더 | 내용 |
|------|------|
| `Output/` | Missing Translation 보고서 |
| `Presubmission Checks/` | Korean, PatternErrors, BracketErrors, BrokenXML, EmptyStr, QualityReport |
| `Failed Reports/` | TRANSFER 실패 보고서 |

---

## 8. 문제 해결

| 문제 | 해결 |
|------|------|
| 매치 타입 비활성화 | 소스 파일에 필수 열 누락 |
| 0건 매치 | 매치 타입 오류, 경로 오류, P4 미동기화, Fuzzy 활성화 시도 |
| STRORIGIN_MISMATCH 전부 | 추출 이후 한국어 원문 변경 — P4 동기화, Fuzzy 시도 |
| 권한 거부 | 대상 XML에 P4 checkout 필요 |
| Excel 못 읽음 | Excel 먼저 닫기 (파일 잠금) |
| Fuzzy 비활성화 | `Model2Vec/` 폴더 없음 |

---

## 9. 용어 사전

| 용어 | 의미 |
|------|------|
| **StringID** | XML 텍스트 항목의 고유 식별자 |
| **StrOrigin** | XML의 원본 한국어 텍스트 |
| **Str** | XML의 번역 텍스트 속성 |
| **Correction** | Excel의 번역문 — Str에 기록 |
| **DescOrigin** | XML의 원본 한국어 음성 연출 설명 |
| **Desc** | 번역된 음성 연출 설명 — XML에 기록 |
| **LOC 폴더** | `languagedata_*.xml` 포함 (언어별 1개) |
| **EXPORT 폴더** | 카테고리별 `.loc.xml` (Dialog/, System/ 등) |
| **SCRIPT** | Dialog/ 및 Sequencer/ 카테고리 |
| **Fan-out** | 동일 StrOrigin 공유하는 모든 항목에 1건 수정 적용 |
| **`<br/>`** | XML의 유일한 올바른 줄바꿈 형식 |
| **Model2Vec** | Fuzzy 매칭용 정적 임베딩 모델 (256차원, torch 불필요) |

*최종 업데이트: 2026년 3월*
