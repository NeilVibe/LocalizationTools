# 08 - Database Integration

**Purpose:** Connecting to external databases, data centers, and sync

---

## Overview

LocaNext can integrate with external databases:
- Use company's existing PostgreSQL server
- Connect to data center databases
- Sync data between systems
- Import/export to other databases

---

## Database Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| **Standalone** | LocaNext's own PostgreSQL | Default setup |
| **External DB** | Company's existing PostgreSQL | Enterprise integration |
| **Hybrid** | Primary + read replicas | High availability |
| **Multi-DB** | Different DBs for different data | Compliance, data residency |

---

## Using Company's Existing PostgreSQL

### Requirements

Your DBA needs to:
1. Create database for LocaNext
2. Create user with appropriate permissions
3. Allow network access from LocaNext server
4. Provide connection details

### Database Setup (DBA Tasks)

```sql
-- Run as PostgreSQL superuser

-- 1. Create database
CREATE DATABASE locanext
    ENCODING 'UTF8'
    LC_COLLATE 'en_US.UTF-8'
    LC_CTYPE 'en_US.UTF-8';

-- 2. Create application user
CREATE USER locanext_app WITH ENCRYPTED PASSWORD 'SECURE_PASSWORD';

-- 3. Grant permissions
GRANT CONNECT ON DATABASE locanext TO locanext_app;
\c locanext
GRANT USAGE ON SCHEMA public TO locanext_app;
GRANT CREATE ON SCHEMA public TO locanext_app;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO locanext_app;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO locanext_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO locanext_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO locanext_app;

-- 4. Allow network access (pg_hba.conf)
-- Add: host locanext locanext_app 10.10.30.0/24 scram-sha-256
```

### Configure LocaNext

```bash
# .env
POSTGRES_HOST=db.company.com
POSTGRES_PORT=5432
POSTGRES_USER=locanext_app
POSTGRES_PASSWORD=SECURE_PASSWORD
POSTGRES_DB=locanext
```

### Test Connection

```bash
cd ~/LocaNext
source venv/bin/activate
python3 -c "
from server.database.db_setup import test_connection
result = test_connection()
print(f'Connection: {result}')
"
```

---

## Data Center Integration

### Connecting to Data Center PostgreSQL

If your company has a central data center:

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATA CENTER                               │
│                                                                  │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │  PostgreSQL Cluster                                       │  │
│   │  ├─ Primary: db-primary.dc.company.com:5432              │  │
│   │  ├─ Replica: db-replica1.dc.company.com:5432             │  │
│   │  └─ Replica: db-replica2.dc.company.com:5432             │  │
│   └──────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │ VPN / Private Network
                              │
┌─────────────────────────────┼───────────────────────────────────┐
│                OFFICE NETWORK                                    │
│                              │                                   │
│   ┌──────────────────────────┼───────────────────────────────┐  │
│   │  LocaNext Server (10.10.30.50)                            │  │
│   │  └─ Connects to data center PostgreSQL                    │  │
│   └──────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Configuration for Data Center

```bash
# .env for data center connection
POSTGRES_HOST=db-primary.dc.company.com
POSTGRES_PORT=5432
POSTGRES_USER=locanext_app
POSTGRES_PASSWORD=SECURE_PASSWORD
POSTGRES_DB=locanext

# Connection pooling (recommended for data center)
POSTGRES_POOL_SIZE=20
POSTGRES_MAX_OVERFLOW=30
POSTGRES_POOL_TIMEOUT=30

# SSL required for data center
POSTGRES_SSL_MODE=require
POSTGRES_SSL_CERT=/etc/locanext/certs/client.crt
POSTGRES_SSL_KEY=/etc/locanext/certs/client.key
POSTGRES_SSL_ROOT_CERT=/etc/locanext/certs/ca.crt
```

### SSL Configuration

```python
# server/database/db_setup.py - add SSL support

from sqlalchemy import create_engine
from server.config import (
    POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER,
    POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_SSL_MODE,
    POSTGRES_SSL_CERT, POSTGRES_SSL_KEY, POSTGRES_SSL_ROOT_CERT
)

def get_engine():
    """Create database engine with SSL if configured."""

    base_url = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

    connect_args = {}

    if POSTGRES_SSL_MODE:
        connect_args["sslmode"] = POSTGRES_SSL_MODE

        if POSTGRES_SSL_CERT:
            connect_args["sslcert"] = POSTGRES_SSL_CERT
        if POSTGRES_SSL_KEY:
            connect_args["sslkey"] = POSTGRES_SSL_KEY
        if POSTGRES_SSL_ROOT_CERT:
            connect_args["sslrootcert"] = POSTGRES_SSL_ROOT_CERT

    return create_engine(
        base_url,
        connect_args=connect_args,
        pool_size=POSTGRES_POOL_SIZE,
        max_overflow=POSTGRES_MAX_OVERFLOW,
        pool_timeout=POSTGRES_POOL_TIMEOUT
    )
```

---

## Data Sync with External Systems

### Export to External Database

```python
# server/integrations/data_export.py

import asyncio
from sqlalchemy import create_engine, text
from server.database.db_setup import get_session
from server.database.models import LDMRow

class DataExporter:
    """Export data to external databases."""

    def __init__(self, target_connection_string: str):
        self.target_engine = create_engine(target_connection_string)

    async def export_translations(self, file_id: int, target_table: str):
        """Export translations to external database."""

        with get_session() as source_session:
            rows = source_session.query(LDMRow).filter(
                LDMRow.file_id == file_id
            ).all()

            with self.target_engine.connect() as target_conn:
                for row in rows:
                    target_conn.execute(
                        text(f"""
                            INSERT INTO {target_table}
                            (source_text, target_text, status, updated_at)
                            VALUES (:source, :target, :status, :updated)
                            ON CONFLICT (source_text)
                            DO UPDATE SET
                                target_text = :target,
                                status = :status,
                                updated_at = :updated
                        """),
                        {
                            "source": row.source,
                            "target": row.target,
                            "status": row.status,
                            "updated": row.updated_at
                        }
                    )
                target_conn.commit()

        return len(rows)
```

