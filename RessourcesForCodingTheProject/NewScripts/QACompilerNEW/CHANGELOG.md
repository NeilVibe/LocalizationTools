# QACompiler Changelog

## v2.6 — 2026-03-26

### Phantom Issue Detection + Log Security

**Commits:** `7dc4b4b3`, `66d15c92`

- **Phantom issue rule:** ISSUE without comment = NO ISSUE. Applied universally:
  - `tracker/masterfile_pending.py` — masterfile pending counts
  - `core/tracker_update.py` — QA file overall stats
  - `core/processing.py` — compilation pipeline + row visibility
- **Named column detection:** Comment columns found by header name (`COMMENT_`, `MEMO_`, `SCREENSHOT_` per user), not positional offset. Prevents cross-tester column bleeding.
- **Safe fallback:** If no comment columns exist in the sheet, ISSUE is treated as real (not phantom).
- **Result:** Pending count dropped from 3,728 → 1,452 (61% reduction, 2,276 phantom issues eliminated).
- **Log security:** All `*_DEBUG.log` files now write to `logs/` subfolder (gitignored). Prevents confidential tester names and game content from being committed to public repo.

---

## v2.5 — 2026-02-25

### StringID Order Fix

**Commit:** `24273d08`

Pre-resolve StringIDs before sorting in 4 generators. Previously, StringID resolution happened after sorting, which could produce out-of-order IDs in the output. Now all generators resolve StringIDs first, then sort by the resolved value.

**Affected generators:** item, newitem, knowledge, itemknowledgecluster

---

## v2.4 — 2026-02-25

### Unified StringID + COMMAND Column + Crash Fixes

**Commit:** `00b57343`

- **Unified StringID system** across all generators via `StringIdConsumer`
- **COMMAND column** added to Quest generator (faction unlock commands)
- Multiple crash fixes for edge cases in XML parsing

### Consumer + Dedup + StringID System

**Commit:** `ad54dda0`, `fed29b2b`

Centralized StringID management across all 12 generators:

**Consumer Rules:**
- `eng_tbl` calls → `consumer=None` (display-only, no StringID consumption)
- `lang_tbl` calls → `consumer=consumer` (target language, consumes StringID)
- Repeated translations (same group/gimmick name) → cache result or `consumer=None`
- One fresh `StringIdConsumer` per language per generator write pass

### NewCharacter Generator

**File:** `generators/newcharacter.py`

New generator for character data in the "NewCharacter" pipeline:
- Row-per-text layout: 5 rows per character (name + knowledge × 2 passes)
- 8 columns output
- QA folder naming: `Username_NewCharacter`
- Master file: `Master_NewCharacter.xlsx`

### NewRegion Generator

**File:** `generators/newregion.py`

Complete rewrite based on `region.py` with DisplayName support:
- Imports parsing/styling/writing from `region.py` (no code duplication)
- Adds `build_displayname_lookup()`: RegionInfo.KnowledgeKey → DisplayName
- Per FactionNode: Name + DisplayName (if different) + Desc (3 rows max)
- QA folder naming: `Username_NewRegion`
- Master file: `Master_NewRegion.xlsx`

### RewardKnowledgeKey Support

`_find_knowledge_key()` now checks both `KnowledgeKey` and `RewardKnowledgeKey` attributes. Applied across 5 files: item.py, newitem.py, itemknowledgecluster.py, newcharacter.py, newregion.py.

### Region Knowledge Lookup Fix

`build_knowledge_name_lookup()` now returns `(Name, Desc)` tuples instead of just Name. FactionNode has no Desc attribute — Desc comes from linked KnowledgeInfo via KnowledgeKey. DisplayName comes from RegionInfo (linked via same KnowledgeKey).

---

## v2.3 — 2026-02-24

### NewItem Pipeline Integration

**File:** `generators/newitem.py`

New generator for the "NewItem" pipeline:
- Standard matching: StringID col 8, Translation col 4
- QA folder naming: `Username_NewItem` (case-sensitive, no underscore in "NewItem")
- Master file: `Master_NewItem.xlsx` (separate from Item, own worker group)
- Pipeline config added to: `config.py`, `generators/__init__.py`, `main.py`, `populate_new.py`, `coverage.py`

### ItemKnowledgeCluster Generator

**File:** `generators/itemknowledgecluster.py`

Mega-sheet generator that clusters items with their knowledge entries for cross-reference review.

---

## v2.2 — Earlier

### Core Generators (8 original)

| # | Category | Generator | Description |
|---|----------|-----------|-------------|
| 1 | Quest | `quest.py` | Main/Faction/Daily/Challenge/Minigame quests |
| 2 | Knowledge | `knowledge.py` | Knowledge entries with hierarchical groups |
| 3 | Item | `item.py` | Items with descriptions and group organization |
| 4 | Region | `region.py` | Faction/Region exploration data |
| 5 | Character | `character.py` | NPC/Monster character info |
| 6 | Skill | `skill.py` | Player skills with knowledge linking |
| 7 | Help | `help.py` | GameAdvice/Help system entries |
| 8 | Gimmick | `gimmick.py` | Interactive gimmick objects |

Plus Script generator (`script.py`) handling both Sequencer and Dialog categories, and Contents (manual, no generator).
