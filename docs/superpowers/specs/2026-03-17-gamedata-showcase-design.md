# v3.4 GameData Showcase — Complete Design Spec (v2.0)

**Date:** 2026-03-17
**Status:** Autoresearch iteration #1 — Improved from 6.4 → targeting 9.0+
**Swarm:** `swarm-1773713597860` | **Hive:** `queen-gamedata-showcase`
**Goal:** Showcase the power of LocaNext's GameData viewer with interconnected mock data, redesigned right panel, AI context, and generated media assets.

---

## 1. Problem Statement

The current GameData UI:
- Uses generic "Details / Cross-Refs / Related / Media" tabs that don't help game devs
- Mock data is scattered across 62 XML files with no clear interconnection story
- No dictionary lookup for attribute values
- AI context is buried and not useful
- No showcase-quality deeply nested XML to demonstrate the tree viewer's power
- Database has leftover test data from previous milestones

**This spec delivers:** A clean, focused showcase with 2 carefully crafted XML files, a preloaded dictionary, AI-powered context, generated character images, and a redesigned collapsible-section panel that demonstrates real value for game developers.

---

## 2. Right Panel Redesign — Collapsible Sections (NOT Tabs)

### 2.1 Architecture Decision: Collapsible Foldouts > Tabs

**Research finding (from Unity, Unreal, Godot, Blender):** Every major game editor uses collapsible foldout sections in a single scrollable panel, NOT hidden tabs. Tabs force users to click around hunting for data. Foldouts let users see section headers + item counts at a glance and keep multiple sections open simultaneously.

**New design:** Single scrollable panel with 4 collapsible sections:

```
┌─────────────────────────────────┐
│ SkillNode [Id: 100]        📌 ─ │ ← Header (tag + key + pin button)
├─────────────────────────────────┤
│ ▼ Properties (8)            ▲  │ ← Section 1: ALWAYS open by default
│   Key          100              │
│   SkillKey     Skill_Sacred... →│ ← clickable xref
│   SkillLevel   [1        ]     │ ← editable inline
│   CooldownSec  [12       ]     │
│   ...                           │
├─────────────────────────────────┤
│ ▶ Dictionary (3 matches)       │ ← Section 2: collapsed by default
├─────────────────────────────────┤
│ ▶ Context                      │ ← Section 3: collapsed, lazy-load
├─────────────────────────────────┤
│ ▼ Media (2 images, 1 audio)    │ ← Section 4: auto-expand if has media
│   [portrait.dds] [icon.dds]    │ ← thumbnail grid
│   ▶ voice_greeting.wem         │ ← audio player
└─────────────────────────────────┘
```

### 2.2 Section 1: Properties (Primary — Always Open)

**Purpose:** Show ALL attributes of the selected node in a structured, editable form.

**Layout:**
- **Editable fields FIRST** (green left border) — Input fields with optimistic save on blur
- **Read-only fields BELOW** — Key-value pairs, clickable xref links in blue
- **Children count** — "3 children" chip at bottom, clickable to navigate

**States:**
- **Default:** All attributes listed, editable ones highlighted
- **Loading:** SkeletonText rows matching attribute count
- **Empty:** "Select a node from the tree" message

### 2.3 Section 2: Dictionary

**Purpose:** Find existing translations/terms matching the selected node's attribute values.

**Algorithm:**
1. On node select → extract primary editable attribute value (e.g., "장로 바론")
2. Run cascade search against preloaded TM:
   - Tier 0: Aho-Corasick exact term detection
   - Tier 1: Hash exact match (100%)
   - Tier 2: Whole embedding (Model2Vec, threshold 0.80 for broader results)
   - Tier 5: N-gram Jaccard fallback
3. Display results with color-coded quality bands

**Result Display (from CAT tool research — Phrase TMS, SDL Trados, MemoQ):**
```
┌────────────────────────────────┐
│ 🟢 장로 바론 → Elder Varon    │ ← Exact (green bg)
│ 🟡 장로 → Elder              │ ← Partial (amber bg)
│ 🟡 현자 → Sage               │ ← Similar 87% (amber bg)
│ ⚪ 수호자 → Guardian          │ ← Fuzzy 72% (gray bg)
└────────────────────────────────┘
```

