# Server Equipment & Pricing Guide

**For:** IT Procurement, Finance, Management
**Classification:** Internal
**Last Updated:** 2025-12-09

---

## Executive Summary

| Question | Answer |
|----------|--------|
| Minimum server cost | **~$1,500** (refurbished) |
| Recommended server cost | **~$3,000-5,000** (new) |
| Monthly operating cost | **$0** (electricity only) |
| Cloud alternative | **$100-300/month** |
| ROI vs commercial CAT | **Payback in 1-2 months** |

---

## 1. Server Requirements

### 1.1 Resource Usage Breakdown

```
LOCANEXT RESOURCE REQUIREMENTS:
═══════════════════════════════════════════════════════════════

Component               RAM        CPU         Disk
────────────────────────────────────────────────────────────────
Python Backend          1 GB       1 core      100 MB
Korean BERT Model       2.4 GB     2 cores*    1.2 GB
FAISS Index (100K)      0.5 GB     -           50 MB
PostgreSQL              1 GB       1 core      varies
Gitea (optional)        0.5 GB     0.5 core    varies
Admin Dashboard         0.2 GB     0.5 core    50 MB
OS Overhead             2 GB       -           20 GB
────────────────────────────────────────────────────────────────
MINIMUM TOTAL           8 GB       5 cores     ~25 GB
RECOMMENDED             16 GB      8 cores     ~100 GB

* CPU usage during embedding generation only (burst)
```

### 1.2 Tier Specifications

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SERVER TIER COMPARISON                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  TIER 1: MINIMUM (Small Team < 10 users)                                    │
│  ──────────────────────────────────────────                                 │
│  • CPU: 4 cores (Intel i5 / AMD Ryzen 5)                                    │
│  • RAM: 8 GB DDR4                                                            │
│  • Storage: 128 GB SSD                                                       │
│  • Network: Gigabit Ethernet                                                 │
│  • Users: Up to 10 concurrent                                                │
│  • Cost: $800-1,500                                                          │
│                                                                              │
│  TIER 2: RECOMMENDED (Medium Team 10-50 users)                              │
│  ────────────────────────────────────────────────                           │
│  • CPU: 8 cores (Intel i7 / AMD Ryzen 7 / Xeon E)                           │
│  • RAM: 16-32 GB DDR4                                                        │
│  • Storage: 256-512 GB NVMe SSD                                              │
│  • Network: Gigabit Ethernet                                                 │
│  • Users: Up to 50 concurrent                                                │
│  • Cost: $2,000-4,000                                                        │
│                                                                              │
│  TIER 3: ENTERPRISE (Large Team 50+ users)                                  │
│  ─────────────────────────────────────────────                              │
│  • CPU: 16+ cores (Xeon Silver / EPYC)                                      │
│  • RAM: 64 GB DDR4 ECC                                                       │
│  • Storage: 1 TB NVMe SSD + RAID                                             │
│  • Network: 10 Gigabit Ethernet                                              │
│  • Users: 100+ concurrent                                                    │
│  • Cost: $5,000-10,000                                                       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Hardware Pricing (2025)

### 2.1 Option A: New Server Hardware

| Tier | Specs | Vendor Examples | Price Range |
|------|-------|-----------------|-------------|
| **Minimum** | 4C/8GB/128GB | Dell OptiPlex, HP ProDesk | $800-1,200 |
| **Recommended** | 8C/32GB/512GB | Dell PowerEdge T150, HPE ML30 | $2,500-4,000 |
| **Enterprise** | 16C/64GB/1TB | Dell PowerEdge R350, HPE DL20 | $5,000-8,000 |

### 2.2 Option B: Refurbished Server Hardware

| Tier | Specs | Sources | Price Range |
|------|-------|---------|-------------|
| **Minimum** | 4C/8GB/128GB | eBay, Amazon Renewed | $400-700 |
| **Recommended** | 8C/32GB/512GB | Dell Outlet, ServerMonkey | $1,000-2,000 |
| **Enterprise** | 16C/64GB/1TB | IT Asset Resellers | $2,000-4,000 |

### 2.3 Option C: Repurpose Existing Hardware

```
COMPATIBLE EXISTING EQUIPMENT:
═══════════════════════════════════════════════════════════════

✅ Can use existing:
├── Desktop PC with 8GB+ RAM
├── Old developer workstation
├── Decommissioned office PC
├── Unused server hardware
└── Virtual machine on existing hypervisor

Cost: $0 (if hardware already available)
```

