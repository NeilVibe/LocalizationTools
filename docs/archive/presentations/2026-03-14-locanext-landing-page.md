# LocaNext Landing Page Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a cinematic scroll landing page for LocaNext as a single self-contained HTML file — Korean language, dark theme, 12 sections across 4 acts.

**Architecture:** Single `index.html` with inlined CSS/JS + CDN libs (Three.js, GSAP ScrollTrigger, Google Fonts). No build step, no framework. Desktop-first (1440px) with responsive scaling. Three.js particles for hero, GSAP ScrollTrigger for all scroll animations.

**Tech Stack:** Three.js (CDN), GSAP + ScrollTrigger (CDN), Pretendard + Noto Sans KR + JetBrains Mono (Google Fonts CDN), vanilla JS, CSS3 glassmorphism/gradients.

**Spec:** `docs/superpowers/specs/2026-03-14-locanext-landing-page-design.md`
**Context:** `docs/superpowers/specs/2026-03-14-landing-page-EXECUTION-GUIDE.md`

---

## File Structure

```
landing-page/
  index.html    (single file, everything inlined — target < 200KB excluding CDN)
```

One file. All CSS in `<style>`, all JS in `<script>`, all content in `<body>`. CDN loads for Three.js, GSAP, and fonts.

---

## Chunk 1: Foundation + Hero (Section 1)

### Task 1: HTML Scaffold + CSS Foundation

**Files:**
- Create: `landing-page/index.html`

- [ ] **Step 1: Create base HTML with CDN imports, CSS variables, reset, typography, glassmorphism, responsive breakpoints, and reduced-motion query**
- [ ] **Step 2: Verify file opens in browser — dark background, no console errors**
- [ ] **Step 3: Commit** `feat: landing page scaffold with CDN imports and CSS foundation`

### Task 2: Hero Section (Section 1) — Three.js Particles + Typewriter

**Files:**
- Modify: `landing-page/index.html`

- [ ] **Step 1: Add Hero HTML** — full-viewport section with canvas, title placeholder, subtitle, scroll indicator
- [ ] **Step 2: Add Hero CSS** — canvas positioning, cursor blink keyframe, scroll indicator pulse
- [ ] **Step 3: Add Three.js particle field** — 1500 indigo/cyan particles, mouse parallax, continuous drift, resize handler. Note: `innerHTML` used for typewriter cursor insertion with hardcoded strings only (no user input, no XSS risk in this static page)
- [ ] **Step 4: Add typewriter effect** — types title at 40ms/char, then fades in subtitle
- [ ] **Step 5: Verify** — particle field, typewriter title, fade-in subtitle, pulsing scroll indicator
- [ ] **Step 6: Commit** `feat: hero section with Three.js particles and typewriter`

---

## Chunk 2: Act 1 — Problem (Sections 2-3)

### Task 3: Section 2 — Current Reality (Pain Points)

**Files:**
- Modify: `landing-page/index.html`

- [ ] **Step 1: Add Section 2 HTML** — 6 pain point glass cards in 3-col grid (red-tinted borders), fake terminal log area, red ambient glow radial gradient
- [ ] **Step 2: Add pain card CSS** — initial opacity:0/translateY, hover border color, glitch keyframe for terminal
- [ ] **Step 3: Add GSAP scroll animation** — stagger pain cards in at 0.15s delay each; auto-scrolling terminal with fake error lines triggered on section enter
- [ ] **Step 4: Verify** — pain cards stagger in on scroll, terminal auto-scrolls errors
- [ ] **Step 5: Commit** `feat: section 2 — problem pain points with scroll animation`

### Task 4: Section 3 — Pain in Numbers

**Files:**
- Modify: `landing-page/index.html`

