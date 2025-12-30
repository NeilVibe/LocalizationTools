# Analytics & AI Integration Vision

> **Status:** Long-term roadmap feature set
> **Created:** 2025-12-30
> **Priority:** Future milestone (post-core stability)

---

## Overview

This document captures the vision for advanced analytics and AI integration in LocaNext, transforming it from a translation management tool into an intelligent productivity platform with deep insights into translator performance and workflow optimization.

---

## Part 1: User Behavior Analytics Dashboard

### 1.1 QA Usage Metrics
- **QA activation frequency** - How often users enable/use QA checks
- **QA issue resolution rate** - % of flagged issues that get addressed
- **Common QA failure patterns** - Which rules trigger most often

### 1.2 Translation Productivity Metrics

#### Time-Based Analysis
- **Average time to confirm a string** relative to:
  - Word count (source)
  - Character count
  - Complexity score (tags, formatting, etc.)
- **Time per word** calculation
- **Daily/weekly/monthly word output**

#### Translation Type Classification
| Type | Description | Tracking |
|------|-------------|----------|
| **TRUE Translation** | User typed from scratch | No prior target, user input |
| **TM Match Confirmed** | Pre-translation from TM accepted as-is | TM match + no edits |
| **TM Match Modified** | Pre-translation edited before confirm | TM match + edits detected |
| **AI Translation Confirmed** | AI suggestion accepted as-is | AI source + no edits |
| **AI Translation Modified** | AI suggestion edited before confirm | AI source + edits detected |

#### Edit Distance Metrics
- **Average % change** from pre-translation to final
- **Edit distance** (Levenshtein) per confirmation
- **Pattern analysis** - What types of strings get modified most?

### 1.3 Work Session Analytics
- **Daily confirmed strings** count
- **Daily TRUE translations** vs **assisted translations**
- **Productivity trends** over time
- **Session duration** tracking
- **Break patterns** (time gaps between confirmations)

### 1.4 Dashboard Visualizations (Future)
- Productivity graphs (words/day, strings/day)
- Translation type pie charts
- Time-to-confirm histograms
- QA compliance scores
- Team comparison views (enterprise)

---

## Part 2: AI Translation Integration

### 2.1 Architecture
```
LocaNext Client
     │
     ▼
┌─────────────────────┐
│  AI Translation     │
│  Endpoint Manager   │
├─────────────────────┤
│  - OpenAI           │
│  - Claude           │
│  - DeepL            │
│  - Custom (WebTrans)│
└─────────────────────┘
     │
     ▼
  Translation API
```

### 2.2 Integration Points

#### File-Level Translation
- **Right-click file → "Translate with AI"**
- Batch translate all untranslated strings
- Progress indicator for large files
- Option to translate only empty targets vs all

#### Cell-Level Translation
- **Right-click cell → "Translate this string"**
- Keyboard shortcut (e.g., Ctrl+T)
- Inline AI suggestion display
- Accept/Modify/Reject workflow

#### Smart Suggestions
- Show AI suggestion on cell focus (optional)
- Confidence score display
- Alternative translations dropdown
- "Translate similar strings" bulk action

### 2.3 AI Provider Configuration
```typescript
interface AIProviderConfig {
  provider: 'openai' | 'claude' | 'deepl' | 'custom';
  apiKey: string;
  endpoint?: string;  // For custom providers
  model?: string;     // e.g., 'gpt-4', 'claude-3'
  sourceLanguage: string;
  targetLanguage: string;
  customPrompt?: string;  // Allow user customization
}
```

### 2.4 Tracking AI Usage
- **AI translations requested** per session/day
- **AI acceptance rate** (confirmed as-is vs modified)
- **AI quality score** (based on edit distance)
- **Cost tracking** (API calls, tokens used)

---

## Part 3: Preference Persistence

### 3.1 Settings to Persist

#### Column Preferences
- `showIndex` - Show row number column
- `showStringId` - Show StringID column
- `showReference` - Show reference column
- `columnWidths` - Custom width percentages

#### Font Preferences
- `fontSize` - Grid font size
- `fontWeight` - Normal/Bold
- `fontFamily` - Font selection
- `fontColor` - Text color