### 2.4 Option D: Cloud Server (Monthly)

| Provider | Specs | Monthly Cost | Annual Cost |
|----------|-------|--------------|-------------|
| **AWS EC2** (t3.xlarge) | 4C/16GB | $120 | $1,440 |
| **Azure** (D4s v3) | 4C/16GB | $140 | $1,680 |
| **Google Cloud** (n2-standard-4) | 4C/16GB | $130 | $1,560 |
| **Hetzner** (CPX41) | 8C/16GB | $35 | $420 |
| **DigitalOcean** (g-4vcpu-16gb) | 4C/16GB | $126 | $1,512 |

**Note:** Cloud requires internet access, may not meet security requirements for air-gapped deployment.

---

## 3. Total Cost of Ownership

### 3.1 One-Time Costs

| Item | Minimum | Recommended | Enterprise |
|------|---------|-------------|------------|
| Server hardware | $800 | $3,000 | $6,000 |
| OS license (if Windows) | $0-800 | $0-800 | $0-2,000 |
| Network switch (if needed) | $0 | $100 | $300 |
| UPS backup (recommended) | $100 | $200 | $500 |
| **Total One-Time** | **$900-1,700** | **$3,300-4,100** | **$6,800-8,800** |

### 3.2 Annual Operating Costs

| Item | Cost | Notes |
|------|------|-------|
| Software licenses | **$0** | All MIT/Apache licensed |
| Electricity | ~$50-100 | ~50-100W average |
| Maintenance | **$0** | Self-maintainable |
| Support contract | **$0** | Optional |
| **Total Annual** | **~$50-100** | Electricity only |

### 3.3 5-Year Total Cost Comparison

```
5-YEAR COST COMPARISON:
═══════════════════════════════════════════════════════════════

                    LocaNext          Commercial CAT Tool
                    ─────────         ───────────────────
Year 0 (Setup)      $3,500            $0
Year 1              $100              $60,000
Year 2              $100              $60,000
Year 3              $100              $60,000
Year 4              $100              $60,000
Year 5              $100              $60,000
─────────────────────────────────────────────────────────────
TOTAL 5-YEAR        $4,000            $300,000

SAVINGS: $296,000 (98.7% reduction)

Breakeven point: ~1 month
```

---

## 4. Recommended Configurations

### 4.1 Best Value: Dell PowerEdge T150

```
RECOMMENDED: Dell PowerEdge T150 Tower Server
═══════════════════════════════════════════════════════════════

Specifications:
├── CPU: Intel Xeon E-2314 (4 cores, 2.8GHz)
├── RAM: 32 GB DDR4 ECC (upgradable to 128GB)
├── Storage: 480 GB SATA SSD
├── RAID: Built-in RAID controller
├── Network: Dual Gigabit Ethernet
├── Form: Tower (quiet, office-friendly)
└── Warranty: 3-year ProSupport

Price: ~$1,800-2,500 (Dell.com, 2025)

Why this one:
✅ ECC memory (server-grade reliability)
✅ Quiet enough for office environment
✅ Expandable for future growth
✅ Dell ProSupport available
✅ No additional cooling required
```

### 4.2 Budget Option: Refurbished Dell OptiPlex

```
BUDGET: Dell OptiPlex 7090 (Refurbished)
═══════════════════════════════════════════════════════════════

Specifications:
├── CPU: Intel Core i7-11700 (8 cores)
├── RAM: 16 GB DDR4 (add 16GB = $50)
├── Storage: 256 GB NVMe SSD (add 512GB = $50)
├── Network: Gigabit Ethernet
├── Form: Small Form Factor
└── Warranty: 90-day (extendable)

Price: ~$400-600 (eBay, Amazon Renewed)

Why this one:
✅ Extremely cost-effective
✅ Modern CPU with good performance
✅ Easy to upgrade RAM/storage
✅ Small footprint
⚠️ No ECC memory (acceptable for small team)
```

### 4.3 Enterprise Option: HPE ProLiant DL20 Gen10+