Each result row: source KR | target EN | score badge | tier indicator

**States:**
- **Loading:** 3 skeleton rows with shimmer
- **Empty:** "No matching terms found" with suggestion to check TM
- **Error:** "Dictionary unavailable" with retry button

**Backend:** New endpoint `POST /api/ldm/gamedata/dictionary-lookup`
- Input: `{ text: string, threshold: float, top_k: int }`
- Output: `{ results: [{ source, target, score, tier, tier_name }] }`
- Implementation: Calls BOTH `GameDataSearcher.search()` for entity detection AND `row_repo.suggest_similar()` for TM pair matching, then merges results

### 2.4 Section 3: Context (AI-Generated)

**Purpose:** AI-generated contextual summary about the selected entity.

**Algorithm:**
1. Node select → extract entity name + key attributes
2. Aho-Corasick scan across ALL loaded XML for mentions of this entity
3. Collect cross-reference data (forward + backward refs)
4. Build prompt with entity info + matched context snippets
5. Stream response from Qwen3 via Ollama API

**Optimized Qwen3 Prompt (from research — few-shot, /no_think, repeat_penalty):**

System:
```
You are a game data analyst for an MMORPG. Given entity data, write exactly
2-3 factual sentences explaining what this entity is, what it does in the game,
and how it connects to other entities. Do not start with 'This entity' or
'Based on'. Do not add disclaimers. Output only the summary.

Example:
Entity: Blade of Dawn | Type: ItemInfo | AttackPower: 320, Grade: 5
Output: Blade of Dawn is a Grade 5 weapon dealing 320 attack power, obtained
as a quest reward. It belongs to the Dawn weapon family alongside Sword of
Twilight. /no_think
```

Ollama params: `temperature: 0.3, num_predict: 150, repeat_penalty: 1.1`

**UX (from JetBrains Insights, Cursor, Notion research):**
- **Streaming:** Typewriter effect as tokens arrive (not "spinner then dump")
- **Skeleton → stream transition:** 3 gray shimmer lines → text streams in
- **Regenerate split-button:** Main = regenerate, dropdown = "More technical" / "Simpler" / "Focus on relationships"
- **Confidence border:** Green left border = backed by structured data, amber = AI-inferred
- **Source attribution:** "Based on: knowledgeinfo_showcase.xml" clickable link below summary
- **Model status badge:** Green dot = Qwen3 connected, red = unavailable → show "AI unavailable — start Ollama" message

**States:**
- **Loading:** 3 skeleton shimmer lines
- **Streaming:** Typewriter text with blinking cursor
- **Complete:** Full summary with regenerate button
- **Error:** "AI unavailable" with setup hint, still shows structured cross-ref data
- **Empty:** "No context available for this node"

### 2.5 Section 4: Media

**Purpose:** Show visual/audio assets linked to the selected entity.

**Algorithm:**
1. Scan node attributes for media references:
   - `UITextureName`, `TextureKey`, `TexturePath`, `TextureRef`
   - `SkillIcon`, `VideoPath`
   - `VoicePath`, `VoiceKey`, `VoiceRef`
2. Check codex image cache + mock_gamedata/textures/
3. Display thumbnails with metadata

**UX (from Unity Inspector, Adobe Bridge, Blender research):**
- **Thumbnail grid:** 64x64 thumbnails on checkerboard background (transparency support)
- **Click-to-expand:** Lightbox overlay at full resolution (click-outside or Escape to close)
- **Audio waveform:** Custom canvas-based waveform (replace native `<audio>` element)
- **Broken asset state:** Red-bordered placeholder with broken-image icon + file path in red monospace
- **Skeleton loading:** Content-shaped placeholder (image rectangle + 2 metadata lines)
- **Generate button:** "Generate AI Image" button if no image exists (nano-banana)

**States:**
- **Loading:** Image-shaped skeleton + text skeleton
- **Populated:** Thumbnail grid + audio player + metadata
- **Empty:** "No media linked to this node" with texture attribute hint
- **Broken:** Red placeholder per broken image, still shows other working media

### 2.6 Visual Design Specification

