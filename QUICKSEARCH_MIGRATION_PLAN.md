# QuickSearch0818 Migration Plan - App #2

**Date:** 2025-11-12
**Source File:** `RessourcesForCodingTheProject/SECONDARY PYTHON SCRIPTS/QuickSearch0818.py`
**Size:** 3,426 lines (153 KB)
**Target:** Migrate to REST API + Svelte frontend

---

## 📋 Migration Strategy (Following XLSTransfer Pattern)

### Pattern from XLSTransfer (App #1):
1. ✅ Backend: Create async API in `server/api/quicksearch_async.py`
2. ✅ Use BaseTool pattern for consistency
3. ✅ Frontend: Create UI in `locaNext/src/routes/quicksearch/+page.svelte`
4. ✅ Each function → API endpoint
5. ✅ Database tracking for all operations
6. ✅ WebSocket progress updates

**This same pattern works perfectly for QuickSearch!**

---

## 🎯 Core Features to Migrate

### Main Functions (7 core operations):

#### 1. **Create Dictionary** ⭐ PRIMARY
- **Original:** `create_dictionary_dialog()` + `process_data()`
- **Input:** XML/TXT/TSV files or folder
- **Process:** Parse files, extract Korean-Translation pairs, create dictionary
- **Output:** `.pkl` dictionary file (game/language structure)
- **API Endpoint:** `/api/v2/quicksearch/create-dictionary`
- **Time:** ~2-3 hours

#### 2. **Load Dictionary**
- **Original:** `load_dictionary_dialog()`
- **Input:** Game + Language selection
- **Process:** Load `.pkl` dictionary into memory
- **Output:** Dictionary loaded, ready for search
- **API Endpoint:** `/api/v2/quicksearch/load-dictionary`
- **Time:** ~30 min

#### 3. **Search (One-Line)** ⭐ PRIMARY
- **Original:** `search_one_line()`
- **Input:** Query string, match type (contains/exact), limit
- **Process:** Search loaded dictionary
- **Output:** Search results (Korean, Translation, StringID)
- **API Endpoint:** `/api/v2/quicksearch/search`
- **Time:** ~1 hour

#### 4. **Search (Multi-Line)**
- **Original:** `search_multi_line()`
- **Input:** Multi-line query
- **Process:** Search each line separately
- **Output:** Aggregated results
- **API Endpoint:** `/api/v2/quicksearch/search-multiline`
- **Time:** ~30 min

#### 5. **Load Reference Dictionary**
- **Original:** `set_reference_dialog()`
- **Input:** Game + Language for reference
- **Process:** Load second dictionary as reference
- **Output:** Reference dictionary available
- **API Endpoint:** `/api/v2/quicksearch/set-reference`
- **Time:** ~30 min

#### 6. **Toggle Reference**
- **Original:** `toggle_reference()`
- **Input:** Enable/Disable flag
- **Process:** Show/hide reference column
- **Output:** Reference visibility toggled
- **API Endpoint:** `/api/v2/quicksearch/toggle-reference`
- **Time:** ~15 min

#### 7. **List Available Dictionaries**
- **Original:** `DictionaryManager.load_available_dictionaries()`
- **Input:** None
- **Process:** Scan dictionary folder for available dictionaries
- **Output:** List of game/language combinations
- **API Endpoint:** `/api/v2/quicksearch/list-dictionaries`
- **Time:** ~30 min

---

## 🏗️ Backend Architecture

### File Structure (Following XLSTransfer Pattern):

```
server/
├── api/
│   ├── quicksearch_async.py       ← NEW (main API endpoints)
│   └── base_tool_api.py            ← REUSE (base class)
├── tools/
│   └── quicksearch/
│       ├── __init__.py
│       ├── dictionary_creator.py   ← Create dictionaries
│       ├── dictionary_loader.py    ← Load dictionaries
│       ├── searcher.py             ← Search operations
│       └── xml_parser.py           ← Parse XML files
└── data/
    └── quicksearch_dictionaries/   ← Store .pkl files
        ├── BDO/
        │   ├── EN/dictionary.pkl
        │   ├── FR/dictionary.pkl
        │   └── ...
        ├── BDM/
        └── ...
```

### API Endpoints (7 total):

1. `POST /api/v2/quicksearch/create-dictionary`
   - Body: `{game, language, files, source_type}`
   - Response: `{success, dictionary_path, pairs_count}`

2. `POST /api/v2/quicksearch/load-dictionary`
   - Body: `{game, language}`
   - Response: `{success, dictionary_loaded, pairs_count}`

3. `POST /api/v2/quicksearch/search`
   - Body: `{query, match_type, limit, start_index}`
   - Response: `{results: [{korean, translation, string_id}], total_count}`

4. `POST /api/v2/quicksearch/search-multiline`
   - Body: `{queries: [], match_type, limit}`
   - Response: `{results: [{line, matches}]}`

5. `POST /api/v2/quicksearch/set-reference`
   - Body: `{game, language}`
   - Response: `{success, reference_loaded}`

6. `POST /api/v2/quicksearch/toggle-reference`
   - Body: `{enabled}`
   - Response: `{success, reference_enabled}`

7. `GET /api/v2/quicksearch/list-dictionaries`
   - Response: `{dictionaries: [{game, language, creation_date, pairs_count}]}`

---

## 🎨 Frontend Architecture

### File Structure (Following XLSTransfer Pattern):

```
locaNext/src/routes/
└── quicksearch/
    ├── +page.svelte                ← Main QuickSearch page
    └── components/
        ├── DictionaryCreator.svelte
        ├── DictionaryLoader.svelte
        ├── SearchBox.svelte
        ├── ResultsTable.svelte
        └── ReferencePanel.svelte
```