```
ENTERPRISE: HPE ProLiant DL20 Gen10+ Rack Server
═══════════════════════════════════════════════════════════════

Specifications:
├── CPU: Intel Xeon E-2336 (6 cores, 2.9GHz)
├── RAM: 64 GB DDR4 ECC
├── Storage: 2x 960GB SSD RAID 1
├── RAID: HPE Smart Array
├── Network: 4x Gigabit Ethernet
├── Form: 1U Rack Mount
└── Warranty: 3-year Foundation Care

Price: ~$4,000-6,000 (HPE.com, 2025)

Why this one:
✅ Full enterprise reliability
✅ RAID mirroring for data protection
✅ iLO remote management
✅ HPE support ecosystem
✅ Rack-mountable for data center
```

---

## 5. Network Requirements

### 5.1 Minimum Network

```
MINIMUM NETWORK REQUIREMENTS:
═══════════════════════════════════════════════════════════════

Server Connection:
├── Speed: 100 Mbps minimum, 1 Gbps recommended
├── Latency: < 50ms to clients
└── Firewall: Allow internal traffic on ports 8888, 3000

Client Requirements:
├── Speed: 10 Mbps per user
├── Browser: Chrome, Edge, Firefox (modern)
└── OS: Windows 10/11, macOS, Linux
```

### 5.2 Firewall Rules (Internal Only)

| Port | Service | Direction | Notes |
|------|---------|-----------|-------|
| 8888 | Backend API | Inbound | Main application |
| 3000 | Gitea | Inbound | Optional, for updates |
| 5175 | Admin Dashboard | Inbound | Management UI |
| 22 | SSH | Inbound | Server management |

**No external/internet ports required.**

---

## 6. Procurement Checklist

### 6.1 For IT Procurement

```
PROCUREMENT CHECKLIST:
═══════════════════════════════════════════════════════════════

Hardware Selection:
[ ] CPU: Minimum 4 cores (8+ recommended)
[ ] RAM: Minimum 8 GB (16-32 GB recommended)
[ ] Storage: Minimum 128 GB SSD (256-512 GB recommended)
[ ] Network: Gigabit Ethernet
[ ] Form factor: Tower or Rack (as per environment)

Software (All Free):
[ ] OS: Ubuntu Server 22.04 LTS or Windows Server
[ ] Python 3.11+
[ ] Node.js 20+
[ ] PostgreSQL 15+ (or use SQLite)

Network:
[ ] IP address in allowed range
[ ] Firewall rules for ports 8888, 3000
[ ] DNS entry (optional but recommended)

Verification:
[ ] Hardware delivered and tested
[ ] OS installed and updated
[ ] Network connectivity confirmed
[ ] LocaNext installation complete
[ ] All tests passing (912 expected)
```

### 6.2 Vendor Contacts

| Vendor | Website | Notes |
|--------|---------|-------|
| Dell | dell.com/servers | PowerEdge recommended |
| HPE | hpe.com | ProLiant series |
| Lenovo | lenovo.com | ThinkSystem series |
| Amazon | amazon.com | Renewed/refurbished |
| eBay | ebay.com | Refurbished servers |

---

## 7. FAQ for Finance/Procurement

**Q: Why not use cloud servers?**
A: Security requirement - data must stay on internal network. Cloud also has ongoing costs ($1,500+/year vs $0/year).

**Q: Can we use existing hardware?**
A: Yes! Any PC with 8GB+ RAM and 4+ cores will work for small teams. Check with IT for available equipment.

**Q: What if we need more capacity later?**
A: Simply upgrade RAM/storage or add second server. LocaNext scales horizontally.

**Q: Is there any recurring cost?**
A: No software costs. Only electricity (~$5-10/month) and optional hardware maintenance.

**Q: What's the warranty situation?**
A: New servers come with 1-3 year warranty. Refurbished varies. Software is self-maintained (no vendor dependency).

**Q: Can we expense this?**
A: Yes, it's a standard IT equipment purchase. No ongoing subscription = easy budgeting.

---

## 8. Sign-Off Template

```
EQUIPMENT PROCUREMENT APPROVAL
═══════════════════════════════════════════════════════════════

Project: LocaNext Localization Platform
Configuration: [ ] Minimum  [ ] Recommended  [ ] Enterprise

Estimated Costs:
├── Hardware: $_____________
├── One-time setup: $_____________
└── Annual operating: $_____________

5-Year Savings vs Commercial Alternative: $_____________

Approved by:

IT Manager: ______________________ Date: ___________

Finance: _________________________ Date: ___________

Department Head: _________________ Date: ___________
```

---

*Document Version: 2025-12-09*
*Classification: Internal - Procurement*
