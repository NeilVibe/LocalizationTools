# Future Ideas Storage

**Purpose:** Park interesting ideas that aren't ready for implementation yet.

---

## IDEA-001: Neil's Probabilistic Check (NPC) ✅ APPROVED

**Status:** APPROVED for implementation (2025-12-13)
**Location:** Moving to P25_LDM_UX_OVERHAUL.md

**Final Design:**
```
1. TM panel shows Source matches ≥92%
2. User clicks [NPC] button
3. Embed user's Target (1 call)
4. Cosine similarity vs each TM Target
5. Any match ≥80%? → ✅ Consistent
   No matches ≥80%? → ⚠️ Potential issue
```

**Code:**
```python
def npc_check(user_target, tm_targets, threshold=0.80):
    """Neil's Probabilistic Check - simple and fast"""
    user_embedding = embed(user_target)

    for tm_target in tm_targets:
        sim = cosine_sim(user_embedding, tm_target.embedding)
        if sim >= threshold:
            return "✅ Consistent"

    return "⚠️ Potential issue"
```

**Why it works:**
- TM matches are high confidence (≥92% Source similarity)
- If user's Target doesn't match ANY expected Target (≥80%) → suspicious
- No FAISS needed, just direct cosine similarity
- Fast: 1 embedding + N cosine calcs (N usually <10)

---

*Add more ideas below as they come up*
