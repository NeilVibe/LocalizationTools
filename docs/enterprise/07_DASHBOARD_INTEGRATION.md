# 07 - Dashboard Integration

**Purpose:** Sending data to company dashboards and external systems

---

## Overview

LocaNext can send metrics and events to external systems:
- Company dashboards (usage stats, progress)
- Monitoring systems (Prometheus, Grafana)
- SIEM/logging (Splunk, ELK)
- Custom webhooks

---

## Integration Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    LOCANEXT BACKEND                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────────────────────────────┐  │
│  │ Internal     │    │  Telemetry Module                     │  │
│  │ Operations   │───►│  server/telemetry/                    │  │
│  │              │    │  ├─ collector.py (gather metrics)     │  │
│  └──────────────┘    │  ├─ exporters/                        │  │
│                      │  │   ├─ webhook.py                    │  │
│                      │  │   ├─ prometheus.py                 │  │
│                      │  │   └─ custom.py                     │  │
│                      │  └─ config.py                         │  │
│                      └──────────────────────────────────────┘  │
│                                    │                            │
└────────────────────────────────────┼────────────────────────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
                    ▼                ▼                ▼
           ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
           │ Company      │  │ Prometheus   │  │ Custom       │
           │ Dashboard    │  │ /Grafana     │  │ Webhook      │
           │              │  │              │  │              │
           └──────────────┘  └──────────────┘  └──────────────┘
```

---

## Configuration

### Environment Variables

```bash
# .env or server/config.py

# Enable telemetry export
TELEMETRY_ENABLED=true

# Company dashboard webhook
DASHBOARD_WEBHOOK_URL=https://dashboard.company.com/api/locanext/metrics
DASHBOARD_WEBHOOK_TOKEN=your_api_token_here
DASHBOARD_WEBHOOK_INTERVAL=300  # seconds (5 minutes)

# Prometheus (if used)
PROMETHEUS_ENABLED=false
PROMETHEUS_PORT=9090

# Custom webhook
CUSTOM_WEBHOOK_URL=
CUSTOM_WEBHOOK_EVENTS=login,file_upload,translation_complete
```

---

## Available Metrics

### User Activity

| Metric | Description | Type |
|--------|-------------|------|
| `active_users` | Currently logged-in users | gauge |
| `login_count` | Total logins today | counter |
| `session_duration_avg` | Average session length (minutes) | gauge |

### Translation Metrics

| Metric | Description | Type |
|--------|-------------|------|
| `files_uploaded` | Files uploaded today | counter |
| `rows_translated` | Rows translated today | counter |
| `words_translated` | Words translated today | counter |
| `tm_matches_used` | TM matches applied | counter |
| `projects_active` | Active projects | gauge |

### System Metrics

| Metric | Description | Type |
|--------|-------------|------|
| `api_requests` | API requests per minute | gauge |
| `db_connections` | Active DB connections | gauge |
| `error_count` | Errors in last hour | counter |
| `backend_uptime` | Server uptime (seconds) | gauge |

---

## Webhook Integration

### Create Telemetry Exporter

Create `server/telemetry/exporters/webhook.py`:

```python
import httpx
import logging
from datetime import datetime
from typing import Dict, Any
from server.config import (
    DASHBOARD_WEBHOOK_URL,
    DASHBOARD_WEBHOOK_TOKEN
)

logger = logging.getLogger(__name__)

