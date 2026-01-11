# 01 - Prerequisites

**Purpose:** What you need before deploying LocaNext at the company

---

## Server Requirements

### Central Server (for Online Mode)

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **OS** | Ubuntu 22.04 LTS | Ubuntu 24.04 LTS |
| **CPU** | 4 cores | 8 cores |
| **RAM** | 8 GB | 16 GB |
| **Disk** | 100 GB SSD | 500 GB SSD |
| **Network** | 100 Mbps | 1 Gbps |

### Software Requirements (Server)

| Software | Version | Purpose |
|----------|---------|---------|
| PostgreSQL | 14+ | Central database |
| Gitea | 1.20+ | Git server, CI/CD, releases |
| Node.js | 20 LTS | Build tools |
| Python | 3.11+ | Backend |
| Git | 2.30+ | Version control |
| WSL2 | Latest | Windows development (optional) |

---

## Client Requirements (User Workstations)

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **OS** | Windows 10 (64-bit) | Windows 11 |
| **CPU** | 4 cores | 8 cores |
| **RAM** | 8 GB | 16 GB |
| **Disk** | 10 GB free | 20 GB free |
| **Network** | Company LAN | Company LAN |

**Note:** First-run setup downloads ~2.3GB embedding model. Ensure sufficient disk space.

---

## Network Requirements

### Ports to Open (Server)

| Port | Service | Access |
|------|---------|--------|
| 5432 | PostgreSQL | Internal LAN only |
| 3000 | Gitea | Internal LAN only |
| 22 | SSH | Admin IPs only |

### Firewall Rules

```bash
# Example UFW rules for server
ufw allow from 10.10.0.0/16 to any port 5432  # PostgreSQL from company network
ufw allow from 10.10.0.0/16 to any port 3000  # Gitea from company network
ufw allow from 10.10.30.0/24 to any port 22   # SSH from admin subnet only
```

### IP Range Planning

| Subnet | Purpose | Example |
|--------|---------|---------|
| Server subnet | Central services | 10.10.30.0/24 |
| User subnet(s) | Workstations | 10.10.10.0/24, 10.10.20.0/24 |
| Admin subnet | IT management | 10.10.30.0/24 |

---

## Information to Gather

Before starting, collect this information from company IT:

### Network Information

```
[ ] Server IP address:        _______________  (e.g., 10.10.30.50)
[ ] Server hostname:          _______________  (e.g., locanext-server)
[ ] Company network range:    _______________  (e.g., 10.10.0.0/16)
[ ] DNS server:               _______________
[ ] Gateway:                  _______________
[ ] Allowed user IP ranges:   _______________
```

### Access Credentials

```
[ ] Server SSH access:        _______________
[ ] PostgreSQL admin user:    _______________
[ ] Gitea admin credentials:  _______________
```

### Integration Points

```
[ ] Company dashboard URL:    _______________  (if applicable)
[ ] Dashboard API endpoint:   _______________  (if applicable)
[ ] External database host:   _______________  (if applicable)
[ ] LDAP/AD server:           _______________  (if applicable)
```

### Policies

```
[ ] Password policy:          _______________  (min length, complexity)
[ ] Session timeout:          _______________  (minutes)
[ ] Data retention policy:    _______________  (days)
[ ] Backup schedule:          _______________
```

---

## Admin Workstation Setup

The admin needs a development environment to build and deploy:

### Option A: WSL2 on Windows (Recommended)

```powershell
# 1. Enable WSL
wsl --install -d Ubuntu-24.04

# 2. Restart computer

# 3. Open Ubuntu terminal and update
sudo apt update && sudo apt upgrade -y

# 4. Install dependencies
sudo apt install -y git curl wget build-essential python3 python3-pip python3-venv nodejs npm postgresql-client
```

### Option B: Native Linux

```bash
# Ubuntu/Debian
sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl wget build-essential python3 python3-pip python3-venv nodejs npm postgresql-client
```

### Option C: macOS

```bash
# Install Homebrew first
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install git node python@3.11 postgresql
```

---

## Claude Code Setup (for AI-assisted deployment)

If using Claude Code for deployment assistance:

```bash
# Install Claude Code
npm install -g @anthropic-ai/claude-code

# Verify installation
claude --version

# Authenticate
claude auth login
```

---

## Checklist Before Proceeding

- [ ] Server provisioned and accessible via SSH
- [ ] Network information collected
- [ ] Firewall rules planned
- [ ] Admin workstation set up with WSL2 or Linux
- [ ] Git, Node.js, Python installed on admin workstation
- [ ] PostgreSQL client installed (for testing connections)
- [ ] Claude Code installed (optional, for AI assistance)

---

## Next Step

Once prerequisites are met, proceed to [02_SERVER_SETUP.md](02_SERVER_SETUP.md).
