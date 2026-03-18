# v3.4 GameData Showcase — WOW Effect Plan v2 (Swarm Research)

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Transform the GameData panel into a WOW-effect showcase with working images, right-click menus, modal editing, and premium visual polish — all backed by carefully tailored mock data.

**Architecture:** 4-tab info panel (Dict/Context/Media/Info) + right-click context menu on XML tree + modal attribute editor + premium visual effects from landing page. Fix critical image auth bug first.

**Tech Stack:** Svelte 5, FastAPI, Ollama/Qwen3:8b, Carbon Components, PIL images

**Power Stack:** Ruflo Hive-Mind (Queen + 8 specialists) + Autoresearch scoring + Viking context + UI/UX Pro skills

---

## CRITICAL BUG FIX (Priority 0)

### Task 1: Fix Image Auth Bug

**Root cause (discovered by research agent):** The `/api/ldm/mapdata/thumbnail/{name}` endpoint requires authentication via `Depends(get_current_active_user_async)`, but browser `<img src="">` tags CANNOT send Authorization headers. The image request gets 401'd silently = broken image.

**Files:**
- Modify: `server/tools/ldm/routes/mapdata.py:81-85`

**Fix option A (recommended):** Fetch image as blob in frontend with auth headers:
```javascript
// In GameDataContextPanel.svelte
async function loadImage(url) {
  const response = await fetch(`${API_BASE}${url}`, { headers: getAuthHeaders() });
  if (!response.ok) return null;
  const blob = await response.blob();
  return URL.createObjectURL(blob);
}
```

**Fix option B:** Remove auth from thumbnail endpoint (simpler but less secure):
```python
@router.get("/mapdata/thumbnail/{texture_name}")
async def get_thumbnail(texture_name: str):  # No auth dependency
```

- [ ] Step 1: Choose fix approach (A for security, B for speed)
- [ ] Step 2: Implement the fix
- [ ] Step 3: Verify image loads in browser via Playwright screenshot

---

## PHASE A: Right-Click Context Menu + Modal Edit

### Task 2: Add Right-Click Context Menu to GameDataTree

Reuse the existing context menu pattern from `TMExplorerGrid.svelte`.

**Files:**
- Modify: `locaNext/src/lib/components/ldm/GameDataTree.svelte`

**Menu options for right-clicking an XML node:**
- "Edit Attribute..." → opens modal
- "Copy Key" → copies node Key to clipboard
- "Copy Value" → copies clicked attribute value
- "Navigate to Reference" → if attribute is a cross-ref Key
- Divider
- "Generate AI Context" → triggers AI summary for this node

- [ ] Step 1: Add contextMenu state (`$state({ show, x, y, node, attrName })`)
- [ ] Step 2: Add `oncontextmenu` handler to `.xml-row` elements
- [ ] Step 3: Render context menu dropdown with menu items
- [ ] Step 4: Add click-outside-to-close handler
- [ ] Step 5: Add keyboard handling (Escape to close)

### Task 3: Create Attribute Edit Modal

New component for editing XML attributes. Beautiful, smooth UIUX.

**Files:**
- Create: `locaNext/src/lib/components/ldm/AttributeEditModal.svelte`
- Modify: `locaNext/src/lib/components/ldm/GameDataTree.svelte` (import + wire up)

**Design:**
- Modal opens on double-click attribute OR right-click → "Edit..."
- Shows: Attribute name (read-only label), current value (editable textarea)
- Korean text input with proper font
- Ctrl+S to save, Escape to cancel
- Warm glow border on the modal (landing page style)
- Smooth fade-in animation (fadeSlideIn)
- Calls `PUT /api/ldm/gamedata/save` on save
- Optimistic UI: update tree immediately, revert on error

- [ ] Step 1: Create modal component with props (open, attrName, attrValue, onSave, onCancel)
- [ ] Step 2: Style with One Dark Pro + warm glow accents
- [ ] Step 3: Wire up double-click on editable attributes in tree
- [ ] Step 4: Wire up right-click menu "Edit..." action
- [ ] Step 5: Implement save API call + optimistic update