class WebhookExporter:
    """Export metrics to company dashboard via webhook."""

    def __init__(self):
        self.url = DASHBOARD_WEBHOOK_URL
        self.token = DASHBOARD_WEBHOOK_TOKEN
        self.client = httpx.AsyncClient(timeout=30)

    async def send_metrics(self, metrics: Dict[str, Any]) -> bool:
        """Send metrics to dashboard."""
        if not self.url:
            logger.debug("Webhook URL not configured")
            return False

        payload = {
            "source": "locanext",
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": metrics
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }

        try:
            response = await self.client.post(
                self.url,
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            logger.info(f"Metrics sent to dashboard: {len(metrics)} metrics")
            return True

        except httpx.HTTPError as e:
            logger.error(f"Failed to send metrics: {e}")
            return False

    async def send_event(self, event_type: str, data: Dict[str, Any]) -> bool:
        """Send individual event to dashboard."""
        if not self.url:
            return False

        payload = {
            "source": "locanext",
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "data": data
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }

        try:
            # Events go to /events endpoint
            event_url = self.url.replace("/metrics", "/events")
            response = await self.client.post(
                event_url,
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            return True

        except httpx.HTTPError as e:
            logger.error(f"Failed to send event: {e}")
            return False
```

### Metrics Collector

Create `server/telemetry/collector.py`:

```python
from datetime import datetime, timedelta
from typing import Dict, Any
from sqlalchemy import func
from server.database.db_setup import get_session
from server.database.models import User, LDMFile, LDMRow, UserSession

class MetricsCollector:
    """Collect metrics from database."""

    async def collect_all(self) -> Dict[str, Any]:
        """Collect all metrics."""
        return {
            "user_metrics": await self.collect_user_metrics(),
            "translation_metrics": await self.collect_translation_metrics(),
            "system_metrics": await self.collect_system_metrics()
        }

    async def collect_user_metrics(self) -> Dict[str, Any]:
        """Collect user-related metrics."""
        with get_session() as session:
            # Active users (session in last 30 minutes)
            cutoff = datetime.utcnow() - timedelta(minutes=30)
            active_users = session.query(func.count(UserSession.id)).filter(
                UserSession.last_activity > cutoff
            ).scalar()

            # Logins today
            today = datetime.utcnow().date()
            logins_today = session.query(func.count(UserSession.id)).filter(
                func.date(UserSession.created_at) == today
            ).scalar()

            return {
                "active_users": active_users or 0,
                "logins_today": logins_today or 0,
                "total_users": session.query(func.count(User.id)).scalar() or 0
            }

    async def collect_translation_metrics(self) -> Dict[str, Any]:
        """Collect translation-related metrics."""
        with get_session() as session:
            today = datetime.utcnow().date()

            # Files uploaded today
            files_today = session.query(func.count(LDMFile.id)).filter(
                func.date(LDMFile.created_at) == today
            ).scalar()

            # Total rows
            total_rows = session.query(func.count(LDMRow.id)).scalar()

            # Rows modified today
            rows_modified = session.query(func.count(LDMRow.id)).filter(
                func.date(LDMRow.updated_at) == today
            ).scalar()

            return {
                "files_uploaded_today": files_today or 0,
                "total_rows": total_rows or 0,
                "rows_modified_today": rows_modified or 0
            }

    async def collect_system_metrics(self) -> Dict[str, Any]:
        """Collect system metrics."""
        import psutil

        return {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent
        }
```

### Schedule Metrics Export

In `server/main.py`:

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from server.telemetry.collector import MetricsCollector
from server.telemetry.exporters.webhook import WebhookExporter

# Initialize
collector = MetricsCollector()
webhook_exporter = WebhookExporter()
scheduler = AsyncIOScheduler()

async def export_metrics_job():
    """Scheduled job to export metrics."""
    metrics = await collector.collect_all()
    await webhook_exporter.send_metrics(metrics)

# Schedule every 5 minutes
scheduler.add_job(export_metrics_job, 'interval', minutes=5)
scheduler.start()
```

---

## Event Hooks

### Send Events on Actions

```python
# In your API endpoints

from server.telemetry.exporters.webhook import WebhookExporter

webhook = WebhookExporter()

@router.post("/api/ldm/files/upload")
async def upload_file(file: UploadFile, current_user: User):
    # ... upload logic ...

    # Send event
    await webhook.send_event("file_upload", {
        "user": current_user.username,
        "filename": file.filename,
        "size_bytes": file.size,
        "project_id": project_id
    })

    return {"success": True}
```

### Available Events

| Event | When | Data |
|-------|------|------|
| `user_login` | User logs in | username, ip, timestamp |
| `user_logout` | User logs out | username, session_duration |
| `file_upload` | File uploaded | user, filename, size, project |
| `file_export` | File exported | user, filename, format |
| `translation_saved` | Row saved | user, file_id, row_count |
| `tm_match_applied` | TM match used | user, match_percent, source |
| `error` | Error occurred | type, message, user |

---

## Company Dashboard API Spec

If your company needs to build a dashboard receiver:

### Metrics Endpoint

```
POST /api/locanext/metrics
Authorization: Bearer <token>
Content-Type: application/json

{
  "source": "locanext",
  "timestamp": "2025-12-16T12:00:00Z",
  "metrics": {
    "user_metrics": {
      "active_users": 15,
      "logins_today": 42,
      "total_users": 100
    },
    "translation_metrics": {
      "files_uploaded_today": 8,
      "total_rows": 150000,
      "rows_modified_today": 1250
    },
    "system_metrics": {
      "cpu_percent": 25.5,
      "memory_percent": 60.2,
      "disk_percent": 45.0
    }
  }
}
```

### Events Endpoint

```
POST /api/locanext/events
Authorization: Bearer <token>
Content-Type: application/json

{
  "source": "locanext",
  "timestamp": "2025-12-16T12:05:30Z",
  "event_type": "file_upload",
  "data": {
    "user": "john.doe",
    "filename": "game_strings.xlsx",
    "size_bytes": 524288,
    "project_id": 42
  }
}
```

---

## Prometheus Integration (Optional)

If using Prometheus/Grafana:

### Expose Metrics Endpoint

```python
# server/telemetry/exporters/prometheus.py
from prometheus_client import Counter, Gauge, generate_latest
from fastapi import Response

# Define metrics
REQUESTS_TOTAL = Counter('locanext_requests_total', 'Total API requests')
ACTIVE_USERS = Gauge('locanext_active_users', 'Current active users')
ROWS_TRANSLATED = Counter('locanext_rows_translated', 'Rows translated')

@router.get("/metrics")
async def metrics():
    return Response(
        content=generate_latest(),
        media_type="text/plain"
    )
```

### Prometheus Config

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'locanext'
    static_configs:
      - targets: ['10.10.30.50:8888']
    metrics_path: '/metrics'
    scrape_interval: 30s
```

---

## Testing Integration

### Test Webhook

```bash
# Manual test
curl -X POST https://dashboard.company.com/api/locanext/metrics \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "source": "locanext",
    "timestamp": "2025-12-16T12:00:00Z",
    "metrics": {"test": true}
  }'
```

### Verify in Logs

```bash
# Check LocaNext logs
tail -f /var/log/locanext/app.log | grep "Metrics sent"
```

---

## Next Step

Dashboard integration configured. Proceed to [08_DATABASE_INTEGRATION.md](08_DATABASE_INTEGRATION.md) for external database connections.
