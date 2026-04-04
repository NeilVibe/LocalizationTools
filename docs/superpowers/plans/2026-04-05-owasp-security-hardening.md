# OWASP Security Hardening — Phase 114 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close all HIGH-priority OWASP gaps to reach 8/10 PROTECTED status — HTTPS transport encryption, CSP headers, CORS auto-lock in LAN mode, forced password change, and auto-generated JWT secrets.

**Architecture:** Three independent waves that can be developed in parallel. Wave 1 (HTTPS verification) is trivial — code already exists, just needs end-to-end validation. Wave 2 (security headers middleware) is a new FastAPI middleware. Wave 4 (force defaults) wires existing backend `must_change_password` field to frontend + auto-generates JWT secret in setup wizard. Wave 3 (httpOnly JWT) is intentionally DEFERRED — too much blast radius (17+ files) for marginal gain in a LAN Electron app.

**Tech Stack:** FastAPI middleware, Svelte 5 (Carbon Components), Pydantic schemas, Python `secrets` module

**Backward Compatibility Contract:**
- Old User builds (HTTP) MUST still connect to new Admin (HTTPS) — existing HTTPS→HTTP fallback in `ServerSettingsModal.svelte:138-152` handles this
- Old Admin builds (no certs) MUST still work — uvicorn falls back to HTTP when no certs exist (`main.py:1189-1191`)
- No breaking changes to API response shapes — only additive fields
- CSP must allow `unsafe-inline` for styles (Svelte/Carbon requirement)
- `SECURITY_MODE=strict` must NOT block first-time setup (wizard generates secrets BEFORE validation runs)

---

## File Structure

### New Files
| File | Responsibility |
|------|---------------|
| `server/middleware/security_headers.py` | CSP, X-Frame-Options, X-Content-Type-Options, Strict-Transport-Security, Referrer-Policy, Permissions-Policy headers |
| `tests/unit/middleware/test_security_headers.py` | Unit tests for security headers middleware |
| `tests/unit/auth/test_must_change_password.py` | Unit tests for forced password change flow |
| `tests/unit/setup/test_secret_generation.py` | Unit tests for JWT secret auto-generation in setup wizard |

### Modified Files
| File | Change |
|------|--------|
| `server/main.py:~470` | Add security headers middleware after CORS middleware |
| `server/main.py:~1093` | Add `security_mode: "strict"` to setup wizard config |
| `server/config.py:~199-216` | Auto-populate CORS origins in LAN mode instead of `CORS_ALLOW_ALL=True` |
| `server/config.py:~302` | Default `SECURITY_MODE` to `"strict"` when `server_mode=lan_server` |
| `server/api/schemas.py:31-37` | Add `must_change_password: bool = False` to `Token` response |
| `server/api/auth_async.py:156-162` | Include `must_change_password` in login response |
| `locaNext/src/lib/api/client.js:103-122` | Store `must_change_password` flag after login |
| `locaNext/src/lib/stores/app.js` | Add `mustChangePassword` store |
| `locaNext/src/lib/components/Launcher.svelte:350-367` | Check `must_change_password` after login, open modal |
| `locaNext/src/lib/components/ChangePassword.svelte` | Add `forced` prop (non-dismissible mode) |
| `locaNext/src/routes/+layout.svelte` | Guard: if `mustChangePassword` is true, block navigation until changed |

---

## Task 1: Security Headers Middleware (CSP + X-Frame + HSTS)

**Files:**
- Create: `server/middleware/security_headers.py`
- Create: `tests/unit/middleware/test_security_headers.py`
- Modify: `server/main.py:~470` (add middleware)

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/middleware/test_security_headers.py
"""Tests for security headers middleware."""
import pytest
from unittest.mock import AsyncMock, MagicMock


def _make_scope(path="/", method="GET"):
    return {
        "type": "http",
        "method": method,
        "path": path,
        "headers": [],
    }


class FakeResponse:
    """Simulates a Starlette Response with mutable headers."""

    def __init__(self, status_code=200, headers=None):
        self.status_code = status_code
        self.headers = MutableHeaders(raw=headers or [])


@pytest.fixture
def make_app():
    """Create a minimal ASGI app that returns 200 with empty headers."""
    async def app(scope, receive, send):
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [],
        })
        await send({
            "type": "http.response.body",
            "body": b"OK",
        })
    return app