- [ ] **Step 1: Add Section 3 HTML** — 4 glass cards in 2x2 grid; two with count-up numbers (40+, 50+), two with text ("always", "impossible"); red ambient glow
- [ ] **Step 2: Add counter utility function** (requestAnimationFrame-based count-up) and GSAP scroll triggers
- [ ] **Step 3: Verify** — numbers count up on scroll, red-tinted glass cards fade in
- [ ] **Step 4: Commit** `feat: section 3 — pain in numbers with animated counters`

---

## Chunk 3: Act 2 — Solution (Sections 4-6)

### Task 5: Section 4 — LocaNext Reveal

**Files:**
- Modify: `landing-page/index.html`

- [ ] **Step 1: Add Section 4 HTML** — light bloom div (radial gradient, starts at 0 size), LocaNext logo with gradient text, tagline, app mockup with perspective transform (fake window chrome, sidebar, translation grid)
- [ ] **Step 2: Add GSAP reveal timeline** — bloom expands, logo scales in with back.out easing, tagline fades, mockup perspective-shifts to flat
- [ ] **Step 3: Verify** — light bloom, logo scale-in, tagline fade, mockup perspective shift
- [ ] **Step 4: Commit** `feat: section 4 — LocaNext reveal with light bloom and app mockup`

### Task 6: Section 5 — Performance Benchmarks

**Files:**
- Modify: `landing-page/index.html`

- [ ] **Step 1: Add Section 5 HTML** — 5 horizontal benchmark bars (500K rows/3s, TM 700K/instant, semantic 10ms, embedding 79x, size 160MB); each has label, stat number, animated fill bar with green→cyan gradient
- [ ] **Step 2: Add GSAP staggered animation** — bars slide in from left (0.2s stagger), fill to 100% on enter
- [ ] **Step 3: Verify** — bars fill on scroll, staggered entry
- [ ] **Step 4: Commit** `feat: section 5 — performance benchmarks with animated bars`

### Task 7: Section 6 — Architecture

**Files:**
- Modify: `landing-page/index.html`

- [ ] **Step 1: Add Section 6 HTML** — 3 pillar glass cards (online/offline/sync) in 3-col grid; SVG network diagram with central PostgreSQL node, 3 connected clients, 1 offline client (dashed, red)
- [ ] **Step 2: Add GSAP animation** — pillars stagger in, SVG connection lines fade in sequentially
- [ ] **Step 3: Verify** — pillars stagger, connections appear
- [ ] **Step 4: Commit** `feat: section 6 — architecture online/offline/sync diagram`

---

## Chunk 4: Act 3 — Future (Sections 7-9)

### Task 8: Section 7 — Multimodal Context Panel

**Files:**
- Modify: `landing-page/index.html`

- [ ] **Step 1: Add Section 7 HTML** — left: fake translation grid (StringID/KR/EN columns, 3-4 rows); right: context panel with stacked items (image placeholder with gradient, audio waveform CSS bars, mini-map dot, character/item metadata cards)
- [ ] **Step 2: Add GSAP timeline** — grid slides in from left, panel slides from right, each panel element fades in sequentially with glow pulse
- [ ] **Step 3: Verify** — grid appears, panel opens, elements highlight sequentially
- [ ] **Step 4: Commit** `feat: section 7 — multimodal context panel mockup`

### Task 9: Section 8 — AI Translation Pipeline

**Files:**
- Modify: `landing-page/index.html`

- [ ] **Step 1: Add Section 8 HTML** — 4 glass cards in horizontal row connected by arrow elements: context parsing → AI feed → human quality → translator confirms. Quality meter bar below. Colored dots (CSS circles with animation) flow along connecting line.
- [ ] **Step 2: Add GSAP pipeline animation** — cards build left-to-right on scroll, dots flow through, quality bar fills, final "confirm" button pulses green
- [ ] **Step 3: Verify** — pipeline builds, dots flow, quality fills
- [ ] **Step 4: Commit** `feat: section 8 — AI translation pipeline with flow animation`

### Task 10: Section 9 — Dev Writing Platform

