# LocalizationTools

> **A unified desktop application suite for localization and translation tools with comprehensive usage analytics**

---

## 📋 Project Overview

LocalizationTools consolidates multiple Python-based localization/translation utilities into a single, user-friendly Gradio desktop application. The system tracks detailed usage analytics to demonstrate tool adoption and effectiveness to management.

### Key Features

- 🎯 **Unified Interface**: Single app with tabbed interface for 10+ tools
- 📊 **Usage Analytics**: Comprehensive tracking of tool usage, performance, and user activity
- 🔄 **Auto-Updates**: Automatic version checking and seamless updates
- 🖥️ **Client-Side Processing**: All heavy processing uses user's CPU (not server)
- 🔐 **User Authentication**: Secure login with role-based access
- 📈 **Admin Dashboard**: Beautiful real-time statistics and reports
- 🌐 **Works Offline**: Full functionality after initial download

---

## 🏗️ Architecture

### Client Application (User's Computer)
- **Technology**: Gradio Desktop App
- **Size**: ~500MB-1GB (one-time download)
- **Processing**: Uses user's CPU for all operations
- **Contains**: All tools, ML models, and dependencies

### Central Server
- **Technology**: FastAPI + PostgreSQL
- **Purpose**: Logging, analytics, authentication, updates
- **Does NOT**: Process files or handle heavy computation

### Admin Dashboard
- **Technology**: Gradio Web Dashboard
- **Features**: Real-time stats, user activity, tool popularity, performance metrics

---

## 📁 Project Structure

```
LocalizationTools/
├── client/                     # CLIENT APPLICATION
│   ├── main.py                # Gradio app entry point
│   ├── config.py              # App configuration
│   ├── ui/                    # UI Components
│   │   ├── app.py             # Main Gradio interface
│   │   ├── theme.py           # Custom styling
│   │   └── components.py      # Reusable UI elements
│   ├── tools/                 # TOOL MODULES
│   │   └── xls_transfer/      # XLSTransfer tool
│   │       ├── ui.py          # Gradio interface
│   │       ├── core.py        # Core logic
│   │       ├── embeddings.py  # AI embeddings
│   │       └── excel_utils.py # Excel operations
│   ├── models/                # ML MODELS
│   │   └── KRTransformer/     # Korean BERT (not in git)
│   └── utils/                 # UTILITIES
│       ├── logger.py          # Send logs to server
│       ├── progress.py        # Progress tracking
│       └── updater.py         # Auto-update system
│
├── server/                    # CENTRAL SERVER
│   ├── main.py                # FastAPI application
│   ├── config.py              # Server configuration
│   ├── api/                   # API ENDPOINTS
│   │   ├── logs.py            # Logging endpoints
│   │   ├── auth.py            # Authentication
│   │   └── stats.py           # Statistics
│   ├── database/              # DATABASE
│   │   ├── models.py          # SQLAlchemy models
│   │   ├── crud.py            # Database operations
│   │   └── connection.py      # DB connection
│   ├── admin/                 # ADMIN DASHBOARD
│   │   └── dashboard.py       # Gradio dashboard
│   └── data/                  # Database storage (not in git)
│
├── scripts/                   # BUILD & SETUP SCRIPTS
│   ├── build_client.py        # PyInstaller build
│   ├── setup_database.py      # Database initialization
│   └── download_models.py     # Download ML models
│
├── tests/                     # TESTS
│   ├── test_xls_transfer.py
│   └── test_api.py
│
├── ARCHIVE/                   # ARCHIVED CODE (clean code policy)
│   ├── old_code/              # Deprecated versions
│   ├── test_scripts/          # One-off test scripts
│   ├── experiments/           # Experimental features
│   └── notes/                 # Development notes
│
├── RessourcesForCodingTheProject/  # ORIGINAL SCRIPTS & TEST DATA
│   ├── MAIN PYTHON SCRIPTS/
│   ├── SECONDARY PYTHON SCRIPTS/
│   └── datausedfortesting/
│
├── Claude.md                  # Complete project documentation
├── Roadmap.md                 # Development roadmap
├── database_schema.sql        # PostgreSQL schema
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL 15+ (for production) or SQLite (for development)

### Installation

1. **Clone the repository**
   ```bash
   git clone git@github.com:NeilVibe/LocalizationTools.git
   cd LocalizationTools
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Download ML models**
   ```bash
   python scripts/download_models.py
   ```

5. **Set up database**
   ```bash
   # For local development (SQLite)
   python scripts/setup_database.py --db sqlite

   # For production (PostgreSQL)
   python scripts/setup_database.py --db postgresql
   ```

6. **Run the client application**
   ```bash
   python client/main.py
   ```

7. **Run the server (separate terminal)**
   ```bash
   uvicorn server.main:app --host localhost --port 8888 --reload
   ```

8. **Run the admin dashboard (separate terminal)**
   ```bash
   python server/admin/dashboard.py
   ```

---

## 🛠️ Development

### Running Tests

```bash
pytest tests/
```

### Code Formatting

```bash
black .
isort .
flake8 .
```

### Building Executable

```bash
python scripts/build_client.py
```

---

## 📊 Database Schema

The application uses PostgreSQL with 13+ tables:

- **users**: User authentication and profiles
- **sessions**: Active user sessions tracking
- **log_entries**: Main usage logs (every tool execution)
- **tool_usage_stats**: Daily aggregated statistics
- **app_versions**: Version management for updates
- **announcements**: Push notifications to users

See `database_schema.sql` for complete schema.

---

## 🔐 Security

- **Passwords**: bcrypt hashed (never stored in plaintext)
- **Sessions**: JWT token-based authentication
- **API**: Secure API key authentication for client-server communication
- **Data Privacy**: User files never sent to server (only metadata)

---

## 📈 Tools Included

### Phase 1 (MVP)
- **XLSTransfer**: AI-powered translation transfer between Excel files

### Planned
- TFM Full/Lite: Translation Memory processing
- Quick Search: Fast file search utilities
- Korean Similarity Checker
- Stack/Remove Duplicates
- And more...

---

## 🧹 Clean Code Policy

**STRICT RULE**: Keep project directories CLEAN.

### ARCHIVE Folder Usage
- All temporary/test scripts → `ARCHIVE/test_scripts/`
- Old code versions → `ARCHIVE/old_code/`
- Failed experiments → `ARCHIVE/experiments/`
- Deprecated tools → `ARCHIVE/deprecated_tools/`

### Never Leave Behind
- ❌ `temp.py`, `test123.py`, `debug_something.py`
- ❌ Orphaned test files
- ❌ Old versions in working directories

---

## 📝 Documentation

- **Claude.md**: Complete project documentation and architecture
- **Roadmap.md**: Detailed development roadmap and timeline
- **database_schema.sql**: PostgreSQL schema with comments

---

## 🤝 Contributing

1. Create feature branch
2. Follow clean code policy
3. Write tests for new features
4. Run code formatters (black, isort)
5. Submit pull request

---

## 📄 License

Internal project - Company use only

---

## 👤 Author

**Neil** - Localization Tools Developer

---

## 🔄 Update System

The application includes an automatic update system:

1. App checks for updates on startup
2. Notifies user if new version available
3. One-click download and install
4. Optional or mandatory updates
5. All tracked in database

---

## 📞 Support

For issues or questions, contact the development team.

---

**Built with ❤️ for efficient localization workflows**
