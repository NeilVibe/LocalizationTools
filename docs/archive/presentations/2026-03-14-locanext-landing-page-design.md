# LocaNext Landing Page — Design Spec

## Overview

A single self-contained HTML file that presents LocaNext as a cinematic scroll experience. Korean language. Dark theme. 12 sections across 4 acts. All "mockups" are CSS/HTML-constructed facsimiles, NOT screenshots or images. Built with Three.js, GSAP ScrollTrigger, and pure CSS — all inlined via CDN. No build step, no dependencies, double-click to open.

## Goals

1. **Product showcase** — Show internal stakeholders what LocaNext is and why they need it
2. **Technical credibility** — Demonstrate architectural depth (5-tier TM cascade, vector embeddings, offline/online sync, multimodal context)
3. **AI capability proof** — Show what one person + AI can build (the meta-message: this page itself was AI-made)
4. **Provoke** — Shake people up about the current broken workflow and the future of localization

## Audience

- Internal company stakeholders (Korean-speaking)
- Management who needs convincing
- Technical leads who need to see the architecture
- Anyone who needs to understand "what AI can really do"

## Tone

Cinematic epic + bold provocative. Dark, dramatic, builds tension. Like a game trailer meets an Apple keynote. Korean copy throughout.

## Delivery

- Single `.html` file (self-contained)
- All CSS/JS inlined or loaded via CDN (Three.js, GSAP, Google Fonts)
- No build step, no npm, no framework — opens in any browser
- Location: `/home/<USERNAME>/LocalizationTools/landing-page/index.html`

## Tech Stack

| Tech | Role | Source |
|------|------|--------|
| Three.js | 3D hero particles, floating UI elements | CDN (unpkg) |
| GSAP + ScrollTrigger | All scroll-triggered animations, timelines | CDN (cdnjs) |
| CSS3 | Glass morphism, gradients, keyframes, dark theme | Inlined |
| Vanilla JS | Counters, typewriter effect, intersection observers | Inlined |
| Pretendard / Noto Sans KR | Korean-optimized typography | Google Fonts CDN |
| SVG | Icons, diagrams, tool logos | Inlined |

## Color Palette

| Role | Color | Usage |
|------|-------|-------|
| Background | `#0a0a0f` | Main dark bg |
| Background accent | `#12121a` | Section alternation |
| Primary glow | `#6366f1` → `#8b5cf6` | Indigo-purple gradient, CTA, highlights |
| Accent | `#06b6d4` | Cyan for data/tech elements |
| Danger/Problem | `#ef4444` | Act 1 — red for broken tools |
| Success/Solution | `#10b981` | Act 2 — green for performance wins |
| Text primary | `#f1f5f9` | Main text |
| Text secondary | `#94a3b8` | Subdued text |
| Glass | `rgba(255,255,255,0.05)` | Glassmorphism cards |

## Typography

| Role | Font | Weight | Size |
|------|------|--------|------|
| Hero title | Pretendard | 900 | 72-96px |
| Section titles | Pretendard | 700 | 48-56px |
| Body | Noto Sans KR | 400 | 18-20px |
| Stats/numbers | JetBrains Mono | 700 | 48-72px |
| Labels | Noto Sans KR | 500 | 14px, uppercase letter-spacing |

---

## Story Arc — 4 Acts

### ACT 1: 문제 인식 (Problem Recognition)
*Make them uncomfortable. Current tools are broken.*

### ACT 2: 솔루션 (The Solution)
*Light breaks through. LocaNext is fast, complete, adaptive.*

### ACT 3: 미래 (The Future)
*Multimodal. AI-powered. Beyond translation.*

### ACT 4: 증명 (The Proof)
*One person + AI. The tool arsenal. This page itself.*

---

## Section-by-Section Design

### Section 1: Hero
**Act:** Opening
**Content:**
- Title types itself: "로컬라이제이션의 미래가 시작됩니다" (The future of localization begins)
- Subtitle fades in: "하나의 플랫폼. 하나의 비전. AI와 함께." (One platform. One vision. With AI.)
- Scroll indicator at bottom

