# 06 - Network Security

**Purpose:** IP restrictions, firewall configuration, access control

---

## Security Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                     SECURITY LAYERS                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Layer 1: NETWORK FIREWALL (Company Router/Firewall)            │
│  └─ Block all external access to internal servers               │
│                                                                  │
│  Layer 2: SERVER FIREWALL (UFW)                                 │
│  └─ Only allow specific IP ranges to specific ports             │
│                                                                  │
│  Layer 3: POSTGRESQL pg_hba.conf                                │
│  └─ Only allow specific networks to connect                     │
│                                                                  │
│  Layer 4: APPLICATION IP WHITELIST                              │
│  └─ Backend validates client IP against allowed ranges          │
│                                                                  │
│  Layer 5: AUTHENTICATION                                        │
│  └─ Username + password required for all operations             │
│                                                                  │
│  Layer 6: AUTHORIZATION                                         │
│  └─ Role-based permissions for each action                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## IP Range Configuration

### Define Your Network Ranges

Example company network:

| Subnet | Purpose | Range |
|--------|---------|-------|
| `10.10.30.0/24` | Servers | 10.10.30.1 - 10.10.30.254 |
| `10.10.10.0/24` | Office A | 10.10.10.1 - 10.10.10.254 |
| `10.10.20.0/24` | Office B | 10.10.20.1 - 10.10.20.254 |
| `10.10.100.0/24` | VPN Clients | 10.10.100.1 - 10.10.100.254 |

Combined: `10.10.0.0/16` (all company IPs)

---

## Layer 2: Server Firewall (UFW)

### Configure UFW

```bash
# SSH to server
ssh admin@10.10.30.50

# Reset UFW (if needed)
sudo ufw --force reset

# Default policies
sudo ufw default deny incoming
sudo ufw default allow outgoing

# SSH - admin subnet only
sudo ufw allow from 10.10.30.0/24 to any port 22 proto tcp comment 'SSH from admin'

# PostgreSQL - company network
sudo ufw allow from 10.10.0.0/16 to any port 5432 proto tcp comment 'PostgreSQL'

# Gitea - company network
sudo ufw allow from 10.10.0.0/16 to any port 3000 proto tcp comment 'Gitea'

# Enable
sudo ufw enable

# Verify
sudo ufw status verbose
```

### Expected Output

```
Status: active
Logging: on (low)
Default: deny (incoming), allow (outgoing), disabled (routed)

To                         Action      From
--                         ------      ----
22/tcp                     ALLOW IN    10.10.30.0/24          # SSH from admin
5432/tcp                   ALLOW IN    10.10.0.0/16           # PostgreSQL
3000/tcp                   ALLOW IN    10.10.0.0/16           # Gitea
```

---

## Layer 3: PostgreSQL Access Control

### pg_hba.conf

Location: `/etc/postgresql/16/main/pg_hba.conf`

```bash
sudo vim /etc/postgresql/16/main/pg_hba.conf
```

Configuration:
```
# TYPE  DATABASE        USER            ADDRESS                 METHOD

# Local connections
local   all             postgres                                peer
local   all             all                                     peer

# IPv4 local connections
host    all             all             127.0.0.1/32            scram-sha-256

# LocaNext app connections - company network only
host    locanext        locanext_app    10.10.0.0/16            scram-sha-256

# Admin connections - admin subnet only
host    locanext        locanext_admin  10.10.30.0/24           scram-sha-256
host    all             postgres        10.10.30.0/24           scram-sha-256

# Deny everything else (implicit, but explicit for clarity)
host    all             all             0.0.0.0/0               reject
```

Reload:
```bash
sudo systemctl reload postgresql
```

---

## Layer 4: Application IP Whitelist

### Configure in Backend

Edit `server/config.py`:

```python
import os

# Allowed IP ranges for API access
ALLOWED_IP_RANGES = os.getenv(
    "ALLOWED_IP_RANGES",
    "10.10.0.0/16,127.0.0.1/32,::1/128"
).split(",")

# Enable/disable IP checking
ENABLE_IP_WHITELIST = os.getenv("ENABLE_IP_WHITELIST", "true").lower() == "true"
```

### IP Validation Middleware

Create `server/middleware/ip_whitelist.py`:

