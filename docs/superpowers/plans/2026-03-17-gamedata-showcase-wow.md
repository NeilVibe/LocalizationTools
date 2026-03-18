# v3.4 GameData Showcase — WOW Effect Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the GameData panel deliver WOW effect for executive demo. Every click on a node cascades into Properties + Dictionary matches + AI Context summary + Media assets. Limited mock data files, maximum visual impact.

**Architecture:** Tab-based right panel (Properties always visible + Dictionary/Context/Media tabs) with warm glow visual polish from landing page. 2 XML files with cross-referencing entities. TM entries seeded for Dictionary. Qwen3:8b for AI summaries. Texture images for Media tab.

**Tech Stack:** Svelte 5, FastAPI, PostgreSQL, Ollama/Qwen3:8b, lxml, Carbon Icons

**Power Stack:** GSD (phases) + Ruflo (swarm memory) + Autoresearch (score loop) + Viking (context) + UI/UX Pro (polish) + Critique (quality gates)

**Baseline:** 2.8/10 composite → **Target: 9/10**

---

## Chunk 1: Data Foundation (Enable All Features)

### Task 1: Build Gamedata Index

The index MUST be built before Dictionary or CrossRefs work. Without it, those tabs show nothing.

**Files:**
- None to modify — API call only

- [ ] **Step 1: Build the multi-tier index**

```bash
curl -s -X POST http://localhost:8888/api/ldm/gamedata/index/build \
  -H "Content-Type: application/json" \
  -H "Cookie: session_token=admin_session" \
  -d '{"path":"StaticInfo"}' | python3 -m json.tool
```

Expected: `entity_count > 0`, `ac_terms_count > 0`, `status: "ready"`

- [ ] **Step 2: Verify Dictionary works**

```bash
curl -s -X POST http://localhost:8888/api/ldm/gamedata/dictionary-lookup \
  -H "Content-Type: application/json" \
  -H "Cookie: session_token=admin_session" \
  -d '{"text":"Elder Varon","threshold":0.3,"top_k":10}' | python3 -m json.tool
```

Expected: `results` array with matches from gamedata entities

- [ ] **Step 3: Verify CrossRefs work**

```bash
curl -s -X POST http://localhost:8888/api/ldm/gamedata/context \
  -H "Content-Type: application/json" \
  -H "Cookie: session_token=admin_session" \
  -d '{"node_id":"r0","tag":"CharacterInfo","attributes":{"KnowledgeKey":"Knowledge_ElderVaron","FactionKey":"Faction_SageOrder"},"editable_attrs":["CharacterName"]}' | python3 -m json.tool
```

Expected: `cross_refs.forward` has entries (KnowledgeKey, FactionKey resolved)

### Task 2: Seed TM Entries for Rich Dictionary Results

Current: 19 TM entries. Need: 30+ covering ALL entity names from both XML files so Dictionary tab shows impressive results with Korean→English translations.

**Files:**
- PostgreSQL `ldm_tm_entries` table (INSERT)

- [ ] **Step 1: Query existing TM entries**

```bash
python3 -c "
import psycopg2
c=psycopg2.connect('postgresql://localization_admin:locanext_dev_2025@localhost:5432/localizationtools')
cur=c.cursor()
cur.execute('SELECT source_text, target_text FROM ldm_tm_entries WHERE tm_id=467')
for r in cur.fetchall(): print(f'{r[0]} → {r[1]}')
c.close()
"
```

- [ ] **Step 2: Insert missing TM entries for all entity names**

Add entries for every entity name, skill name, region name, knowledge title that appears in the 2 XML files. This ensures Dictionary tab returns rich results for ANY node clicked.

Key entries needed (KR→EN):
- 그림자 키라 → Shadow Kira
- 현자의 결사 → Sage Order
- 전투 능력치 → Combat Stats
- 어둠의 교단 → Dark Cult
- 정화의 빛 → Purifying Light
- 고대의 지혜 → Ancient Wisdom
- 봉인 해제 → Seal Release
- Plus all stat names, skill names, region names from the XML

