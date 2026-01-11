# Future Features (API-Dependent)

**Status:** Planned for when external API access is available
**Created:** 2025-12-17

---

## Overview

This folder contains documentation for features that **require external API access** (QWEN/Claude translation API). These features are fully documented and ready to implement once API access is available.

---

## Contents

### smart-translation/

Complete Smart Translation Pipeline from WebTranslatorNew:

| File | Description |
|------|-------------|
| `SMART_TRANSLATION_PIPELINE.md` | Full 2-stage pipeline with all source references |
| `WEBTRANSLATORNEW_REFERENCE.md` | How to navigate WebTranslatorNew source code |

### Features Included

1. **Cluster Preprocessing (Core Glossary)**
   - Generate embeddings for similar entry grouping
   - Build similarity graph (90% threshold)
   - Translate cluster representatives only

2. **Character-Based Phased Processing**
   - Process shortest entries first (2, 3, 4... 51+ chars)
   - Progressive glossary building
   - Better context for longer entries

3. **Multi-line Refinement**
   - Line-by-line translation with full context
   - Structure preservation

4. **Dynamic Glossary Auto-Creation**
   - Extract unique terms
   - Filter against existing glossaries
   - Translate only what's new

---

## Prerequisites

Before implementing these features, you need:

```
1. Translation API Access:
   - QWEN MT API (cost-effective for batch translation)
   - OR Claude API (higher quality)

2. API Key Configuration

3. Budget for API calls:
   - 10,000 entries ~= $5-50 depending on provider and text length
```

---

## What CAN Be Done Now (No API Required)

These features from the documentation do NOT require API access:

| Feature | Status | Location |
|---------|--------|----------|
| Data Preprocessing (duplicate filtering) | Can implement now | `DataPreprocessor` class |
| TM Matching (5-tier cascade) | Already exists | `tm_indexer.py` |
| Embedding generation (local QWEN model) | Already exists | Local model |
| FAISS index building | Already exists | `tm_indexer.py` |
| Clustering (without translation) | Can implement now | grouping only |

---

## When to Use These Docs

1. **When you get API access** - Follow the implementation checklist
2. **For reference** - Understanding how WebTranslatorNew works
3. **For planning** - Estimating costs before getting API

---

*These features are parked here until API access is available.*
*Documentation is complete and ready to use.*