```python
from fastapi import Request, HTTPException
from ipaddress import ip_address, ip_network
from server.config import ALLOWED_IP_RANGES, ENABLE_IP_WHITELIST
import logging

logger = logging.getLogger(__name__)

def get_client_ip(request: Request) -> str:
    """Get real client IP, handling proxies."""
    # Check X-Forwarded-For header (if behind proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    # Check X-Real-IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Direct connection
    return request.client.host

def is_ip_allowed(client_ip: str) -> bool:
    """Check if IP is in allowed ranges."""
    if not ENABLE_IP_WHITELIST:
        return True

    try:
        ip = ip_address(client_ip)
        for range_str in ALLOWED_IP_RANGES:
            network = ip_network(range_str.strip(), strict=False)
            if ip in network:
                return True
        return False
    except ValueError as e:
        logger.error(f"Invalid IP address: {client_ip} - {e}")
        return False

async def ip_whitelist_middleware(request: Request, call_next):
    """Middleware to check client IP against whitelist."""
    client_ip = get_client_ip(request)

    if not is_ip_allowed(client_ip):
        logger.warning(f"Blocked request from unauthorized IP: {client_ip}")
        raise HTTPException(
            status_code=403,
            detail=f"Access denied. Your IP ({client_ip}) is not authorized."
        )

    response = await call_next(request)
    return response
```

### Add Middleware to App

In `server/main.py`:

```python
from server.middleware.ip_whitelist import ip_whitelist_middleware

# Add middleware
app.middleware("http")(ip_whitelist_middleware)
```

---

## Layer 5 & 6: Authentication & Authorization

See [05_USER_MANAGEMENT.md](05_USER_MANAGEMENT.md) for:
- User authentication (JWT)
- Role-based authorization
- Session management

---

## Monitoring & Logging

### Enable Connection Logging (PostgreSQL)

Edit `/etc/postgresql/16/main/postgresql.conf`:

```ini
log_connections = on
log_disconnections = on
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '
```

### View Connection Logs

```bash
sudo tail -f /var/log/postgresql/postgresql-16-main.log
```

### Application Logging

Logs blocked IPs:

```bash
# If using journald
journalctl -u locanext-backend -f | grep "Blocked request"

# Or check log files
tail -f /var/log/locanext/app.log | grep "unauthorized IP"
```

---

## Testing Security

### Test Firewall

From authorized IP:
```bash
# Should succeed
nc -zv 10.10.30.50 5432
nc -zv 10.10.30.50 3000
```

From unauthorized IP:
```bash
# Should fail/timeout
nc -zv 10.10.30.50 5432
```

### Test PostgreSQL Access

```bash
# From authorized IP - should work
psql -h 10.10.30.50 -U locanext_app -d locanext -c "SELECT 1;"

# From unauthorized IP - should fail
# "no pg_hba.conf entry for host..."
```

### Test API IP Whitelist

```bash
# From authorized IP
curl http://10.10.30.50:8888/health
# {"status": "healthy"...}

# From unauthorized IP (e.g., via external proxy)
# {"detail": "Access denied. Your IP (x.x.x.x) is not authorized."}
```

---

## VPN Users

For remote workers connecting via VPN:

1. VPN assigns IP from allowed range (e.g., `10.10.100.0/24`)
2. Add VPN range to allowed ranges:

```bash
# .env
ALLOWED_IP_RANGES=10.10.0.0/16,10.10.100.0/24

# pg_hba.conf
host    locanext        locanext_app    10.10.100.0/24          scram-sha-256

# UFW
sudo ufw allow from 10.10.100.0/24 to any port 5432
```

---

## Emergency: Block Specific IP

If compromised machine detected:

```bash
# Block immediately
sudo ufw deny from 10.10.20.123

# Block in PostgreSQL (immediate effect)
sudo -u postgres psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE client_addr = '10.10.20.123';"
```

---

## Security Checklist

- [ ] Company firewall blocks external access to server
- [ ] UFW configured with deny-by-default
- [ ] PostgreSQL pg_hba.conf restricts by IP
- [ ] Application IP whitelist enabled
- [ ] Connection logging enabled
- [ ] All passwords are strong
- [ ] No default passwords in production
- [ ] SSH key-only access (password disabled)
- [ ] Regular security updates applied

---

## Next Step

Security configured. Proceed to [07_DASHBOARD_INTEGRATION.md](07_DASHBOARD_INTEGRATION.md) for company dashboard integration.
