# AI Hallucination Warnings for LocalizationTools

## Purpose
This document serves as a critical warning about AI-assisted code migrations and refactoring. It documents real cases of "AI hallucination" that occurred during this project's development.

## What is AI Hallucination in Code Migration?

AI hallucination occurs when an AI assistant makes **unauthorized changes** to code during migration, refactoring, or enhancement tasks. The AI may:
- Substitute libraries, models, or dependencies with "more common" alternatives
- Simplify complex logic it doesn't fully understand
- Add "helpful" features that weren't requested
- Remove functionality it deems "unnecessary"
- Change configuration values to "sensible defaults"

**These changes often seem logical to the AI but break critical functionality.**

---

## Real Case Study: XLSTransfer Model Substitution

### What Happened

During migration from Tkinter → Electron/Svelte, the AI **changed the embedding model** without authorization:

**Original (XLSTransfer0225.py:41):**
```python
model = SentenceTransformer('snunlp/KR-SBERT-V40K-klueNLI-augSTS')
```

**After Migration (XLSTransfer.svelte:44):**
```javascript
let dictModel = 'paraphrase-multilingual-MiniLM-L12-v2';  // ❌ WRONG!
```

### Why Did This Happen?

1. **Training Data Bias**: Generic multilingual models appear more frequently in AI training data
2. **"Unusual" Model Names**: Korean-specific model names seemed unusual to the AI
3. **False Optimization**: AI thought "multilingual = better" without understanding domain requirements
4. **Lack of Context**: AI didn't know this was a Korean game localization tool

### Impact

- ❌ Incorrect embeddings for Korean text
- ❌ Poor translation matching quality
- ❌ Wasted computation on wrong model
- ❌ Potential loss of user trust

### Resolution

**Fixed on 2025-11-09** after comprehensive code audit revealed the issue.

---

## Types of AI Hallucinations Observed

### 1. Dependency/Model Substitution
**Risk Level:** 🔴 CRITICAL

**What AI Does:**
- Changes specific models to generic ones
- Substitutes libraries with "better" alternatives
- Updates dependency versions without testing

**Real Example:**
```javascript
// Original: Korean-specific BERT model
'snunlp/KR-SBERT-V40K-klueNLI-augSTS'

// AI Changed To: Generic multilingual model
'paraphrase-multilingual-MiniLM-L12-v2'
```

**Prevention:**
- Explicitly state model names are SACRED
- Document WHY specific models are used
- Add model validation tests
- Version-lock critical dependencies

---

### 2. Feature Simplification
**Risk Level:** 🟡 HIGH

**What AI Does:**
- Removes multi-step workflows for "simpler UX"
- Eliminates intermediate sub-GUIs
- Assumes "modern = minimal"

**Real Example:**
```
Original: File selector → Sheet selector → Column selector (3 steps)
AI Changed: Single file upload (1 step)
Lost: Ability to select specific sheets/columns
```

**Prevention:**
- Explicitly preserve all workflow steps
- Document why complexity exists
- Test with real user workflows
- Compare feature parity systematically

---

### 3. "Helpful" Additions
**Risk Level:** 🟢 MEDIUM

**What AI Does:**
- Adds functions not in original
- Implements "obvious" improvements
- Extends functionality beyond scope

**Real Example:**
```
Original: 10 specific functions
AI Added: "Find Duplicates", "Validate Dictionary"
Problem: Extra maintenance burden, not requested
```

**Prevention:**
- Specify "ONLY migrate, DO NOT add"
- Require approval for new features
- Separate migration from enhancement

---

### 4. Configuration "Normalization"
**Risk Level:** 🟡 HIGH

**What AI Does:**
- Changes thresholds to "standard" values
- Updates file paths to "conventional" locations
- Modifies constants to "sensible defaults"

**Real Example:**
```python
# Original: Carefully tuned threshold
FAISS_THRESHOLD = 0.85

# AI Might Change To: "Industry standard"
FAISS_THRESHOLD = 0.90  # "Better precision"
```

**Prevention:**
- Mark critical values as SACRED
- Document why specific values chosen
- Add configuration validation tests

---

### 5. Architecture Over-Engineering
**Risk Level:** 🟡 HIGH

**What AI Does:**
- Splits monolithic code into "clean modules"
- Creates abstraction layers
- Introduces design patterns

**Real Example:**
```
Original: 1435-line single file (working perfectly)
AI Refactored: 8 modules, 5 abstraction layers
Problem: Functionality lost in translation between modules
```

**Prevention:**
- Refactoring is GOOD, but verify each module
- Test after EACH module split
- Compare outputs continuously

---

## Prevention Strategies

### Before Migration

1. **Document Critical Components**
   ```markdown
   ## CRITICAL - DO NOT CHANGE
   - Model: snunlp/KR-SBERT-V40K-klueNLI-augSTS
   - Threshold: 0.85 (tuned over 6 months)
   - Algorithm: clean_text() removes _x000D_
   ```

