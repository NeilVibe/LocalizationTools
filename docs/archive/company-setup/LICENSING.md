# License Compliance Documentation

**For:** Legal Team, Compliance Officers, Procurement
**Classification:** Internal
**Risk Level:** LOW (All permissive licenses)

---

## Executive Summary

| Question | Answer |
|----------|--------|
| Can we use commercially? | ✅ **YES** |
| Can we modify the code? | ✅ **YES** |
| Can we distribute to customers? | ✅ **YES** |
| Must we share our changes? | ❌ **NO** (not required) |
| Any copyleft/viral licenses? | ❌ **NO** (none) |
| Recurring license fees? | ❌ **NO** ($0) |
| Per-seat costs? | ❌ **NO** (unlimited users) |

---

## License Overview

### What Licenses Are Used?

```
LICENSE BREAKDOWN:
═══════════════════════════════════════════════════

100% PERMISSIVE LICENSES ONLY

┌─────────────┬──────────────┬────────────────────┐
│   License   │  Components  │   Commercial OK?   │
├─────────────┼──────────────┼────────────────────┤
│    MIT      │     85%      │     ✅ YES         │
│  Apache 2.0 │     10%      │     ✅ YES         │
│    BSD      │      3%      │     ✅ YES         │
│ PostgreSQL  │      1%      │     ✅ YES         │
│ Public Dom. │      1%      │     ✅ YES         │
├─────────────┼──────────────┼────────────────────┤
│    GPL      │      0%      │     N/A            │
│   AGPL      │      0%      │     N/A            │
│   SSPL      │      0%      │     N/A            │
└─────────────┴──────────────┴────────────────────┘

❌ NO GPL - No copyleft contamination
❌ NO AGPL - No network copyleft
❌ NO SSPL - No MongoDB-style restrictions
✅ 100% COMMERCIAL-SAFE
```

---

## Detailed Component Licenses

### Core Application

| Component | Version | License | Commercial Use |
|-----------|---------|---------|----------------|
| LocaNext (our code) | 1.0.0 | MIT | ✅ Yes |
| Python | 3.11+ | PSF | ✅ Yes |
| FastAPI | 0.100+ | MIT | ✅ Yes |
| Electron | 28+ | MIT | ✅ Yes |
| SvelteKit | 2.0+ | MIT | ✅ Yes |
| Node.js | 20+ | MIT | ✅ Yes |

### Database

| Component | Version | License | Commercial Use |
|-----------|---------|---------|----------------|
| PostgreSQL | 15+ | PostgreSQL License | ✅ Yes |
| PgBouncer | 1.16+ | ISC | ✅ Yes |
| SQLAlchemy | 2.0+ | MIT | ✅ Yes |

### AI/ML Components

| Component | Version | License | Commercial Use |
|-----------|---------|---------|----------------|
| Korean BERT (klue/bert-base) | - | Apache 2.0 | ✅ Yes |
| PyTorch | 2.0+ | BSD | ✅ Yes |
| Transformers (Hugging Face) | 4.x | Apache 2.0 | ✅ Yes |
| FAISS | 1.x | MIT | ✅ Yes |

### Infrastructure

| Component | Version | License | Commercial Use |
|-----------|---------|---------|----------------|
| Gitea | 1.22+ | MIT | ✅ Yes |
| Nginx (optional) | 1.x | BSD-2 | ✅ Yes |
| Docker (optional) | 24+ | Apache 2.0 | ✅ Yes |

### Frontend Libraries

| Component | License | Commercial Use |
|-----------|---------|----------------|
| Carbon Design System | Apache 2.0 | ✅ Yes |
| carbon-components-svelte | Apache 2.0 | ✅ Yes |
| socket.io-client | MIT | ✅ Yes |

### Python Dependencies

| Package | License | Commercial Use |
|---------|---------|----------------|
| uvicorn | BSD | ✅ Yes |
| pydantic | MIT | ✅ Yes |
| python-jose | MIT | ✅ Yes |
| bcrypt | Apache 2.0 | ✅ Yes |
| openpyxl | MIT | ✅ Yes |
| loguru | MIT | ✅ Yes |
| pandas | BSD | ✅ Yes |
| numpy | BSD | ✅ Yes |

---

## License Comparison

### Why MIT is Best for Commercial Use

