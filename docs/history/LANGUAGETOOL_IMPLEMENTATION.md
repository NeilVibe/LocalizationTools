# LanguageTool Implementation - WIP

**Status:** PLANNED | **Priority:** 2 | **Effort:** 7-10 hours

---

## Overview

Self-hosted spelling/grammar/style checking for target text in LDM.

| Feature | Value |
|---------|-------|
| **Cost** | $0 (self-hosted, LGPL 2.1) |
| **Limits** | None |
| **Languages** | 30+ (EN, DE, FR, ES, PT, RU, PL, NL, IT, etc.) |
| **Checks** | Spelling + Grammar + Style |
| **Smart** | Context-aware (catches "their" vs "there") |

**Note:** Korean NOT supported. Only target languages get checked.

---

## Architecture: Central Server

```
Central Server (172.28.150.120)
├── PostgreSQL (:5432)        ← already running
└── LanguageTool Server (:8081) ← NEW

LocaNext.exe (User PC)
├── Frontend: Right-click file → "Check Spelling/Grammar"
├── Backend: POST /api/ldm/files/{id}/check-grammar
└── HTTP call to central LT server
```

### Why Central (Not Bundled)

| Aspect | Bundled | Central (chosen) |
|--------|---------|------------------|
| Install size | +200MB each | +0 |
| Java required | Each PC | Server only |
| Maintenance | Per install | One place |
| Updates | Redeploy app | Update server |
| Offline mode | Works | No grammar check |

**Trade-off accepted:** Offline mode = no grammar check (QA feature, not critical)

---

## Resource Usage (Monitor This)

| Resource | Expected | Notes |
|----------|----------|-------|
| **RAM** | 400-800MB | Java heap, varies by load |
| **CPU** | Low idle, spikes on check | Batch requests help |
| **Disk** | ~200MB | Server installation |
| **Network** | Minimal | JSON over HTTP |

**Action:** Monitor server during testing. Adjust if needed.

---

## Implementation Phases

### Phase 1: Central Server Setup

**Effort:** 2-3 hours

| Step | Task | Command/Details |
|------|------|-----------------|
| 1.1 | SSH to central server | `ssh user@172.28.150.120` |
| 1.2 | Install Java (if needed) | `sudo apt install openjdk-17-jre-headless` |
| 1.3 | Download LanguageTool | Get ZIP from GitHub releases (~200MB) |
| 1.4 | Extract | `unzip LanguageTool-*.zip -d /opt/languagetool` |
| 1.5 | Create systemd service | Auto-start on boot |
| 1.6 | Start server | `systemctl start languagetool` |
| 1.7 | Test endpoint | `curl http://172.28.150.120:8081/v2/check` |
| 1.8 | Open firewall | Port 8081 for internal network |

**Systemd service file:** `/etc/systemd/system/languagetool.service`
```ini
[Unit]
Description=LanguageTool Server
After=network.target

[Service]
Type=simple
User=languagetool
WorkingDirectory=/opt/languagetool/LanguageTool-6.x
ExecStart=/usr/bin/java -cp languagetool-server.jar org.languagetool.server.HTTPServer --port 8081 --allow-origin "*"
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Health check URL:** `http://172.28.150.120:8081/v2/check?language=en-US&text=test`

---

### Phase 2: Backend Endpoint

**Effort:** 1-2 hours

#### 2.1 Create LanguageTool Client

**File:** `server/utils/languagetool.py`

