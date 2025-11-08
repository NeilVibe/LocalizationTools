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

### `setup_environment.py`
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