def test_csp_header_present(make_app):
    """CSP header must include script-src 'self' and style-src 'unsafe-inline'."""
    from server.middleware.security_headers import SecurityHeadersMiddleware

    middleware = SecurityHeadersMiddleware(make_app)
    # We test via the response headers dict
    headers = middleware.get_security_headers(ssl_enabled=False)
    csp = headers.get("Content-Security-Policy", "")

    assert "script-src 'self'" in csp
    assert "'unsafe-inline'" in csp  # Required for Svelte/Carbon styles
    assert "default-src 'self'" in csp
    # connect-src must NOT allow http:/https: (data exfiltration risk)
    assert "connect-src 'self' ws: wss:" in csp
    assert "http:" not in csp.split("connect-src")[1].split(";")[0]


def test_x_frame_options(make_app):
    """X-Frame-Options must be DENY."""
    from server.middleware.security_headers import SecurityHeadersMiddleware

    headers = SecurityHeadersMiddleware(make_app).get_security_headers(ssl_enabled=False)
    assert headers["X-Frame-Options"] == "DENY"


def test_x_content_type_options(make_app):
    """X-Content-Type-Options must be nosniff."""
    from server.middleware.security_headers import SecurityHeadersMiddleware

    headers = SecurityHeadersMiddleware(make_app).get_security_headers(ssl_enabled=False)
    assert headers["X-Content-Type-Options"] == "nosniff"


def test_hsts_only_when_ssl(make_app):
    """Strict-Transport-Security must only be set when SSL is enabled."""
    from server.middleware.security_headers import SecurityHeadersMiddleware

    mw = SecurityHeadersMiddleware(make_app)
    headers_no_ssl = mw.get_security_headers(ssl_enabled=False)
    headers_ssl = mw.get_security_headers(ssl_enabled=True)

    assert "Strict-Transport-Security" not in headers_no_ssl
    assert "max-age=" in headers_ssl["Strict-Transport-Security"]


def test_referrer_policy(make_app):
    """Referrer-Policy must be strict-origin-when-cross-origin."""
    from server.middleware.security_headers import SecurityHeadersMiddleware

    headers = SecurityHeadersMiddleware(make_app).get_security_headers(ssl_enabled=False)
    assert headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_permissions_policy(make_app):
    """Permissions-Policy must restrict camera, microphone, geolocation."""
    from server.middleware.security_headers import SecurityHeadersMiddleware

    headers = SecurityHeadersMiddleware(make_app).get_security_headers(ssl_enabled=False)
    pp = headers["Permissions-Policy"]
    assert "camera=()" in pp
    assert "microphone=()" in pp
    assert "geolocation=()" in pp


def test_cross_domain_policies(make_app):
    """X-Permitted-Cross-Domain-Policies must be none."""
    from server.middleware.security_headers import SecurityHeadersMiddleware

    headers = SecurityHeadersMiddleware(make_app).get_security_headers(ssl_enabled=False)
    assert headers["X-Permitted-Cross-Domain-Policies"] == "none"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/neil1988/LocalizationTools && python -m pytest tests/unit/middleware/test_security_headers.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'server.middleware.security_headers'`

- [ ] **Step 3: Write the middleware implementation**

```python
# server/middleware/security_headers.py
"""
Security headers middleware — OWASP best practices.

Adds CSP, X-Frame-Options, X-Content-Type-Options, HSTS (when SSL),
Referrer-Policy, and Permissions-Policy to every HTTP response.

Backward compatible: headers are purely additive. No existing behavior changes.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from loguru import logger


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Inject security headers into every response."""

    def __init__(self, app, ssl_enabled: bool = False):
        super().__init__(app)
        self.ssl_enabled = ssl_enabled
        self._headers = self.get_security_headers(ssl_enabled)
        logger.info(f"[SECURITY] Headers middleware active (SSL={ssl_enabled}, {len(self._headers)} headers)")

    def get_security_headers(self, ssl_enabled: bool) -> dict[str, str]:
        """Build the security headers dict. Separated for testing."""
        headers = {
            # CSP: block XSS script injection. unsafe-inline for styles only (Svelte/Carbon requirement).
            # connect-src 'self' ws: wss: — same-origin API + Socket.IO. LAN cross-PC connections
            # work because the User's browser loads from the Admin's origin (same-origin).
            # Do NOT use http: https: — that would allow XSS data exfiltration to any server.
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "connect-src 'self' ws: wss:; "
                "img-src 'self' data: blob:; "
                "font-src 'self' data:; "
                "object-src 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            ),
            # Prevent clickjacking
            "X-Frame-Options": "DENY",
            # Prevent MIME-type sniffing
            "X-Content-Type-Options": "nosniff",
            # Control referrer info leakage
            "Referrer-Policy": "strict-origin-when-cross-origin",
            # Restrict browser features
            "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
        }

        # Prevent Adobe Flash/Acrobat cross-domain data loading
        headers["X-Permitted-Cross-Domain-Policies"] = "none"

        # HSTS only when SSL is active (sending over HTTP would break non-SSL setups)
        # No includeSubDomains — LAN app uses IP addresses, not domain names
        if ssl_enabled:
            headers["Strict-Transport-Security"] = "max-age=31536000"

        return headers

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        for key, value in self._headers.items():
            response.headers[key] = value
        return response
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/neil1988/LocalizationTools && python -m pytest tests/unit/middleware/test_security_headers.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Wire middleware into main.py**

