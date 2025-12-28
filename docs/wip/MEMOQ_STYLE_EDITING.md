# MemoQ-Style Non-Modal Editing

**Created:** 2025-12-28 | **Priority:** P1 | **Status:** PLANNING

---

## Vision

Transform LDM from modal-based editing to **inline non-modal editing** like memoQ. This is a major UX upgrade that enables faster, more fluid translation workflows.

---

## Current vs Proposed

| Aspect | Current (Modal) | Proposed (Non-Modal) |
|--------|-----------------|----------------------|
| **Edit** | Double-click opens modal | Click row, edit inline |
| **TM/QA** | Separate panels/modals | Fixed column on right |
| **Navigation** | Close modal, scroll, reopen | Arrow keys, seamless |
| **Context** | Limited (one row at a time) | Full (see surrounding rows) |
| **Speed** | Slow (modal open/close) | Fast (instant switching) |

---

## Layout Design

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  LDM - Project Name / Folder / File.xlf                              [Menu] │
├─────────────────────────────────────────────────────────────────────────────┤
│ # │ Source                  │ Target (editable)      │ TM/QA Panel (fixed) │
├───┼─────────────────────────┼────────────────────────┼─────────────────────┤
│ 1 │ Hello world             │ Bonjour le monde       │ ┌─────────────────┐ │
│   │                         │                        │ │ TM MATCHES      │ │
├───┼─────────────────────────┼────────────────────────┤ │                 │ │
│ 2 │ Click here to continue  │ [EDITING: cursor here] │ │ 100% Bonjour... │ │
│   │ with the process        │ Cliquez ici pour...    │ │  98% Salut...   │ │
│   │                         │ _                      │ │  85% Bienvenue  │ │
├───┼─────────────────────────┼────────────────────────┤ │                 │ │
│ 3 │ Save changes            │ Enregistrer            │ ├─────────────────┤ │
│   │                         │                        │ │ QA ISSUES       │ │
├───┼─────────────────────────┼────────────────────────┤ │                 │ │
│ 4 │ Cancel                  │ Annuler                │ │ 1 grammar issue │ │
│   │                         │                        │ │ [LanguageTool]  │ │
└───┴─────────────────────────┴────────────────────────┴─┴─────────────────┴─┘
```

---

## Feature Breakdown

### 1. Inline Cell Editing

- Click any Target cell to start editing
- Auto-expand cell height as content grows (already works!)
- Tab/Enter to move to next row
- Escape to cancel changes
- Auto-save on blur

### 2. Fixed TM/QA Column (Right Side)

**Width:** ~300px fixed, collapsible

**Contains:**
```
┌─────────────────────────────────┐
│ TM MATCHES                      │
├─────────────────────────────────┤
│ 100% │ Bonjour le monde         │
│      │ Source: Project A        │ ← metadata
│      │ Created: 2024-01-15      │
│      │ By: John (Review)        │
├─────────────────────────────────┤
│  98% │ Salut le monde           │
│      │ Source: Auto-TM          │ ← auto-generated
│      │ Created: 2024-02-20      │
├─────────────────────────────────┤
│ QA ISSUES                       │
├─────────────────────────────────┤
│ [!] Missing period              │
│     LanguageTool: punctuation   │
│                                 │
│ [!] Number mismatch             │
│     Built-in: consistency       │
└─────────────────────────────────┘
```

### 3. TM Entry Metadata

Each TM match shows:
- **Match percentage** (100%, 98%, fuzzy)
- **Source project/file** (where it came from)
- **Creation type:**
  - `Manual` - User entered
  - `Review` - From confirmed translation
  - `Auto-TM` - LocaNext auto-generated
  - `Import` - From TMX import
- **Created by** (username)
- **Created date**
- **Last modified** (if different)

### 4. QA Integration

**QA Panel shows:**
- Built-in checks (numbers, tags, consistency)
- LanguageTool grammar/spelling
- Click issue → highlights in Target cell

**Grammar Providers:**
- LanguageTool (current, 30+ languages)
- Potential alternatives (see Research section)

---

## Settings (Optional Toggle)

```
Settings > General > Editing Mode
├── Modal (Classic) - Edit in popup modal
│   └── Spacious, focused, current default
│
└── Inline (MemoQ-style) - Edit directly in grid
    ├── TM/QA panel on right (fixed)
    ├── Faster workflow
    └── See surrounding context