### UI Layout (Similar to XLSTransfer):

```
┌─────────────────────────────────────────┐
│  QuickSearch - Dictionary Search Tool   │
├─────────────────────────────────────────┤
│  [Create Dictionary] [Load Dictionary]  │
│  [Set Reference] [Reference: OFF]       │
├─────────────────────────────────────────┤
│  Current: BDO-EN │ Reference: BDM-FR    │
├─────────────────────────────────────────┤
│  Search: [_________________] [Search]   │
│  Match Type: ○ Contains ● Exact Match   │
├─────────────────────────────────────────┤
│  Results (showing 50 of 1234):          │
│  ┌───────┬──────────┬───────────────┐  │
│  │Korean │Translation│Reference      │  │
│  ├───────┼──────────┼───────────────┤  │
│  │안녕    │Hello     │Bonjour        │  │
│  │...    │...       │...            │  │
│  └───────┴──────────┴───────────────┘  │
│  [Load More Results]                    │
└─────────────────────────────────────────┘
```

---

## 📊 Implementation Phases

### Phase 1: Backend Core (4 hours)
- [x] Analyze QuickSearch0818.py features
- [ ] Create `server/api/quicksearch_async.py` with BaseTool
- [ ] Create `server/tools/quicksearch/` modules
- [ ] Implement dictionary creator (XML/TXT parsing)
- [ ] Implement dictionary loader
- [ ] Implement search function
- [ ] Test all endpoints with Postman/curl

### Phase 2: Frontend UI (3 hours)
- [ ] Create `locaNext/src/routes/quicksearch/+page.svelte`
- [ ] Create Dictionary Creator modal
- [ ] Create Dictionary Loader modal
- [ ] Create Search interface
- [ ] Create Results table component
- [ ] Add reference panel support

### Phase 3: Integration (1 hour)
- [ ] Connect frontend to backend APIs
- [ ] Add WebSocket progress updates for dictionary creation
- [ ] Add database tracking for operations
- [ ] Test end-to-end flow

### Phase 4: Testing & Polish (1 hour)
- [ ] Test with real XML/TXT files
- [ ] Test search with large dictionaries
- [ ] Test multi-line search
- [ ] Test reference dictionary feature
- [ ] Add loading states and error handling

**Total Estimated Time: ~9 hours**

---

## 🔄 Dictionary Format

### Original Format (Pickle):
```python
{
    'split_dict': {
        'token1': [(korean, translation, string_id), ...],
        'token2': [...],
    },
    'whole_dict': {
        'full_text': [(korean, translation, string_id), ...],
    },
    'string_keys': {
        'string_id': (korean, translation),
    },
    'creation_date': '11/12 14:30'
}
```

### Backend Storage:
- Keep `.pkl` format for compatibility
- Store in `server/data/quicksearch_dictionaries/GAME/LANGUAGE/`
- Keep same structure for easy migration

---

## 🎯 Games & Languages Support

**Games:** BDO, BDM, BDC, CD (4 games)
**Languages:** DE, IT, PL, EN, ES, SP, FR, ID, JP, PT, RU, TR, TH, TW, CH (15 languages)

**Total Combinations:** 4 × 15 = 60 possible dictionaries

---

## 📝 Key Technical Details

### XML Parsing:
- Use `lxml` library (already in dependencies)
- Extract `<locstr>` tags with Korean/Translation pairs
- Handle nested XML structure

### Text File Parsing:
- Tab-delimited format: `Korean\tTranslation\tStringID`
- TSV support

### Search Algorithm:
- **Contains:** Use Aho-Corasick algorithm (fast multi-pattern matching)
- **Exact Match:** Direct dictionary lookup
- **Tokenization:** Split text by `\n` or `\\n`

### Threading:
- Dictionary creation runs in background
- Progress updates via WebSocket
- Non-blocking search operations

---

## 🚀 Success Criteria

1. ✅ Can create dictionaries from XML/TXT files
2. ✅ Can load existing dictionaries
3. ✅ Can search Korean → Translation
4. ✅ Can search Translation → Korean
5. ✅ Multi-line search works
6. ✅ Reference dictionary displays correctly
7. ✅ All operations tracked in database
8. ✅ Progress updates work
9. ✅ No data loss (all features from original)
10. ✅ Admin dashboard shows QuickSearch stats

---

## 📋 Migration Checklist

### Backend:
- [ ] Create API file structure
- [ ] Implement BaseTool subclass
- [ ] Create dictionary creator
- [ ] Create dictionary loader
- [ ] Create search function
- [ ] Add database tracking
- [ ] Add WebSocket support
- [ ] Test all endpoints

### Frontend:
- [ ] Create main page
- [ ] Create dictionary creator UI
- [ ] Create dictionary loader UI
- [ ] Create search interface
- [ ] Create results table
- [ ] Add reference support
- [ ] Add progress indicators
- [ ] Add error handling

### Testing:
- [ ] Test dictionary creation from XML
- [ ] Test dictionary creation from TXT
- [ ] Test dictionary creation from folder
- [ ] Test search (contains)
- [ ] Test search (exact match)
- [ ] Test multi-line search
- [ ] Test reference dictionary
- [ ] Test with large files (1000+ entries)
- [ ] Test concurrent operations

### Documentation:
- [ ] Update roadmap with completion
- [ ] Document API endpoints
- [ ] Add to admin dashboard menu
- [ ] Update README

---

## 🎉 Expected Result

**After Migration:**
- QuickSearch fully functional in web app
- Same features as original desktop app
- Accessible from browser
- Real-time progress updates
- Operation tracking in admin dashboard
- Multi-user support
- Cloud-ready architecture

**User Experience:**
Same workflow as original, but in modern web interface!