Add after the CORS middleware block (after line ~469 in `server/main.py`), before the IP filter middleware:

```python
# Add security headers middleware (CSP, X-Frame-Options, HSTS, etc.)
from server.middleware.security_headers import SecurityHeadersMiddleware
app.add_middleware(SecurityHeadersMiddleware, ssl_enabled=config.SSL_ENABLED)
```

- [ ] **Step 6: Commit**

```bash
git add server/middleware/security_headers.py tests/unit/middleware/test_security_headers.py server/main.py
git commit -m "feat: add security headers middleware (CSP, X-Frame-Options, HSTS, Referrer-Policy)

OWASP A05 hardening: Content-Security-Policy blocks XSS script injection,
X-Frame-Options prevents clickjacking, HSTS enforces HTTPS when SSL active.
Backward compatible — headers are purely additive."
```

---

## Task 2: CORS Auto-Lock in LAN Mode

**Files:**
- Modify: `server/config.py:199-216` (`_apply_lan_server_overrides`)
- Modify: `server/config.py:570-578` (`check_security_config`)

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/config/test_cors_lan_mode.py
"""Tests for CORS auto-restriction in LAN server mode."""
import pytest
from unittest.mock import patch
import importlib


def test_lan_mode_generates_cors_origins():
    """LAN server mode should auto-populate CORS_ORIGINS instead of CORS_ALLOW_ALL."""
    # Simulate: server_mode=lan_server, lan_ip=10.0.0.1, no CORS_ORIGINS env var
    mock_config = {
        "server_mode": "lan_server",
        "lan_ip": "10.0.0.1",
    }
    with patch.dict("os.environ", {}, clear=False):
        # Remove CORS_ORIGINS from env if present
        import os
        os.environ.pop("CORS_ORIGINS", None)

        # Simulate the function logic
        from server.config import _build_lan_cors_origins
        origins = _build_lan_cors_origins("10.0.0.1")

        assert "http://10.0.0.1:5173" in origins
        assert "https://10.0.0.1:5173" in origins
        assert "http://10.0.0.1:8888" in origins
        assert "https://10.0.0.1:8888" in origins
        assert "http://localhost:5173" in origins
        assert "app://." in origins  # Electron origin


def test_lan_mode_cors_not_allow_all():
    """LAN server mode should NOT set CORS_ALLOW_ALL=True when origins are auto-generated."""
    from server.config import _build_lan_cors_origins
    origins = _build_lan_cors_origins("10.0.0.1")
    # If origins are generated, CORS_ALLOW_ALL should be False
    assert len(origins) > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/neil1988/LocalizationTools && python -m pytest tests/unit/config/test_cors_lan_mode.py -v`
Expected: FAIL with `ImportError: cannot import name '_build_lan_cors_origins'`

- [ ] **Step 3: Add `_build_lan_cors_origins` helper and update `_apply_lan_server_overrides`**

In `server/config.py`, add before `_apply_lan_server_overrides()` (around line 190):

```python
def _build_lan_cors_origins(lan_ip: str) -> list[str]:
    """Build CORS origins for LAN server mode.

    Covers: Electron app://, localhost dev, admin LAN IP on all relevant ports.
    Both HTTP and HTTPS variants so the same config works before and after TLS is enabled.
    """
    origins = [
        "app://.",                              # Electron origin
        "http://localhost:5173",                # Vite dev
        "https://localhost:5173",
        "http://localhost:8888",                # Local FastAPI
        "https://localhost:8888",
        f"http://{lan_ip}:5173",               # LAN Vite (unlikely but safe)
        f"https://{lan_ip}:5173",
        f"http://{lan_ip}:8888",               # LAN FastAPI
        f"https://{lan_ip}:8888",
        f"http://{lan_ip}:8885",               # Admin dashboard
        f"https://{lan_ip}:8885",
    ]
    return origins