**Files:**
- Modify: `landing-page/index.html`

- [ ] **Step 1: Add Section 9 HTML** — fake editor mockup (dark code-editor style, line numbers, Korean text being "typed"), autocomplete dropdown with 4 TM match items (each with relevance % badge), side panel with theme cluster tags
- [ ] **Step 2: Add GSAP animation** — typewriter in editor area, dropdown staggers in, relevance percentages count up, theme tags fade in
- [ ] **Step 3: Verify** — editor types, suggestions appear, scores animate
- [ ] **Step 4: Commit** `feat: section 9 — dev writing platform with autocomplete mockup`

---

## Chunk 5: Act 4 — Proof (Sections 10-12)

### Task 11: Section 10 — Tool Arsenal

**Files:**
- Modify: `landing-page/index.html`

- [ ] **Step 1: Add Section 10 HTML** — center LocaNext hub node, 8 satellite tool nodes arranged in circle pattern via CSS (absolute positioning or grid), each with name + Korean desc. SVG or CSS connection lines between hub and satellites.
- [ ] **Step 2: Add GSAP entrance animation** — tools fly in from edges (0.2s stagger), connection lines draw after all placed, slow CSS orbital rotation on container
- [ ] **Step 3: Verify** — tools stagger in, connections draw, gentle orbit
- [ ] **Step 4: Commit** `feat: section 10 — tool arsenal hexagonal grid`

### Task 12: Section 11 — The Builder (Stats)

**Files:**
- Modify: `landing-page/index.html`

- [ ] **Step 1: Add Section 11 HTML** — large stat numbers (912+, 161+, 0, 60+, 9, 55+, 13, 500K+) in responsive grid with Korean labels; below: tech stack nodes (PostgreSQL, FastAPI, Svelte 5, Electron, FAISS, Model2Vec) as small glass pills connected with lines
- [ ] **Step 2: Add GSAP animation** — stats fly in with parallax y-offsets, count-up on each, tech nodes connect with animated lines, background glow pulses
- [ ] **Step 3: Verify** — stats animate with depth, count up, nodes connect
- [ ] **Step 4: Commit** `feat: section 11 — builder stats and tech architecture`

### Task 13: Section 12 — Closing

**Files:**
- Modify: `landing-page/index.html`

- [ ] **Step 1: Add Section 12 HTML** — centered closing statement, gradient LocaNext logo with glow, minimal dark bg
- [ ] **Step 2: Add GSAP fade-in** — slow 2s opacity reveal on scroll
- [ ] **Step 3: Verify** — minimal, dramatic, slow fade
- [ ] **Step 4: Commit** `feat: section 12 — closing statement`

---

## Chunk 6: Polish + Final

### Task 14: Section Transitions + Smooth Scrolling

- [ ] **Step 1: Add smooth color transitions between act themes** (red ambient → indigo → purple → dark)
- [ ] **Step 2: Add gradient divider lines between major acts**
- [ ] **Step 3: Verify full scroll experience end-to-end**
- [ ] **Step 4: Commit** `fix: polish section transitions and scroll flow`

### Task 15: Responsive + Performance

- [ ] **Step 1: Test and fix tablet (768px)** — stack grids to 2-col or 1-col
- [ ] **Step 2: Test mobile (375px)** — disable Three.js, simplify animations
- [ ] **Step 3: Verify `prefers-reduced-motion`** disables all animation
- [ ] **Step 4: Check file size < 200KB** (excluding CDN)
- [ ] **Step 5: Commit** `fix: responsive layout and performance optimizations`

### Task 16: Final Verification

- [ ] **Step 1: Open in browser, scroll all 12 sections**
- [ ] **Step 2: Take screenshots of each section**
- [ ] **Step 3: Check console for zero errors**
- [ ] **Step 4: Final commit** `feat: LocaNext landing page — complete cinematic scroll experience`
