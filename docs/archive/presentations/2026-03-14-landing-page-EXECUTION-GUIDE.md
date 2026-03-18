# Landing Page Execution Guide — FULL CONTEXT

> This file contains EVERYTHING needed to build the LocaNext landing page from scratch, even if context is lost.

## What We're Building

A **cinematic scroll landing page** for LocaNext — single self-contained HTML file.
- **Korean language** throughout
- **Dark theme**, cinematic epic + bold provocative tone
- **4 Acts, 12 sections** — problem → solution → future → proof
- **Target:** Internal stakeholders + "look how powerful AI is" showcase
- **Location:** `landing-page/index.html`

## Design Spec

Full spec at: `docs/superpowers/specs/2026-03-14-locanext-landing-page-design.md`

## How To Build — Skills to Invoke

### Phase 1: Plan
```
/superpowers:writing-plans
```
Create implementation plan from the spec. The plan should break into:
- Section 1-3 (Hero + Act 1 Problem)
- Section 4-6 (Act 2 Solution + Architecture)
- Section 7-9 (Act 3 Multimodal + AI Pipeline)
- Section 10-12 (Act 4 Arsenal + Closing)

### Phase 2: Execute with Parallel Agents
```
/superpowers:subagent-driven-development
```
Or use `/superpowers:dispatching-parallel-agents` for independent sections.

### Skills to FUSE During Implementation

| Skill | Invoke When | Purpose |
|-------|-------------|---------|
| `ui-ux-pro-max` | Before writing any CSS/layout | Color palette, typography, spacing system |
| `threejs-animation` | Hero section, particle systems | 3D scene setup, particle physics, mouse interaction |
| `award-winning-website` | Overall structure | GSAP scroll patterns, section transitions |
| `animated-component-libraries` | Every section | Magic UI components, motion patterns |
| `frontend-design` | Component-level code | Production-grade HTML/CSS/JS |
| `theme-factory` | Color system setup | Dark theme implementation |
| `canvas-design` | Background effects | Procedural/generative backgrounds |
| `algorithmic-art` | Particle systems | Procedural visual generation |

### Phase 3: Review
```
/superpowers:requesting-code-review
```
Then verify with Playwright MCP screenshots.

### Phase 4: Verify
```
/superpowers:verification-before-completion
```
Open in browser, take screenshots, verify all animations.

## Tech Stack (CDN URLs)

```html
<!-- Three.js (UMD global build — use THREE.Scene() etc directly) -->
<script src="https://unpkg.com/three@0.160.0/build/three.min.js"></script>

<!-- GSAP + ScrollTrigger -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/ScrollTrigger.min.js"></script>

<!-- Fonts (Pretendard for titles + Noto Sans KR for body + JetBrains Mono for stats) -->
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&family=JetBrains+Mono:wght@700&display=swap" rel="stylesheet">
```

### Required JS Boilerplate
```js
// Register GSAP plugin (MUST do this)
gsap.registerPlugin(ScrollTrigger);

// Skip Three.js on mobile to save ~600KB
const isMobile = window.innerWidth < 768;
if (!isMobile) { /* initialize Three.js scene */ }
```

### HTML Root
```html
<html lang="ko">
```

## Color Palette

```css
:root {
  --bg: #0a0a0f;
  --bg-alt: #12121a;
  --primary: #6366f1;
  --primary-light: #8b5cf6;
  --accent: #06b6d4;
  --danger: #ef4444;
  --success: #10b981;
  --text: #f1f5f9;
  --text-dim: #94a3b8;
  --glass: rgba(255,255,255,0.05);
  --glass-border: rgba(255,255,255,0.1);
}
```

## The 4 Acts — Korean Copy

### ACT 1: 문제 인식
- Hero: "로컬라이제이션의 미래가 시작됩니다"
- Sub: "하나의 플랫폼. 하나의 비전. AI와 함께."
- Problem: "지금, 당신의 워크플로우를 솔직하게 돌아봅시다"
- Pain: 6개 분리된 스크립트, 커맨드라인, 협업 불가, 오프라인 불가, 느린 검색, 엑셀 지옥