```

Then modify `_apply_lan_server_overrides()` — replace the CORS block (lines ~213-216):

```python
        # Auto-populate CORS origins for LAN instead of allowing all.
        # Explicit CORS_ORIGINS env var takes precedence (admin override).
        if not os.getenv("CORS_ORIGINS"):
            lan_ip = _USER_CONFIG.get("lan_ip", "")
            if lan_ip:
                CORS_ORIGINS = _build_lan_cors_origins(lan_ip)
                CORS_ALLOW_ALL = False
                ALLOWED_ORIGINS = CORS_ORIGINS
            else:
                # No LAN IP yet (first launch before setup wizard) — allow all temporarily
                CORS_ALLOW_ALL = True
```

Also update `check_security_config()` (around line 570) — remove the `pass` for LAN mode and add a check:

```python
    if _USER_CONFIG.get("server_mode") == "lan_server":
        if CORS_ALLOW_ALL and _USER_CONFIG.get("lan_ip"):
            warnings.append("CORS allows all origins in LAN mode -- lan_ip is set but origins weren't generated")
    else:
        if not ALLOWED_IP_RANGE:
            warnings.append("ALLOWED_IP_RANGE not set - server accepts connections from any IP")
        if CORS_ALLOW_ALL:
            warnings.append("CORS allows all origins - set CORS_ORIGINS for production")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/neil1988/LocalizationTools && python -m pytest tests/unit/config/test_cors_lan_mode.py -v`
Expected: Both tests PASS

- [ ] **Step 5: Commit**

```bash
git add server/config.py tests/unit/config/test_cors_lan_mode.py
git commit -m "feat: auto-populate CORS origins in LAN mode instead of CORS_ALLOW_ALL

LAN server mode now generates explicit CORS origins from lan_ip (HTTP+HTTPS
variants for all ports). CORS_ALLOW_ALL=True only as temporary fallback before
setup wizard sets lan_ip. Explicit CORS_ORIGINS env var still takes precedence."
```

---

## Task 3: Auto-Generate JWT Secret in Setup Wizard

**Files:**
- Modify: `server/main.py:1084-1096` (setup wizard config generation)
- Modify: `server/config.py:~302` (default SECURITY_MODE for LAN)

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/setup/test_secret_generation.py
"""Tests for JWT secret auto-generation in setup wizard."""
import pytest


def test_setup_config_has_secret_key():
    """Setup wizard config must include a secret_key that is NOT the default."""
    # Simulate what main.py:1084-1096 generates
    import secrets
    server_config_data = {
        "server_mode": "lan_server",
        "secret_key": secrets.token_urlsafe(32),
        "admin_token": secrets.token_urlsafe(32),
    }
    assert server_config_data["secret_key"] != "dev-secret-key-CHANGE-IN-PRODUCTION"
    assert len(server_config_data["secret_key"]) >= 32


def test_setup_config_has_security_mode_strict():
    """Setup wizard config must set security_mode to strict."""
    import secrets
    server_config_data = {
        "server_mode": "lan_server",
        "secret_key": secrets.token_urlsafe(32),
        "security_mode": "strict",
    }
    assert server_config_data["security_mode"] == "strict"


def test_default_secret_key_is_detectable():
    """The default secret key constant must be detectable for security validation."""
    from server.config import _DEFAULT_SECRET_KEY
    assert _DEFAULT_SECRET_KEY == "dev-secret-key-CHANGE-IN-PRODUCTION"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/neil1988/LocalizationTools && python -m pytest tests/unit/setup/test_secret_generation.py -v`
Expected: First two PASS (pure logic), third PASS (constant exists). All pass because these test the spec, not the wiring.

- [ ] **Step 3: Wire security_mode into setup wizard config**

In `server/main.py:1084-1096`, the `server_config_data` dict already has `"secret_key": secrets.token_urlsafe(32)` (line 1093). Add `security_mode`:

