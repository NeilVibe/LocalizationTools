# LocaNext - Localization Tools Platform

> **Modern web-based platform for localization and translation tools with comprehensive usage analytics and admin dashboard**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![SvelteKit](https://img.shields.io/badge/SvelteKit-2.0+-orange.svg)](https://kit.svelte.dev/)
[![License](https://img.shields.io/badge/License-Internal-red.svg)](LICENSE)

---

## 📋 Overview

LocaNext is a modern web-based platform that consolidates multiple localization and translation tools into a unified interface. Built with FastAPI backend and SvelteKit frontend, it provides powerful tools for translators while tracking comprehensive usage analytics for management insights.

### 🎯 Key Features

- 🌐 **Modern Web Platform**: Browser-based interface accessible from anywhere
- ⚡ **Real-Time Updates**: WebSocket-powered live progress tracking
- 📊 **Comprehensive Analytics**: Detailed usage statistics, rankings, and performance metrics
- 🎨 **Beautiful Admin Dashboard**: Interactive charts, leaderboards, and reports
- 🔐 **Secure Authentication**: JWT-based user authentication with role management
- 🚀 **Scalable Architecture**: FastAPI backend + SvelteKit frontend
- 📈 **16 Admin API Endpoints**: Complete statistics and rankings system
- 🔄 **Background Processing**: Async task processing with real-time progress updates
- 💾 **Flexible Database**: SQLite for development, PostgreSQL for production

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    LOCANEXT PLATFORM                         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────┐         ┌──────────────────┐          │
│  │  SvelteKit       │         │  Admin Dashboard │          │
│  │  Frontend        │◄────────┤  (SvelteKit)     │          │
│  │  (Port 5173)     │         │  (Port 5173)     │          │
│  └────────┬─────────┘         └────────┬─────────┘          │
│           │                             │                     │
│           │        REST API + WebSocket │                     │
│           ▼                             ▼                     │
│  ┌─────────────────────────────────────────────────┐         │
│  │         FastAPI Backend (Port 8888)             │         │
│  │  ┌──────────────┐  ┌──────────────────────┐    │         │
│  │  │ Tool APIs    │  │ Admin APIs           │    │         │
│  │  │ - XLSTransfer│  │ - Statistics (10)    │    │         │
│  │  │ - More...    │  │ - Rankings (6)       │    │         │
│  │  └──────────────┘  └──────────────────────┘    │         │
│  │  ┌──────────────┐  ┌──────────────────────┐    │         │
│  │  │ Auth & Users │  │ Progress Tracking    │    │         │
│  │  └──────────────┘  └──────────────────────┘    │         │
│  │  ┌──────────────────────────────────────────┐  │         │
│  │  │         WebSocket Manager                 │  │         │
│  │  │   (Real-time progress updates)            │  │         │
│  │  └──────────────────────────────────────────┘  │         │
│  └─────────────────────────────────────────────────┘         │
│                           │                                   │
│                           ▼                                   │
│  ┌─────────────────────────────────────────────────┐         │
│  │    Database (SQLite/PostgreSQL)                 │         │
│  │  - users, sessions, active_operations           │         │
│  │  - log_entries, error_logs                      │         │
│  └─────────────────────────────────────────────────┘         │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack

**Frontend:**
- SvelteKit 2.0 - Modern reactive framework
- Chart.js - Interactive data visualizations
- Carbon Design System - IBM's design language
- Socket.IO Client - Real-time WebSocket connection

**Backend:**
- FastAPI - High-performance async Python framework
- SQLAlchemy 2.0 - Modern async ORM
- Socket.IO - WebSocket server for real-time updates
- Pydantic - Data validation and settings management

**Database:**
- SQLite (Development) - Zero-config database
- PostgreSQL (Production) - Robust production database

**ML/AI:**
- Sentence Transformers - Semantic text embeddings
- Korean BERT Models - Korean language processing

---

## 📁 Project Structure

```
LocalizationTools/
├── locaNext/                   # FRONTEND (SvelteKit)
│   ├── src/
│   │   ├── routes/            # Pages and API routes
│   │   ├── lib/               # Shared components and utilities
│   │   └── stores/            # Svelte stores for state management
│   └── package.json
│
├── adminDashboard/            # ADMIN DASHBOARD (SvelteKit)
│   ├── src/
│   │   ├── routes/
│   │   │   ├── +page.svelte           # Overview page
│   │   │   ├── stats/+page.svelte     # Statistics with charts
│   │   │   ├── rankings/+page.svelte  # User/App rankings
│   │   │   ├── users/+page.svelte     # User management
│   │   │   └── logs/+page.svelte      # Activity logs
│   │   └── lib/
│   │       └── api/client.js          # API client (16 methods)
│   └── package.json
│
├── server/                    # BACKEND (FastAPI)
│   ├── main.py                # FastAPI application entry point
│   ├── config.py              # Server configuration
│   ├── api/                   # API ENDPOINTS
│   │   ├── auth_async.py              # Authentication
│   │   ├── xlstransfer_async.py       # XLSTransfer tool API
│   │   ├── stats.py                   # Statistics API (10 endpoints)
│   │   ├── rankings.py                # Rankings API (6 endpoints)
│   │   ├── progress_operations.py     # Progress tracking
│   │   ├── base_tool_api.py           # Base class for tools
│   │   └── schemas.py                 # Pydantic models
│   ├── database/              # DATABASE
│   │   ├── models.py          # SQLAlchemy models
│   │   └── db_setup.py        # Database setup
│   ├── utils/                 # UTILITIES
│   │   ├── auth.py            # JWT authentication
│   │   ├── websocket.py       # WebSocket manager
│   │   └── dependencies.py    # FastAPI dependencies
│   └── data/                  # Database storage (gitignored)
│
├── client/                    # TOOL IMPLEMENTATIONS
│   └── tools/
│       ├── xls_transfer/      # XLSTransfer - AI-powered Excel tool
│       │   ├── core.py                # Core functionality
│       │   ├── embeddings.py          # AI embeddings
│       │   ├── translation.py         # Translation logic
│       │   └── excel_utils.py         # Excel operations
│       └── text_batch_processor/      # Text processing tool
│
├── tests/                     # TESTS
│   ├── test_dashboard_api.py          # Dashboard API tests (20 tests)
│   ├── test_async_auth.py             # Authentication tests
│   ├── test_async_infrastructure.py   # Infrastructure tests
│   └── integration/                   # Integration tests
│
├── docs/                      # DOCUMENTATION
│   ├── TESTING_GUIDE.md       # How to test the system
│   ├── STATS_DASHBOARD_SPEC.md # Dashboard specification
│   ├── ADMIN_SETUP.md         # Admin setup guide
│   └── PERFORMANCE.md         # Performance benchmarks
│
├── scripts/                   # BUILD & SETUP SCRIPTS
│   └── setup_database.py      # Database initialization
│
├── NewScripts/                # RAPID SCRIPT DEVELOPMENT (Side Project)
│   ├── README.md              # Guide for building new scripts
│   ├── 2025-11/               # Scripts organized by month
│   └── archive/               # Old or deprecated scripts
│
├── RessourcesForCodingTheProject/  # REFERENCE SCRIPT LIBRARY
│   ├── MAIN PYTHON SCRIPTS/   # 9 major tools (XLSTransfer, QuickSearch, etc.)
│   ├── SECONDARY PYTHON SCRIPTS/  # 74 utility scripts
│   └── datausedfortesting/    # Test data
│
├── archive/                   # ARCHIVED CODE
│   └── gradio_version/        # Old Gradio-based version
│
├── Roadmap.md                 # Development roadmap
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+**
- **Node.js 18+** (for SvelteKit frontend)
- **PostgreSQL 15+** (for production) or use SQLite for development

### Installation

1. **Clone the repository**
   ```bash
   git clone git@github.com:NeilVibe/LocalizationTools.git
   cd LocalizationTools
   ```

2. **Backend Setup**
   ```bash
   # Create virtual environment
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate

   # Install Python dependencies
   pip install -r requirements.txt

   # Set up database (SQLite for development)
   python3 scripts/setup_database.py --db sqlite
   ```

3. **Frontend Setup**
   ```bash
   # Install frontend dependencies
   cd locaNext
   npm install
   cd ..

   # Install admin dashboard dependencies
   cd adminDashboard
   npm install
   cd ..
   ```

### Running the Application

**Terminal 1: Start Backend Server**
```bash
source venv/bin/activate
python3 server/main.py
# Server runs on http://localhost:8888
```

**Terminal 2: Start Frontend**
```bash
cd locaNext
npm run dev
# Frontend runs on http://localhost:5173
```

**Terminal 3: Start Admin Dashboard** (Optional)
```bash
cd adminDashboard
npm run dev
# Admin dashboard runs on http://localhost:5173
```

### Access the Platform

- **Main Application**: http://localhost:5173
- **Admin Dashboard**: http://localhost:5173 (separate instance)
- **API Documentation**: http://localhost:8888/docs
- **Backend Health**: http://localhost:8888/health

### Default Admin Credentials

```
Username: admin
Password: admin123
```

## ⚠️ 🔐 CRITICAL SECURITY WARNING 🔐 ⚠️

**THIS IS A PUBLIC REPOSITORY WITH DEFAULT CREDENTIALS!**

### FOR LOCAL DEVELOPMENT ONLY:
- The default credentials (`admin/admin123`) are **ONLY** for local testing
- These credentials are **PUBLICLY KNOWN** because this is a public repository
- **NEVER** use these credentials in production or on internet-accessible servers

### BEFORE DEPLOYING TO PRODUCTION:
1. **IMMEDIATELY** change the default admin password:
   ```bash
   # After first login, go to User Settings → Change Password
   # Or use SQL to update:
   UPDATE users SET password_hash = '<new_bcrypt_hash>' WHERE username = 'admin';
   ```

2. **SET ENVIRONMENT VARIABLES** for all secrets:
   ```bash
   export SECRET_KEY="<generate-strong-random-key>"
   export POSTGRES_PASSWORD="<strong-database-password>"
   export API_KEY="<generate-strong-api-key>"
   ```

3. **DISABLE** the default admin user and create proper user accounts

4. **ENABLE** proper authentication and change all default passwords

### Generate Secure Secrets:
```bash
# Generate strong SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate strong API_KEY
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

**IF YOU DEPLOY WITH DEFAULT CREDENTIALS, YOUR SYSTEM WILL BE COMPROMISED!**

---

## 📊 Admin Dashboard Features

The admin dashboard provides comprehensive analytics and management tools:

### 📈 Statistics Page
- Real-time metrics (active users, operations, success rate)
- Interactive charts (operations over time, success rates, tool usage)
- Period filters (last 30 days, 90 days, 1 year)
- Tool performance details with usage bars

### 🏆 Rankings Page
- Top 3 podium display with medals
- User rankings (by operations and time spent)
- App rankings (most used tools)
- Function rankings (most called functions)
- Period filters (daily, weekly, monthly, all-time)

### 👥 Users Page
- User management and activity tracking
- User details and statistics
- Active sessions monitoring

### 📝 Logs Page
- Real-time operation logs
- Error tracking and debugging
- Filterable by user, tool, status

---

## 🔧 Available Tools

### 1. XLSTransfer ✅ (Fully Operational)

AI-powered translation transfer between Excel files using semantic similarity matching.

**Features:**
- Dictionary creation from bilingual Excel files
- AI-powered semantic matching using Korean BERT
- Excel-to-Excel translation transfer
- Support for multiple sheets
- Real-time progress tracking
- Full frontend UI in SvelteKit

**API Endpoints:**
- `POST /api/v2/xlstransfer/test/create-dictionary`
- `POST /api/v2/xlstransfer/test/load-dictionary`
- `POST /api/v2/xlstransfer/test/translate-excel`
- `POST /api/v2/xlstransfer/test/translate-file`
- `GET /api/v2/xlstransfer/health`

### 2. QuickSearch ✅ (Fully Operational)

Dictionary-based translation search tool for game localization projects.

**Features:**
- Create dictionaries from XML/TXT/TSV files
- Multi-game support (BDO, BDM, BDC, CD)
- Multi-language support (15 languages: DE, IT, PL, EN, ES, SP, FR, ID, JP, PT, RU, TR, TH, TW, CH)
- One-line and multi-line search modes
- Contains/Exact match options
- Reference dictionary comparison
- StringID fast lookup
- Full frontend UI in SvelteKit

**API Endpoints:**
- `GET /api/v2/quicksearch/health`
- `POST /api/v2/quicksearch/create-dictionary`
- `POST /api/v2/quicksearch/load-dictionary`
- `POST /api/v2/quicksearch/search`
- `POST /api/v2/quicksearch/search-multiline`
- `POST /api/v2/quicksearch/set-reference`
- `POST /api/v2/quicksearch/toggle-reference`
- `GET /api/v2/quicksearch/list-dictionaries`

### 3. More Tools Coming Soon...

Additional tools from `RessourcesForCodingTheProject/` will be added to the platform:
- Korean Similarity Checker
- TFM Full/Lite
- And many more...

---

## 🧪 Testing

### Run All Tests
```bash
pytest tests/ -v
```

### Run Specific Test Suite
```bash
# Dashboard API tests (20 tests)
pytest tests/test_dashboard_api.py -v

# Authentication tests
pytest tests/test_async_auth.py -v

# Infrastructure tests
pytest tests/test_async_infrastructure.py -v
```

### Test Coverage
```bash
pytest tests/ --cov=server --cov-report=html
```

### Manual Testing Guide

See `docs/TESTING_GUIDE.md` for comprehensive manual testing instructions.

---

## 📡 API Endpoints

### Statistics API (10 endpoints)

```bash
GET /api/v2/admin/stats/overview
GET /api/v2/admin/stats/daily?days=30
GET /api/v2/admin/stats/weekly?weeks=12
GET /api/v2/admin/stats/monthly?months=6
GET /api/v2/admin/stats/tools/popularity?days=30
GET /api/v2/admin/stats/tools/{tool_name}/functions?days=30
GET /api/v2/admin/stats/performance/fastest?limit=10
GET /api/v2/admin/stats/performance/slowest?limit=10
GET /api/v2/admin/stats/errors/rate?days=30
GET /api/v2/admin/stats/errors/top?limit=10
```

### Rankings API (6 endpoints)

```bash
GET /api/v2/admin/rankings/users?period=monthly&limit=20
GET /api/v2/admin/rankings/users/by-time?period=monthly
GET /api/v2/admin/rankings/apps?period=monthly
GET /api/v2/admin/rankings/functions?period=monthly&limit=20
GET /api/v2/admin/rankings/functions/by-time?period=monthly
GET /api/v2/admin/rankings/top?period=monthly
```

### Authentication & User Management

```bash
POST /api/v2/auth/register
POST /api/v2/auth/login
GET /api/v2/auth/me
GET /api/v2/users
```

### Progress Tracking

```bash
GET /api/progress/operations
POST /api/progress/operations/{operation_id}/clear
WebSocket: ws://localhost:8888/ws/socket.io
```

**Interactive API Documentation:** http://localhost:8888/docs

---

## 📊 Database Schema

### Main Tables

- **users** - User accounts and profiles
- **sessions** - Active user sessions (JWT tokens)
- **active_operations** - Real-time operation tracking with progress
- **log_entries** - Historical operation logs
- **error_logs** - Error tracking and debugging

### Key Fields in active_operations

- `operation_id` - Unique operation identifier
- `user_id` - User who initiated the operation
- `tool_name` - Which tool was used (e.g., "XLSTransfer")
- `function_name` - Which function was called
- `status` - pending, running, completed, failed
- `progress_percentage` - 0-100% completion
- `current_step` - Detailed progress message
- `started_at` - Operation start timestamp
- `completed_at` - Operation end timestamp
- `file_info` - JSON metadata about processed files

---

## 🔐 Security

- **Password Hashing**: bcrypt with salt
- **Session Management**: JWT tokens with expiration
- **CORS**: Configured for specific origins
- **SQL Injection Protection**: SQLAlchemy ORM with parameterized queries
- **File Uploads**: Validated file types and size limits
- **API Rate Limiting**: Configurable per endpoint
- **Environment Variables**: Sensitive data in .env (gitignored)

---

## 🚀 Deployment

### Development

```bash
# Backend
python3 server/main.py

# Frontend
cd locaNext && npm run dev
```

### Production

```bash
# Backend with production settings
uvicorn server.main:app --host 0.0.0.0 --port 8888 --workers 4

# Frontend build
cd locaNext
npm run build
npm run preview
```

### Environment Variables

Create `.env` file in project root:

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost/locanext

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS
ALLOWED_ORIGINS=http://localhost:5173,https://yourdomain.com
```

---

## 📈 Current Status

**Version:** 2512090343 (Semantic: 1.3.0)
**Last Updated:** 2025-12-08
**Status:** Production Ready - Auto-Update Enabled

### ✅ Completed Features

- ✅ FastAPI backend with 23 tool endpoints + 16 admin endpoints
- ✅ SvelteKit frontend with modern UI
- ✅ Admin dashboard with charts and rankings
- ✅ Real-time WebSocket progress tracking
- ✅ XLSTransfer tool (App #1 - fully operational with frontend UI)
- ✅ QuickSearch tool (App #2 - fully operational with frontend UI)
- ✅ User authentication and sessions
- ✅ Comprehensive test suite (95% passing)
- ✅ Database schema with SQLAlchemy
- ✅ API documentation with Swagger
- ✅ BaseToolAPI pattern for rapid app development

### 🚧 In Progress

- ⏳ App #3 selection (from RessourcesForCodingTheProject)
- ⏳ Authentication for admin dashboard
- ⏳ Export functionality (CSV/PDF/Excel)
- ⏳ Production deployment configuration

---

## 📝 Documentation

- **[Roadmap.md](Roadmap.md)** - Detailed development roadmap and progress
- **[docs/TESTING_GUIDE.md](docs/TESTING_GUIDE.md)** - Complete testing instructions
- **[docs/STATS_DASHBOARD_SPEC.md](docs/STATS_DASHBOARD_SPEC.md)** - Dashboard specification
- **[docs/ADMIN_SETUP.md](docs/ADMIN_SETUP.md)** - Admin setup guide
- **[docs/PERFORMANCE.md](docs/PERFORMANCE.md)** - Performance benchmarks

---

## 🧹 Clean Code Policy

We maintain a strict clean code policy:

✅ **DO:**
- Write clear, documented code
- Add tests for new features
- Use type hints (Python) and TypeScript (frontend)
- Follow existing code style

❌ **DON'T:**
- Leave `temp.py`, `test123.py` in working directories
- Commit commented-out code
- Skip documentation for complex logic

**Archive Policy:** Old/experimental code goes in `archive/` folder, not in working directories.

---

## 🤝 Contributing

1. Create a feature branch (`git checkout -b feature/amazing-feature`)
2. Write tests for new functionality
3. Run linters and tests (`pytest tests/`)
4. Commit changes (`git commit -m 'Add amazing feature'`)
5. Push to branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

---

## 📄 License

**Internal Project - Company Use Only**

This is a proprietary internal tool. All rights reserved.

---

## 👤 Author

**Neil** - Lead Developer
Localization Tools Team

---

## 🔗 Quick Links

- **API Docs**: http://localhost:8888/docs
- **Admin Dashboard**: http://localhost:5173
- **GitHub Issues**: [Report bugs or request features](https://github.com/NeilVibe/LocalizationTools/issues)

---

## ⚡ Performance

- **Backend Response Time**: <200ms average
- **WebSocket Latency**: <100ms
- **Database Queries**: <50ms average
- **Frontend Load Time**: <2s initial load
- **Chart Rendering**: <500ms

---

## 🎉 Acknowledgments

Built with modern technologies to provide a fast, reliable, and user-friendly localization platform.

**Tech Stack:**
- FastAPI - High-performance Python web framework
- SvelteKit - Next-generation frontend framework
- Socket.IO - Real-time bidirectional communication
- Chart.js - Beautiful interactive charts
- SQLAlchemy - Python SQL toolkit and ORM
- Sentence Transformers - State-of-the-art embeddings

---

**Last Updated:** 2025-11-11
**Built with ❤️ for efficient localization workflows**
