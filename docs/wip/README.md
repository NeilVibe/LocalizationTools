# WIP - Work In Progress

**Updated:** 2025-12-16 | **Active Files:** 7 | **Open Issues:** 0

---

## Quick Navigation

| Need | File |
|------|------|
| **Session state?** | [SESSION_CONTEXT.md](SESSION_CONTEXT.md) |
| **Bug list?** | [ISSUES_TO_FIX.md](ISSUES_TO_FIX.md) |
| **Roadmap?** | [Roadmap.md](../../Roadmap.md) |

---

## Current Status

```
Build 295 ✅ PASSED | v25.1216.1626
├── Open Issues: 0 (all 38 fixed!)
├── P36 Pretranslation Stack: Planning (NEW!)
├── P25 LDM UX: 85%
└── Enterprise Docs: Created
```

---

## Active WIP

| File | Status | Description |
|------|--------|-------------|
| `SESSION_CONTEXT.md` | Always | Claude handoff state |
| `ISSUES_TO_FIX.md` | 0 open | Bug tracker |
| `P36_PRETRANSLATION_STACK.md` | Planning | **NEW!** Unified TM + KR Similar + XLS Transfer |
| `P25_LDM_UX_OVERHAUL.md` | 85% | TM matching, QA checks |
| `P17_LDM_TASKS.md` | 80% | LDM feature list |

## Reference WIP

| File | Description |
|------|-------------|
| `P23_DATA_FLOW_ARCHITECTURE.md` | Local ↔ Central data flow |
| `P24_STATUS_DASHBOARD.md` | Server status (paused) |
| `P34_RESOURCE_CHECK_PROTOCOL.md` | Zombie cleanup protocol |
| `IDEAS_FUTURE.md` | Future feature ideas |

---

## Archived (History)

| Location | Contents |
|----------|----------|
| `history/wip-archive/` | 12 completed P* files |
| `history/ISSUES_HISTORY.md` | 38 fixed issues |
| `history/ROADMAP_ARCHIVE.md` | Old roadmap items |

---

## Quick Commands

```bash
# Check build
http://172.28.150.120:3000/neilvibe/LocaNext/actions

# Trigger build
echo "Build" >> GITEA_TRIGGER.txt && git add -A && git commit -m "Build" && git push origin main && git push gitea main

# Check servers
./scripts/check_servers.sh
```

---

*Keep WIP lean. Archive completed work to `docs/history/`.*
