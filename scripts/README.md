# Scripts

Build and setup scripts for LocalizationTools.

## 🚀 Quick Start

**Automated Setup** (Recommended):
```bash
python scripts/setup_environment.py
```

This will:
1. Check Python version (3.10+ required)
2. Create virtual environment
3. Install all dependencies
4. Download Korean BERT model
5. Verify installation

---

## 📜 Available Scripts

### 🧹 Maintenance Scripts

#### `clean_logs.sh`
**Purpose**: Clean and archive old logs for fresh start

**Usage**:
```bash
./scripts/clean_logs.sh
```

**What it does**:
- Archives all logs to `logs/archive/TIMESTAMP/`
- Resets current logs with clean markers
- Preserves historical data
- Prevents confusion for future Claude sessions

**When to use**:
- Before starting new development sessions
- After fixing major bugs (to clear error history)
- When logs become too large
- Before demonstrating to stakeholders

**Logs cleaned**:
- `server/data/logs/error.log` (backend errors)
- `server/data/logs/server.log` (backend activity)
- `server_output.log` (server console output)
- `logs/locanext_*.log` (frontend logs)

---

### 🔍 Monitoring Scripts

#### `monitor_system.sh`
**Purpose**: Comprehensive system health check

**Usage**:
```bash
./scripts/monitor_system.sh
```

**What it checks**:
- Backend health (port 8888)
- Frontend health (port 5173)
- Database connectivity
- Active operations
- WebSocket functionality
- Recent logs

---

#### `monitor_backend_live.sh`
**Purpose**: Live dashboard updating every 5 seconds

**Usage**:
```bash
./scripts/monitor_backend_live.sh
```

**Shows**:
- Backend health status
- Running operations count
- Recent API calls
- Last 5 log entries
- Real-time updates

---

#### `monitor_taskmanager.sh`
**Purpose**: Monitor TaskManager component activity

**Usage**:
```bash
./scripts/monitor_taskmanager.sh
```

**Monitors**:
- TaskManager API calls (`/api/progress/operations`)
- Auth token usage
- WebSocket progress events
- Frontend component loads

---

#### `monitor_all_servers.sh`
**Purpose**: Quick health check for all 3 servers

**Usage**:
```bash
./scripts/monitor_all_servers.sh
```

**Checks**:
- Backend API (port 8888)
- Frontend Dev Server (port 5173)
- Auth Server (port 8000)

---

#### `monitor_logs_realtime.sh`
**Purpose**: Tail logs with color coding

**Usage**:
```bash
./scripts/monitor_logs_realtime.sh
```

**Features**:
- Color-coded output (errors in red, success in green)
- Filters relevant entries
- Real-time updates

---

#### `monitor_frontend_errors.sh`
**Purpose**: Track frontend errors specifically

**Usage**:
```bash
./scripts/monitor_frontend_errors.sh
```

**Monitors**: Frontend error log with filtering

---

### 🧪 Testing Scripts

#### `test_full_xlstransfer_workflow.sh`
**Purpose**: Complete workflow test for XLSTransfer

**Usage**:
```bash
./scripts/test_full_xlstransfer_workflow.sh
```

**Tests**:
- File upload
- Processing pipeline
- Progress tracking
- Output generation

---

### 🛠️ Setup Scripts

#### `setup_environment.py`
**Purpose**: Complete automated environment setup

**Usage**:
```bash
python scripts/setup_environment.py
```

**What it does**:
- Checks Python version compatibility
- Creates virtual environment (optional)
- Installs all packages from requirements.txt
- Downloads ML models
- Verifies everything works

---

### `download_models.py`
**Purpose**: Download Korean BERT model to local project folder

**Usage**:
```bash
python scripts/download_models.py
```

**What it does**:
- Downloads Korean-specific BERT model
- Saves directly to `client/models/KRTransformer/`
- Verifies model loads correctly
- Tests with sample Korean text

**Model Location**: `client/models/KRTransformer/` (visible in project, not hidden)

**Model Details**:
- Name: snunlp/KR-SBERT-V40K-klueNLI-augSTS
- Size: ~400MB
- Optimized for: Korean game localization and translation
- Used for: Semantic similarity in translation matching

---

### `setup_database.py` (TODO)
**Purpose**: Initialize PostgreSQL or SQLite database

**Usage**:
```bash
# SQLite (development)
python scripts/setup_database.py --db sqlite

# PostgreSQL (production)
python scripts/setup_database.py --db postgresql
```

**What it will do**:
- Create database tables from schema
- Set up initial admin user
- Insert default app version
- Verify connections

---

### `build_client.py` (TODO)
**Purpose**: Build standalone executable with PyInstaller

**Usage**:
```bash
python scripts/build_client.py
```

**What it will do**:
- Package client application
- Bundle ML models
- Create single executable
- Output to `dist/LocalizationTools.exe`

---

## 🧹 Clean Code Standards

All scripts follow project cleanliness standards:
- Clear, descriptive names
- Comprehensive error handling
- User-friendly output messages
- Progress indicators
- Helpful troubleshooting tips

---

## 🔧 Manual Setup (Alternative)

If you prefer manual setup:

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# 2. Upgrade pip
pip install --upgrade pip

# 3. Install dependencies
pip install -r requirements.txt

# 4. Download models
python scripts/download_models.py

# 5. Verify
python -c "import gradio, fastapi, sentence_transformers; print('✓ Ready!')"
```

---

## 📝 Notes

- All scripts are designed to be run from the project root directory
- Virtual environment is recommended but optional
- Scripts provide clear error messages and troubleshooting tips
- Model is downloaded to project folder (not hidden cache)

---

**Keep it CLEAN!** 🧹
