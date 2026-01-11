# 09 - Maintenance

**Purpose:** Backups, updates, monitoring, and routine maintenance

---

## Backup Strategy

### What to Backup

| Component | Location | Frequency | Retention |
|-----------|----------|-----------|-----------|
| PostgreSQL database | Server | Daily | 30 days |
| User config files | Server | Weekly | 90 days |
| Gitea data | Server | Daily | 30 days |
| SSL certificates | Server | Before expiry | Keep current |
| .env configuration | Server | On change | Keep history |

### PostgreSQL Backup

#### Automated Daily Backup

Create `/opt/scripts/backup_postgres.sh`:

```bash
#!/bin/bash
# PostgreSQL backup script

BACKUP_DIR="/backup/postgresql"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="locanext"
RETENTION_DAYS=30

# Create backup directory
mkdir -p $BACKUP_DIR

# Dump database
pg_dump -h localhost -U postgres $DB_NAME | gzip > "$BACKUP_DIR/${DB_NAME}_${DATE}.sql.gz"

# Delete old backups
find $BACKUP_DIR -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete

# Log
echo "$(date): Backup completed - ${DB_NAME}_${DATE}.sql.gz" >> /var/log/backup.log
```

Schedule with cron:
```bash
# Run daily at 2 AM
0 2 * * * /opt/scripts/backup_postgres.sh
```

#### Manual Backup

```bash
# Full backup
pg_dump -h localhost -U postgres locanext > locanext_backup_$(date +%Y%m%d).sql

# Compressed
pg_dump -h localhost -U postgres locanext | gzip > locanext_backup_$(date +%Y%m%d).sql.gz

# Custom format (supports parallel restore)
pg_dump -h localhost -U postgres -Fc locanext > locanext_backup_$(date +%Y%m%d).dump
```

#### Restore from Backup

```bash
# From SQL file
psql -h localhost -U postgres -d locanext < locanext_backup.sql

# From compressed
gunzip -c locanext_backup.sql.gz | psql -h localhost -U postgres -d locanext

# From custom format
pg_restore -h localhost -U postgres -d locanext locanext_backup.dump
```

### Gitea Backup

```bash
# Backup Gitea data
tar -czf /backup/gitea/gitea_$(date +%Y%m%d).tar.gz /var/lib/gitea /etc/gitea

# Restore
tar -xzf gitea_backup.tar.gz -C /
```

---

## Updates

### Updating LocaNext

#### Method 1: Via Gitea (Recommended)

```bash
# On admin workstation
cd ~/LocaNext

# Pull latest changes
git pull company main

# Install any new dependencies
source venv/bin/activate
pip install -r requirements.txt
cd locaNext && npm install && cd ..

# Build new version
echo "Build $(date +%Y%m%d%H%M)" >> GITEA_TRIGGER.txt
git add -A
git commit -m "Trigger build for update"
git push company main

# Monitor build at http://10.10.30.50:3000/locanext/LocaNext/actions
```

#### Method 2: Manual Update

```bash
# On admin workstation
cd ~/LocaNext
git pull company main

# Update dependencies
source venv/bin/activate
pip install -r requirements.txt

# Build
cd locaNext
npm install
npm run build
npm run electron:build

# New installer at dist/
```

### User Update Process

#### Automatic (Future Feature)

LocaNext can check for updates on startup:
- Queries Gitea API for latest release
- Compares with current version
- Prompts user to update
- Downloads and runs installer

#### Manual (Current)

1. Admin emails users about new version
2. Users download from Gitea: `http://10.10.30.50:3000/locanext/LocaNext/releases`
3. Users run installer (overwrites previous)
4. No data loss (data in PostgreSQL/SQLite)

### Updating Server Components

#### PostgreSQL

```bash
# Check current version
psql --version

# Update (Ubuntu)
sudo apt update
sudo apt upgrade postgresql-16

# Restart
sudo systemctl restart postgresql
```

#### Gitea

```bash
# Download new version
wget https://dl.gitea.com/gitea/VERSION/gitea-VERSION-linux-amd64 -O /tmp/gitea
sudo mv /tmp/gitea /usr/local/bin/gitea
sudo chmod +x /usr/local/bin/gitea

# Restart
sudo systemctl restart gitea
```

---

## Monitoring

### Health Check Script

Create `/opt/scripts/health_check.sh`:

```bash
#!/bin/bash
# LocaNext health check

ALERT_EMAIL="admin@company.com"

# Check PostgreSQL
if ! pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
    echo "PostgreSQL DOWN" | mail -s "LocaNext Alert: PostgreSQL" $ALERT_EMAIL
fi

# Check Gitea
if ! curl -s http://localhost:3000/api/v1/version > /dev/null; then
    echo "Gitea DOWN" | mail -s "LocaNext Alert: Gitea" $ALERT_EMAIL
fi

# Check disk space
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | tr -d '%')
if [ $DISK_USAGE -gt 85 ]; then
    echo "Disk usage at ${DISK_USAGE}%" | mail -s "LocaNext Alert: Disk Space" $ALERT_EMAIL
fi

# Log check
echo "$(date): Health check completed" >> /var/log/locanext_health.log
```