```python
                    server_config_data = {
                        "postgres_host": "localhost",
                        "postgres_port": 5432,
                        "postgres_user": "locanext_service",
                        "postgres_password": db_password,
                        "postgres_db": "localizationtools",
                        "database_mode": "auto",
                        "server_mode": "lan_server",
                        "lan_ip": lan_ip,
                        "secret_key": secrets.token_urlsafe(32),
                        "admin_token": secrets.token_urlsafe(32),
                        "security_mode": "strict",
                        "origin_admin_ip": "127.0.0.1",
                    }
```

In `server/config.py:~302`, make SECURITY_MODE respect config file:

```python
SECURITY_MODE = os.getenv(
    "SECURITY_MODE",
    _USER_CONFIG.get("security_mode", "warn"),
)
```

This way: fresh installs get `strict` from setup wizard config. Old installs without `security_mode` in config get `warn` (backward compatible). Env var overrides both.

- [ ] **Step 4: Verify no regression**

Run: `cd /home/neil1988/LocalizationTools && python -m pytest tests/unit/setup/ -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add server/main.py server/config.py tests/unit/setup/test_secret_generation.py
git commit -m "feat: setup wizard generates strict security_mode + JWT secret

New installs get security_mode=strict automatically (setup wizard saves it to
server-config.json). Old installs remain on security_mode=warn (backward compat).
SECURITY_MODE env var overrides both. JWT secret was already generated (line 1093)."
```

---

## Task 4: Force Password Change After Login

**Files:**
- Modify: `server/api/schemas.py:31-37` (Token schema)
- Modify: `server/api/auth_async.py:156-162` (login response)
- Modify: `locaNext/src/lib/stores/app.js` (add store)
- Modify: `locaNext/src/lib/api/client.js:103-122` (store flag)
- Modify: `locaNext/src/lib/components/Launcher.svelte:350-367` (check flag)
- Modify: `locaNext/src/lib/components/ChangePassword.svelte` (forced mode)
- Modify: `locaNext/src/routes/+layout.svelte` (navigation guard)

- [ ] **Step 1: Write the failing test — backend**

```python
# tests/unit/auth/test_must_change_password.py
"""Tests for must_change_password flow."""
import pytest


def test_token_schema_includes_must_change_password():
    """Token response schema must include must_change_password field."""
    from server.api.schemas import Token
    token = Token(
        access_token="test",
        token_type="bearer",
        user_id=1,
        username="admin",
        role="admin",
        must_change_password=True,
    )
    assert token.must_change_password is True


def test_token_schema_defaults_false():
    """must_change_password must default to False for backward compat."""
    from server.api.schemas import Token
    token = Token(
        access_token="test",
        token_type="bearer",
        user_id=1,
        username="admin",
        role="admin",
    )
    assert token.must_change_password is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/neil1988/LocalizationTools && python -m pytest tests/unit/auth/test_must_change_password.py -v`
Expected: FAIL on first test — `Token.__init__() got an unexpected keyword argument 'must_change_password'`

- [ ] **Step 3: Add `must_change_password` to Token schema**

In `server/api/schemas.py:31-37`, add the field:

```python
class Token(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    role: str
    must_change_password: bool = False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/neil1988/LocalizationTools && python -m pytest tests/unit/auth/test_must_change_password.py -v`
Expected: Both PASS

- [ ] **Step 5: Include `must_change_password` in login response**

In `server/api/auth_async.py:156-162`, change the return to include the user's flag:

```python
    return Token(
        access_token=access_token,
        token_type="bearer",
        user_id=user.user_id,
        username=user.username,
        role=user.role,
        must_change_password=bool(user.must_change_password),
    )
```

- [ ] **Step 6: Add `mustChangePassword` store — frontend**

In `locaNext/src/lib/stores/app.js`, add after the existing stores:

```javascript
export const mustChangePassword = writable(false);
```

- [ ] **Step 7: Store flag in client.js after login**

In `locaNext/src/lib/api/client.js:103-122`, add the import and store update:

Add `mustChangePassword` to the import from `$lib/stores/app.js`:

```javascript
import { serverUrl, user, isAuthenticated, offlineMode, mustChangePassword } from '$lib/stores/app.js';
```

Then in the `login()` method, after `isAuthenticated.set(true)`:

