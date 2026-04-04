# Phase 110: Auth Architecture Fix + Dashboard + Audio

## Problem Statement

The auth system uses **synthetic user identities** (`ORIGIN_ADMIN`, `LOCAL`, `OFFLINE`) that don't exist as real rows in the `users` table. This crashes on PostgreSQL (`WHERE user_id = 'ORIGIN_ADMIN'` → integer vs varchar). The dashboard is unusable on Admin builds with PG.

**Clean slate:** User will fully reinstall. No migration needed. Full reconstruction.

---

## Architecture: Role Hierarchy & Localhost Auto-Elevation

### Role Model (3 tiers)

| Role | Who | Powers | How assigned |
|------|-----|--------|-------------|
| `superadmin` | Host machine owner | Everything. Create/delete admins. Server config. DB management. | Auto-assigned to seeded `admin` user (user_id=1) in `db_setup.py` |
| `admin` | Team leads, managers | Create/delete regular users. View stats. Access dashboard. | Created by superadmin via dashboard |
| `user` | Translators, team members | Use LocaNext tools. No admin access. | Created by admin/superadmin |

### Localhost Auto-Elevation (Zero Synthetic Users)

```
Dashboard loads on localhost:8888/dashboard/
  ↓
GET /health → { is_origin_admin: true }  (IP check: 127.0.0.1/::1)
  ↓
POST /api/origin-admin-token  (IP-locked to localhost)
  ↓
Backend: SELECT * FROM users WHERE role = 'superadmin' ORDER BY user_id LIMIT 1
  → fallback: WHERE role = 'admin' ORDER BY user_id LIMIT 1
  → nuclear fallback: WHERE user_id = 1 (machine owner, always exists)
  ↓
JWT with REAL integer user_id → all downstream queries work on SQLite AND PG
```

### No More Synthetic User IDs

Every JWT points to a real user row. Period.

| Before | After |
|--------|-------|
| `user_id: "ORIGIN_ADMIN"` (string) | Real superadmin integer user_id |
| `user_id: "LOCAL"` (string) | Real LOCAL user integer user_id (queried from DB) |
| `user_id: "OFFLINE"` (string) | Keep username-based lookup (already works) |

### DB Seeding (`db_setup.py`)

| User | user_id | Role | Purpose |
|------|---------|------|---------|
| `admin` | 1 | `superadmin` | Machine owner. Nuclear fallback. Cannot be deleted. |
| `OFFLINE` | 2 | `user` | Offline Storage access |
| `LOCAL` | 3 | `admin` | SQLite auto-login identity |

### Role Enforcement

| Action | Required Role |
|--------|--------------|
| Use LocaNext tools | `user` |
| Access dashboard | `admin` |
| Create/delete users | `admin` |
| Create/delete admins | `superadmin` |
| Server config / setup wizard | `superadmin` |
| Cannot be deleted | user_id=1 only |

### OFFLINE_MODE Handling

Keep as-is. The `OFFLINE_MODE_*` prefix returns `user_id: "OFFLINE"` which is caught at `auth.py:273` and resolved by username lookup. Not broken, not blocking. Keep fallback for one release, add deprecation log, remove later.

---

## Enriched Debug Logging Strategy

**ONE keyword to search: `PHASE110`**

All new logging uses `[PHASE110:MODULE]` prefix so the user can test ONCE on <PC_NAME>, grab the log file (`server/data/logs/server.log`), and search for `PHASE110` to get a complete picture of what happened.

### Log Tags

| Tag | Where | What it logs |
|-----|-------|-------------|
| `[PHASE110:SEED]` | `db_setup.py` | Each user created/updated: username, user_id, role |
| `[PHASE110:TOKEN]` | `main.py` | Token creation: which DB user resolved, integer user_id used |
| `[PHASE110:AUTH]` | `auth.py` | Token validation path taken: standard lookup vs OFFLINE/LOCAL fallback |
| `[PHASE110:ROLE]` | `auth_service.py` | Role validation: user X, action Y, required role Z |
| `[PHASE110:HEALTH]` | `health.py` | Server health query results: DB type, version, connection, table count |
| `[PHASE110:AUDIO]` | `codex_audio.py` | Category tree stats: total paths, max depth, root count |

