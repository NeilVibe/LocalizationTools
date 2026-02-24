# QACompiler - Session Context

> Active work state. Updated each session.

---

## Current Focus

**NEW Item Datasheet** - Building a new item datasheet generator with 4-step pass and row-per-text structure.

## Status

- [x] Codebase exploration complete (6 agents, full analysis)
- [x] Plan document written ([WIP_NEW_ITEM_DATASHEET.md](WIP_NEW_ITEM_DATASHEET.md))
- [x] All decisions finalized with user
- [x] Preparation phase committed
- [ ] Plan Mode → implementation
- [ ] Testing
- [ ] GUI integration

## Key Technical Facts

1. **ItemInfo attributes**: `StrKey`, `ItemName`, `ItemDesc`, `KnowledgeKey`
2. **KnowledgeInfo attributes**: `StrKey`, `Name`, `Desc`
3. **Link**: `ItemInfo.KnowledgeKey` value == `KnowledgeInfo.StrKey`
4. **Current loader** only maps `StrKey → Desc` — new loader needed for `StrKey → (Name, Desc, source_file)`
5. **Not all items have KnowledgeKey** → output blocks of 2, 3, or 4 rows
6. **Empty knowledge texts skipped** — only non-empty rows output
7. **StringID**: EXPORT index technique, different source_file for item vs knowledge rows

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `generators/newitem.py` | CREATE | New item datasheet generator |
| `generators/__init__.py` | MODIFY | Register new generator |
| `config.py` | MODIFY | Add "NewItem" to CATEGORIES |
| `gui/app.py` | NONE | Auto-detects from CATEGORIES |

## Output Structure

```
NewItemData_Map_All/
├── ExecuteFiles/          ← /create item commands
└── NewItem_LQA_*.xlsx     ← one per language
```

## Excel Columns (8 total)

DataType | Filename | SourceText (KR) | Translation | STATUS | COMMENT | SCREENSHOT | STRINGID

---

*Last updated: 2026-02-24*