2. **Create Validation Test Suite**
   - Input/output pairs from original
   - Edge case testing
   - Performance benchmarks

3. **Explicit Migration Instructions**
   ```
   Task: Migrate Tkinter GUI to Svelte

   PRESERVE (DO NOT CHANGE):
   - All model names
   - All threshold values
   - All core algorithms
   - All function names

   MIGRATE ONLY:
   - GUI framework (Tkinter → Svelte)
   - UI components
   - Event handlers
   ```

### During Migration

1. **Incremental Verification**
   - Test after each component migration
   - Compare outputs with original
   - Review every dependency change

2. **Explicit Questioning**
   Ask AI: "Did you change any model names, thresholds, or algorithms?"

3. **Code Review Checklist**
   - [ ] Same models/libraries?
   - [ ] Same configuration values?
   - [ ] Same core algorithms?
   - [ ] Same function signatures?
   - [ ] All features present?

### After Migration

1. **Comprehensive Audit**
   - Side-by-side code comparison
   - Diff critical sections
   - Test with real data

2. **User Acceptance Testing**
   - Run original and new versions in parallel
   - Compare translation quality
   - Verify performance

3. **Documentation Updates**
   - Document all intentional changes
   - Flag any discovered hallucinations
   - Update this warning document

---

## Specific Warnings for LocalizationTools

### XLSTransfer Tool

**SACRED Components (NEVER CHANGE):**

1. **Model Name:**
   ```python
   MODEL_NAME = "snunlp/KR-SBERT-V40K-klueNLI-augSTS"
   ```
   ⚠️ This is a Korean-specific BERT model, not generic multilingual

2. **Core Algorithms:**
   - `clean_text()` - Removes `_x000D_` (critical for Excel exports)
   - `simple_number_replace()` - Preserves game codes like `{ItemID}`
   - `analyze_code_patterns()` - Detects game code patterns
   - Split/Whole mode logic - Based on newline count matching

3. **Threshold Values:**
   ```python
   DEFAULT_FAISS_THRESHOLD = 0.85  # Tuned for Korean game localization
   ```

4. **File Processing:**
   - Must support multi-sheet Excel files
   - Must support column selection (A-Z)
   - Must preserve code blocks in translations

### Other Tools

*(To be documented as issues arise)*

---

## How to Report AI Hallucinations

If you discover an AI hallucination:

1. **Document the Issue**
   ```markdown
   ## AI Hallucination: [Brief Description]
   **Date Found:** YYYY-MM-DD
   **Component:** [File/Function]
   **Original Code:** [Code snippet]
   **AI Changed To:** [Code snippet]
   **Impact:** [Critical/High/Medium/Low]
   **Why It Happened:** [Theory]
   **Fix Applied:** [Description]
   ```

2. **Add to This Document**
   - Update relevant section
   - Add to case studies if significant
   - Update prevention strategies

3. **Create Test to Prevent Recurrence**
   - Add validation test
   - Add to CI/CD pipeline

---

## Checklist for AI-Assisted Development

Use this checklist for ANY AI-assisted code changes:

### Pre-Development
- [ ] Documented critical components
- [ ] Created test suite with original
- [ ] Specified exactly what CAN change
- [ ] Specified what CANNOT change
- [ ] Set up validation pipeline

### During Development
- [ ] Reviewing changes incrementally
- [ ] Asking AI about modifications
- [ ] Testing after each major change
- [ ] Comparing with original outputs

### Post-Development
- [ ] Comprehensive code diff review
- [ ] All critical components unchanged
- [ ] Configuration values verified
- [ ] Dependencies/models verified
- [ ] Feature parity confirmed
- [ ] Performance benchmarked
- [ ] User acceptance testing passed
- [ ] Documentation updated

---

## Key Takeaways

1. **AI is a tool, not a trusted expert** - Always verify critical changes
2. **Explicit > Implicit** - State what must NOT change, don't assume AI knows
3. **Test continuously** - Don't wait until the end to validate
4. **Domain knowledge matters** - AI doesn't understand Korean game localization nuances
5. **Trust but verify** - Code reviews are CRITICAL for AI-generated code

---

## References

- [XLSTransfer Migration Audit](./XLSTransfer_Migration_Audit.md)
- Original XLSTransfer code: `RessourcesForCodingTheProject/MAIN PYTHON SCRIPTS/XLSTransfer0225.py`
- Backend implementation: `client/tools/xls_transfer/`
- Frontend implementation: `locaNext/src/lib/components/apps/XLSTransfer.svelte`

---

**Remember: The original code was described as "flawless and needs to stay that way" - AI should enhance, not alter the foundation.**

*Last Updated: 2025-11-09*
*Maintained by: Development Team*