### Import from External Database

```python
# server/integrations/data_import.py

class DataImporter:
    """Import data from external databases."""

    def __init__(self, source_connection_string: str):
        self.source_engine = create_engine(source_connection_string)

    async def import_translations(self, source_table: str, target_file_id: int):
        """Import translations from external database."""

        with self.source_engine.connect() as source_conn:
            result = source_conn.execute(
                text(f"SELECT source_text, target_text FROM {source_table}")
            )
            rows = result.fetchall()

        with get_session() as target_session:
            for source_text, target_text in rows:
                # Find or create row
                ldm_row = target_session.query(LDMRow).filter(
                    LDMRow.file_id == target_file_id,
                    LDMRow.source == source_text
                ).first()

                if ldm_row:
                    ldm_row.target = target_text
                else:
                    ldm_row = LDMRow(
                        file_id=target_file_id,
                        source=source_text,
                        target=target_text
                    )
                    target_session.add(ldm_row)

            target_session.commit()

        return len(rows)
```

---

## API for External Data Access

### REST API Endpoints

```python
# server/api/external_data.py

from fastapi import APIRouter, Depends, HTTPException
from server.auth.dependencies import get_current_admin

router = APIRouter(prefix="/api/external", tags=["external"])

@router.post("/export/{file_id}")
async def export_file(
    file_id: int,
    target_db: str,  # Connection string (encrypted/from config)
    target_table: str,
    current_user = Depends(get_current_admin)
):
    """Export file to external database."""
    exporter = DataExporter(target_db)
    count = await exporter.export_translations(file_id, target_table)
    return {"exported_rows": count}

@router.post("/import")
async def import_data(
    source_db: str,
    source_table: str,
    target_file_id: int,
    current_user = Depends(get_current_admin)
):
    """Import data from external database."""
    importer = DataImporter(source_db)
    count = await importer.import_translations(source_table, target_file_id)
    return {"imported_rows": count}
```

---

## Scheduled Data Sync

### Configure Sync Job

```python
# server/jobs/data_sync.py

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from server.integrations.data_export import DataExporter
from server.config import EXTERNAL_DB_CONNECTION, SYNC_INTERVAL_HOURS

scheduler = AsyncIOScheduler()

async def sync_to_data_center():
    """Scheduled job to sync data to data center."""
    exporter = DataExporter(EXTERNAL_DB_CONNECTION)

    # Sync all modified files in last interval
    # Implementation depends on your needs

scheduler.add_job(
    sync_to_data_center,
    'interval',
    hours=SYNC_INTERVAL_HOURS
)
```

---

## Multiple Database Support

### Different DBs for Different Data

```python
# server/config.py

# Primary database (translations)
PRIMARY_DB_HOST = os.getenv("PRIMARY_DB_HOST", "10.10.30.50")
PRIMARY_DB_NAME = os.getenv("PRIMARY_DB_NAME", "locanext")

# User database (if separate)
USER_DB_HOST = os.getenv("USER_DB_HOST", "10.10.30.50")
USER_DB_NAME = os.getenv("USER_DB_NAME", "locanext_users")

# Analytics database (if separate)
ANALYTICS_DB_HOST = os.getenv("ANALYTICS_DB_HOST", "analytics.dc.company.com")
ANALYTICS_DB_NAME = os.getenv("ANALYTICS_DB_NAME", "locanext_analytics")
```

### Database Router

```python
# server/database/router.py

class DatabaseRouter:
    """Route queries to appropriate database."""

    def __init__(self):
        self.primary_engine = create_engine(PRIMARY_DB_URL)
        self.user_engine = create_engine(USER_DB_URL)
        self.analytics_engine = create_engine(ANALYTICS_DB_URL)

    def get_engine_for_model(self, model_class):
        """Return appropriate engine for model."""
        if model_class in [User, UserSession]:
            return self.user_engine
        elif model_class in [AnalyticsEvent, Metrics]:
            return self.analytics_engine
        else:
            return self.primary_engine
```

---

## Connection Pooling

### PgBouncer Setup (Optional)

For high-traffic deployments:

```bash
# Install PgBouncer
sudo apt install pgbouncer

# Configure /etc/pgbouncer/pgbouncer.ini
[databases]
locanext = host=db.company.com port=5432 dbname=locanext

[pgbouncer]
listen_addr = 127.0.0.1
listen_port = 6432
auth_type = scram-sha-256
auth_file = /etc/pgbouncer/userlist.txt
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 50
```

---

## Testing External Connections

```bash
# Test connectivity
psql -h db.company.com -U locanext_app -d locanext -c "SELECT 1;"

# Test from LocaNext
cd ~/LocaNext
source venv/bin/activate
python3 -c "
from server.database.db_setup import get_engine
engine = get_engine()
with engine.connect() as conn:
    result = conn.execute('SELECT version()').fetchone()
    print(f'Connected: {result[0]}')
"
```

---

## Next Step

Database integration configured. Proceed to [09_MAINTENANCE.md](09_MAINTENANCE.md) for backups and updates.
