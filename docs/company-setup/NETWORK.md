# Network Setup Guide

**For:** IT Department, Network Administrators
**Classification:** Internal

---

## Network Architecture

```
COMPANY NETWORK TOPOLOGY
════════════════════════════════════════════════════════════════════

                         INTERNET
                             │
                             │ ❌ BLOCKED (no inbound/outbound needed)
                             │
                    ┌────────┴────────┐
                    │    FIREWALL     │
                    │  (Company Edge) │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
   SERVERS VLAN         USERS VLAN           MGMT VLAN
   (192.168.1.0/24)    (192.168.10.0/24)    (192.168.100.0/24)
        │                    │                    │
        │                    │                    │
   ┌────┴────┐          ┌────┴────┐          ┌────┴────┐
   │ Gitea   │          │ User    │          │ Admin   │
   │ :3000   │◄────────►│ Desktop │          │ Dash    │
   │         │          │ Apps    │          │ :5175   │
   └────┬────┘          └────┬────┘          └─────────┘
        │                    │
   ┌────┴────┐               │
   │ Central │◄──────────────┘
   │ Server  │  (Telemetry)
   │ :9999   │
   └─────────┘
```

---

## 1. Server Requirements

### 1.1 Gitea Server (Git + CI/CD)

| Spec | Minimum | Recommended |
|------|---------|-------------|
| CPU | 1 core | 2+ cores |
| RAM | 512 MB | 2 GB |
| Disk | 10 GB | 50 GB |
| OS | Linux (any) | Ubuntu 22.04 LTS |

### 1.2 Central Telemetry Server

| Spec | Minimum | Recommended |
|------|---------|-------------|
| CPU | 1 core | 2+ cores |
| RAM | 1 GB | 4 GB |
| Disk | 20 GB | 100 GB |
| OS | Linux (any) | Ubuntu 22.04 LTS |

### 1.3 Admin Dashboard Server

| Spec | Minimum | Recommended |
|------|---------|-------------|
| CPU | 1 core | 2+ cores |
| RAM | 512 MB | 2 GB |
| Disk | 5 GB | 20 GB |
| OS | Linux (any) | Ubuntu 22.04 LTS |

**Note:** All three can run on a single server for small teams (<20 users).

---

## 2. Port Configuration

### 2.1 Required Ports

| Service | Port | Protocol | Direction | Purpose |
|---------|------|----------|-----------|---------|
| Gitea Web | 3000 | TCP | Inbound | Git web UI |
| Gitea SSH | 2222 | TCP | Inbound | Git SSH |
| Central Server | 9999 | TCP | Inbound | Telemetry API |
| Admin Dashboard | 5175 | TCP | Inbound | Admin web UI |
| Desktop Backend | 8888 | TCP | Local only | Desktop app API |

### 2.2 Firewall Rules (iptables example)

```bash
# Gitea Web (internal only)
iptables -A INPUT -p tcp --dport 3000 -s 192.168.0.0/16 -j ACCEPT
iptables -A INPUT -p tcp --dport 3000 -j DROP

# Gitea SSH (internal only)
iptables -A INPUT -p tcp --dport 2222 -s 192.168.0.0/16 -j ACCEPT
iptables -A INPUT -p tcp --dport 2222 -j DROP

# Central Server (internal only)
iptables -A INPUT -p tcp --dport 9999 -s 192.168.0.0/16 -j ACCEPT
iptables -A INPUT -p tcp --dport 9999 -j DROP

# Admin Dashboard (internal only)
iptables -A INPUT -p tcp --dport 5175 -s 192.168.0.0/16 -j ACCEPT
iptables -A INPUT -p tcp --dport 5175 -j DROP

# Block all outbound to internet (air-gapped)
iptables -A OUTPUT -d 192.168.0.0/16 -j ACCEPT
iptables -A OUTPUT -d 10.0.0.0/8 -j ACCEPT
iptables -A OUTPUT -d 172.16.0.0/12 -j ACCEPT
iptables -A OUTPUT -d 127.0.0.0/8 -j ACCEPT
iptables -A OUTPUT -j DROP  # Block all other outbound
```

### 2.3 Windows Firewall Rules

```powershell
# Allow Gitea (internal network only)
New-NetFirewallRule -DisplayName "Gitea Web" -Direction Inbound -Protocol TCP -LocalPort 3000 -RemoteAddress 192.168.0.0/16 -Action Allow
New-NetFirewallRule -DisplayName "Gitea SSH" -Direction Inbound -Protocol TCP -LocalPort 2222 -RemoteAddress 192.168.0.0/16 -Action Allow
```

---

## 3. DNS Configuration

### 3.1 Internal DNS Records

Add these to your internal DNS server:

```
; LocaNext Internal DNS Records
git.company.local.     IN A    192.168.1.10    ; Gitea server
telemetry.company.local. IN A  192.168.1.11    ; Central server
admin.company.local.   IN A    192.168.1.12    ; Admin dashboard
```

### 3.2 Hosts File Alternative

If no internal DNS, add to each machine's hosts file:

**Linux/Mac:** `/etc/hosts`
**Windows:** `C:\Windows\System32\drivers\etc\hosts`