**Visual:**
- Full-viewport dark background
- Three.js particle field — thousands of small glowing dots (indigo/cyan), drifting slowly
- Particles react to mouse movement (parallax displacement)
- Subtle depth-of-field blur on distant particles
- Title emerges from particle cloud

**Animation:**
- Typewriter effect on title (40ms per character)
- Subtitle fades in 1s after title completes
- Particles continuously drift, mouse-reactive
- Scroll indicator pulses

---

### Section 2: The Problem — Current Reality
**Act:** 1
**Content:**
- Header: "지금, 당신의 워크플로우를 솔직하게 돌아봅시다" (Let's honestly look at your current workflow)
- Pain points appear one by one:
  - "6개의 분리된 스크립트" (6 separate scripts)
  - "커맨드라인 의존" (Command-line dependent)
  - "협업 불가능" (No collaboration)
  - "오프라인 작업 불가" (No offline work)
  - "느린 검색, 느린 매칭" (Slow search, slow matching)
  - "엑셀 지옥" (Excel hell)

**Visual:**
- Dark background with subtle red ambient glow
- Fragmented UI mockups floating, cracked/glitching (CSS glitch effect)
- Each pain point slides in from different directions with red accent
- Terminal windows with fake error logs scrolling

**Animation:**
- Scroll-triggered: each pain point staggers in (0.3s delay between)
- Glitch effect on mockup images (CSS `clip-path` animation)
- Red pulse on background
- Error log auto-scrolls

---

### Section 3: Pain in Numbers
**Act:** 1
**Content:**
- Stats that hurt (animated counters):
  - "수동 작업 시간: 매주 40시간+" (Manual work: 40+ hours/week)
  - "스크립트 전환: 하루 50회+" (Script switching: 50+ times/day)
  - "데이터 유실 위험: 항상" (Data loss risk: always)
  - "실시간 협업: 불가능" (Real-time collaboration: impossible)

**Visual:**
- Large numbers count up from 0
- Red-tinted cards with glass morphism
- Background: slow red particle drift

**Animation:**
- Numbers count up when section enters viewport
- Cards fade in sequentially
- Transition: red fades to dark, then light breaks through

---

### Section 4: LocaNext Reveal
**Act:** 2
**Content:**
- Header: "이제, 제대로 된 걸 보여드리겠습니다" (Now let me show you something real)
- LocaNext logo materializes from particles
- Tagline: "빠르고. 완벽하고. 적응하는. 게임 로컬라이제이션 플랫폼." (Fast. Complete. Adaptive. Game localization platform.)

**Visual:**
- Dramatic transition: darkness cracks, light explodes through
- Three.js particles converge from scattered positions into a centered cluster; LocaNext logo overlaid as HTML/CSS text with glow effect (NOT particle-shaped text — too complex for scope)
- Purple/indigo glow bloom effect (CSS radial-gradient pulse behind logo)
- App mockup materializes below (CSS 3D perspective transform)

**Animation:**
- Scroll triggers particle convergence
- Light bloom CSS animation (radial gradient pulse)
- Logo holds for 1s, then app mockup perspective-shifts into view
- Background transitions from red-dark to indigo-dark

---

### Section 5: Performance
**Act:** 2
**Content:**
- Header: "속도가 다릅니다" (The speed is different)
- Benchmark comparisons:
  - "50만 행 로드: 3초" (500K rows load: 3 seconds)
  - "TM 구축: 70만 엔트리 — 즉시" (TM build: 700K entries — instant)
  - "시맨틱 검색: 10ms" (Semantic search: 10ms)
  - "벡터 임베딩: 79배 빠름" (Vector embedding: 79x faster)
  - "앱 크기: 160MB (2GB+ → 160MB)" (App size: 160MB, down from 2GB+)

**Visual:**
- Horizontal comparison bars animating from left
- "Before" (red, slow) vs "After" (green/cyan, instant)
- Numbers count up with glow effect
- Speed lines / motion blur CSS on the "fast" side

**Animation:**
- Each benchmark scrolls in and bar fills to completion
- Numbers have odometer-style count-up
- Staggered reveal (0.4s between each)

---

### Section 6: Architecture — Online/Offline/Sync
**Act:** 2
**Content:**
- Header: "온라인. 오프라인. 제로 지연 동기화." (Online. Offline. Zero-lag sync.)
- Three pillars:
  - "온라인 모드" — PostgreSQL, WebSocket 실시간, 50+ 동시 사용자
  - "오프라인 모드" — SQLite, 완전한 기능 동일성, 자동 전환
  - "충돌 해결" — Clean conflict resolution, 데이터 무결성 보장

**Visual:**
- Animated network diagram: central server node, multiple client nodes
- Connection lines pulse with data flow (cyan dots traveling along paths)
- Offline node disconnects gracefully, reconnects with sync animation
- Glass morphism cards for each pillar

**Animation:**
- Diagram builds itself on scroll
- Data flow dots move along connection lines
- Disconnect/reconnect animation plays in sequence
- Cards slide up with stagger

---

### Section 7: Multimodal Context Panel
**Act:** 3
**Content:**
- Header: "번역 그 이상. 멀티모달 컨텍스트." (Beyond translation. Multimodal context.)
- Description: Translation grid with context panel showing:
  - 게임 내 이미지 (In-game images matched by StringID)
  - 음성 재생 (Audio playback — original, English, other VO)
  - 맵 위치 (Map location of the region)
  - 캐릭터 배경 (Character backstory, description)
  - 아이템 메타데이터 (Item group, children, attributes)
  - 디버그 명령어 (In-game debug/teleport commands)

**Visual:**
- Mockup of translation grid with side panel expanding
- Panel shows: image thumbnail, audio waveform, mini-map, metadata cards
- Each element highlights sequentially
- Floating labels point to each element

**Animation:**
- Grid appears first (slide in from left)
- Context panel slides open from right
- Each element in panel fades in sequentially (image → audio → map → meta)
- Subtle glow pulse on each as it activates

---

### Section 8: AI Translation Pipeline
**Act:** 3
**Content:**
- Header: "컨텍스트가 AI를 바꿉니다" (Context changes AI)
- Flow:
  1. 파싱된 컨텍스트 (이미지, 오디오, 메타데이터) → Parsed context
  2. AI에 정확한 맥락 전달 → Feed AI the RIGHT context
  3. 인간 수준의 번역 품질 → Human-level translation quality
  4. 번역가는 확인만 → Translator just confirms
- The automatic pipeline: 개발자 작성 → AI 번역 → 번역가 확인

**Visual:**
- Horizontal flow diagram with animated arrows
- Each step is a glass card with icon
- Data streams (colored dots) flow from left to right through pipeline
- Quality meter rises as context gets added

**Animation:**
- Pipeline builds left-to-right on scroll
- Dots flow through each stage
- Quality bar fills up
- Final "확인" (confirm) button pulses green

---

### Section 9: Dev Writing Platform
**Act:** 3
**Content:**
- Header: "개발자도 직접 씁니다. VSCODE는 이제 그만." (Devs write directly. No more VSCODE.)
- Features:
  - 실시간 용어집/TM/TB 관리 (Real-time glossary/TM/TB)
  - 타이핑할 때마다 적응형 벡터 임베딩 (Adaptive vector embedding on every keystroke)
  - 유사도 + 테마 기반 제안 (Similarity + theme-based suggestions)
  - 통합 용어 관리 — 혼란 없는 일관성 (Unified terminology — consistency without confusion)

**Visual:**
- Mockup of text editor with autocomplete dropdown
- As "typing" happens, suggestions appear in real-time
- Suggestions glow with relevance score
- Side panel shows TM matches and theme clusters

**Animation:**
- Typewriter effect in the editor mockup
- Autocomplete dropdown appears with staggered items
- Relevance scores count up
- Theme tags fade in

---

### Section 10: Tool Arsenal
**Act:** 4
**Content:**
- Header: "하나가 아닙니다. 전체 생태계입니다." (It's not one tool. It's an ecosystem.)
- Tools reveal one by one:
  - LocaNext (메인 플랫폼)
  - QuickTranslate (Excel↔XML)
  - QACompiler (데이터시트 생성)
  - LanguageDataExporter (XML→Excel)
  - MapDataGenerator (데이터 시각화)
  - ExtractAnything (추출 도구)
  - QuickSearch (용어집 QA)
  - KR Similar (유사 문자열)
  - XLS Transfer (일괄 전송)

**Visual:**
- Each tool has an icon/logo in a hexagonal grid
- Tools fly in from edges and snap into position
- Connection lines draw between related tools
- Center: LocaNext hub, satellites orbit

**Animation:**
- Scroll triggers tools entering one by one (0.2s stagger)
- Each one has subtle glow effect on entry
- Connection lines draw after all tools placed
- Final: orbital animation (tools slowly rotate around center)

---

### Section 11: The Builder
**Act:** 4
**Content:**
- Header: "이 모든 것을 한 사람이 만들었습니다. AI와 함께." (One person built all of this. With AI.)
- Stats cascade:
  - "912+ 테스트 통과" (912+ tests passing)
  - "161+ 버그 수정 (미해결: 0)" (161+ bugs fixed, 0 open)
  - "60+ 빌드 릴리스" (60+ build releases)
  - "9개 도구" (9 tools)
  - "55+ API 엔드포인트" (55+ API endpoints)
  - "13개 언어 지원" (13 language support)
  - "50만+ 행 처리" (500K+ rows handled)
- Subtext: architecture diagram fades in — PostgreSQL, FastAPI, Svelte 5, Electron, FAISS, Model2Vec

**Visual:**
- Stats appear as large glowing numbers floating in 3D space
- Each stat has subtle particle trail
- Architecture diagram renders as connected nodes
- Purple/indigo glow intensifies

**Animation:**
- Numbers fly in from different z-depths (parallax 3D feel)
- Count-up animation on each
- Architecture nodes connect with animated lines
- Background glow pulses with each stat

---

### Section 12: Closing
**Act:** 4
**Content:**
- Statement: "이것이 로컬라이제이션의 미래입니다." (This is the future of localization.)
- Sub: "그리고 이 웹페이지도 AI가 만들었습니다." (And this webpage was also made by AI.)
- LocaNext logo, subtle particle background
- Optional: contact or "더 알아보기" (Learn more) CTA

**Visual:**
- Minimal. Dark background, centered text
- LocaNext logo with subtle glow
- Particles from hero section return, closing the loop
- Fade to near-black

**Animation:**
- Text fades in slowly (2s)
- Logo pulses once
- Particles slow down and settle
- Smooth fade out

---

## Responsive Behavior

- **Desktop-first** (1440px design width)
- Scales down to tablet (768px) — reduced particle count, simplified 3D
- Mobile (375px) — particles disabled, GSAP animations simplified, stacked layout
- Three.js canvas resizes with `window.resize` handler

## Performance Budget

- Target: 60fps scroll on mid-range laptop
- Three.js particles: max 2000 (reduce on mobile)
- GSAP: use `will-change` and `transform` only (no layout triggers)
- Images: zero (all code-generated visuals)
- Total file size target: < 200KB (excluding CDN libs)

## Accessibility

- `prefers-reduced-motion` media query: disable all animations, show static layout
- Semantic HTML: proper heading hierarchy, alt text concepts on visual sections
- Contrast ratio: minimum 4.5:1 on all text

## File Structure

```
landing-page/
└── index.html    (single file, everything inlined)
```

---

*Spec written: 2026-03-14*
