# Session Context — 2026-04-05

## Current Work
- Phase 114: OWASP Security Hardening (DONE, builds running)
- Phase 113: LAN Connection Fix (DONE, included in builds)
- Builds: GitHub Admin + User, Gitea Full — monitoring every 300s

## What Was Done This Session (2026-04-05)

### Phase 114 — OWASP Security Hardening
- OWASP scorecard: 6/10 → 8/10 PROTECTED
- SecurityHeadersMiddleware: CSP, X-Frame-Options DENY, HSTS, Referrer-Policy, Permissions-Policy
- CORS auto-lock: LAN mode generates 13 explicit origins from lan_ip (no more CORS_ALLOW_ALL)
- Strict security mode: new installs get security_mode=strict from setup wizard
- Forced password change: must_change_password in Token response + non-dismissible modal
- 103 tests (unit + integration), 6-agent final review
- Full PostgreSQL simulation: real PG, real network IP, real CORS, real auth

### Privacy Scrub
- 340+ files scrubbed: internal IPs, usernames, Korean names, PC names
- Zero sensitive data on public GitHub (neilvibe/MYCOM kept — public/low-risk)
- CI injects real Gitea URL at build time (localhost placeholder in repo)
- Scripts now use $HOME / Path.home() (more portable)

### Builds Triggered
- GitHub Admin: run 23985566344
- GitHub User: auto-triggers after Admin
- Gitea Full: run 576

## Next Session
- Check build results (3 greens target)
- PEARL testing: install new builds, test LAN connection, images, language switching
- If builds fail: debug and fix

## Key Commits (2026-04-05)
| Hash | What |
|------|------|
| 2bef1073 | Phase 114 OWASP hardening |
| 1f53baaf | Integration tests (20 tests) |
| ab54efa0 | Scrub PEARL IPs |
| 70c47a9d | Full privacy scrub (340 files) |
| bf6027e8 | Restore neilvibe |
| debafe4b | Fix $HOME paths |
| da4b36dd | CI build-time URL injection |
