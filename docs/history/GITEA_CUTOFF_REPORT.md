# Gitea Cutoff Report

**Date:** 2025-12-27 02:45 | **Build 395:** SUCCESS

---

## Summary

Gitea stopped after Build 395 confirmed successful.

---

## Resource Comparison

| Metric | Gitea ON | Gitea OFF | Saved |
|--------|----------|-----------|-------|
| **RAM Used** | 3.1 GB | 2.8 GB | **~300 MB** |
| **Gitea Process** | 354 MB | 0 | 354 MB |
| **act_runner** | 25 MB | 0 | 25 MB |
| **CPU Load** | 2.18 | 0.76 | Lower |

---

## What Was Running

| Process | RAM | Notes |
|---------|-----|-------|
| LanguageTool (Java) | 1.5 GB | Still running (P5) |
| PostgreSQL | ~100 MB | Still running (central DB) |
| Gitea | 354 MB | **STOPPED** |
| act_runner | 25 MB | **STOPPED** |

---

## Status

- Build 395: SUCCESS (verified in database)
- Gitea: STOPPED (killed PID 629667)
- act_runner: STOPPED
- CI/CD: OFFLINE (no new builds until Gitea restarted)

---

## To Restart Gitea

```bash
cd ~/gitea && ./gitea web &
cd ~/gitea && ./act_runner daemon --config runner_config.yaml &
```

---

## Conclusion

Stopping Gitea saved ~300 MB RAM and reduced CPU load. System is now running lighter. No new builds possible until Gitea is restarted.

---

*Report generated 2025-12-27 02:45*