```python
import httpx
from typing import Optional
from server.utils.logger import logger

LANGUAGETOOL_URL = "http://172.28.150.120:8081/v2/check"

class LanguageToolClient:
    """Client for LanguageTool API."""

    def __init__(self, base_url: str = LANGUAGETOOL_URL):
        self.base_url = base_url

    async def check(self, text: str, language: str = "en-US") -> dict:
        """
        Check text for spelling/grammar errors.

        Args:
            text: Text to check
            language: Language code (en-US, de-DE, fr, es, etc.)

        Returns:
            Dict with matches (errors) and metadata
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.base_url,
                    data={"text": text, "language": language}
                )
                response.raise_for_status()
                return response.json()
        except httpx.ConnectError:
            logger.warning("LanguageTool server not available")
            return {"matches": [], "error": "Server unavailable"}
        except Exception as e:
            logger.error(f"LanguageTool error: {e}")
            return {"matches": [], "error": str(e)}

    async def is_available(self) -> bool:
        """Check if LanguageTool server is running."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}?language=en-US&text=test")
                return response.status_code == 200
        except:
            return False

# Singleton instance
languagetool = LanguageToolClient()
```

#### 2.2 Create Grammar Check Endpoint

**File:** `server/tools/ldm/routes/grammar.py`

```python
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from server.utils.languagetool import languagetool
from server.tools.ldm.tm_manager import TMManager

router = APIRouter(prefix="/api/ldm", tags=["ldm-grammar"])

class GrammarError(BaseModel):
    row_id: int
    row_number: int
    text: str
    message: str
    offset: int
    length: int
    replacements: List[str]
    rule_id: str
    category: str

class GrammarCheckRequest(BaseModel):
    language: str = "en-US"

class GrammarCheckResponse(BaseModel):
    file_id: int
    language: str
    total_rows: int
    rows_with_errors: int
    total_errors: int
    errors: List[GrammarError]
    server_available: bool

@router.post("/files/{file_id}/check-grammar", response_model=GrammarCheckResponse)
async def check_grammar(file_id: int, request: GrammarCheckRequest):
    """
    Check spelling/grammar for all target text in a file.
    Uses central LanguageTool server.
    """
    # Check server availability
    if not await languagetool.is_available():
        raise HTTPException(
            status_code=503,
            detail="LanguageTool server is not available. Grammar check requires online connection."
        )

    # Get file rows from database
    tm = TMManager()
    rows = await tm.get_file_rows(file_id)

    if not rows:
        raise HTTPException(status_code=404, detail="File not found or empty")

    errors = []
    rows_with_errors = set()

    for row in rows:
        target_text = row.get("target", "")
        if not target_text:
            continue

        result = await languagetool.check(target_text, request.language)

        for match in result.get("matches", []):
            errors.append(GrammarError(
                row_id=row["id"],
                row_number=row["row_number"],
                text=target_text,
                message=match["message"],
                offset=match["offset"],
                length=match["length"],
                replacements=[r["value"] for r in match.get("replacements", [])[:5]],
                rule_id=match["rule"]["id"],
                category=match["rule"]["category"]["name"]
            ))
            rows_with_errors.add(row["id"])

    return GrammarCheckResponse(
        file_id=file_id,
        language=request.language,
        total_rows=len(rows),
        rows_with_errors=len(rows_with_errors),
        total_errors=len(errors),
        errors=errors,
        server_available=True
    )

@router.get("/grammar/status")
async def grammar_status():
    """Check if LanguageTool server is available."""
    available = await languagetool.is_available()
    return {
        "available": available,
        "server_url": languagetool.base_url
    }
```

#### 2.3 Register Router

**File:** `server/tools/ldm/router.py` (edit)

```python
from server.tools.ldm.routes.grammar import router as grammar_router
# ... add to router includes
```

---

### Phase 3: Frontend UI

**Effort:** 3-4 hours

#### 3.1 Add Context Menu Item

**File:** `locaNext/src/lib/components/ldm/FileExplorer.svelte` (edit)

Add to context menu:
```svelte
<MenuItem on:click={() => checkGrammar(file.id)}>
    Check Spelling/Grammar
</MenuItem>
```

#### 3.2 Create Grammar Check Modal

**File:** `locaNext/src/lib/components/ldm/GrammarCheckModal.svelte` (NEW)