**Color Palette (One Dark Pro — complete):**
```css
--panel-bg: #252526;           /* panel background */
--panel-bg-hover: #2c313a;     /* hover state */
--panel-border: #3c3c3c;       /* borders */
--panel-border-subtle: #2d2d2d;

--section-header-bg: #21252b;  /* collapsible section headers */
--section-header-hover: #282c34;

--prop-key: #d19a66;           /* property names (orange) */
--prop-value: #abb2bf;         /* property values (light gray) */
--prop-editable-bg: rgba(152, 195, 121, 0.05);
--prop-editable-border: rgba(152, 195, 121, 0.2);

--badge-exact: #2d5a3d;        /* exact match bg (dark green) */
--badge-similar: #5a4a2d;      /* similar match bg (dark amber) */
--badge-fuzzy: #3a3a3a;        /* fuzzy match bg (dark gray) */

--ai-border-confident: #10b981; /* green left border */
--ai-border-inferred: #f59e0b; /* amber left border */

--media-checkerboard-light: #3a3a3a;
--media-checkerboard-dark: #2d2d2d;
--media-broken-border: #e06c75;
```

**Spacing scale:** 4px / 8px / 12px / 16px / 24px
**Font sizes:** Section header 11px bold uppercase, prop-key 12px, prop-value 13px, AI text 13px line-height 1.6
**Border-radius:** Sections 0px (sharp edges), badges 4px, thumbnails 4px, inputs 3px
**Animations:**
- Section expand: `max-height` transition 150ms ease-out (skip if > 30 children)
- Chevron rotate: 150ms ease
- Dictionary results: stagger-in, each fades in 50ms after previous
- AI text: typewriter 20ms per character
- Node selection highlight: 300ms background pulse then settle

### 2.7 Context-Adaptive Section Ordering (Blender Pattern)

Sections auto-reorder and auto-expand based on entity type:

| Entity Type | Auto-Expand | Section Order |
|------------|-------------|---------------|
| CharacterInfo | Properties + Media | Props → Media → Dictionary → Context |
| ItemInfo | Properties + Media | Props → Media → Dictionary → Context |
| SkillNode/SkillRef | Properties + Context | Props → Context → Dictionary → Media |
| KnowledgeInfo | Properties + Dictionary | Props → Dictionary → Context → Media |
| RegionInfo | Properties | Props → Context → Media → Dictionary |
| Default | Properties only | Props → Dictionary → Context → Media |

---

## 3. Mock Data Design

### 3.1 File 1: `characterinfo_showcase.staticinfo.xml`

**Changes from v1 (addressing review findings):**
- Add `KnowledgeKey="Knowledge_ElderVaron"` on CharacterInfo root (fixes orphaned knowledge)
- Add dialogue line where Elder Varon mentions "그림자 암살자 키라" (fixes AC asymmetry)
- Add more attributes per node (15+ on root, matching production fidelity)
- Add mixed KR/EN attribute values (e.g., `Job="Paladin_클래스"`)
- Add a 200+ char Korean description to test truncation/tooltip
- Add intra-file cross-ref: Shadow Kira's DialogueSet mentions `CHAR_001`
- Remove dangling `FactionKey` → either add faction entries to File 2 or remove
- Add equipment slots on characters (cross-ref to future item data)

**Depth verification (both branches must reach 5+):**
- Branch A: CharacterInfo → StatGroup → StatEntry → LevelScaling → Formula → Coefficient (depth 5) ✓
- Branch B: CharacterInfo → SkillSet → SkillRef → BuffEffect → AreaEffect → TargetFilter (depth 5) ✓
- Branch C (NEW): CharacterInfo → DialogueSet → DialogueLine → EmotionData → TriggerCondition (depth 4)

### 3.2 File 2: `knowledgeinfo_showcase.staticinfo.xml`

**Changes from v1 (addressing review findings):**
- Add depth 5+ nesting: KnowledgeInfo → LevelData → Learnable → UnlockReward → StatBonus → Stat
- Add faction knowledge entries (Knowledge_SageOrder, Knowledge_DarkCult) to resolve dangling FactionKeys
- Add `Knowledge_SealedLibrary` with `RegionKey="Region_SealedLibrary"` to fix namespace mismatch
- Total 8 entries (was 6): +2 faction entries
- Each KnowledgeInfo with at least depth 3 nesting

### 3.3 Mock Dictionary (TM Entries)