### ACT 2: 솔루션
- Reveal: "이제, 제대로 된 걸 보여드리겠습니다"
- Tagline: "빠르고. 완벽하고. 적응하는."
- Performance: 50만 행 3초, TM 70만 즉시, 시맨틱 10ms, 임베딩 79배, 160MB
- Architecture: 온라인/오프라인/제로 지연 동기화

### ACT 3: 미래
- Multimodal: "번역 그 이상. 멀티모달 컨텍스트."
- AI Pipeline: "컨텍스트가 AI를 바꿉니다"
- Dev Platform: "개발자도 직접 씁니다. VSCODE는 이제 그만."

### ACT 4: 증명
- Arsenal: "하나가 아닙니다. 전체 생태계입니다."
- Builder: "이 모든 것을 한 사람이 만들었습니다. AI와 함께."
- Stats: 912+ tests, 161+ bugs, 60+ builds, 9 tools, 55+ APIs, 13 languages, 500K+ rows
- Closing: "이것이 로컬라이제이션의 미래입니다. 그리고 이 웹페이지도 AI가 만들었습니다."

## Key Stats for Counters

| Stat | Value | Korean |
|------|-------|--------|
| Tests passing | 912+ | 테스트 통과 |
| Bugs fixed | 161+ | 버그 수정 |
| Open bugs | 0 | 미해결 버그 |
| Build releases | 60+ | 빌드 릴리스 |
| Tools | 9 | 도구 |
| API endpoints | 55+ | API 엔드포인트 |
| Languages | 13 | 언어 지원 |
| Rows handled | 500K+ | 행 처리 |
| TM entries | 700K+ | TM 엔트리 |
| Concurrent users | 50+ | 동시 사용자 |
| Semantic search | 10ms | 시맨틱 검색 |
| Embedding speed | 79x | 임베딩 속도 |
| App size | 160MB | 앱 크기 |

## 9 Tools for Arsenal Section

1. **LocaNext** — 메인 플랫폼 (게임 로컬라이제이션)
2. **QuickTranslate** — Excel↔XML 전송
3. **QACompiler** — 데이터시트 생성 (16개 제너레이터)
4. **LanguageDataExporter** — XML→Excel 카테고리 분류
5. **MapDataGenerator** — 데이터 시각화 (MAP, CHARACTER, ITEM, AUDIO)
6. **ExtractAnything** — 추출 도구 (8개 탭)
7. **QuickSearch** — 용어집 QA 검색
8. **KR Similar** — 유사 한국어 문자열 매칭
9. **XLS Transfer** — 일괄 데이터 전송

## Architecture for Diagram Section

```
LocaNext.exe (User PC)          Central PostgreSQL
├─ Embedded Python Backend  ──→  ├─ ALL text data
├─ FAISS indexes (local)         ├─ Users, sessions
├─ Model2Vec (local, 128MB)      └─ TM entries, logs
└─ File parsing (local)

ONLINE:  PostgreSQL + WebSocket (multi-user, real-time sync)
OFFLINE: SQLite (single-user, auto-fallback, zero data loss)
```

## Multimodal Vision (Section 7-8)

The "wow factor" — next to every translation string:
- **Images** matched by StringID (game screenshots, character art)
- **Audio** playback (original KR, ENG, other available VO)
- **Map location** with visual indicator
- **Character metadata** (backstory, description)
- **Item metadata** (group, parent, children)
- **Debug commands** (teleport, spawn)
- **All of this → feeds AI** for context-aware translation
- **Automatic pipeline:** Dev writes → Context parsed → AI translates → Translator confirms
- **Adaptive embeddings:** Every keystroke → real-time vector suggestions (similarity + theme)

---

*This document is self-contained. Any new Claude session can pick this up and build the landing page.*