Features:
- Language selector dropdown (EN-US, DE-DE, FR, ES, etc.)
- "Check" button to start
- Loading spinner during check
- Results grouped by row
- Error highlight with context
- One-click "Apply Fix" button
- "Export to Excel" button
- Error count summary

#### 3.3 API Integration

**File:** `locaNext/src/lib/api/ldm.ts` (edit)

```typescript
export async function checkGrammar(fileId: number, language: string = "en-US") {
    return await post(`/api/ldm/files/${fileId}/check-grammar`, { language });
}

export async function getGrammarStatus() {
    return await get("/api/ldm/grammar/status");
}
```

---

### Phase 4: Testing

**Effort:** 1 hour

| Test | Description |
|------|-------------|
| Unit test | `languagetool.py` client |
| Integration test | `/check-grammar` endpoint |
| E2E test | Full flow via CDP |
| Offline test | Graceful degradation |
| Load test | Multiple concurrent checks |

---

## Supported Languages

| Code | Language | Code | Language |
|------|----------|------|----------|
| en-US | English (US) | de-DE | German |
| en-GB | English (UK) | fr | French |
| es | Spanish | pt-BR | Portuguese (BR) |
| pt-PT | Portuguese (PT) | ru | Russian |
| pl | Polish | nl | Dutch |
| it | Italian | uk | Ukrainian |
| zh-CN | Chinese (Simplified) | ja | Japanese |

**Not Supported:** Korean (ko) - source text won't be checked

---

## API Response Example

```json
{
    "file_id": 123,
    "language": "en-US",
    "total_rows": 500,
    "rows_with_errors": 12,
    "total_errors": 18,
    "errors": [
        {
            "row_id": 45,
            "row_number": 46,
            "text": "He dont know nothing.",
            "message": "Use \"doesn't\" instead of \"dont\"",
            "offset": 3,
            "length": 4,
            "replacements": ["doesn't"],
            "rule_id": "DONT",
            "category": "Grammar"
        }
    ],
    "server_available": true
}
```

---

## Files Summary

| File | Action | Purpose |
|------|--------|---------|
| `server/utils/languagetool.py` | NEW | LT client wrapper |
| `server/tools/ldm/routes/grammar.py` | NEW | Grammar check endpoint |
| `server/tools/ldm/router.py` | EDIT | Register grammar router |
| `locaNext/src/lib/components/ldm/FileExplorer.svelte` | EDIT | Context menu item |
| `locaNext/src/lib/components/ldm/GrammarCheckModal.svelte` | NEW | Results UI |
| `locaNext/src/lib/api/ldm.ts` | EDIT | API functions |
| `server/tests/tools/ldm/test_grammar.py` | NEW | Unit tests |

---

## Dependencies

| Dependency | Version | Notes |
|------------|---------|-------|
| `httpx` | Already in requirements | Async HTTP client |
| Java 17+ | Server only | Not needed on client PCs |
| LanguageTool | 6.x | Download from GitHub |

---

## Rollback Plan

If issues arise:
1. Stop LanguageTool service on central server
2. Endpoint returns 503 gracefully
3. Frontend shows "Grammar check unavailable (offline)"
4. No client-side changes needed

---

## Checklist

- [ ] **Phase 1: Server Setup**
  - [ ] SSH to central server
  - [ ] Install Java 17
  - [ ] Download LanguageTool
  - [ ] Create systemd service
  - [ ] Start and test
  - [ ] Open firewall port 8081

- [ ] **Phase 2: Backend**
  - [ ] Create `languagetool.py` client
  - [ ] Create `grammar.py` route
  - [ ] Register router
  - [ ] Test endpoint locally

- [ ] **Phase 3: Frontend**
  - [ ] Add context menu item
  - [ ] Create GrammarCheckModal
  - [ ] Add API functions
  - [ ] Test full flow

- [ ] **Phase 4: Testing**
  - [ ] Unit tests
  - [ ] Integration tests
  - [ ] E2E test (CDP)
  - [ ] Monitor server resources

---

*Created: 2025-12-25 | Central server architecture*
