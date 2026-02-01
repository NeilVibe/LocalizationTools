# TMX Transfer 사용 가이드

**번역 전송을 위한 간단한 3단계 프로세스**

---

## 프로그램 소개

TMX Transfer는 Excel 파일의 번역을 XML 게임 파일로 전송하는 프로그램입니다:
1. 고유한 StringID 생성
2. Excel 데이터를 TMX 형식으로 변환
3. 번역 매칭 및 XML 파일로 전송

---

## 1단계: StringID 생성

**목적**: 각 번역 문자열에 대한 고유 식별자 생성

### 사용 방법:

1. **Excel 파일 준비** - 2개의 열 필요:
   - **1열**: DialogVoice (대화 식별자)
   - **2열**: EventName (이벤트 식별자)

   예시:
   ```
   DialogVoice         EventName
   aidialog_npc       aidialog_npc_greeting_01
   aidialog_quest     aidialog_quest_start_02
   ```

2. **프로그램 실행**
   - `tmxtransfer8.py` 실행
   - **"Generate StringID"** 버튼 클릭

3. **Excel 파일 선택**
   - 프로그램이 EventName에서 고유한 부분을 추출합니다
   - 결과: StringID가 포함된 새 Excel 파일 (`*_stridgenerated.xlsx`)

   결과:
   ```
   greeting_01
   start_02
   ```

---

## 2단계: TMX 변환을 위한 Excel 준비

**목적**: TMX로 변환 가능한 올바른 형식의 Excel 파일 생성

### 필수 Excel 형식:

Excel 파일은 반드시 **정확한 순서로 5개의 열**이 있어야 합니다:

| 열 | 이름 | 설명 | 예시 |
|----|------|------|------|
| **1열** | StrOrigin | 원본 한국어 텍스트 | 안녕하세요 |
| **2열** | Str | 영어 번역 | Hello |
| **3열** | StringID | 고유 식별자 | greeting_01 |
| **4열** | DescOrigin | 원본 한국어 설명 (선택사항) | 인사말입니다 |
| **5열** | Desc | 영어 설명 (선택사항) | This is a greeting |

### 중요 사항:

✅ **1-3열은 필수** (기본 번역용)
✅ **4-5열은 선택사항** (하지만 설명이 있으면 추가 권장)
✅ **StringID**는 XML 파일의 ID와 일치해야 합니다
✅ **Str** (2열)는 반드시 영어여야 합니다 (한글 불가)
✅ **Desc** (5열)는 반드시 영어여야 합니다 (한글 불가)

### Excel 예시:

```
StrOrigin        Str              StringID        DescOrigin           Desc
안녕하세요       Hello            greeting_01     인사말입니다         This is a greeting
시작하기         Start            start_02        퀘스트 시작          Quest start
종료             End              end_03          퀘스트 종료          Quest end
```

---

## 3단계: Excel을 TMX로 변환

**목적**: Excel 데이터를 번역 전송을 위한 TMX 형식으로 변환

### 사용 방법:

1. **프로그램 실행**
   - `tmxtransfer8.py` 실행

2. **변환 유형 선택**:

   **옵션 A: Excel → TMX** (표준 형식)
   - **"Excel → TMX"** 버튼 클릭
   - 대부분의 경우 이것을 사용

   **옵션 B: Excel → MemoQ-TMX** (MemoQ 소프트웨어용)
   - **"Excel → MemoQ-TMX"** 버튼 클릭
   - MemoQ 번역 소프트웨어를 사용하는 경우

3. **모드 선택**:
   - **File 모드**: 단일 Excel 파일 변환
   - **Folder 모드**: 폴더 내 모든 Excel 파일 변환

4. **Excel 파일 선택** (2단계에서 준비한 파일)

5. **결과**:
   - 모든 번역이 포함된 TMX 파일 생성
   - `.tmx` 확장자로 저장
   - 일반 문자열과 설명이 모두 포함됨

---

## 4단계: Simple Translate (번역 전송)

**목적**: TMX의 번역을 XML 파일과 자동으로 매칭하여 업데이트

### 사용 방법:

1. **파일 준비**:
   - ✅ TMX 파일 (3단계에서 생성)
   - ✅ 업데이트할 XML 파일

2. **프로그램 실행**
   - `tmxtransfer8.py` 실행

3. **모드 선택**:
   - **File 모드**: 단일 XML 파일 업데이트
   - **Folder 모드**: 폴더 내 모든 XML 파일 업데이트

4. **XML 업로드**:
   - **"Upload XML Folder/File"** 클릭
   - XML 파일 또는 폴더 선택
   - 준비되면 버튼이 **초록색**으로 변경됨

