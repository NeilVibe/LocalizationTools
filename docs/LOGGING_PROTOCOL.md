# 📋 Logging Protocol - LocaNext Project

**Version**: 1.0
**Last Updated**: 2025-11-09
**Status**: Official Protocol - MUST FOLLOW

---

## 🎯 Purpose

This document establishes the **mandatory logging protocol** for all LocaNext development. Every function, API endpoint, and component MUST follow this protocol to ensure comprehensive monitoring and debugging capabilities.

---

## 🚨 Golden Rule

**LOG EVERYTHING. AT EVERY STEP.**

When building new features or migrating code from original resources to LocaNext:
- ✅ Log when a function starts
- ✅ Log key parameters and inputs
- ✅ Log processing steps
- ✅ Log success/failure outcomes
- ✅ Log timing/performance metrics
- ✅ Log errors with full context

---

## 📚 Backend Logging (Python/FastAPI)

### Import Statement

```python
from loguru import logger
import time  # For performance timing
```

### Log Levels

| Level | When to Use | Example |
|-------|-------------|---------|
| `logger.info()` | Function entry, normal operations | `logger.info("User login requested")` |
| `logger.success()` | Successful completion | `logger.success("Dictionary created successfully")` |
| `logger.warning()` | Non-critical issues | `logger.warning("Using default threshold")` |
| `logger.error()` | Errors that can be handled | `logger.error("File upload failed")` |
| `logger.critical()` | System-critical failures | `logger.critical("Database connection lost")` |

### Logging Pattern - API Endpoints

```python
@router.post("/api/endpoint")
async def endpoint_function(
    param1: str,
    param2: int,
    current_user: dict = Depends(get_current_active_user_async)
):
    """API endpoint description"""

    # 1. START: Log entry with timing
    start_time = time.time()
    username = current_user.get("username", "unknown") if isinstance(current_user, dict) else getattr(current_user, "username", "unknown")

    logger.info(f"Endpoint called by user: {username}", {
        "user": username,
        "param1": param1,
        "param2": param2
    })

    # 2. VALIDATE: Log validation checks
    if not param1:
        logger.error("Invalid parameter: param1 is empty")
        raise HTTPException(status_code=400, detail="param1 is required")

    # 3. PROCESS: Log each processing step
    try:
        logger.info("Starting data processing")

        # Do work here
        result = process_data(param1, param2)

        logger.info("Data processed successfully", {"result_count": len(result)})

        # 4. SUCCESS: Log completion with metrics
        elapsed_time = time.time() - start_time

        logger.success(f"Endpoint completed in {elapsed_time:.2f}s", {
            "user": username,
            "elapsed_time": elapsed_time,
            "result_count": len(result)
        })

        return {"success": True, "data": result}

    except Exception as e:
        # 5. ERROR: Log failure with full context
        elapsed_time = time.time() - start_time

        logger.error(f"Endpoint failed after {elapsed_time:.2f}s: {str(e)}", {
            "user": username,
            "error": str(e),
            "error_type": type(e).__name__,
            "elapsed_time": elapsed_time
        })

        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
```

### Logging Pattern - File Operations

```python
# Log file uploads
file_size = len(await file.read())
logger.info(f"File uploaded: {file.filename}", {
    "filename": file.filename,
    "size_bytes": file_size,
    "path": str(file_path)
})

# Log file processing
logger.info(f"Processing file: {filename}", {
    "operation": "translation",
    "file_type": "excel"
})

# Log file creation
logger.success(f"Output file created: {output_path}", {
    "input": input_file,
    "output": output_path,
    "size_bytes": output_size
})
```

### Logging Pattern - Module Initialization

```python
# At module level
try:
    from server.tools.xlstransfer import core, embeddings, translation
    logger.success("XLSTransfer modules loaded successfully", {
        "core": core is not None,
        "embeddings": embeddings is not None,
        "translation": translation is not None
    })
except ImportError as e:
    logger.error(f"Failed to import modules: {e}")
```

---

## 🎨 Frontend Logging (JavaScript/Svelte)

### Import Statement

```javascript
import { logger } from "$lib/utils/logger.js";
```

### Frontend Log Levels

| Function | When to Use | Example |
|----------|-------------|---------|
| `logger.info(msg, data)` | Normal operations | `logger.info("Component mounted")` |
| `logger.success(msg, data)` | Successful actions | `logger.success("File uploaded")` |
| `logger.warning(msg, data)` | Non-critical issues | `logger.warning("Slow network detected")` |
| `logger.error(msg, data)` | Errors | `logger.error("API call failed", {error})` |
| `logger.critical(msg, data)` | Critical failures | `logger.critical("Lost backend connection")` |
| `logger.component(name, event, data)` | Component lifecycle | `logger.component("XLSTransfer", "mounted")` |
| `logger.apiCall(endpoint, method, data)` | API interactions | `logger.apiCall("/api/upload", "POST")` |

### Logging Pattern - Svelte Components