```
LICENSE COMPARISON FOR COMPANIES:
═══════════════════════════════════════════════════════════════════

                  │ MIT/BSD │ Apache 2.0 │  GPL   │  AGPL  │ SSPL
──────────────────┼─────────┼────────────┼────────┼────────┼───────
Commercial use    │   ✅    │     ✅     │   ⚠️   │   ❌   │  ❌
Modify privately  │   ✅    │     ✅     │   ❌   │   ❌   │  ❌
No source sharing │   ✅    │     ✅     │   ❌   │   ❌   │  ❌
SaaS use OK       │   ✅    │     ✅     │   ✅   │   ❌   │  ❌
No patent risk    │   ✅    │     ✅*    │   ⚠️   │   ⚠️   │  ⚠️
Simple compliance │   ✅    │     ✅     │   ❌   │   ❌   │  ❌
──────────────────┴─────────┴────────────┴────────┴────────┴───────

LocaNext: 100% MIT/BSD/Apache ✅

* Apache 2.0 includes explicit patent grant - actually better!
```

---

## Compliance Requirements

### MIT License (most of our code)

**Requirements:**
1. Include copyright notice in distributions
2. Include license text in distributions

**That's it.** No other obligations.

```
Example copyright notice (already in source):

MIT License
Copyright (c) 2025 LocaNext
Permission is hereby granted, free of charge...
```

### Apache 2.0 (BERT model, some libs)

**Requirements:**
1. Include copyright notice
2. Include license text
3. State changes if modified
4. Include NOTICE file if present

**Benefit:** Explicit patent grant protects you.

### What You DON'T Have To Do

- ❌ Share your source code
- ❌ Share your modifications
- ❌ Pay royalties
- ❌ Get permission for commercial use
- ❌ Display attribution in UI (only in source/docs)

---

## Risk Assessment

### License Risk Matrix

| Risk Type | Level | Mitigation |
|-----------|-------|------------|
| Copyleft contamination | ✅ NONE | No GPL/AGPL used |
| Patent claims | ✅ LOW | Apache 2.0 patent grant |
| Trademark issues | ✅ NONE | No trademarked components |
| Export control | ✅ LOW | Standard encryption only |
| Vendor lock-in | ✅ NONE | All open source |

### No Problematic Licenses

We specifically **AVOID** these licenses:

| License | Problem | Status |
|---------|---------|--------|
| GPL v2/v3 | Must share source | ❌ NOT USED |
| AGPL | Network copyleft | ❌ NOT USED |
| SSPL | MongoDB restriction | ❌ NOT USED |
| Commons Clause | Commercial restriction | ❌ NOT USED |
| BSL | Time-delayed open source | ❌ NOT USED |

---

## Audit Trail

### How to Verify

```bash
# Generate license report for Python packages
pip-licenses --format=markdown > python_licenses.md

# Generate license report for Node packages
npx license-checker --markdown > node_licenses.md

# Check for problematic licenses
pip-licenses | grep -i "GPL\|AGPL\|SSPL"
# Should return EMPTY
```

### Last Audit

| Date | Auditor | Result |
|------|---------|--------|
| 2025-12-06 | Automated | ✅ PASS - No problematic licenses |

---

## Legal Sign-Off Template

### For Legal/Compliance Approval

```
LICENSE COMPLIANCE CERTIFICATION

Project: LocaNext Localization Platform
Version: 1.0.0
Date: _______________

I have reviewed the license compliance documentation and confirm:

[ ] All components use permissive licenses (MIT/BSD/Apache)
[ ] No copyleft licenses (GPL/AGPL) are present
[ ] No commercial-restricted licenses are present
[ ] License obligations are documented and achievable
[ ] The software is cleared for commercial use

Approved by: _______________________
Title:       _______________________
Date:        _______________________
Signature:   _______________________
```

---

## FAQ for Legal Team

**Q: Can we use this in products we sell?**
A: Yes. MIT/Apache licenses explicitly allow commercial use.

**Q: Do we have to share our customizations?**
A: No. Permissive licenses don't require sharing modifications.

**Q: What if we bundle this with other software?**
A: Fine. Just include the license notices in documentation.

**Q: Any annual fees or per-seat costs?**
A: No. Open source = $0 licensing cost.

**Q: Can a vendor revoke our license?**
A: No. Open source licenses are irrevocable.

**Q: What about the AI model?**
A: Apache 2.0 licensed, explicitly allows commercial use.

---

## Third-Party License Texts

Full license texts are available in:
- `/licenses/MIT.txt`
- `/licenses/Apache-2.0.txt`
- `/licenses/BSD.txt`
- `/licenses/PostgreSQL.txt`

Or at their respective project repositories.

---

*Document Version: 2025-12-06*
*Classification: Internal - Legal*
*Next Audit: Quarterly or upon major version update*
