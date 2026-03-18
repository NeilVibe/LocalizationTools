# v3.4 GameData Showcase — Next Session Plan (v3)

> **For agentic workers:** Use full power stack: GSD + Ruflo + Ralph + Autoresearch + Viking + UI/UX Pro skills

**Current Score:** 9.5/10 (backend solid, frontend needs browser cache fix + more WOW)

---

## STARTUP CHECKLIST (MUST DO EVERY SESSION)

```bash
# 1. Check servers
./scripts/check_servers.sh

# 2. Rebuild gamedata index (in-memory, lost on restart)
curl -s -X POST http://localhost:8888/api/ldm/gamedata/index/build \
  -H "Content-Type: application/json" \
  -H "Cookie: session_token=admin_session" \
  -d '{"path":"StaticInfo"}'
# Expected: entity_count=20

# 3. Verify image serving (no auth needed)
curl -s -o /dev/null -w "HTTP %{http_code}, %{size_download} bytes" \
  http://localhost:8888/api/ldm/mapdata/thumbnail/character_varon
# Expected: HTTP 200, ~397000 bytes

# 4. Verify AI summary
curl -s -X POST http://localhost:8888/api/ldm/gamedata/context/ai-summary \
  -H "Content-Type: application/json" -H "Cookie: session_token=admin_session" \
  -d '{"node_id":"test","tag":"CharacterInfo","attributes":{"CharacterName":"장로 바론"},"editable_attrs":["CharacterName"]}' \
  | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); print(f'available={d[\"available\"]}, len={len(d[\"summary\"])}')"
# Expected: available=True, len>50

# 5. Open browser with cache bypass
# User: press Ctrl+Shift+R in browser to force reload
```

## KNOWN BUGS TO FIX

### Bug 1: Image not visible (browser cache)
**Symptom:** Old PIL placeholder shows instead of new Gemini portrait
**Root cause:** Browser caches the old image at same URL
**Fix options:**
- A) Add cache-busting query param: `thumbnail_url + '?v=' + Date.now()`
- B) User does Ctrl+Shift+R (hard refresh)
- C) Set `Cache-Control: no-cache` header on thumbnail endpoint

### Bug 2: AI Context not generating on click
**Symptom:** Context tab shows "요약을 생성하려면 클릭하세요" instead of auto-generating
**Root cause:** The $effect auto-trigger only fires when activeTab === 'context' AND node changes. If user clicks Context tab AFTER node is already selected, it may not trigger.
**Fix:** Ensure fetchAISummary() is called on tab switch regardless of aiNodeId check

### Bug 3: Index lost on restart
**Symptom:** Dictionary returns 0 results, CrossRefs return 0
**Root cause:** Index is in-memory singleton, lost on Python process restart
**Fix:** Auto-build index on server startup (add to lifespan function in main.py)

---

## REMAINING TASKS

### P0: Fix bugs above (30 min)
- Cache-busting on thumbnail URLs
- Auto-trigger AI on Context tab click
- Auto-build index on startup

### P1: More WOW Visual Polish (2 hours)
Use UI/UX skills chain: bolder → polish → critique → colorize → delight
- Landing page conic gradient border rotation (6s)
- Hover expansion on cards
- Custom animated cursor (optional)
- More staggered animations

### P2: Nano-banana Item/Skill Icons (1 hour)
Current item/skill/region icons are still PIL placeholders (9-19KB)
Generate with Gemini: weapon icons, skill effect icons, region landscapes

### P3: Audio Generation (research needed)
No TTS available without API keys
- fal.ai CSM-1B: needs FAL_KEY
- ElevenLabs: needs API key
- Browser SpeechSynthesis: available but low quality
Decision: skip audio for v3.4 showcase, defer to v3.5

### P4: Demo Script (30 min)
60-second narrated click sequence:
1. Open Game Data → expand characterinfo
2. Click Elder Varon → Media tab shows portrait (WOW!)
3. Click Context tab → Korean AI backstory loads
4. Click Dictionary tab → 5 matches with scores
5. Click Info tab → grouped attributes with cross-ref links
6. Click KnowledgeKey link → navigates to knowledge entry
7. Right-click a node → context menu appears
8. Double-click an attribute → edit modal opens
9. Click another character (Kira) → different portrait + different AI context

---

## POWER STACK USAGE

| Tool | How to Use |
|------|-----------|
| **Ruflo** | `mcp__ruflo__hive-mind_init` → `hive-mind_spawn(count=8)` → assign tasks → consensus validation |
| **Ralph** | `/ralph-loop "improve showcase" --max-iterations 10 --completion-promise "WOW 9.5+"` |
| **Autoresearch** | Score 5 dimensions → fix weakest → rescore → repeat |
| **Viking** | `viking_search("gamedata showcase patterns")` before any research |
| **UI/UX Skills** | critique → clarify → colorize → animate → polish → audit → harden |
| **Nano-banana** | `python3 ~/.claude/skills/nano-banana/scripts/generate_image.py "prompt" output.png` |
| **Stitch MCP** | `mcp__stitch__generate_screen_from_text` for UI design variants |