**19 entries + 3 NEW fuzzy-test entries:**
- Add "장로 바혼" (typo of 장로 바론) → tests n-gram fuzzy Tier 5
- Add "성스러운 화염" (synonym: Sacred Blaze vs Sacred Flame) → tests embedding similarity
- Add "암살" (partial of 암살자) → tests substring detection

### 3.4 Cross-Reference Verification Map

| Source Key | Source File | Target Key | Target File | Link Type | Status |
|-----------|-------------|------------|-------------|-----------|--------|
| CHAR_001.KnowledgeKey | File 1 | Knowledge_ElderVaron | File 2 | Forward | ✓ Fixed |
| CHAR_001.SkillRef.KnowledgeKey | File 1 | Knowledge_SacredFlame | File 2 | Forward | ✓ |
| CHAR_001.SkillRef.KnowledgeKey | File 1 | Knowledge_HolyShield | File 2 | Forward | ✓ |
| CHAR_002.KnowledgeKey | File 1 | Knowledge_ShadowKira | File 2 | Forward | ✓ NEW |
| CHAR_002.SkillRef.KnowledgeKey | File 1 | Knowledge_ShadowStrike | File 2 | Forward | ✓ |
| CHAR_002.SkillRef.KnowledgeKey | File 1 | Knowledge_VanishStep | File 2 | Forward | ✓ |
| CHAR_001.RegionKey | File 1 | Knowledge_SealedLibrary.RegionKey | File 2 | Shared | ✓ Fixed |
| Knowledge_SacredFlame.CheckCharacterKey | File 2 | CHAR_001 | File 1 | Backward | ✓ |
| Knowledge_ShadowStrike.CheckCharacterKey | File 2 | CHAR_002 | File 1 | Backward | ✓ |
| Knowledge_SageOrder (NEW) | File 2 | CHAR_001.FactionKey | File 1 | Backward | ✓ Fixed |
| Knowledge_DarkCult (NEW) | File 2 | CHAR_002.FactionKey | File 1 | Backward | ✓ Fixed |

**AC Cross-File Detection (verified):**
- "장로 바론" in File 2: Knowledge_ElderVaron.Name, Desc, Dev Memo ✓
- "키라" in File 1: Elder Varon dialogue line (NEW) ✓ Fixed
- "성스러운 불꽃" in File 1: dialogue text ✓
- "봉인된 도서관" in File 1: CharacterDesc, dialogue ✓

### 3.5 Generated Images (4 via nano-banana)

1. **Elder Varon portrait** — "Ancient wise sage, long white beard, glowing blue eyes, ornate golden robes with seal symbols, dark library background, fantasy MMORPG character portrait, 512x512"
2. **Shadow Kira portrait** — "Female shadow assassin, dark hooded cloak, glowing crimson daggers, dark aura, fantasy MMORPG boss portrait, 512x512"
3. **Sacred Flame icon** — "Holy golden flame spell icon, circular ornate border, dark background, fantasy RPG skill icon, 128x128"
4. **Sealed Library scene** — "Ancient magical library, glowing seals on bookshelves, floating books, holy light beams through darkness, fantasy RPG environment, 512x512"

### 3.6 TEXTURE_ATTRS Fix (Critical — from technical review)

The existing media resolver at `gamedata_context_service.py:39-42` checks:
```python
TEXTURE_ATTRS = ("TextureName", "IconTexture", "Texture", "ImagePath")
VOICE_ATTRS = ("VoiceId", "SoundId", "AudioFile")
```

But our showcase XML uses `UITextureName`, `TextureKey`, `TexturePath`, `VoicePath`, `VoiceKey`.

**Fix:** Extend both tuples:
```python
TEXTURE_ATTRS = ("TextureName", "IconTexture", "Texture", "ImagePath", "UITextureName", "TextureKey", "TexturePath", "SkillIcon")
VOICE_ATTRS = ("VoiceId", "SoundId", "AudioFile", "VoicePath", "VoiceKey")
```

### 3.7 Codex Entries (8 entries, not 6)

