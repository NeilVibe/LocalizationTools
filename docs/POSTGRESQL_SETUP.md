# PostgreSQL Setup Guide

PostgreSQL is already configured in `server/config.py` with connection pooling.

## Quick Setup

### 1. Set Environment Variables

```bash
export DATABASE_TYPE=postgresql
export POSTGRES_USER=localization_admin
export POSTGRES_PASSWORD=your_secure_password
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=localizationtools
```

### 2. Create Database

```bash
# Install PostgreSQL if needed
sudo apt-get install postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql
CREATE DATABASE localizationtools;
CREATE USER localization_admin WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE localizationtools TO localization_admin;
\q
```

### 3. Server Automatically Uses PostgreSQL

When `DATABASE_TYPE=postgresql`, the server uses:
- **Driver**: asyncpg (async) + psycopg2 (sync)
- **Connection Pool**: 20 base connections + 10 overflow
- **Pool Timeout**: 30 seconds
- **Pool Recycle**: 3600 seconds (1 hour)
- **Pool Pre-ping**: Enabled (validates connections)

## Current Configuration

All settings in `server/config.py`:

```python
# PostgreSQL URL (automatically used when DATABASE_TYPE=postgresql)
POSTGRES_DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# Connection pooling (already configured)
DB_POOL_SIZE = 20
DB_MAX_OVERFLOW = 10
DB_POOL_TIMEOUT = 30
DB_POOL_RECYCLE = 3600
```

## Performance Benefits

- ✅ **10-100x better concurrency** vs SQLite
- ✅ **Connection pooling** reduces overhead
- ✅ **Async operations** with asyncpg
- ✅ **Production-ready** for high load
- ✅ **ACID compliance** for data integrity

## Status

**PostgreSQL support is READY** - just set environment variables and create the database!