```javascript
<script>
import { onMount } from "svelte";
import { logger } from "$lib/utils/logger.js";

// Component state
let data = [];
let isLoading = false;

onMount(async () => {
  logger.component("ComponentName", "mounted");

  try {
    await loadData();
  } catch (error) {
    logger.error("Component initialization failed", { error: error.message });
  }
});

async function loadData() {
  logger.info("Loading data from API");
  isLoading = true;

  try {
    logger.apiCall("/api/data", "GET");
    const response = await api.getData();

    data = response.data;
    logger.success("Data loaded successfully", { count: data.length });

  } catch (error) {
    logger.error("Data loading failed", {
      endpoint: "/api/data",
      error: error.message
    });
  } finally {
    isLoading = false;
  }
}

async function handleSubmit() {
  logger.component("ComponentName", "submit", { dataCount: data.length });

  try {
    logger.apiCall("/api/submit", "POST", { items: data.length });
    const result = await api.submit(data);

    logger.success("Submission completed", { result });

  } catch (error) {
    logger.error("Submission failed", { error: error.message });
  }
}
</script>
```

### Logging Pattern - File Uploads (Browser)

```javascript
async function handleFileUpload(event) {
  const files = event.target.files;

  logger.info("File upload started", {
    file_count: files.length,
    filenames: Array.from(files).map(f => f.name)
  });

  for (const file of files) {
    logger.info(`Uploading file: ${file.name}`, {
      filename: file.name,
      size: file.size,
      type: file.type
    });

    try {
      const result = await api.uploadFile(file);
      logger.success(`File uploaded: ${file.name}`, result);
    } catch (error) {
      logger.error(`File upload failed: ${file.name}`, {
        filename: file.name,
        error: error.message
      });
    }
  }
}
```

---

## 🔍 Monitoring System Usage

### Real-Time Monitoring

```bash
# Monitor ALL servers (recommended during development)
bash scripts/monitor_logs_realtime.sh

# Monitor specific log files
tail -f server/data/logs/server.log        # Backend
tail -f logs/locanext_app.log              # LocaNext
tail -f logs/dashboard_app.log             # Dashboard

# Monitor errors only
tail -f server/data/logs/error.log         # Backend errors
tail -f logs/locanext_error.log            # LocaNext errors
tail -f logs/dashboard_error.log           # Dashboard errors
```

### Quick Status Check

```bash
# Check all servers status
bash scripts/monitor_all_servers.sh
```

---

## 📊 Log Format

All logs follow this structure:
```
YYYY-MM-DD HH:MM:SS | LEVEL | module:function:line - Message | {"key": "value"}
```

Example:
```
2025-11-09 14:40:45 | SUCCESS | xlstransfer_async:create_dictionary:133 - Dictionary created in 2.45s | {"user": "admin", "files": 3, "elapsed_time": 2.45}
```

---

## ✅ Checklist for New Code

Before committing new code, verify:

- [ ] Imported logger module (`from loguru import logger` or `import { logger }`)
- [ ] Added `start_time = time.time()` for functions that process data
- [ ] Logged function entry with parameters
- [ ] Logged each major processing step
- [ ] Logged success/failure with timing
- [ ] Logged errors with full context (error message, type, user, timing)
- [ ] Included structured data in log calls (dictionaries/objects)
- [ ] Tested logging by running the function and checking logs

---

## 🚫 What NOT to Do

❌ **Don't use print() statements**
```python
print("Processing file...")  # BAD
logger.info("Processing file...")  # GOOD
```

❌ **Don't log without context**
```python
logger.info("Success")  # BAD - no context
logger.success("Dictionary created successfully", {"files": 3})  # GOOD
```

❌ **Don't ignore errors**
```python
try:
    process_data()
except:
    pass  # BAD - swallows errors silently

try:
    process_data()
except Exception as e:
    logger.error(f"Processing failed: {e}")  # GOOD
    raise
```

❌ **Don't log sensitive data**
```python
logger.info("User login", {"password": password})  # BAD - security risk
logger.info("User login", {"username": username})  # GOOD
```

---

## 📁 Log File Locations

### Backend (Python)
- Main log: `server/data/logs/server.log`
- Error log: `server/data/logs/error.log`
- Archive: `server/data/logs/archive/` (logs older than 7 days)

### LocaNext (Electron/Browser)
- Main log: `logs/locanext_app.log`
- Error log: `logs/locanext_error.log`
- Archive: `logs/archive/`

### Admin Dashboard
- Main log: `logs/dashboard_app.log`
- Error log: `logs/dashboard_error.log`
- Archive: `logs/archive/`

---

## 🎯 Example: Perfect Logging Implementation

See `server/api/xlstransfer_async.py` for a complete example of this protocol in action.

Key highlights:
- ✅ Logger imported at top
- ✅ Module loading logged on import
- ✅ Every endpoint has entry/exit logging
- ✅ User context captured
- ✅ Timing metrics included
- ✅ File operations logged with sizes
- ✅ Errors logged with full context
- ✅ Structured data in every log call

---

## 📝 Migration Protocol

When migrating code from original resources to LocaNext:

1. **Before writing any code**:
   - Import logger
   - Add timing variables

2. **While writing code**:
   - Log function entry
   - Log each major step
   - Log all file operations
   - Log all API calls

3. **Before testing**:
   - Log success/failure
   - Log performance metrics
   - Log error handling

4. **After testing**:
   - Review logs to ensure all operations are captured
   - Verify error cases are logged
   - Confirm timing data is present

---

## 🔮 Future: Central Logging

**Planned**: All user installations will send logs to a central dashboard for remote monitoring.

This will enable:
- Real-time monitoring of all user installations
- Proactive error detection
- Usage analytics
- Performance tracking across user base

Protocol will be updated when this feature is implemented.

---

**Remember**: Comprehensive logging is NOT optional. It's the foundation of a maintainable, debuggable, and professional system. When in doubt, log more rather than less.