---

## PHASE B: Visual WOW Polish (Landing Page Techniques)

### Task 4: Premium Visual Effects on Right Panel

Apply landing page techniques to GameDataContextPanel.svelte.

**Files:**
- Modify: `locaNext/src/lib/components/ldm/GameDataContextPanel.svelte`

**Effects to add:**
1. **Multi-layer shadow on panel** (5 layers like landing page)
2. **Breathing glow on active tab** (24px→32px, 5s cycle)
3. **16px border-radius** on cards/images
4. **Backdrop blur** on panel header (frosted glass)
5. **Staggered content reveal** (nth-child animation delays)
6. **Hover elevation** on dictionary cards (translateY -2px + shadow)
7. **Gradient text** on entity names in dictionary

### Task 5: Premium Media Tab (Character Card)

Make the Media tab feel like a premium character card.

**Design:**
- Full-width image with warm glow border on hover
- Character name in gradient text below
- Audio player with custom play button (not default HTML)
- Dark background (#1a1a2e) with 16px border-radius
- Reflection effect below image (like landing page mockups)

### Task 6: Premium Context Tab

**Enhance AI Context section:**
- Loading: shimmer animation (not plain spinner)
- Generated: Korean text with warm accent border-left
- Attribute summary: clean key-value with warm section headers
- Smooth transitions between loading → generated states

---

## PHASE C: AI Context Fix + Performance

### Task 7: Fix AI Summary Loading UX

**Current issue:** 1.5s delay feels slow because no feedback.

- [ ] Step 1: Add shimmer loading animation (already exists via shimmerRows)
- [ ] Step 2: Auto-trigger AI summary when Context tab is clicked (not manual)
- [ ] Step 3: Add simple in-memory LRU cache (avoid re-generating same node)
- [ ] Step 4: Verify AI generates Korean output consistently

### Task 8: Performance Audit

- [ ] Step 1: Run all API endpoints with timing
- [ ] Step 2: Check for any frontend console errors
- [ ] Step 3: Verify Svelte compilation (svelte-check)
- [ ] Step 4: Check for $effect loops or excessive re-renders

---

## PHASE D: XML Viewer Improvements

### Task 9: Already Done — Text Wrapping

XML viewer text wrapping was applied (white-space: pre-wrap). Verify it works.

---

## EXECUTION ORDER

| Priority | Task | Agent Type | Depends On |
|----------|------|-----------|------------|
| P0 | Task 1: Fix Image Auth | Backend | None |
| P1 | Task 2: Right-Click Menu | Frontend | None |
| P1 | Task 3: Edit Modal | Frontend | Task 2 |
| P2 | Task 4: Visual WOW | Frontend CSS | None |
| P2 | Task 5: Media Card | Frontend CSS | Task 1 |
| P2 | Task 6: Context Polish | Frontend | None |
| P3 | Task 7: AI Loading UX | Frontend+Backend | None |
| P3 | Task 8: Performance | Debug | All |

**Parallel execution:** Tasks 1, 2, 4, 6, 7 are independent. Launch 5 agents simultaneously.

---

## AUTORESEARCH SCORING (after each iteration)

| Dimension | Target | Metric |
|-----------|--------|--------|
| Image display | 10/10 | Playwright screenshot shows character portrait |
| Right-click menu | 10/10 | Right-click on node shows context menu |
| Modal edit | 10/10 | Double-click attr → modal → save works |
| Visual WOW | 9/10 | Landing page-level glow, shadows, animations |
| AI Context (Korean) | 9/10 | Korean summary generates in <2s with loading indicator |
| Dictionary | 9/10 | 3+ results with gradient entity names |
| Media (big image) | 9/10 | Full-width portrait, warm glow border |
| **Composite** | **9.3/10** | All features working, visually premium |
