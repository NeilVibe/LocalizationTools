# P5 LanguageTool - Test Report

**Date:** 2025-12-26
**Server:** LanguageTool 6.6 on 172.28.150.120:8081

---

## CDP Test Results

| Test | Status | Details |
|------|--------|---------|
| **P3 MERGE** | ✅ PASS | API structure verified, validation works |
| **P4 CONVERT** | ✅ PASS | 5/5 tests (TXT→Excel/XML/TMX, rejections) |
| **P5 GRAMMAR** | ✅ PASS | 11/11 fixture tests |

---

## Grammar Detection Capabilities

### Basic Errors (All Detected)

| Error Type | Example | Detection |
|------------|---------|-----------|
| Spelling | "tset" → "test" | ✅ |
| Spelling | "grammer" → "grammar" | ✅ |
| Contraction | "dont" → "don't" | ✅ |
| Article | "a amazing" → "an amazing" | ✅ |

### Advanced Errors (Detected)

| Error Type | Example | Detection |
|------------|---------|-----------|
| Modal verb | "could of" → "could have" | ✅ |
| Possessive | "its" → "it's" | ✅ |
| Possessive | "your" → "you're" | ✅ |
| Pronoun case | "Between you and I" → "me" | ✅ |
| Pronoun order | "Me and him went" → "He and I" | ✅ |
| Conditional | "If I would have known" → "had known" | ✅ |

### Known Limitations (Not Detected)

| Error Type | Example | Status |
|------------|---------|--------|
| Tense shift | "Yesterday I go and bought" | ❌ Missed |
| Their/They're | "Their going to the store" | ❌ Missed |
| Subjunctive | "I wish I was" → "were" | ❌ Missed |
| Everyone/has | "Everyone have their opinion" | ❌ Missed |
| Data singular | "The data shows" vs "show" | ❌ Missed |

---

## Multi-Language Support

### Requested Languages (13)

| Language | Code | Status | Error Detection | Notes |
|----------|------|--------|-----------------|-------|
| English (US) | en-US | ✅ SUPPORTED | ✅ 3 errors found | Full support |
| French | fr | ✅ SUPPORTED | ✅ 2 errors found | Full support |
| German | de-DE | ✅ SUPPORTED | ✅ 1 error found | Full support |
| Italian | it | ✅ SUPPORTED | ⚠️ Limited | Basic support |
| Polish | pl | ✅ SUPPORTED | ✅ 1 error found | Full support |
| Russian | ru | ✅ SUPPORTED | ✅ 1 error found | Full support |
| **Turkish** | tr | ❌ NOT SUPPORTED | - | **Not available in LT** |
| Japanese | ja | ✅ SUPPORTED | ⚠️ Limited | Basic support |
| Spanish (Spain) | es | ✅ SUPPORTED | ✅ 1 error found | Full support |
| Spanish (Mexico) | es | ⚠️ Use "es" | ✅ Works with "es" | No MX variant |
| Chinese Simplified | zh-CN | ⚠️ Use "zh" | ⚠️ Limited | Basic support |
| Chinese Traditional | zh-TW | ❌ Use "zh" | ⚠️ Limited | No TW variant |
| Portuguese (Brazil) | pt-BR | ✅ SUPPORTED | ✅ 1 error found | Full support |

### Summary

- **Fully Supported:** 10/13 languages
- **Not Supported:** Turkish (tr)
- **Use Base Code:** Spanish Mexico (use "es"), Chinese Traditional (use "zh")

---

## Spanish Variants (Detailed Analysis)

### Available Variants

| Code | Name | Description |
|------|------|-------------|
| es | Spanish | Generic Spanish (recommended) |
| es-AR | Spanish (voseo) | Argentine Spanish with voseo conjugations |
| es-ES | Spanish | Spain/Castilian Spanish |

### Testing Results

**Key Finding:** All Spanish variants (es, es-AR, es-ES) use **identical grammar rules**. No functional difference in error detection.

| Test Sentence | Error Type | Detection |
|--------------|------------|-----------|
| "El agua esta fria." | Missing accents (está, fría) | ✅ Detected (2 errors) |
| "Voy ha comprar." | ha/a confusion | ✅ Detected |
| "Havía muchas personas." | Spelling (Había) | ✅ Detected |
| "Yo soy mas alto." | Missing accent (más) | ✅ Detected |
| "Tu eres mi amigo." | Missing accent (Tú) | ✅ Detected |
| "Ayer yo compro pan." | Tense error (compré) | ❌ NOT detected |

### Voseo Detection (es-AR)

| Sentence | es-AR | es-ES | Notes |
|----------|-------|-------|-------|
| "Vos tenés razón." | ✅ 0 errors | ✅ 0 errors | Voseo accepted by both |
| "Vos tenes razón." | ❌ 1 error | ❌ 1 error | Accent error detected by both |
| "Vos sabés mucho." | ✅ 0 errors | ✅ 0 errors | Correct voseo |
| "Tú tienes razón." | ✅ 0 errors | ✅ 0 errors | Standard form accepted |

**Conclusion:** es-AR recognizes voseo conjugations but enforces same rules as es-ES.

### Regional Vocabulary

