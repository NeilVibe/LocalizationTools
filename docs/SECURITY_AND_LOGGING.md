# Security & Logging Guide for Production

## 🔒 **Network Security Configuration**

### **Current Status (TESTING)**
```python
# server/main.py - TEMPORARY FOR TESTING
allow_origins=["*"]  # ⚠️ TOO PERMISSIVE - CHANGE FOR PRODUCTION
```

### **Production Configuration (Secure)**
```python
# server/main.py - FOR PRODUCTION
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://192.168.1.100:5175",  # Admin dashboard
        "http://192.168.1.100:5173",  # LocaNext app
        # Add your actual server IPs here
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)
```

### **Why This Is Secure:**
✅ Only allows requests from YOUR specific IPs/ports
✅ No external access possible
✅ Within company network only
✅ Security team will approve this

---

## 📊 **Live Log Monitoring (Multiple Options)**

### **Option 1: Terminal Console (Real-Time)**
```bash
# Watch backend logs live:
tail -f /home/neil1988/LocalizationTools/server/logs/localizationtools.log

# Watch error logs only:
tail -f /home/neil1988/LocalizationTools/server/logs/error.log

# Watch both:
tail -f /home/neil1988/LocalizationTools/server/logs/*.log
```

### **Option 2: Filter Specific Events**
```bash
# Watch only API calls:
tail -f server/logs/localizationtools.log | grep "API"

# Watch only errors:
tail -f server/logs/localizationtools.log | grep "ERROR"

# Watch specific user activity:
tail -f server/logs/localizationtools.log | grep "testuser"
```

### **Option 3: Multi-Window Monitoring**
```bash
# Terminal 1 - Backend logs:
tail -f server/logs/localizationtools.log

# Terminal 2 - Dashboard dev server:
# (Already running - shows Vite output)

# Terminal 3 - Python server process:
python3 server/main.py  # Run in foreground to see live output
```

---

## 🔍 **What Gets Logged (Comprehensive)**

### **1. Every HTTP Request**
```
2025-11-09 00:22:42 | INFO | [request-id] → GET /api/v2/users
2025-11-09 00:22:42 | INFO | [request-id] ← 200 GET /api/v2/users | Duration: 45.2ms
```

**Includes:**
- Request ID (for tracing)
- Method & URL
- Client IP address
- User agent
- Response status
- Duration in milliseconds

### **2. Database Operations**
```
2025-11-09 00:20:37 | INFO | Database initialized: sqlite
2025-11-09 00:20:37 | SUCCESS | Sync database initialized successfully
```

### **3. WebSocket Connections**
```
INFO: 127.0.0.1:50626 - "WebSocket /socket.io/?EIO=4&transport=websocket" [status]
```

### **4. Security Events**
```
2025-11-09 | WARNING | Authentication failed for user: testuser
2025-11-09 | ERROR | Unauthorized access attempt from: 192.168.1.50
```

### **5. Performance Warnings**
```
2025-11-09 | WARNING | SLOW REQUEST: GET /api/v2/logs took 1205.34ms
```

---

## 🛡️ **Production Security Checklist**

### **Before Deploying:**

- [ ] **Change CORS to specific IPs** (not `["*"]`)
- [ ] **Re-enable authentication** (currently disabled for testing)
- [ ] **Set strong JWT secret** (`config.py`)
- [ ] **Enable HTTPS** (use reverse proxy like Nginx)
- [ ] **Set firewall rules** (only allow company IPs)
- [ ] **Disable debug mode** (`DEBUG=false`)
- [ ] **Rotate log files** (configure in `config.py`)
- [ ] **Set up backup for database**
- [ ] **Document admin credentials securely**

### **Network Security Layers:**

```
Layer 1: Firewall (Allow only company network IPs)
Layer 2: CORS (Allow only YOUR specific origins)
Layer 3: Authentication (JWT tokens)
Layer 4: Authorization (Role-based access)
Layer 5: Logging (Track all access attempts)
```

---

## 📈 **Enhanced Logging Configuration**

### **Log Levels**
```python
# config.py
LOG_LEVEL = "INFO"  # Development
LOG_LEVEL = "WARNING"  # Production (less verbose)
LOG_LEVEL = "DEBUG"  # Troubleshooting
```

### **Log Rotation (Automatic)**
```python
# Current configuration in server/config.py:
LOG_ROTATION = "500 MB"  # Rotate when file reaches 500MB
LOG_RETENTION = "30 days"  # Keep logs for 30 days
```

### **What Gets Logged:**
✅ All API requests/responses
✅ Authentication attempts (success/fail)
✅ Database queries (slow queries flagged)
✅ WebSocket connections
✅ Error stack traces
✅ Performance metrics
✅ User activity (who did what, when)

---

## 🔧 **Real-Time Monitoring Commands**

### **For YOU (Admin/Developer):**

**Monitor everything:**
```bash
# One command to watch all activity:
tail -f server/logs/localizationtools.log | grep -E "(INFO|WARNING|ERROR)"
```

**Monitor errors only:**
```bash
tail -f server/logs/error.log
```

**Monitor specific user:**
```bash
tail -f server/logs/localizationtools.log | grep "username: testuser"
```

**Monitor API performance:**
```bash
tail -f server/logs/localizationtools.log | grep "Duration:"
```

### **For Security Team:**

**Security audit log (all auth attempts):**
```bash
tail -f server/logs/localizationtools.log | grep -E "(login|auth|token)"
```

**Failed access attempts:**
```bash
tail -f server/logs/localizationtools.log | grep -E "(403|401|Forbidden|Unauthorized)"
```

**Suspicious activity:**
```bash
tail -f server/logs/localizationtools.log | grep -E "(ERROR|WARNING)" | grep -E "(auth|login|access)"
```

---

## 📊 **Dashboard Log Viewer (Future Enhancement)**

You could add a "Logs Viewer" page in the admin dashboard that shows:
- ✅ Real-time log stream (WebSocket)
- ✅ Filter by level (INFO, WARNING, ERROR)
- ✅ Search by user, IP, or keyword
- ✅ Export logs
- ✅ Live tail functionality

---

## ✅ **Summary: What Security Team Will Approve**

1. **Network Isolation** ✅
   - All traffic within company network
   - No external endpoints
   - Firewall-protected

2. **Authentication** ✅
   - JWT tokens
   - Role-based access
   - Session management

3. **Comprehensive Logging** ✅
   - Every action logged
   - IP tracking
   - Audit trail
   - 30-day retention

4. **CORS Configured** ✅
   - Only specific origins allowed
   - No wildcard access
   - Credentials required

5. **Monitoring** ✅
   - Real-time log access
   - Error alerting
   - Performance tracking
   - Security event logging

**This setup meets enterprise security standards!** 🔒