### Example log output (success case)

```
2026-04-03 14:00:01 | INFO     | [PHASE110:SEED] admin user_id=1 role=superadmin (seeded)
2026-04-03 14:00:01 | INFO     | [PHASE110:SEED] OFFLINE user_id=2 role=user (seeded)
2026-04-03 14:00:01 | INFO     | [PHASE110:SEED] LOCAL user_id=3 role=admin (sqlite only, seeded)
...
2026-04-03 14:05:12 | INFO     | [PHASE110:TOKEN] origin-admin-token: resolved superadmin user_id=1 username=admin
2026-04-03 14:05:12 | INFO     | [PHASE110:AUTH] token user_id=1 (int), standard DB lookup → found admin role=superadmin
2026-04-03 14:05:13 | INFO     | [PHASE110:HEALTH] db=postgresql version=16.x tables=24 connected=true
2026-04-03 14:05:20 | INFO     | [PHASE110:AUDIO] category tree: 47 paths, max_depth=4, 8 roots
```

### Example log output (failure case)

```
2026-04-03 14:05:12 | ERROR    | [PHASE110:TOKEN] origin-admin-token: NO superadmin/admin found in DB! Fallback to user_id=1
2026-04-03 14:05:12 | WARNING  | [PHASE110:AUTH] token user_id=1, DB lookup returned None — user missing from DB
```

---

## Implementation (ONE commit, ONE test)

### Execution Order (8 tasks, strict sequence)

#### Task 1: `server/services/auth_service.py`
- Add `"superadmin"` to `VALID_ROLES` → `["user", "admin", "superadmin"]`
- Add role hierarchy guard: admin cannot assign `superadmin`, only superadmin can
- Add user_id=1 delete protection in `admin_delete_user()`
- Add `[PHASE110:ROLE]` logging on role assignment attempts

#### Task 2: `server/database/db_setup.py`
- Change seeded `admin` user role from `"admin"` to `"superadmin"`
- Ensure existing admin gets role updated to `superadmin` (not just new installs)
- Add `[PHASE110:SEED]` logging for each user: username, user_id, role
- Keep OFFLINE user as `"user"`, LOCAL user as `"admin"` (correct already)

#### Task 3: `server/main.py` — `/api/origin-admin-token` endpoint (line 743)
- Replace hardcoded `user_id: "ORIGIN_ADMIN"` with real DB query:
  ```python
  # Query: superadmin first → admin fallback → user_id=1 nuclear fallback
  user = db.query(User).filter(User.role == 'superadmin').order_by(User.user_id).first()
  if not user:
      user = db.query(User).filter(User.role == 'admin').order_by(User.user_id).first()
  if not user:
      user = db.query(User).filter(User.user_id == 1).first()
  ```
- Use `user.user_id` (integer) in JWT
- Add `[PHASE110:TOKEN]` logging: which user resolved, what user_id

#### Task 4: `server/main.py` — `/health` auto_token (line 724)
- Replace hardcoded `user_id: "LOCAL"` with real DB query:
  ```python
  local_user = db.query(User).filter(User.username == 'LOCAL').first()
  ```
- Use `local_user.user_id` (integer) in JWT
- Add `[PHASE110:TOKEN]` logging

#### Task 5: `server/utils/auth.py` — BOTH sync AND async versions
- **Sync** `get_current_user()` (line 167): the OFFLINE/LOCAL username fallback stays (already correct — resolves to real integer user_id). No ORIGIN_ADMIN case exists here. Add `[PHASE110:AUTH]` logging at each decision point.
- **Async** `get_current_user_async()` (line 238): same treatment. Add logging.
- Both functions: log the path taken (standard int lookup vs username fallback) and the resolved user_id.

> **NOTE:** ORIGIN_ADMIN never had a special case in auth.py — it just fell through to the standard `WHERE user_id == "ORIGIN_ADMIN"` query which crashed on PG. With Task 3 fixed, this path is never reached anymore (JWT always has integer user_id).

