# Technology Stack -- v13.0 Production Path Resolution

**Project:** LocaNext v13.0
**Researched:** 2026-03-26

## Existing Stack (No Changes Needed)

v13.0 requires ZERO new dependencies. All work uses existing infrastructure.

### Backend (Python/FastAPI)

| Technology | Purpose | Status |
|------------|---------|--------|
| FastAPI | REST API for mapdata endpoints | 7 endpoints already built |
| lxml | XML parsing in MegaIndex | 35 dicts already built |
| Pillow (PIL) | DDS -> PNG conversion | MediaConverter working |
| Pydantic | Request/response models | 7 response models defined |
| loguru | Logging | Used throughout |

### Frontend (Svelte 5)

| Technology | Purpose | Status |
|------------|---------|--------|
| Svelte 5 Runes | ImageTab, AudioTab, RightPanel | Components complete |
| Carbon Components Svelte | UI components (Dropdown, InlineLoading, Tag, InlineNotification) | In use |
| Carbon Icons | Image, Music, CheckmarkFilled, ErrorFilled | In use |

### Infrastructure

| Technology | Purpose | Status |
|------------|---------|--------|
| vgmstream | WEM -> WAV conversion | MediaConverter wired |
| Vitest | Unit testing (169 tests) | Infrastructure ready |
| Playwright | E2E testing | Infrastructure ready |

## New Components to Build (NOT new dependencies)

| Component | Carbon Components Used | Complexity |
|-----------|----------------------|------------|
| Branch+Drive selector | Dropdown + TextInput | Low |
| Path validation indicator | InlineNotification + Tag | Low |
| StrKey-based entity matching | Pure Python dict lookup | Medium |
| MegaIndex domain services | Pure Python refactor | Medium |

## Installation

No new packages needed. Existing `requirements.txt` and `package.json` are sufficient.
