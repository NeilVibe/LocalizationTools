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

## Implementation Plan (FINALIZED)

### Phase 1: Layout Foundation
1. Add resizable right column to VirtualGrid (~300px default)
2. Excel-style column resize handles (hover to resize any column)
3. Collapsible TM/QA panel (show/hide button)
4. Basic TM matches display

### Phase 2: Click Behaviors
1. **Single Click** → Select row, load TM/QA in right panel
2. **Double Click** → Activate inline editing in Target cell
3. **Ctrl+Click** → Open Edit Modal (fallback)
4. Auto-save on blur

### Phase 3: Keyboard Navigation
1. Tab → Next row
2. Enter → Confirm edit, move to next
3. Escape → Cancel edit
4. Arrow keys → Navigate rows

### Phase 4: TM Metadata
1. Add fields to TM model: `source_type`, `created_by`, `source_project`, `created_at`
2. Track creation source (Manual, Review, Auto-TM, Import)
3. Display metadata under each TM match in panel

### Phase 5: QA Integration
1. Show QA issues in right panel (below TM)
2. LanguageTool grammar checks
3. Built-in checks (numbers, tags, consistency)
4. Click issue → highlight error in Target cell

### Phase 6: Polish & Cleanup
1. Performance optimization (prefetch TM for nearby rows)
2. Remove Edit Modal entirely (if inline editing satisfactory)
3. Mobile/responsive behavior

---

## Decisions Made

| Question | Decision |
|----------|----------|
| **Drop Modal?** | Keep as Ctrl+Click fallback during development |
| **Single Click** | Load TM/QA info for selected row |
| **Double Click** | Activate inline editing mode |
| **TM Panel** | Resizable (user draggable) |
| **Grid Columns** | Resizable (Excel-style hover to resize) |
| **Grammar Provider** | Stick with LanguageTool (31 languages) |
| **When Load TM?** | On single-click (row select) |

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

## Status

**PREPARATION PHASE COMPLETE** - Ready to begin Phase 1 implementation.

### Next Actions
1. Begin Phase 1: Add resizable right column to VirtualGrid
2. Implement Excel-style column resize handles
3. Create TM/QA panel component

---

*This is a MAJOR feature - will significantly improve translation workflow*