```sql
INSERT INTO ldm_tm_entries (tm_id, source_text, target_text, created_by, created_at)
VALUES
(467, '그림자 키라', 'Shadow Kira', 'admin', NOW()),
(467, '현자의 결사', 'Sage Order', 'admin', NOW()),
...
```

- [ ] **Step 3: Verify Dictionary returns rich results**

```bash
curl -s -X POST http://localhost:8888/api/ldm/gamedata/dictionary-lookup \
  -H "Content-Type: application/json" \
  -H "Cookie: session_token=admin_session" \
  -d '{"text":"장로 바론","threshold":0.3,"top_k":10}'
```

Expected: 5+ results with both gamedata entity matches AND TM translation matches

### Task 3: Fix UITextureName → Actual File Mapping

Current XML uses `UITextureName="cd_portrait_elder_varon"` but actual files are `character_varon.dds`. The Media tab detects the attribute but the thumbnail URL won't resolve. Need to either rename files or update XML attributes.

**Files:**
- Modify: `tests/fixtures/mock_gamedata/StaticInfo/characterinfo/characterinfo_showcase.staticinfo.xml`
- Modify: `tests/fixtures/mock_gamedata/StaticInfo/knowledgeinfo/knowledgeinfo_showcase.staticinfo.xml`

- [ ] **Step 1: List actual texture files with names matching entities**

```bash
ls tests/fixtures/mock_gamedata/textures/character_*.dds
ls tests/fixtures/mock_gamedata/textures/characters/
```

- [ ] **Step 2: Update UITextureName in XML to match actual filenames**

Ensure `UITextureName` values in XML match files in `textures/` directory.

- [ ] **Step 3: Verify Media endpoint returns correct thumbnail URLs**

Test with curl, confirm `thumbnail_url` resolves to an existing file.

---

## Chunk 2: Tab UI Visual Polish (WOW Effect)

### Task 4: Add Landing Page Visual Effects to Tab Panel

Apply warm glow accents, staggered animations, hover elevation, gradient text from the landing page to GameDataContextPanel.svelte.

**Files:**
- Modify: `locaNext/src/lib/components/ldm/GameDataContextPanel.svelte`

- [ ] **Step 1: Add warm glow CSS variables**

```css
--warm: #d49a5c;
--warm-bright: #f0b878;
--warm-glow: rgba(212, 154, 92, 0.3);
```

- [ ] **Step 2: Add glow to active tab**

```css
.tab-btn.active {
  color: var(--warm-bright);
  border-bottom-color: var(--warm);
  text-shadow: 0 0 8px var(--warm-glow);
}
```

- [ ] **Step 3: Add staggered fade-in animation for tab content items**

```css
@keyframes fadeSlideIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
.dict-row, .ai-summary, .media-thumb-wrap {
  animation: fadeSlideIn 0.25s ease-out backwards;
}
.dict-row:nth-child(1) { animation-delay: 0ms; }
.dict-row:nth-child(2) { animation-delay: 60ms; }
.dict-row:nth-child(3) { animation-delay: 120ms; }
```

- [ ] **Step 4: Add hover elevation to dictionary cards**

```css
.dict-row {
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.dict-row:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3), 0 0 8px var(--warm-glow);
}
```

- [ ] **Step 5: Add gradient text to entity names**

```css
.dict-source {
  background: linear-gradient(135deg, var(--warm), var(--warm-bright));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
```

- [ ] **Step 6: Add pulse indicator for live AI status**

```css
@keyframes statusPulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
.ai-status-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: #10b981;
  animation: statusPulse 2s infinite;
}
```

- [ ] **Step 7: Verify visually with Playwright screenshot**

Navigate to localhost:5173, click a node, switch tabs, take screenshots of each tab.

---