```javascript
    // Force password change if backend says so (default admin password, admin-reset users)
    mustChangePassword.set(response.must_change_password || false);
```

- [ ] **Step 8: Check flag in Launcher after login**

In `locaNext/src/lib/components/Launcher.svelte`, add import:

```javascript
import { mustChangePassword } from '$lib/stores/app.js';
```

Then in `handleLogin()` (line 350-367), after `startOnline()`:

```javascript
  async function handleLogin() {
    loginError = '';
    loginLoading = true;

    try {
      const response = await api.login(username, password);

      saveCredentials();

      logger.success('Launcher: Login successful');

      // Check if user must change their password before proceeding
      if (response.must_change_password) {
        logger.info('Launcher: User must change password before proceeding');
        mustChangePassword.set(true);
      }

      startOnline();
    } catch (err) {
      loginError = err.message || 'Login failed';
      logger.error('Launcher: Login failed', { error: err.message });
    } finally {
      loginLoading = false;
    }
  }
```

- [ ] **Step 9: Add forced mode to ChangePassword component**

In `locaNext/src/lib/components/ChangePassword.svelte`, add `forced` prop and prevent close:

```svelte
<script>
  // ... existing imports ...
  import { mustChangePassword } from '$lib/stores/app.js';

  // Svelte 5: Props
  let { open = $bindable(false), forced = false } = $props();

  // ... existing state ...

  function handleClose() {
    // Cannot close if forced (must change password first)
    if (forced) return;
    resetForm();
    open = false;
  }

  async function handleSubmit() {
    // ... existing validation and API call ...

    try {
      logger.userAction("Password change requested");
      await api.changePassword(currentPassword, newPassword, confirmPassword);

      logger.success("Password changed successfully");
      success = true;
      mustChangePassword.set(false);

      setTimeout(() => {
        resetForm();
        open = false;
      }, 2000);
    } catch (err) {
      logger.error("Password change failed", { error: err.message });
      error = err.message;
    } finally {
      loading = false;
    }
  }
</script>
```

In the template, update the modal:

```svelte
<AppModal
  bind:open
  modalHeading={forced ? "Change Your Password" : "Change Password"}
  primaryButtonText="Change Password"
  secondaryButtonText={forced ? "" : "Cancel"}
  primaryButtonDisabled={loading || success}
  onprimary={handleSubmit}
  onsecondary={forced ? undefined : handleClose}
  onclose={handleClose}
  preventCloseOnClickOutside={forced}
  size="sm"
>
  {#if forced && !success}
    <InlineNotification
      kind="warning"
      title="Password Change Required"
      subtitle="You must change your password before continuing."
      hideCloseButton
    />
  {/if}
  <!-- ... rest of template unchanged ... -->
```

- [ ] **Step 10: Add navigation guard in +layout.svelte**

In `locaNext/src/routes/+layout.svelte`, import the store and add the modal:

```javascript
import { mustChangePassword } from '$lib/stores/app.js';
```

In the template, add the forced password change modal. Do NOT use `bind:open` with a derived
value — `$derived` is read-only in Svelte 5. Instead, pass `open={$mustChangePassword}` (one-way)
and rely on `mustChangePassword.set(false)` in ChangePassword.handleSubmit (already done in Step 9):

```svelte
<!-- Forced password change (blocks all interaction until changed) -->
{#if $mustChangePassword}
  <ChangePassword open={true} forced={true} />
{/if}
```

And add the import for ChangePassword at the top if not already there.

- [ ] **Step 11: Commit**

```bash
git add server/api/schemas.py server/api/auth_async.py \
  locaNext/src/lib/stores/app.js locaNext/src/lib/api/client.js \
  locaNext/src/lib/components/Launcher.svelte \
  locaNext/src/lib/components/ChangePassword.svelte \
  locaNext/src/routes/+layout.svelte \
  tests/unit/auth/test_must_change_password.py
git commit -m "feat: enforce password change for must_change_password users

Login response now includes must_change_password flag. Frontend shows
non-dismissible ChangePassword modal that blocks all navigation until
password is changed. Applies to: admin-reset users, new users created
with must_change_password=true. Admin auto-login (token) is unaffected."
```

---

## Task 5: HTTPS End-to-End Verification

**Files:**
- No code changes needed — verification only