5. **TMX 업로드**:
   - **"Upload TMX File"** 클릭
   - TMX 파일 선택 (3단계에서 생성한 파일)
   - 준비되면 버튼이 **초록색**으로 변경됨

6. **Simple Translate 실행**:
   - **"KR+ID SIMPLE TRANSLATE"** 버튼 클릭
   - 프로그램이 자동으로 다음을 수행합니다:
     - StringID + 한국어 텍스트(StrOrigin)로 매칭
     - StringID + 한국어 설명(DescOrigin)으로 설명 매칭
     - XML 파일에서 일치하는 항목 업데이트

7. **결과 확인**:
   - 팝업 창에 업데이트된 번역 수가 표시됩니다
   - 예시: "Updated Str: 150, Updated Desc: 45"
   - XML 파일이 업데이트되었습니다!

---

## 매칭 로직

**Simple Translate**는 다음을 사용하여 번역을 매칭합니다:

1. **StringID** + **StrOrigin** (한국어 텍스트)
   - 둘 다 정확히 일치해야 함
   - XML의 `Str` 속성 업데이트

2. **StringID** + **DescOrigin** (한국어 설명)
   - 둘 다 정확히 일치해야 함
   - XML의 `Desc` 속성 업데이트

**왜 둘 다 필요한가?**
- StringID만으로는 충분히 고유하지 않음
- 한국어 텍스트로 올바른 문자열인지 확인
- 잘못된 번역이 적용되는 것을 방지

---

## 고급: 2-Step Translate

**대체 매칭 방법 (폴백 포함)**

더 많은 매칭을 원하면 **"2-STEP MATCH KR+ID → KR"** 사용:

1. **첫 번째 시도**: StringID + 한국어 텍스트로 매칭 (Simple Translate와 동일)
2. **두 번째 시도**: 매칭 실패 시, 한국어 텍스트만으로 시도 (StringID 무시)

**사용 시기**:
- StringID가 변경되었을 가능성이 있을 때
- 최대한 많은 번역을 적용하고 싶을 때
- 한국어 원본 텍스트가 고유하다고 확신할 때

**주의**: 매칭 수가 많을수록 = 잘못된 매칭의 위험도 증가

---

## 빠른 참조

### 전체 워크플로우 요약:

```
1. StringID 생성
   ↓
2. Excel 준비 (5개 열: StrOrigin, Str, StringID, DescOrigin, Desc)
   ↓
3. Excel → TMX (Excel을 TMX 형식으로 변환)
   ↓
4. Simple Translate (XML + TMX 업로드, 번역 클릭)
   ↓
5. 완료! (XML 파일이 번역으로 업데이트됨)
```

### 파일 요구사항:

| 단계 | 입력 | 출력 |
|------|------|------|
| StringID 생성 | Excel (2열: DialogVoice, EventName) | StringID가 포함된 Excel |
| Excel → TMX | Excel (5열: StrOrigin, Str, StringID, DescOrigin, Desc) | TMX 파일 |
| Simple Translate | XML 파일 + TMX 파일 | 업데이트된 XML 파일 |

---

## 성공을 위한 팁

✅ **항상 StringID를 먼저 생성** - 이 단계를 건너뛰지 마세요
✅ **열 순서 확인** - Excel 열은 정확한 순서여야 합니다
✅ **Str/Desc에 한글 금지** - 영어 번역만 가능
✅ **XML StringID와 일치** - StringID는 XML에 존재해야 합니다
✅ **먼저 파일 하나로 테스트** - 전체 폴더 처리 전에
✅ **백업 유지** - 원본 XML 파일은 덮어쓰여집니다

---

## 문제 해결

### 문제: "매칭을 찾을 수 없음"
- ✓ Excel과 XML 간 StringID 일치 확인
- ✓ 한국어 텍스트(StrOrigin) 정확히 일치 확인
- ✓ 추가 공백이나 숨겨진 문자 확인

### 문제: "버튼이 회색으로 유지됨"
- ✓ XML과 TMX 파일 모두 업로드
- ✓ 번역 전 두 버튼 모두 초록색이어야 함

### 문제: "업데이트가 적음"
- ✓ StringID 형식이 XML과 일치하는지 확인
- ✓ 더 많은 매칭을 위해 2-Step Translate 시도
- ✓ 한국어 텍스트가 정확히 일치하는지 확인

---

**마지막 업데이트**: 2025-11-21
**프로그램 버전**: tmxtransfer8.py
**대상**: 로컬라이제이션 팀

---

*문제가 생기면 StringID와 열 순서를 먼저 확인해보세요!*