| Sentence | Region | Detection |
|----------|--------|-----------|
| "Voy a manejar el carro." | Mexico/LATAM | ✅ No false positive |
| "Voy a conducir el coche." | Spain | ✅ No false positive |
| "Necesito la computadora." | LATAM | ✅ No false positive |
| "Necesito el ordenador." | Spain | ✅ No false positive |

**Conclusion:** Regional vocabulary differences (carro/coche, computadora/ordenador) are all accepted.

### Recommendation

| Your Need | Use Code |
|-----------|----------|
| Spain/Castilian Spanish | `es` or `es-ES` |
| Mexico/Latin America | `es` |
| Argentina (voseo) | `es-AR` |
| Any Spanish | `es` (safest) |

---

## Chinese Variants (Detailed Analysis)

### Available Variants

| Code | Name | Status |
|------|------|--------|
| zh-CN | Chinese (Simplified) | ✅ Supported |
| zh | Chinese (base) | ✅ Works (same as zh-CN) |
| zh-TW | Chinese (Traditional) | ❌ **NOT SUPPORTED** |

### Testing Results

**Key Finding:** LanguageTool has **very limited** Chinese support. Only zh-CN exists, with minimal grammar rules.

| Test Sentence | Script | Detection |
|--------------|--------|-----------|
| "我很開心。" | Traditional (開) | 0 errors (accepted) |
| "我很开心。" | Simplified (开) | 0 errors (accepted) |
| "這個東西很好。" | Traditional (這, 東) | 0 errors (accepted) |
| "这个东西很好。" | Simplified (这, 东) | 0 errors (accepted) |
| "電腦非常好用。" | Traditional (電腦) | 0 errors (accepted) |
| "电脑非常好用。" | Simplified (电脑) | 0 errors (accepted) |

### Key Observations

1. **Traditional Characters Accepted:** zh-CN accepts Traditional Chinese characters without flagging them as errors
2. **No Script Enforcement:** Will not catch if you mix Simplified/Traditional in same document
3. **Limited Rules:** Chinese grammar rules are very basic - mostly punctuation and spacing

### Practical Implications

| Scenario | Result |
|----------|--------|
| Check Simplified Chinese text | Works (limited rules) |
| Check Traditional Chinese text | Works with `zh-CN` (limited rules) |
| Enforce Simplified-only | ❌ Cannot do this |
| Enforce Traditional-only | ❌ Cannot do this |
| Detect character typos | ❌ Very limited |

### Recommendation

| Your Need | Use Code | Notes |
|-----------|----------|-------|
| Simplified Chinese | `zh` or `zh-CN` | Basic support |
| Traditional Chinese | `zh` or `zh-CN` | Same engine, no dedicated rules |
| Strict script checking | ❌ Not possible | LanguageTool limitation |

**Bottom Line:** For Chinese, LanguageTool provides basic spelling/punctuation checks only. For serious Chinese QA, consider supplementary tools.

---

## All 60 Supported Languages

LanguageTool supports these languages:

| Code | Language | Code | Language |
|------|----------|------|----------|
| ar | Arabic | nl | Dutch |
| ast | Asturian | en | English (6 variants) |
| be | Belarusian | eo | Esperanto |
| br | Breton | fr | French (4 variants) |
| ca | Catalan (3 variants) | gl | Galician |
| zh | Chinese | de | German (4 variants) |
| crh | Crimean Tatar | el | Greek |
| da | Danish | ga | Irish |
| it | Italian | km | Khmer |
| ja | Japanese | fa | Persian |
| pl | Polish | pt | Portuguese (5 variants) |
| ro | Romanian | ru | Russian |
| sk | Slovak | sl | Slovenian |
| es | Spanish (3 variants) | sv | Swedish |
| tl | Tagalog | ta | Tamil |
| uk | Ukrainian | | |

---

## Performance

| Metric | Value |
|--------|-------|
| Single row check | ~43ms |
| 10K rows | ~7 minutes |
| RAM usage | 937MB |
| CPU (idle) | 0% |
| CPU (checking) | 8.6% |

---

## Recommendations

### For Production Use

1. **Turkish (tr):** Not supported. Consider alternative spell-check solution.
2. **Chinese:** Use code "zh" for both Simplified and Traditional.
3. **Spanish variants:** Use "es" for all Spanish (Spain, Mexico, Latin America).
4. **Large files:** Consider batch processing or progress indicator (7+ min for 10K rows).

### Grammar Rule Coverage

- **Best coverage:** English, German, French, Spanish, Portuguese
- **Basic coverage:** Japanese, Chinese, Italian (mostly spelling)
- **No coverage:** Turkish

---

## Correct Language Codes

Use these codes when calling the API:

```javascript
const LANGUAGE_CODES = {
  "ENG": "en-US",      // or en-GB, en-CA, en-AU
  "FRE": "fr",         // or fr-CA, fr-BE, fr-CH
  "GER": "de-DE",      // or de-AT, de-CH
  "ITA": "it",
  "POL": "pl",
  "RUS": "ru",
  "TUR": null,         // NOT SUPPORTED
  "JPN": "ja",
  "SPA_ES": "es",
  "SPA_MX": "es",      // Use "es" for all Spanish
  "ZHO_CN": "zh",
  "ZHO_TW": "zh",      // Use "zh" for all Chinese
  "POR_BR": "pt-BR"    // or just "pt"
};
```

---

*Report generated: 2025-12-26*