#### Task 6: `server/api/health.py` — New `/api/v2/server-health` endpoint
- Returns: DB type (postgresql/sqlite), DB version, connection status, uptime, table count, DB size
- Add `[PHASE110:HEALTH]` logging
- Simple read-only endpoint, no auth required (like existing /health)

#### Task 7: Frontend changes
- **`StatusPage.svelte`**: Add "Server & Database" card calling `/api/v2/server-health`
- **`AudioExportTree.svelte`**: Change `AUTO_EXPAND_DEPTH` from `0` to `2`
- **`users/+page.svelte`**: Role dropdown shows `[user, admin, superadmin]` for superadmins, `[user, admin]` for admins

#### Task 8: Audio category tree — BUG FIX + logging

**BUG FOUND: Windows backslash kills tree nesting**

`mega_index_data_parsers.py` computes `rel_dir` WITHOUT normalizing backslashes:
```python
# Line 276 — NO .replace("\\", "/")
rel_dir = str(xml_path.relative_to(export_folder).parent)
# Line 334 — NO .replace("\\", "/") 
rel_dir = str(xml_path.relative_to(export_folder).parent)
```

On Windows (<PC_NAME>), `Path.parent` produces `Dialog\QuestDialog`. Then `_build_category_tree()` splits on `/`:
```python
parts = full_path.split("/")  # "Dialog\QuestDialog".split("/") → ["Dialog\QuestDialog"] = 1 segment!
```

**One segment = no nesting = no children = no chevrons = flat list.**

Meanwhile MDG normalizes: `rel_dir = str(...).replace("\\", "/")`
And even line 320 of the SAME FILE does `.replace("\\", "/")` for `filename_key`!

**FIX (2 lines):**
```python
# Line 276: add .replace("\\", "/")
rel_dir = str(xml_path.relative_to(export_folder).parent).replace("\\", "/")

# Line 334: add .replace("\\", "/")  
rel_dir = str(xml_path.relative_to(export_folder).parent).replace("\\", "/")
```

**Also:**
1. Change `AUTO_EXPAND_DEPTH` from `0` to `2` in `AudioExportTree.svelte` (match MDG)
2. Add `[PHASE110:AUDIO]` logging in `codex_audio.py:get_audio_categories()`:
   - Total paths, max depth, number of root nodes, sample paths (first 5)
   - Confirms tree nesting works after the backslash fix

---

## Security Notes (While In Auth Code)

| Issue | Fix in Phase 110? |
|-------|-------------------|
| Health leaks admin JWT (SQLite) | YES — now uses real user_id (less damage if leaked) |
| SECRET_KEY defaults to well-known | YES — setup wizard generates random key |
| No token revocation | NO — future phase |
| Role column no DB constraint | NO — low priority |
| user_id=1 undeletable | YES — guard in admin_delete_user() |

---

## Test Plan (ONE test on <PC_NAME>)

### Pre-test: Search log for `PHASE110`

After installing on <PC_NAME>, grab `server/data/logs/server.log` and search for `PHASE110`. Expected output:

1. `[PHASE110:SEED]` — 3 users seeded with correct roles
2. `[PHASE110:TOKEN]` — origin-admin-token resolved to integer user_id
3. `[PHASE110:AUTH]` — token validation succeeded with integer user_id
4. `[PHASE110:HEALTH]` — DB info retrieved
5. `[PHASE110:AUDIO]` — tree stats (depth, root count)

### Functional checks

1. **PG mode:** Dashboard Users/Stats/Logs load without 500
2. **SQLite mode:** auto_token still works, dashboard accessible
3. **Superadmin:** Can create admins. Admin cannot create superadmin.
4. **user_id=1:** Cannot be deleted via API
5. **Localhost:** Auto-elevated to superadmin without login prompt
6. **StatusPage:** Shows DB type, version, connection status
7. **Audio tree:** Folders collapsed initially, expandable (if data has depth)
8. **Dashboard nav:** All `/dashboard/*` routes work

### If something fails

1. Grab log file: `server/data/logs/server.log`
2. Search: `PHASE110` 
3. The tag + message tells us exactly which step failed and why
4. One targeted fix, one rebuild
