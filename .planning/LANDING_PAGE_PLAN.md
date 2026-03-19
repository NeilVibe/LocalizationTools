# Landing Page — CRAFT Phase Plan

> Content complete. Now building the rocket piece by piece.
> Each piece = deep research → autoresearch loop → implement → verify → commit.
> Stable base: 7881cc6c

## COMPLETED
- [x] Phase A: Performance (WebP 90% reduction, conditional Three.js, preconnect)
- [x] Phase B: Entrance animation (opacity fade, camera pullback, rotation ramp, mesh gradient)
- [x] Phase E: Accessibility (cursor fix, aria-labels, contrast)
- [x] Swarm redesign (Queen/Hive/Ralph/Autoresearch + 12 outer nodes + galaxy bg)
- [x] Subtle polish (Lenis, twinkle, color temp, scroll Z drift, CSS refinements)

## CRAFT PIECES (each = deep research + autoresearch before implementation)

### Piece 1: Section Reveals — blur-to-sharp materialization
Replace all basic fade-ins with blur(8px)→blur(0) + scale(0.97→1.0).
Apple-style "content materializes from nothing."

### Piece 2: Scroll-driven particle color journey
Particles shift copper→blue as user scrolls. Subliminal narrative depth.
Near-zero performance cost (just color interpolation in existing loop).

### Piece 3: Animated gradient borders on feature cards
CSS @property rotating conic-gradient. Hover-only, 1px, copper→blue cycle.
"Liquid light" border effect. The 2025-2026 signature luxury technique.

### Piece 4: Magnetic button interactions
CTA buttons with inner text parallax on hover. Elastic snap-back.
Limit to 2-3 buttons max. Signature premium interaction.

### Piece 5: Hero background depth layer
Second ambient layer behind mesh gradient — slower speed, different colors.
Creates parallax depth perception between two gradient layers.

### Piece 6: Swarm canvas polish pass
Refine node sizes, connection line aesthetics, data particle density.
Add subtle glow halo on queen node. Worker orbit trail effect.

### Piece 7: Typography motion
Key headings with word-by-word slide-up reveal (Korean word-based split).
GSAP 3.13 SplitText (now free) or manual split function.

### Piece 8: Closing section cinematic
Final section grand finale — particles reconverge, warm glow crescendo.
The "wow this was incredible" moment before the page ends.

### Piece 9: Performance + Lighthouse audit
Run full Lighthouse audit, fix any remaining issues.
Target: 90+ performance, 100 accessibility.

### Piece 10: Mobile polish pass
Ensure premium feel without particles. Typography, spacing, timing.

## RESEARCH TOOLS
- Autoresearch (5+ competing agents per piece)
- UI/UX Pro Max (design critique before implementing)
- Nano Banana (generate textures/backgrounds if needed)
- Stitch MCP (prototype screens)
- Skill search (find new skills per piece)
- brains-trust (second opinion on design decisions)
- Critique skill (audit after each piece)

## SKIP LIST
- Cursor trail particles (conflicts)
- Radial ambient pulse (conflicts)
- Progressive disclosure blur (usability tax)
- defer on scripts (breaks inline execution)