```
192.168.1.10    git.company.local
192.168.1.11    telemetry.company.local
192.168.1.12    admin.company.local
```

---

## 4. Air-Gapped Deployment

### 4.1 What is Air-Gapped?

```
NORMAL NETWORK:              AIR-GAPPED NETWORK:

Internet ◄──► Company        Internet ✗ ┃ Company
                                        ┃
(connected)                  (no connection at all)
```

### 4.2 Air-Gapped Installation Steps

```bash
# ON CONNECTED MACHINE (preparation):

# 1. Download all packages
pip download -d ./packages -r requirements.txt
npm pack (for each npm package)

# 2. Download Gitea binary
wget https://dl.gitea.com/gitea/1.22.3/gitea-1.22.3-linux-amd64

# 3. Download LocaNext installer
# (from GitHub releases or build yourself)

# 4. Copy everything to USB drive

# ON AIR-GAPPED MACHINE:

# 1. Install from local packages
pip install --no-index --find-links=./packages -r requirements.txt

# 2. Copy Gitea binary
cp gitea-1.22.3-linux-amd64 /opt/gitea/gitea

# 3. Install LocaNext
# Run installer from USB
```

### 4.3 Air-Gapped Updates

```
UPDATE PROCESS (no internet):
═══════════════════════════════════════════════════

Step 1: Download update on connected machine
        ↓
Step 2: Security scan the update
        ↓
Step 3: Copy to USB/approved transfer
        ↓
Step 4: Transfer to air-gapped network
        ↓
Step 5: Test in staging environment
        ↓
Step 6: Deploy to production
```

---

## 5. TLS/HTTPS Configuration (Optional)

### 5.1 Self-Signed Certificates

```bash
# Generate CA
openssl genrsa -out ca.key 4096
openssl req -new -x509 -days 3650 -key ca.key -out ca.crt

# Generate server certificate
openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr
openssl x509 -req -days 365 -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out server.crt
```

### 5.2 Gitea HTTPS Config

```ini
# /home/gitea/custom/conf/app.ini
[server]
PROTOCOL = https
CERT_FILE = /path/to/server.crt
KEY_FILE = /path/to/server.key
```

### 5.3 Central Server HTTPS

```bash
# Environment variables
export SSL_CERTFILE=/path/to/server.crt
export SSL_KEYFILE=/path/to/server.key
```

---

## 6. Network Checklist

### 6.1 Pre-Installation Checklist

- [ ] Server IP addresses assigned
- [ ] DNS records created (or hosts files updated)
- [ ] Firewall rules configured
- [ ] Ports 3000, 2222, 9999, 5175 open internally
- [ ] External internet blocked (if air-gapped)
- [ ] TLS certificates generated (if using HTTPS)

### 6.2 Post-Installation Verification

```bash
# Test Gitea connectivity
curl http://git.company.local:3000/

# Test Central Server
curl http://telemetry.company.local:9999/health

# Test Admin Dashboard
curl http://admin.company.local:5175/

# Verify no external connections
netstat -an | grep ESTABLISHED | grep -v "192.168\|10.0\|172.16\|127.0"
# Should return EMPTY
```

---

## 7. Network Diagram (Detailed)

```
┌─────────────────────────────────────────────────────────────────────┐
│                        COMPANY NETWORK                               │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                     SERVER SEGMENT                           │    │
│  │                     192.168.1.0/24                           │    │
│  │                                                              │    │
│  │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │    │
│  │   │   GITEA     │  │  CENTRAL    │  │   ADMIN     │         │    │
│  │   │   SERVER    │  │  TELEMETRY  │  │  DASHBOARD  │         │    │
│  │   │             │  │             │  │             │         │    │
│  │   │ .1.10:3000  │  │ .1.11:9999  │  │ .1.12:5175  │         │    │
│  │   │      :2222  │  │             │  │             │         │    │
│  │   └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │    │
│  │          │                │                │                 │    │
│  └──────────┼────────────────┼────────────────┼─────────────────┘    │
│             │                │                │                      │
│             └────────────────┼────────────────┘                      │
│                              │                                       │
│                     ┌────────┴────────┐                              │
│                     │  CORE SWITCH    │                              │
│                     └────────┬────────┘                              │
│                              │                                       │
│  ┌───────────────────────────┼───────────────────────────────────┐  │
│  │                    USER SEGMENT                                │  │
│  │                    192.168.10.0/24                             │  │
│  │                           │                                    │  │
│  │   ┌─────────┐   ┌─────────┴─────────┐   ┌─────────┐           │  │
│  │   │  PC 1   │   │       PC 2        │   │  PC 3   │           │  │
│  │   │LocanNext│   │     LocaNext      │   │LocaNext │           │  │
│  │   │ .10.101 │   │      .10.102      │   │ .10.103 │           │  │
│  │   └─────────┘   └───────────────────┘   └─────────┘           │  │
│  │                                                                │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
                                 │
                                 │ ❌ BLOCKED
                                 │
                            [ INTERNET ]
```

---

*Document Version: 2025-12-06*
*Classification: Internal - IT*
