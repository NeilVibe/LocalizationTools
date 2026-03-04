# KnowledgeData2 Dedup — Surgical Secondary Duplicate Removal

## Problem

When a generator resolves knowledge data through **two passes**:
- **Pass 1 (Primary):** Direct `KnowledgeKey`/`RewardKnowledgeKey` attribute lookup → `KnowledgeData` rows
- **Pass 2 (Secondary):** Identical name match (e.g., ItemName == KnowledgeInfo.Name) → `KnowledgeData2` rows

...the **same KnowledgeInfo entry** can be found by BOTH passes, producing **pure duplicate rows** where SourceText, Translation, AND StringID are all identical between a primary-type row and a KnowledgeData2 row within the same entity cluster.

## Solution: Surgical Per-Cluster Dedup

**After pre-resolving translations but before writing to Excel**, compare each `KnowledgeData2` row against all non-`KnowledgeData2` rows in the **same cluster** (same entity). If a KnowledgeData2 row has an exact triple match `(SourceText, Translation, StringID)` with ANY primary-type row, **drop the KnowledgeData2 row**.

### Rules

1. **Scope: Per-cluster only.** Never compare across different entities/clusters. Each entity (ItemInfo, CharacterInfo) is an isolated dedup scope.

2. **Direction: KnowledgeData2 loses.** Only KnowledgeData2 rows are candidates for removal. Primary rows (ItemData, CharacterData, KnowledgeData, ChildKnowledgeData, InspectData, InspectKnowledgeData) are NEVER removed.

3. **Match criteria: Triple match required.** All three must be identical:
   - `SourceText (KR)` — the Korean source text
   - `Translation` — the resolved translation for the current language
   - `STRINGID` — the resolved StringID

   If even ONE differs, the KnowledgeData2 row is kept.

4. **Timing: Post-resolution, pre-write.** Dedup happens AFTER `resolve_translation()` pre-resolve (so we have actual Translation + StringID values), but BEFORE writing rows to Excel.

## Affected Generators

| Generator | Has KnowledgeData2? | Dedup Applied? | Reason |
|-----------|---------------------|----------------|--------|
| `item.py` | Yes | **YES** | Pass 2 name match can duplicate Pass 1 KnowledgeKey data |
| `character.py` | Yes | **YES** | Same — Pass 2 name match can duplicate Pass 1 |
| `skill.py` | Yes | **NO (EXCEPTION)** | Skills have location-dependent placement (UIPositionXY tree ordering). Removing data risks losing test coverage at specific tree positions. |
| `region.py` | No (uses DisplayName instead) | N/A | No KnowledgeData2 type exists |
| `itemknowledgecluster.py` | Uses `KnowledgeMatch-Exact` (different name) | N/A | Already has its own within-cluster dedup by `kor_text` |

### Skill Exception Rationale

Skill rows are ordered by `UIPositionXY` within SkillTreeInfo groups. A skill appearing in Tree A at position (640, 30) may have KnowledgeData2 that looks identical to its KnowledgeData — but removing it could lose test coverage for that specific tree position. Since skills have **location-dependent placement** and no safe way to determine which duplicate is "safe" to remove without understanding the tree context, we keep all rows for safety.

## Cluster Definition (Per Generator)

### item.py — Cluster = One ItemInfo

```
Per ItemInfo (identified by StrKey):
  1. ItemData              — item_name_kor       [PRIMARY]
  2. ItemData              — item_desc_kor       [PRIMARY]
  2b. ChildKnowledgeData   — inline children     [PRIMARY - Pass 0]
  3. KnowledgeData         — knowledge_name_kor  [PRIMARY - Pass 1]
  4. KnowledgeData         — knowledge_desc_kor  [PRIMARY - Pass 1]
  5. KnowledgeData2        — knowledge2_name_kor [SECONDARY - Pass 2] ← DEDUP CANDIDATE
  6. KnowledgeData2        — knowledge2_desc_kor [SECONDARY - Pass 2] ← DEDUP CANDIDATE
  7+. InspectData           — inspect descriptions [PRIMARY]
  7b+. InspectKnowledgeData — linked knowledge    [PRIMARY]
```

**Dedup logic:** For rows 5 and 6, check if `(source_text, translation, stringid)` matches ANY of rows 1–4 or 7+. If yes, drop the KnowledgeData2 row.

### character.py — Cluster = One CharacterInfo

```
Per CharacterInfo (identified by StrKey):
  1. CharacterData         — char_name_kor       [PRIMARY]
  1b. ChildKnowledgeData   — inline children     [PRIMARY - Pass 0]
  2. KnowledgeData         — knowledge_name_kor  [PRIMARY - Pass 1]
  3. KnowledgeData         — knowledge_desc_kor  [PRIMARY - Pass 1]
  4. KnowledgeData2        — knowledge2_name_kor [SECONDARY - Pass 2] ← DEDUP CANDIDATE
  5. KnowledgeData2        — knowledge2_desc_kor [SECONDARY - Pass 2] ← DEDUP CANDIDATE
```

**Dedup logic:** For rows 4 and 5, check if `(source_text, translation, stringid)` matches ANY of rows 1–3. If yes, drop the KnowledgeData2 row.

## Implementation

### Where in the code

Both `item.py` and `character.py` use a **pre-resolve phase** that builds a `pre` dict mapping `(strkey, field_name)` → `(translation, stringid)`. The dedup filter runs AFTER this pre-resolve, BEFORE the Excel write loop.

### Algorithm (pseudocode)

```python
# After pre-resolve, before write loop:
for each entity in cluster:
    # Collect primary triples: (kor_text, translation, stringid)
    primary_triples = set()
    for each non-KnowledgeData2 field in entity:
        kor = entity.field_kor
        trans, sid = pre[(entity.strkey, field_name)]
        if kor:
            primary_triples.add((kor, trans, sid))

    # Check KnowledgeData2 fields against primary triples
    for each KnowledgeData2 field in entity:
        kor = entity.field_kor
        trans, sid = pre[(entity.strkey, field_name)]
        if (kor, trans, sid) in primary_triples:
            # Pure duplicate — mark for skip
            entity.field_kor = ""  # or flag to skip during write
```

### Logging

When a KnowledgeData2 row is deduped, log at DEBUG level:
```
KnowledgeData2 dedup: '{kor_text[:40]}...' in {strkey} — matches primary data
```

At the end, log a summary at INFO level:
```
KnowledgeData2 dedup: removed {N} duplicate rows across {M} entities
```

---

*Created: 2026-03-05*