#### UI Preferences
- `sidePanelWidth` - TM/QA panel width
- `sidePanelCollapsed` - Panel state
- `defaultFilter` - Last used filter
- `searchHistory` - Recent searches

#### Workflow Preferences
- `autoSaveInterval` - Auto-save frequency
- `confirmOnNavigate` - Warn on unsaved changes
- `qaAutoRun` - Auto-run QA on file open

### 3.2 Storage Options

| Option | Pros | Cons |
|--------|------|------|
| **LocalStorage** | Fast, offline, no DB changes | Per-device only |
| **PostgreSQL** | Synced across devices, backup | Requires connection |
| **Hybrid** | Best of both | More complexity |

**Recommendation:** Hybrid approach
- Save to LocalStorage immediately (fast UX)
- Sync to PostgreSQL when online (persistence)
- Load from PostgreSQL on new device, fallback to defaults

### 3.3 Implementation Priority
1. **Phase 1:** LocalStorage for column/font preferences
2. **Phase 2:** PostgreSQL sync for cross-device
3. **Phase 3:** Full preference management UI

---

## Part 4: Data Model Extensions

### 4.1 New Tables Required

```sql
-- User preferences (synced)
CREATE TABLE user_preferences (
  user_id INTEGER REFERENCES users(id),
  preference_key VARCHAR(100),
  preference_value JSONB,
  updated_at TIMESTAMP DEFAULT NOW(),
  PRIMARY KEY (user_id, preference_key)
);

-- Translation activity log (analytics)
CREATE TABLE translation_activity (
  id SERIAL PRIMARY KEY,
  user_id INTEGER REFERENCES users(id),
  file_id INTEGER REFERENCES files(id),
  row_id INTEGER,
  action_type VARCHAR(50),  -- 'confirm', 'edit', 'ai_request', 'tm_apply'
  source_text TEXT,
  original_target TEXT,     -- Before user edit
  final_target TEXT,        -- After user edit
  translation_source VARCHAR(50),  -- 'manual', 'tm', 'ai'
  edit_distance INTEGER,
  time_spent_ms INTEGER,
  word_count INTEGER,
  created_at TIMESTAMP DEFAULT NOW()
);

-- AI usage tracking
CREATE TABLE ai_translations (
  id SERIAL PRIMARY KEY,
  user_id INTEGER REFERENCES users(id),
  provider VARCHAR(50),
  source_text TEXT,
  ai_response TEXT,
  final_text TEXT,
  was_modified BOOLEAN,
  edit_distance INTEGER,
  tokens_used INTEGER,
  cost_estimate DECIMAL(10,6),
  created_at TIMESTAMP DEFAULT NOW()
);
```

---

## Part 5: Implementation Roadmap

### Phase 1: Foundation (Current Focus)
- [x] Core LDM functionality
- [x] TM integration
- [x] QA system
- [ ] **Preference persistence (LocalStorage)**
- [ ] **Fix column resize for all columns**

### Phase 2: Analytics Foundation
- [ ] Translation activity logging
- [ ] Basic time tracking
- [ ] Edit distance calculation
- [ ] Simple dashboard with key metrics

### Phase 3: Advanced Analytics
- [ ] Productivity calculations
- [ ] Translation type classification
- [ ] Trend visualization
- [ ] Export reports

### Phase 4: AI Integration
- [ ] AI provider configuration UI
- [ ] File-level AI translation
- [ ] Cell-level AI translation
- [ ] AI usage tracking

### Phase 5: Intelligence
- [ ] Smart suggestions
- [ ] Predictive analytics
- [ ] Team performance comparisons
- [ ] Quality scoring algorithms

---

## Summary

This vision transforms LocaNext into:
1. **A productivity tracker** - Know exactly how efficient translators are
2. **A quality monitor** - Track edit patterns and QA compliance
3. **An AI-assisted tool** - Integrate any translation API
4. **A data-driven platform** - Make decisions based on real metrics

The key differentiator: **Distinguishing real human translation work from assisted/automated translation**, providing honest productivity metrics.

---

*Document maintained in: `docs/wip/ANALYTICS_AI_VISION.md`*