All auto-generated from the 2 XML files:
1. `character/Character_ElderVaron`
2. `character/Character_ShadowKira`
3. `knowledge/Knowledge_ElderVaron`
4. `knowledge/Knowledge_SacredFlame`
5. `knowledge/Knowledge_HolyShield`
6. `knowledge/Knowledge_ShadowStrike`
7. `knowledge/Knowledge_VanishStep`
8. `knowledge/Knowledge_SealedLibrary`

---

## 4. DB Operations

### 4.1 Nuke Sequence (verified safe)

```bash
# 1. Backup first (automatic)
./scripts/db_manager.sh nuke

# 2. Clear old fixtures
rm -rf tests/fixtures/mock_gamedata/StaticInfo/*

# 3. Place new showcase files
# (scripted placement of 2 XML files)

# 4. Reset CodexService singleton
# Backend restart OR first /codex/ API call triggers lazy re-init

# 5. Load folder in UI → triggers index build
# POST /api/ldm/gamedata/index/build (called by frontend on folder load)
```

**NOTE:** Codex rebuilds LAZILY on first API call (verified in codex_service.py — `if not self._initialized: self.initialize()`). NO explicit restart needed, but recommended for clean slate.

---

## 5. Execution Plan — Phases, Skills, Agents

### Phase 37: Mock Data + DB Reset (2 hours)
**3 parallel agents:**

| Agent | Task | Skills |
|-------|------|--------|
| Agent A: XML Author | Create 2 showcase XML files with ALL fixes from 3.1-3.2 | xml-localization |
| Agent B: DB Manager | Nuke DB, clear fixtures, verify clean state | sql-expert |
| Agent C: Dictionary Builder | Create TM entries via API (22 entries) | fastapi-expert |

**Verification gate:** `curl /api/ldm/codex/types` returns 2 types (character, knowledge) with correct counts.

**Commit after:** `git commit -m "feat(v3.4): showcase mock data + DB reset"`

### Phase 38: Backend Updates (2 hours)
**2 parallel agents:**

| Agent | Task | Skills |
|-------|------|--------|
| Agent D: Dictionary Endpoint | Create `/api/ldm/gamedata/dictionary-lookup` endpoint bridging cascade search + TM suggest | fastapi-expert, python-pro |
| Agent E: Context Optimizer | Optimize Qwen3 prompts, fix TEXTURE_ATTRS/VOICE_ATTRS, update context service | python-pro |

**Verification gate:**
- `curl /api/ldm/gamedata/dictionary-lookup -d '{"text":"장로 바론"}'` returns 3+ matches
- `curl /api/ldm/gamedata/context -d '{...}'` returns media.has_image=true

**Commit after:** `git commit -m "feat(v3.4): dictionary endpoint + context optimization"`

### Phase 39: Right Panel Redesign (4 hours)
**2 parallel agents + 1 sequential:**

| Agent | Task | Skills |
|-------|------|--------|
| Agent F: Panel Shell | Rewrite GameDataContextPanel.svelte → collapsible sections architecture | svelte-code-writer, svelte5-best-practices |
| Agent G: Properties Section | Rewrite NodeDetailPanel as collapsible Properties section | svelte-code-writer, svelte-core-bestpractices |
| Agent H (after F+G): Dictionary + Context + Media sections | Build 3 remaining sections with async fetch, streaming AI, image grid | svelte-code-writer, ui-ux-pro-max, frontend-design |

**Verification gate:** Playwright screenshot of all 4 sections with populated data.

**Commit after:** `git commit -m "feat(v3.4): collapsible panel with Properties/Dictionary/Context/Media"`

### Phase 40: Image Generation + Visual Polish (2 hours)
**2 parallel agents:**

| Agent | Task | Skills |
|-------|------|--------|
| Agent I: Image Generator | Generate 4 images via nano-banana, place in textures/ | nano-banana |
| Agent J: Visual Polish | Apply One Dark Pro theme to panel, add animations, fix spacing | bolder, polish, critique, animate, colorize |

**Autoresearch loop on Agent J:**
```
for each iteration:
  1. Take Playwright screenshot
  2. Score visual quality (1-10) against One Dark Pro reference
  3. If < 8: identify top 3 visual issues, fix them
  4. If >= 8: done
```

**Commit after:** `git commit -m "style(v3.4): One Dark Pro panel + generated images"`

### Phase 41: Verification + Showcase Test (1 hour)