## Chunk 3: Autoresearch Quality Loop

### Task 5: Score All 5 Dimensions

Run the mechanical scoring after Tasks 1-4 are complete.

**Scoring script (run after each iteration):**

```bash
#!/bin/bash
echo "=== SHOWCASE SCORE ==="

# 1. Dictionary (target: 5+ results)
D=$(curl -s -X POST http://localhost:8888/api/ldm/gamedata/dictionary-lookup \
  -H "Content-Type: application/json" -H "Cookie: session_token=admin_session" \
  -d '{"text":"장로 바론","threshold":0.3,"top_k":10}' | python3 -c "import sys,json; print(len(json.loads(sys.stdin.read()).get('results',[])))")
echo "Dictionary: $D results"

# 2. AI Summary (target: 100+ chars, English)
A=$(curl -s -X POST http://localhost:8888/api/ldm/gamedata/context/ai-summary \
  -H "Content-Type: application/json" -H "Cookie: session_token=admin_session" \
  -d '{"node_id":"r0","tag":"CharacterInfo","attributes":{"CharacterName":"장로 바론","Key":"CHAR_001","Level":"85","Job":"Sage"},"editable_attrs":["CharacterName"]}' | python3 -c "import sys,json; s=json.loads(sys.stdin.read()).get('summary',''); print(len(s))")
echo "AI Summary: $A chars"

# 3. Media (target: has_image=true)
M=$(curl -s -X POST http://localhost:8888/api/ldm/gamedata/context \
  -H "Content-Type: application/json" -H "Cookie: session_token=admin_session" \
  -d '{"node_id":"r0","tag":"CharacterInfo","attributes":{"UITextureName":"character_varon","VoicePath":"audio/elder_varon.wem"},"editable_attrs":["CharacterName"]}' | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); m=d.get('media',{}); print(f'img={m.get(\"has_image\")},audio={m.get(\"has_audio\")}')")
echo "Media: $M"

# 4. CrossRefs (target: fwd>0 AND bwd>0)
C=$(curl -s -X POST http://localhost:8888/api/ldm/gamedata/context \
  -H "Content-Type: application/json" -H "Cookie: session_token=admin_session" \
  -d '{"node_id":"r0","tag":"CharacterInfo","attributes":{"KnowledgeKey":"Knowledge_ElderVaron","FactionKey":"Faction_SageOrder"},"editable_attrs":["CharacterName"]}' | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); cr=d.get('cross_refs',{}); print(f'fwd={len(cr.get(\"forward\",[]))},bwd={len(cr.get(\"backward\",[]))}')")
echo "CrossRefs: $C"

# 5. Tab UI — visual (Playwright screenshot comparison)
echo "Tab UI: manual visual check via Playwright"
```

### Task 6: Iterate — Fix Weakest Dimension

After scoring, identify the lowest-scoring dimension and fix it. Repeat until composite >= 9/10.

**Iteration protocol:**
1. Run scoring script
2. Identify weakest dimension
3. Make ONE focused fix
4. Re-score
5. If improved → keep. If same/worse → revert
6. Repeat

---

## Chunk 4: Final Verification & Demo Script

### Task 7: Playwright Visual Verification

Take screenshots of every tab in every state:
- Properties tab with editable fields
- Dictionary tab with 5+ results
- Context tab with AI summary
- Media tab with character portrait

### Task 8: 60-Second Demo Script

Document the exact click sequence for the executive demo:
1. Open LocaNext → GameData browser
2. Expand StaticInfo → characterinfo → click showcase file
3. Click "Elder Varon" in the tree
4. Properties: show 15 attributes, cross-ref links glow blue
5. Dictionary tab: 5+ Korean→English translations appear with staggered animation
6. Context tab: AI generates 3-sentence summary about the character
7. Media tab: character portrait displays
8. Click a cross-ref link → navigates to knowledge entry
9. Repeat tabs — shows knowledge context + related entities
