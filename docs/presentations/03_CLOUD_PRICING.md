# LocaNext Cloud Pricing Guide

---

## Deployment Options

| Option | Monthly Cost | Best For |
|--------|--------------|----------|
| **On-Premise** | $0 | Existing server |
| **Cloud VM** | $20-150/month | New deployment |
| **Managed** | $100-500/month | Full service |

---

## Cloud Provider Pricing (2025)

### Option 1: Budget (10-30 users)

```
+------------------------------------------------------------------+
|                    BUDGET OPTION                                  |
|                    $20-50/month                                   |
+------------------------------------------------------------------+
|                                                                   |
|  AWS Lightsail                                                    |
|  - 2 vCPU, 4GB RAM, 80GB SSD                                      |
|  - $20/month                                                      |
|                                                                   |
|  DigitalOcean Droplet                                             |
|  - 2 vCPU, 4GB RAM, 80GB SSD                                      |
|  - $24/month                                                      |
|                                                                   |
|  Vultr Cloud Compute                                              |
|  - 2 vCPU, 4GB RAM, 80GB SSD                                      |
|  - $24/month                                                      |
|                                                                   |
|  Google Cloud (e2-medium)                                         |
|  - 2 vCPU, 4GB RAM, 50GB SSD                                      |
|  - ~$35/month                                                     |
|                                                                   |
+------------------------------------------------------------------+
```

---

### Option 2: Standard (30-100 users)

```
+------------------------------------------------------------------+
|                    STANDARD OPTION                                |
|                    $50-100/month                                  |
+------------------------------------------------------------------+
|                                                                   |
|  AWS EC2 (t3.medium)                                              |
|  - 2 vCPU, 4GB RAM + RDS PostgreSQL                               |
|  - $50-80/month                                                   |
|                                                                   |
|  Azure (B2s VM)                                                   |
|  - 2 vCPU, 4GB RAM + PostgreSQL Flexible                          |
|  - $60-90/month                                                   |
|                                                                   |
|  Google Cloud (n2-standard-2)                                     |
|  - 2 vCPU, 8GB RAM + Cloud SQL                                    |
|  - $70-100/month                                                  |
|                                                                   |
+------------------------------------------------------------------+
```

---

### Option 3: Enterprise (100+ users)

```
+------------------------------------------------------------------+
|                    ENTERPRISE OPTION                              |
|                    $150-300/month                                 |
+------------------------------------------------------------------+
|                                                                   |
|  AWS (t3.large + RDS)                                             |
|  - 4 vCPU, 8GB RAM + Managed PostgreSQL                           |
|  - $150-200/month                                                 |
|                                                                   |
|  Azure (D2s_v3 + PostgreSQL)                                      |
|  - 4 vCPU, 8GB RAM + Managed PostgreSQL                           |
|  - $180-250/month                                                 |
|                                                                   |
|  Google Cloud (n2-standard-4 + Cloud SQL)                         |
|  - 4 vCPU, 16GB RAM + Managed PostgreSQL                          |
|  - $200-300/month                                                 |
|                                                                   |
+------------------------------------------------------------------+
```

---

## Korean Cloud Providers

| Provider | Spec | Monthly |
|----------|------|---------|
| **Naver Cloud** | 2vCPU/4GB | ~40,000 KRW |
| **NHN Cloud** | 2vCPU/4GB | ~35,000 KRW |
| **KT Cloud** | 2vCPU/4GB | ~45,000 KRW |

---

## Cost Comparison Summary

```
+------------------------------------------------------------------+
|                    ANNUAL COST RANGE                              |
+------------------------------------------------------------------+
|                                                                   |
|  BUDGET (Small Team)                                              |
|  +------------------------+-------------------+                   |
|  | Cloud VM               | $240-600/year     |                   |
|  | Software Licenses      | $0                |                   |
|  | Support (DIY)          | $0                |                   |
|  +------------------------+-------------------+                   |
|  | TOTAL                  | $240-600/year     |                   |
|  +------------------------+-------------------+                   |
|                                                                   |
|  STANDARD (Medium Team)                                           |
|  +------------------------+-------------------+                   |
|  | Cloud VM + DB          | $600-1,200/year   |                   |
|  | Software Licenses      | $0                |                   |
|  | Backup Storage         | $50-100/year      |                   |
|  +------------------------+-------------------+                   |
|  | TOTAL                  | $650-1,300/year   |                   |
|  +------------------------+-------------------+                   |
|                                                                   |
|  ENTERPRISE (Large Team)                                          |
|  +------------------------+-------------------+                   |
|  | Cloud Infrastructure   | $1,800-3,600/year |                   |
|  | Software Licenses      | $0                |                   |
|  | Backup + DR            | $200-500/year     |                   |
|  +------------------------+-------------------+                   |
|  | TOTAL                  | $2,000-4,100/year |                   |
|  +------------------------+-------------------+                   |
|                                                                   |
+------------------------------------------------------------------+
```

---

## On-Premise (Zero Cloud Cost)

| Requirement | Notes |
|-------------|-------|
| Server | Any Windows/Linux server |
| RAM | 4GB minimum, 8GB recommended |
| Storage | 50GB minimum |
| Network | Company intranet only |
| Cost | **$0** (use existing infrastructure) |

---

## Recommendation

```
+------------------------------------------------------------------+
|                    RECOMMENDED APPROACH                           |
+------------------------------------------------------------------+
|                                                                   |
|  PHASE 1: On-Premise (NOW)                                        |
|  - Use existing company server                                    |
|  - Zero additional cost                                           |
|  - Test with real users                                           |
|                                                                   |
|  PHASE 2: Cloud (OPTIONAL - Future)                               |
|  - Migrate to cloud if needed                                     |
|  - Budget: $50-100/month                                          |
|  - Better uptime, easier backup                                   |
|                                                                   |
+------------------------------------------------------------------+
```

---

*Prices as of December 2025 - Subject to change*
*LocaNext v2512110832*