```

**Question:** Should we make this a setting or just go full non-modal?

---

## Technical Feasibility

### Easy (Already Have)
- Cell auto-expand on content
- VirtualGrid is stable
- TM matching API works
- QA API works
- Click-to-edit patterns exist

### Medium Effort
- Fixed right column layout (CSS flex/grid)
- TM metadata display component
- Keyboard navigation (Tab, Enter, Arrow)

### Needs Design
- How to handle very long content?
- Mobile/narrow screen behavior?
- TM panel collapse/expand?

---

## Implementation Plan

### Phase 1: Layout Foundation
1. Add fixed right column to VirtualGrid
2. Make it collapsible (show/hide button)
3. Basic TM matches display

### Phase 2: Inline Editing
1. Click-to-edit Target cells
2. Auto-save on blur
3. Keyboard navigation (Tab, Enter, Escape)

### Phase 3: TM Metadata
1. Add metadata fields to TM entry model
2. Track creation source (manual, review, auto, import)
3. Display in TM panel

### Phase 4: QA Integration
1. Show QA issues in right panel
2. LanguageTool integration
3. Click issue → highlight in cell

### Phase 5: Polish
1. Settings toggle (optional)
2. Performance optimization
3. Mobile responsive

---

## Open Questions

1. **Drop Modal Completely?** User says ready to go full non-modal
2. **TM Panel Width?** 250px? 300px? User resizable?
3. **Grammar Provider?** Stick with LanguageTool or explore alternatives?
4. **When to Load TM?** On row select? Prefetch nearby rows?

---

## Grammar Checker Research (COMPLETED)

### Current: LanguageTool
- **Languages:** 31 languages (full support for EN, DE, FR, ES, NL)
- **RAM:** ~900MB (with lazy load optimization)
- **Type:** Java server, self-hosted
- **Pros:** Most mature, best multilingual support
- **Cons:** Heavy, requires server

### Alternative 1: Harper (Rust, Offline)
- **Languages:** English only (UK, US, CA, AU dialects)
- **RAM:** 1/50th of LanguageTool (~18MB)
- **Type:** Native Rust, runs locally, WebAssembly support
- **Pros:** Fastest, most private, tiny footprint
- **Cons:** English only (other languages "on horizon")
- **Source:** [GitHub - Automattic/harper](https://github.com/Automattic/harper)

### Alternative 2: Hugging Face GEC Models
- **T5-based:** [Unbabel/gec-t5_small](https://huggingface.co/Unbabel/gec-t5_small) - multilingual
- **mBART-based:** [MRNH/mbart-english-grammar-corrector](https://huggingface.co/MRNH/mbart-english-grammar-corrector)
- **Dataset:** [multilingual-gec](https://huggingface.co/datasets/juancavallotti/multilingual-gec) (EN, ES, FR, DE)
- **Research:** mBART-25 achieves results comparable to single-language solutions
- **Pros:** Can run locally, no server needed
- **Cons:** Need to load model (~500MB-2GB), inference time

### Recommendation

| Use Case | Best Choice |
|----------|-------------|
| **30+ languages** | LanguageTool (current) |
| **English-only, speed critical** | Harper |
| **Custom/offline, 4-7 languages** | Hugging Face T5/mBART |
| **Korean/CJK focus** | LanguageTool + custom rules |

**Verdict:** Stick with **LanguageTool** for now (best multilingual). Consider Harper for English-only projects in future. Hugging Face models need more research for production readiness.

---

## Next Actions

1. Document this feature request in Roadmap.md
2. Create prototype of fixed right column
3. Test inline editing with current VirtualGrid
4. Decide: Setting toggle or full non-modal?

---

*This is a MAJOR feature - will significantly improve translation workflow*
