# NewScripts Master Roadmap

**Purpose**: Track development of individual standalone scripts and their migration to LocaNext platform

**Last Updated**: 2025-11-22

---

## 📊 Overview

This roadmap tracks:
1. **Standalone Scripts** - Individual Python scripts for ad-hoc localization tasks
2. **Script Status** - Active development, Complete, or Migrated to LocaNext
3. **Migration Path** - Which scripts have been integrated into LocaNext platform

---

## 🎯 Script Development Status

### ✅ Completed Scripts

#### WordCountMaster (V2.0)
**Status**: ✅ COMPLETE + MIGRATED TO LOCANEXT (2025-11-22)
**Location**: `NewScripts/WordCountMaster/`
**Purpose**: Track translation word count changes over time

**Features**:
- Compare TODAY's data vs. any past date
- Smart weekly/monthly categorization (7 days vs 30 days)
- Generate Excel reports with 4 sheets (2 active, 2 N/A)
- Track multiple languages (excluding Korean)
- History tracking in JSON file

**Files**:
- `wordcount_diff_master.py` (1015 lines) - Production script
- `wordcount_diff_master_v1_backup.py` - V1.0 backup
- Complete documentation (V2_COMPLETE.md, V2_DESIGN.md, V2_STATUS.md)

**Migration to LocaNext**:
- ✅ Backend API: `server/api/wordcount_async.py`
- ✅ Processor: `server/tools/wordcount/processor.py`
- ✅ Frontend: `locaNext/src/lib/components/apps/WordCountMaster.svelte`
- ✅ Registered as App #3 in LocaNext platform
- ✅ 5 API endpoints: health, process, history, download, clear

**Version History**:
- V1.0: Original with 6 sheets (Daily, Weekly, Monthly × Full/Detailed)
- V2.0: Simplified with 4 sheets (Weekly OR Monthly × Full/Detailed)

---

### 📋 Planned Scripts

> **Note**: Add new script projects here as they are requested by coworkers

#### Korean Similarity Checker
**Status**: 📋 Planned
**Priority**: Medium
**Estimated Time**: 3-4 hours

**Purpose**: Check semantic similarity between Korean text pairs using BERT

**Proposed Features**:
- Upload Excel with Korean text pairs
- Calculate similarity scores using KR-SBERT model
- Export results to Excel
- Batch processing support

**Migration Potential**: High - Good candidate for LocaNext App #4

---

#### TFM Full/Lite
**Status**: 📋 Planned
**Priority**: Low
**Estimated Time**: 4-6 hours

**Purpose**: Translation File Manager for various file formats

**Proposed Features**:
- Support multiple file formats (XML, TXT, TMX)
- Merge and split translation files
- Format validation and cleanup
- Batch operations

**Migration Potential**: Medium

---

#### TextSwapper
**Status**: 📋 Planned
**Priority**: Low
**Estimated Time**: 2-3 hours

**Purpose**: Swap text columns in Excel files

**Proposed Features**:
- Column swapping with preview
- Regex-based find/replace
- Multiple swap operations
- Undo support

**Migration Potential**: Low - Simple utility, may not need platform integration

---

## 🔄 Migration Pipeline to LocaNext

When a standalone script proves valuable, it can be migrated to the LocaNext platform following this pattern:

### Migration Checklist

**Analysis Phase** (30 min):
- [ ] Read and understand original script
- [ ] Identify core functionality
- [ ] Note any dependencies or external files
- [ ] Plan API structure

**Backend Development** (2-3 hours):
- [ ] Create API file: `server/api/{tool_name}_async.py`
- [ ] Use BaseToolAPI pattern
- [ ] Create processor module if needed: `server/tools/{tool_name}/`
- [ ] Register API in `server/main.py`
- [ ] Test endpoints with FastAPI /docs

**Frontend Development** (2-3 hours):
- [ ] Create Svelte component: `locaNext/src/lib/components/apps/{ToolName}.svelte`
- [ ] Use Carbon Design System components
- [ ] Add to navigation in `+layout.svelte`
- [ ] Add routing in `+page.svelte`
- [ ] Test UI functionality

**Documentation** (30 min):
- [ ] Update root `README.md` with tool description and API endpoints
- [ ] Update root `Roadmap.md` to mark completion
- [ ] Update this NewScripts roadmap with migration status

### Successfully Migrated Scripts

1. **WordCountMaster** (2025-11-22)
   - Standalone → LocaNext App #3
   - Full feature parity maintained
   - Enhanced with WebSocket progress tracking

---

## 📂 Folder Structure

```
NewScripts/
├── ROADMAP.md                 # This file - Master roadmap for all scripts
├── README.md                  # Reference documentation
├── WORKFLOW.md                # Development workflow guide
├── WordCountMaster/           # ✅ Complete - Migrated to LocaNext
│   ├── wordcount_diff_master.py
│   ├── V2_COMPLETE.md
│   ├── V2_DESIGN.md
│   └── ...
├── guides/                    # User guides for scripts
└── archive/                   # Old/deprecated scripts
```

---

## 🎓 Development Guidelines

### When to Create a NewScript

Create a standalone script when:
- A coworker requests a quick automation task
- The task is Excel/XML/text processing related
- It needs to be delivered quickly (within 1-2 days)
- It may or may not need a web UI

### When to Migrate to LocaNext

Migrate a script to LocaNext when:
- The script is used frequently by multiple people
- It would benefit from a web UI
- It needs user tracking and analytics
- It fits the platform architecture

### Script Development Standards

**Code Quality**:
- Clear function names and comments
- Error handling for all file operations
- Progress logging for long operations
- Comprehensive testing with sample data

**Documentation**:
- README.md with quick start guide
- Example input/output files
- Known limitations and edge cases
- Version history

**File Handling**:
- Support both absolute and relative paths
- Validate file existence before processing
- Clear error messages for file issues
- Clean up temporary files

---

## 📈 Metrics

**Total Scripts**: 1 complete
**Migrated to LocaNext**: 1
**Active Development**: 0
**Planned**: 3

**Migration Success Rate**: 100% (1/1 completed scripts migrated)

---

## 🔮 Future Vision

As NewScripts grows, we're building:
1. **Pattern Library**: Reusable code for common tasks
2. **Tool Ecosystem**: Suite of localization utilities
3. **LocaNext Apps**: Best scripts become platform features
4. **Knowledge Base**: Reference implementations for future work

---

**Maintained by**: Neil Schmitt
**Review Frequency**: Weekly during active development
