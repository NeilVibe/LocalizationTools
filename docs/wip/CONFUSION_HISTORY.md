# Claude Confusion History

**Purpose:** Document every time Claude gets confused, hallucinates, or takes the wrong approach. This helps prevent repeating mistakes and identifies patterns that need better documentation.

---

## 2025-12-27 Session

### Confusion 1: Auto-Login Process
**What happened:**
- I tried to run CDP login with `CDP_TEST_USER` environment variables from WSL
- Environment variables don't pass through WSL-to-Windows node execution
- I didn't understand the proper auto-login flow

**Root cause:**
- Didn't read the documentation thoroughly
- Assumed I could pass env vars directly to Windows node from WSL

**Fix needed:**
- Document that credentials need to be passed differently for WSL-to-Windows
- Create a simpler login mechanism that doesn't require env vars

---

### Confusion 2: Build 397 Missing Changes
**What happened:**
- I made changes to VirtualGrid.svelte (hover CSS fix)
- Build 397 was marked successful
- But the deployed app didn't have the CSS fix

**Root cause:**
- I used the WRONG CSS variable (`--cds-layer-hover-02` vs `--cds-layer-hover-01`)
- The CSS WAS deployed, but it still had mismatched colors
- I didn't verify the actual deployed CSS until user complained

**Fix needed:**
- Always verify deployed changes by extracting app.asar and checking
- Don't mark issues as FIXED until visually verified

---

### Confusion 3: Playground Refresh vs Reinstall
**What happened:**
- I kept trying to reinstall the entire Playground app
- The install script wasn't found
- I didn't understand the update mechanism

**Root cause:**
- Not clear on difference between:
  - Full reinstall (download installer, run NSIS)
  - Update push (use auto-update feature)
  - Hot refresh (just reload the Electron app)

**Fix needed:**
- Document all three refresh methods clearly
- Create a "quick update" flow that doesn't require full reinstall

---

### Confusion 4: Where Scripts Live
**What happened:**
- I tried to run `./scripts/playground_install.sh` but it didn't exist
- The session summary said the script existed at that path

**Root cause:**
- Scripts may have been moved or the path was wrong
- I trusted outdated information from the summary

**Fix needed:**
- Update CLAUDE.md with correct script locations
- Create a script discovery command

---

### Confusion 5: neil/neil Credentials
**What happened:**
- Tried to login as neil/neil
- Got "Incorrect username or password"
- Had to discover admin/admin123 works

**Root cause:**
- Assumed neil/neil from old documentation
- The user "neil" exists but password might be different

**Fix needed:**
- Document correct test credentials
- Create a dedicated CI test user with known password

---

## Patterns Identified

1. **Documentation Trust Problem:** I trust documentation/summaries without verifying
2. **Environment Assumption:** I assume WSL-Windows interop works smoothly
3. **Verification Gap:** I mark things as "FIXED" before visual verification
4. **Path Confusion:** Script paths change and I don't verify they exist
5. **Credential Confusion:** Multiple users exist, unclear which to use

---

## Prevention Rules (Add to CLAUDE.md)

1. **ALWAYS verify script paths exist** before running
2. **ALWAYS extract and check deployed CSS** after build
3. **NEVER trust env var passing** from WSL to Windows
4. **ALWAYS use known credentials** (admin/admin123)
5. **ALWAYS take screenshots** as proof of fixes

---

*Created: 2025-12-27 | Purpose: Prevent Claude from repeating mistakes*
