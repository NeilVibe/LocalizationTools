# Dev Tests (Linux localhost:5173)

**Fast UI testing via Vite dev server - no Windows build required**

---

## Folder Structure

```
dev_tests/
├── README.md                    ← This file
├── MANUAL_SEARCH_TEST.md        ← Manual search test checklist
├── screenshots/                 ← Test screenshots stored here
└── playwright/                  ← Playwright test files (future)
```

---

## Quick Reference

| Test Type | Command/Location |
|-----------|-----------------|
| Manual Tests | See MANUAL_SEARCH_TEST.md |
| Playwright | `cd locaNext && npx playwright test` |
| Screenshots | Saved to `screenshots/` folder |

---

## vs Windows Testing

| Aspect | Dev Tests (Linux) | Windows Tests (Playground) |
|--------|------------------|---------------------------|
| Server | localhost:5173 | Electron app |
| Speed | Instant reload | 15+ min build |
| Use | UI development | Final validation |
| Protocol | DEV_MODE_PROTOCOL.md | MASTER_TEST_PROTOCOL.md |

---

## Known Issues

### Playwright + Svelte 5

Playwright's `fill()` method has compatibility issues with Svelte 5's reactive bindings:
- Svelte immediately resets DOM values to match `$state()`
- Workaround: Use manual testing or `page.evaluate()` to call component functions

---

*Dev testing folder | 2025-12-28*