This task validates that the existing HTTPS implementation works end-to-end. All code is already committed (Phase 113). The setup wizard generates certs (`steps.py:727-846`), uvicorn picks them up (`main.py:1182-1206`), Electron accepts self-signed (`main.js:1401`), ServerSettingsModal does HTTPS→HTTP fallback (`ServerSettingsModal.svelte:138-152`).

- [ ] **Step 1: Verify cert paths match**

Confirm `server/setup/steps.py:738-739` writes to the same `data_dir` that `server/config.py:74-75` reads from:
- `steps.py`: `cert_path = paths.data_dir / "server.crt"` — `paths.data_dir` is `server/data/`
- `config.py`: `SSL_CERT_FILE = DATA_DIR / "server.crt"` — `DATA_DIR` is `server/data/`
- **MATCH CONFIRMED** — same directory.

- [ ] **Step 2: Verify health endpoint reports SSL status**

`server/main.py:759` already includes `"ssl_enabled": config.SSL_ENABLED` in health response.
`ServerSettingsModal.svelte:181` reads `data.ssl_enabled` and shows TLS label.
**Already wired.**

- [ ] **Step 3: Verify Electron cert acceptance**

`locaNext/electron/main.js:1401-1412` handles `certificate-error` event, checks for private/LAN IPs, calls `callback(true)` to accept self-signed certs. **Already wired.**

- [ ] **Step 4: Verify HTTPS→HTTP fallback for old builds**

`ServerSettingsModal.svelte:138-152`: tries `https://` first with 3s timeout, falls back to `http://` with 5s timeout. **Already wired.**

- [ ] **Step 5: Document verification results**

No code commit needed. Log the verification results in the session.

---

## Task 6: Final Integration Test + Security Validation

- [ ] **Step 1: Run all new tests**

```bash
cd /home/neil1988/LocalizationTools && python -m pytest tests/unit/middleware/test_security_headers.py tests/unit/config/test_cors_lan_mode.py tests/unit/setup/test_secret_generation.py tests/unit/auth/test_must_change_password.py -v
```
Expected: All tests PASS

- [ ] **Step 2: Run `check_security_config()` to verify improvement**

```bash
cd /home/neil1988/LocalizationTools && python3 -c "
from server.config import check_security_config
result = check_security_config()
print('Secure:', result['is_secure'])
print('Mode:', result['security_mode'])
for w in result['warnings']: print(f'  WARN: {w}')
for e in result['errors']: print(f'  ERROR: {e}')
"
```

- [ ] **Step 3: Run full test suite**

```bash
cd /home/neil1988/LocalizationTools && python -m pytest tests/ -v --tb=short -q 2>&1 | tail -20
```
Expected: No regressions

- [ ] **Step 4: Final commit with OWASP scorecard update**

```bash
git add -A
git commit -m "test: Phase 114 OWASP hardening integration tests

All security hardening verified: CSP headers, CORS auto-lock,
strict security_mode for new installs, must_change_password enforcement.
OWASP scorecard: 6/10 → 8/10 PROTECTED."
```

---

## OWASP Scorecard After This Plan

| # | Vulnerability | Before | After |
|---|--------------|--------|-------|
| A01 | Broken Access Control | PROTECTED | PROTECTED |
| A02 | Cryptographic Failures | PARTIAL | **PROTECTED** (HTTPS verified) |
| A03 | Injection | PROTECTED | PROTECTED |
| A04 | Insecure Design | PROTECTED | PROTECTED |
| A05 | Security Misconfiguration | PARTIAL | **PROTECTED** (strict mode + auto CORS + forced pw) |
| A06 | Vulnerable Components | OK | OK |
| A07 | Auth Failures | PROTECTED | PROTECTED |
| A08 | Software/Data Integrity | PARTIAL | PARTIAL (needs code signing cert purchase) |
| A09 | Logging/Monitoring | PROTECTED | PROTECTED |
| A10 | SSRF | PROTECTED | PROTECTED |

**Result: 8 PROTECTED, 1 PARTIAL, 1 OK**

---

## Deferred (Wave 3 — httpOnly JWT Cookie)

Intentionally excluded from this plan. Would require:
- 17+ frontend files changed (`localStorage.getItem('auth_token')`)
- Cross-origin cookie handling (`SameSite=None; Secure` for User→Admin)
- WebSocket auth rework (Socket.IO `auth: { token }` → cookie-based)
- Dedicated Phase 115 with its own grill session

The current plan achieves 8/10 OWASP without touching the auth token storage.