**Demo script (60-second walkthrough):**
1. Open folder → tree loads with deep nesting (5 sec)
2. Click Elder Varon → Properties shows 15+ attrs, Dictionary finds 6 matches, Context generates "Elder Varon is..." summary, Media shows portrait (15 sec)
3. Click KnowledgeKey xref → smooth scroll to knowledge entry in tree (5 sec)
4. Click Sacred Flame knowledge → Dictionary finds "성스러운 불꽃", Context shows skill info (10 sec)
5. Expand depth-5 nesting → Formula > Coefficient visible (5 sec)
6. Click Shadow Kira → different portrait, different AI summary, boss stats (10 sec)
7. Click dialogue line → Korean text with `<br/>` tags renders beautifully (5 sec)
8. Collapse/expand sections in panel → smooth animations (5 sec)

**Negative tests:**
- Node with no dictionary matches → "No matching terms" state
- Node with no media → "No media linked" placeholder
- Ollama not running → "AI unavailable" graceful fallback

**Commit after:** `git commit -m "test(v3.4): showcase verification complete"`

### Phase 42: Autoresearch Polish Loop

**Ralph loop prompt:**
```
Score the v3.4 GameData Showcase on 5 dimensions:
1. Visual beauty (screenshot vs One Dark Pro reference)
2. Data interconnection (click xrefs, verify navigation)
3. Dictionary accuracy (search "장로 바론", verify 3+ results)
4. AI context quality (verify 2-3 sentence summary generated)
5. Media display (verify portraits + icons visible)

Each dimension 1-10. Composite must be >= 9.0.
If < 9.0: identify weakest dimension, make ONE focused fix, re-score.
If >= 9.0: output SHOWCASE_COMPLETE.
```

---

## 6. Success Criteria (Measurable)

| Criterion | Target | Verification |
|-----------|--------|--------------|
| XML nesting depth | 5+ levels with fold/expand | Count visible levels in Playwright screenshot |
| Cross-references | Click xref → navigates to target | Playwright click test |
| Dictionary results | 3+ matches for "장로 바론" | API curl test |
| AI Context | 2-3 sentence summary in < 5 seconds | API response time check |
| Media display | 2+ images visible in Media section | Playwright screenshot |
| Korean text | `<br/>` rendered, line-height 1.6 | Visual inspection |
| Panel theme | One Dark Pro colors match viewer | Screenshot comparison |
| Performance | < 500ms to render tree | Performance.now() measurement |
| Zero errors | No Svelte errors, no console errors | Playwright console check |
| Properties section | All attributes shown, editable ones highlighted | Playwright snapshot |
| Empty states | All 4 sections show correct empty state | Playwright test with empty node |
| Graceful AI fallback | Context shows message when Ollama down | Kill Ollama, verify UI |

---

## 7. Files to Create/Modify

### New Files
- `tests/fixtures/mock_gamedata/StaticInfo/characterinfo/characterinfo_showcase.staticinfo.xml`
- `tests/fixtures/mock_gamedata/StaticInfo/knowledgeinfo/knowledgeinfo_showcase.staticinfo.xml`
- `tests/fixtures/mock_gamedata/textures/characters/elder_varon_portrait.png` (generated)
- `tests/fixtures/mock_gamedata/textures/characters/shadow_kira_portrait.png` (generated)
- `tests/fixtures/mock_gamedata/textures/skills/sacred_flame_icon.png` (generated)
- `tests/fixtures/mock_gamedata/textures/regions/sealed_library.png` (generated)
- `server/tools/ldm/routes/gamedata_dictionary.py` (new endpoint)

### Modified Files
- `locaNext/src/lib/components/ldm/GameDataContextPanel.svelte` — Rewrite to collapsible sections
- `locaNext/src/lib/components/ldm/NodeDetailPanel.svelte` — Integrate as Properties section
- `locaNext/src/lib/components/ldm/GameDataTree.svelte` — Minor polish
- `server/tools/ldm/services/gamedata_context_service.py` — Fix TEXTURE_ATTRS, optimize Qwen3 prompt
- `server/tools/ldm/routes/gamedata.py` — Register dictionary-lookup route

### Deleted
- Old mock XML files in StaticInfo/ (replaced by 2 showcase files)