Schedule:
```bash
# Every 5 minutes
*/5 * * * * /opt/scripts/health_check.sh
```

### Log Monitoring

```bash
# PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-16-main.log

# Gitea logs
sudo journalctl -u gitea -f

# System logs
sudo tail -f /var/log/syslog
```

### Database Statistics

```sql
-- Active connections
SELECT count(*) FROM pg_stat_activity WHERE datname = 'locanext';

-- Database size
SELECT pg_size_pretty(pg_database_size('locanext'));

-- Table sizes
SELECT tablename, pg_size_pretty(pg_total_relation_size(tablename::text))
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(tablename::text) DESC;

-- Slow queries (if log enabled)
SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;
```

---

## Routine Maintenance Tasks

### Weekly

- [ ] Check backup integrity (restore test)
- [ ] Review error logs
- [ ] Check disk space
- [ ] Review user activity

### Monthly

- [ ] Apply security updates
- [ ] Review and rotate logs
- [ ] Analyze database performance
- [ ] Clean old backup files
- [ ] Review user accounts (remove inactive)

### Quarterly

- [ ] Full disaster recovery test
- [ ] Security audit
- [ ] Performance review
- [ ] Documentation review
- [ ] User training review

---

## Database Maintenance

### Vacuum and Analyze

```bash
# Manual vacuum
psql -h localhost -U postgres -d locanext -c "VACUUM ANALYZE;"

# Automated (configure in postgresql.conf)
autovacuum = on
autovacuum_vacuum_threshold = 50
autovacuum_analyze_threshold = 50
```

### Reindex (if needed)

```sql
-- Reindex specific table
REINDEX TABLE ldm_rows;

-- Reindex entire database (requires maintenance window)
REINDEX DATABASE locanext;
```

### Clean Old Sessions

```sql
-- Delete sessions older than 30 days
DELETE FROM user_sessions WHERE last_activity < NOW() - INTERVAL '30 days';

-- Delete orphaned locks
DELETE FROM ldm_locks WHERE acquired_at < NOW() - INTERVAL '1 day';
```

---

## Pre-Installing Embedding Model

For environments without internet access:

### Download Model Offline

```bash
# On machine with internet
python3 -c "
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('Qwen/Qwen3-Embedding-0.6B')
model.save('/tmp/qwen-embedding')
"

# Package for transfer
tar -czf qwen-embedding.tar.gz /tmp/qwen-embedding
```

### Install on Air-Gapped System

```bash
# Copy qwen-embedding.tar.gz to target system

# Extract to models directory
mkdir -p /opt/locanext/models
tar -xzf qwen-embedding.tar.gz -C /opt/locanext/models/
mv /opt/locanext/models/tmp/qwen-embedding /opt/locanext/models/

# Configure LocaNext to use local model
# .env
EMBEDDING_MODEL_PATH=/opt/locanext/models/qwen-embedding
```

---

## Disaster Recovery

### Recovery Procedure

1. **Assess Damage**
   - What failed? (Server, database, network)
   - Is data intact?
   - What's the last good backup?

2. **Restore Server** (if needed)
   - Provision new server
   - Install OS and dependencies
   - Follow [02_SERVER_SETUP.md](02_SERVER_SETUP.md)

3. **Restore Database**
   ```bash
   # Create fresh database
   sudo -u postgres createdb locanext

   # Restore from backup
   gunzip -c /backup/postgresql/locanext_latest.sql.gz | psql -U postgres -d locanext
   ```

4. **Restore Gitea** (if needed)
   ```bash
   # Extract backup
   tar -xzf /backup/gitea/gitea_latest.tar.gz -C /

   # Restart
   sudo systemctl restart gitea
   ```

5. **Verify**
   - Test database connection
   - Test Gitea access
   - Test user login
   - Build and deploy test version

6. **Notify Users**
   - System restored
   - Any data loss (from backup date)
   - Next steps

---

## Performance Tuning

### PostgreSQL Tuning

Based on server RAM (16GB example):

```ini
# postgresql.conf
shared_buffers = 4GB                    # 25% of RAM
effective_cache_size = 12GB             # 75% of RAM
maintenance_work_mem = 1GB
work_mem = 64MB
max_connections = 200
checkpoint_completion_target = 0.9
wal_buffers = 64MB
default_statistics_target = 100
random_page_cost = 1.1                  # SSD
effective_io_concurrency = 200          # SSD
```

### Connection Pooling

If experiencing connection limits:

```bash
# Install PgBouncer
sudo apt install pgbouncer

# Configure connection pooling
# See 08_DATABASE_INTEGRATION.md
```

---

## Next Step

Maintenance configured. Proceed to [10_TROUBLESHOOTING.md](10_TROUBLESHOOTING.md) for common issues and solutions.
