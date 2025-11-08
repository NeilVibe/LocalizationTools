# LocalizationTools - Development Roadmap

## Project Phases Overview

```
Phase 1: Foundation & MVP (Week 1-2)
├── Set up project structure
├── Build basic Gradio interface for XLSTransfer
├── Implement central logging server
└── Create basic admin dashboard

Phase 2: Multi-Tool Integration (Week 3-4)
├── Add 3-5 additional tools
├── Enhance UI/UX
├── Improve logging and analytics
└── Add user settings

Phase 3: Polish & Features (Week 5-6)
├── User authentication
├── Auto-update system
├── Advanced analytics
└── Performance optimization

Phase 4: Production Ready (Week 7-8)
├── Full tool suite
├── Comprehensive testing
├── Documentation
└── Deployment
```

---

## Phase 1: Foundation & MVP (Week 1-2)

### Milestone: Single Tool Working with Analytics

### 1.1 Project Setup
**Tasks**:
- [x] Initialize Git repository
- [ ] Create project folder structure
- [ ] Set up virtual environment
- [ ] Install core dependencies (gradio, fastapi, pandas, etc.)
- [ ] Download and cache Korean BERT model locally

**File Structure**:
```
LocalizationTools/
├── client/                 # Gradio app (user-side)
│   ├── app.py             # Main Gradio app
│   ├── tools/             # Individual tool modules
│   │   ├── xls_transfer.py
│   │   └── __init__.py
│   ├── utils/             # Shared utilities
│   │   ├── logger.py      # Logging to server
│   │   └── config.py
│   └── models/            # ML models directory
│       └── KRTransformer/
├── server/                # Central server
│   ├── main.py           # FastAPI app
│   ├── database.py       # DB models
│   ├── api/              # API endpoints
│   │   └── logs.py
│   └── admin/            # Admin dashboard
│       └── dashboard.py
├── requirements.txt
├── build_client.py       # PyInstaller script
└── README.md
```

**Estimated Time**: 1 day

---

### 1.2 Build XLSTransfer Gradio Interface

**Tasks**:
- [ ] Convert XLSTransfer0225.py to Gradio components
- [ ] Create tabbed interface for different functions:
  - Create Dictionary
  - Load Dictionary
  - Transfer to Excel
  - Transfer to Close
  - Check Newlines
  - Combine Excel Files
  - Newline Auto Adapt
  - Simple Excel Transfer
- [ ] Implement file upload/download
- [ ] Add progress indicators
- [ ] Handle errors gracefully with user-friendly messages

**Key Components**:
```python
import gradio as gr

with gr.Blocks() as app:
    with gr.Tab("Create Dictionary"):
        # File upload
        # Column selection
        # Process button
        # Progress bar

    with gr.Tab("Transfer to Excel"):
        # File upload
        # Settings
        # Process button

    # ... other tabs
```

**Estimated Time**: 3 days

---

### 1.3 Implement Local Processing & Logging

**Tasks**:
- [ ] Refactor XLSTransfer functions to work with Gradio callbacks
- [ ] Load Korean BERT model on app startup
- [ ] Implement progress callbacks
- [ ] Create logging utility that sends to server
- [ ] Add error handling and user feedback

**Logging Format**:
```python
{
    "user_id": "anonymous_123",  # or authenticated user
    "session_id": "uuid-here",
    "tool": "XLSTransfer",
    "function": "create_dictionary",
    "timestamp_start": "2025-01-08T10:30:00",
    "timestamp_end": "2025-01-08T10:30:45",
    "duration_seconds": 45,
    "file_size_mb": 2.5,
    "rows_processed": 5000,
    "status": "success",  # or "error"
    "error_message": null
}
```

**Estimated Time**: 2 days

---

### 1.4 Set Up Database

**Tasks**:
- [x] Design PostgreSQL schema (see `database_schema.sql`)
- [ ] Install PostgreSQL locally for development
- [ ] Create SQLite version for local testing
- [ ] Run schema creation scripts
- [ ] Create database connection utilities
- [ ] Test database connections
- [ ] Set up SQLAlchemy ORM models

**Database Setup**:
```bash
# For local testing (SQLite)
python scripts/setup_database.py --db sqlite

# For production (PostgreSQL)
python scripts/setup_database.py --db postgresql
```

**Schema includes**:
- 13+ tables covering all aspects (users, logs, stats, errors, etc.)
- Pre-computed views for dashboard performance
- Automated aggregation functions
- Optimized indexes for common queries

See `database_schema.sql` for complete schema.

**Estimated Time**: 2 days

---

### 1.5 Build Central Logging Server

**Tasks**:
- [ ] Set up FastAPI project structure
- [ ] Implement database models with SQLAlchemy
- [ ] Create authentication endpoints (login, register)
- [ ] Implement POST /api/logs endpoint
- [ ] Add user session management
- [ ] Create API for querying logs
- [ ] Add API key authentication for client apps
- [ ] Test all endpoints

**API Endpoints**:
- `POST /api/auth/login` - User authentication
- `POST /api/auth/register` - User registration (admin only)
- `POST /api/logs` - Receive log entry from client
- `POST /api/sessions/start` - Start new session
- `POST /api/sessions/end` - End session
- `GET /api/stats/overview` - Get aggregated statistics
- `GET /api/stats/tools` - Tool usage statistics
- `GET /api/stats/users` - User activity data
- `GET /api/version/latest` - Check for updates
- `GET /api/announcements` - Get active announcements

**Authentication**:
- bcrypt password hashing
- JWT tokens for session management
- API keys for client-server communication

**Estimated Time**: 3 days

---

### 1.6 Create Comprehensive Admin Dashboard

**CRITICAL**: Dashboard must be CLEAN, DETAILED, and BEAUTIFUL to impress management.

**Tasks**:
- [ ] Build Gradio dashboard interface with professional design
- [ ] Implement real-time metrics (auto-refresh every 30s)
- [ ] Create comprehensive charts with Plotly (interactive)
- [ ] Add date range filtering (daily/weekly/monthly/custom)
- [ ] Implement all analytics views (see STATS_DASHBOARD_SPEC.md)

**Dashboard Sections** (See STATS_DASHBOARD_SPEC.md for full details):

1. **Overview / Home Page**:
   - Real-time active users count (🟢 live)
   - Today's operations total
   - Overall success rate percentage
   - Average processing duration

2. **Usage Analytics**:
   - **Daily Usage**: Line chart (last 30 days)
   - **Weekly Aggregation**: Table with week-by-week breakdown
   - **Monthly Aggregation**: Bar chart with monthly comparison
   - Shows: operations count, unique users, success rate, avg duration

3. **Tool Popularity**:
   - **Most Used Tools**: Horizontal bar chart with percentages
   - **Function-Level Breakdown**: Expandable tables per tool
   - Shows: usage count, % of total, avg duration, success rate

4. **Performance Metrics**:
   - **Fastest Functions**: Top 10 table (sorted by speed)
   - **Slowest Functions**: Bottom 10 table
   - **Performance Over Time**: Line chart showing duration trends
   - Min/max/average duration for each function

5. **Connection Analytics**:
   - **Daily Connections**: Bar chart of daily active users
   - **Weekly Connections**: Table with retention rates
   - **Monthly Active Users (MAU)**: Line chart with growth trend
   - Total sessions, operations per user

6. **User Leaderboard**:
   - Top 20 most active users (current month)
   - Shows: operations count, time spent, active days, top tool
   - Sortable and filterable

7. **Error Tracking**:
   - **Error Rate Over Time**: Line chart (percentage)
   - **Most Common Errors**: Table with error types, frequencies
   - Affected users count, most common tool per error

8. **Export Reports**:
   - PDF: Executive summary with key charts
   - Excel: Detailed data tables
   - PowerPoint: Management presentation
   - CSV: Raw data for custom analysis
   - Report types: Daily, Weekly, Monthly, Custom Range, User-Specific

**Visual Design**:
- **Color coded**: Green (success), Red (error), Blue (info)
- **Interactive charts**: Hover tooltips, click to drill down
- **Responsive layout**: Works on desktop, tablet, mobile
- **Auto-refresh**: Real-time metrics update automatically
- **Clean UI**: Professional, easy to read, impressive

**Database Queries**:
- All optimized queries documented in STATS_DASHBOARD_SPEC.md
- Use pre-computed views for fast loading
- Implement caching for expensive queries

**Estimated Time**: 5 days (comprehensive dashboard is critical!)

---

### 1.7 Testing & MVP Release

**Tasks**:
- [ ] Test XLSTransfer all functions in Gradio
- [ ] Verify logging works correctly
- [ ] Test admin dashboard
- [ ] Create test data
- [ ] Fix bugs
- [ ] Document basic usage

**Deliverable**:
- Working Gradio app with XLSTransfer
- Central server receiving logs
- Basic admin dashboard showing statistics

**Estimated Time**: 2 days

**Total Phase 1 Time**: 18 days (3.5 weeks)

---

## Phase 2: Multi-Tool Integration (Week 3-4)

### Milestone: 5+ Tools Available with Enhanced UI

### 2.1 Select & Prioritize Additional Tools

**Tasks**:
- [ ] Review all existing scripts in MAIN/SECONDARY folders
- [ ] Select 4-5 most impactful tools based on:
  - Frequency of use
  - Processing complexity
  - User requests
  - Business value

**Recommended Tools to Add**:
1. **TFMFULL0116.py** - TFM full processing
2. **QS0305.py** - Quick Search functionality
3. **KRSIMILAR0124.py** - Korean similarity checker
4. **stackKR.py** - Stack Korean files
5. **removeduplicate.py** - Remove duplicates

**Estimated Time**: 1 day

---

### 2.2 Convert Tools to Gradio Modules

**Tasks**:
For each tool:
- [ ] Analyze script functionality
- [ ] Refactor into modular functions
- [ ] Create Gradio interface
- [ ] Add to main app as new tab
- [ ] Implement logging for each function
- [ ] Add progress tracking
- [ ] Test thoroughly

**Template for Each Tool**:
```python
# tools/tool_name.py

def process_function(input_file, settings):
    # Original logic here
    # Add progress callbacks
    # Return results
    pass

def create_gradio_interface():
    with gr.Tab("Tool Name"):
        # UI components
        # Buttons
        # File uploads
        pass
    return interface
```

**Estimated Time**: 2 days per tool = 10 days

---

### 2.3 Enhance UI/UX

**Tasks**:
- [ ] Add app branding (logo, colors, theme)
- [ ] Implement dark mode toggle
- [ ] Add tooltips and help text
- [ ] Create better progress indicators
- [ ] Add sound notifications on completion
- [ ] Improve error messages
- [ ] Add keyboard shortcuts

**Estimated Time**: 2 days

---

### 2.4 Improve Analytics

**Tasks**:
- [ ] Track individual function usage within tools
- [ ] Add performance metrics (CPU, memory)
- [ ] Track error rates
- [ ] Add user feedback mechanism
- [ ] Enhance dashboard with new metrics

**New Metrics**:
- Function-level usage
- Average file sizes processed
- Success/error rates
- Performance trends over time
- User retention rates

**Estimated Time**: 2 days

**Total Phase 2 Time**: 15 days (3 weeks)

---

## Phase 3: Polish & Advanced Features (Week 5-6)

### Milestone: Production-Quality Application

### 3.1 User Authentication System

**Tasks**:
- [ ] Add login screen to Gradio app
- [ ] Implement user registration
- [ ] Create authentication API endpoints
- [ ] Store user credentials securely (hashed)
- [ ] Add "Remember Me" functionality
- [ ] Allow anonymous mode (optional login)

**Benefits**:
- Accurate user tracking
- Personalized settings
- User-specific analytics

**Estimated Time**: 3 days

---

### 3.2 Auto-Update System

**Tasks**:
- [ ] Implement version checking
- [ ] Create update server endpoint
- [ ] Add update notification in app
- [ ] Build auto-download mechanism
- [ ] Create update installer/patcher
- [ ] Test update process

**Update Flow**:
1. App checks version on startup
2. If new version available, show notification
3. User clicks "Update"
4. Download only changed files
5. Apply update and restart

**Estimated Time**: 4 days

---

### 3.3 Advanced Analytics Dashboard

**Tasks**:
- [ ] Add advanced charts (heatmaps, trends)
- [ ] Create exportable reports (PDF, Excel)
- [ ] Add custom date range filtering
- [ ] Implement user comparison views
- [ ] Add tool efficiency metrics
- [ ] Create monthly summary reports

**Dashboard Features**:
- Daily/Weekly/Monthly views
- Tool usage heatmap by hour/day
- User leaderboard (most active)
- Performance benchmarks
- Export to PowerPoint for presentations

**Estimated Time**: 3 days

---

### 3.4 Settings & Preferences

**Tasks**:
- [ ] Add user settings panel
- [ ] Allow theme customization
- [ ] Add default file locations
- [ ] Create tool-specific presets
- [ ] Add notification preferences
- [ ] Implement settings sync (server-side)

**Estimated Time**: 2 days

**Total Phase 3 Time**: 12 days (2.5 weeks)

---

## Phase 4: Production Ready (Week 7-8)

### Milestone: Full Deployment

### 4.1 Complete Tool Suite

**Tasks**:
- [ ] Add remaining tools (aim for 10+ total)
- [ ] Ensure all tools are fully integrated
- [ ] Standardize UI across all tools
- [ ] Complete all logging implementations

**Estimated Time**: 5 days

---

### 4.2 Packaging & Distribution

**Tasks**:
- [ ] Configure PyInstaller for optimal build
- [ ] Bundle ML models efficiently
- [ ] Minimize executable size where possible
- [ ] Create installer (NSIS or similar)
- [ ] Set up auto-update infrastructure
- [ ] Create uninstaller

**Build Configuration**:
```python
# build_client.py
import PyInstaller.__main__

PyInstaller.__main__.run([
    'client/app.py',
    '--name=LocalizationTools',
    '--onefile',
    '--windowed',
    '--add-data=models:models',
    '--icon=icon.ico',
    '--hidden-import=gradio',
    '--hidden-import=sentence_transformers',
    # ... other imports
])
```

**Estimated Time**: 3 days

---

### 4.3 Testing & QA

**Tasks**:
- [ ] Unit tests for all tool functions
- [ ] Integration tests for logging
- [ ] UI/UX testing
- [ ] Performance testing (large files)
- [ ] Cross-platform testing (if applicable)
- [ ] Beta testing with real users
- [ ] Bug fixing

**Test Cases**:
- All tool functions work correctly
- Logging captures all events
- Dashboard displays accurate data
- Updates work smoothly
- Error handling is robust
- Performance is acceptable

**Estimated Time**: 4 days

---

### 4.4 Documentation

**Tasks**:
- [ ] User manual (how to use each tool)
- [ ] Video tutorials (optional)
- [ ] Admin guide (dashboard usage)
- [ ] Developer docs (for maintenance)
- [ ] API documentation
- [ ] Troubleshooting guide

**Estimated Time**: 2 days

---

### 4.5 Deployment

**Tasks**:
- [ ] Deploy central server to production
- [ ] Set up SSL certificates
- [ ] Configure domain (your.company.com)
- [ ] Set up database backups
- [ ] Create monitoring/alerting
- [ ] Release client application
- [ ] Announce to users

**Infrastructure**:
- Server: AWS/DigitalOcean/Azure
- Database: PostgreSQL (production)
- Domain: SSL-secured
- Backup: Daily automated backups

**Estimated Time**: 2 days

**Total Phase 4 Time**: 16 days (3 weeks)

---

## Total Timeline: 9-10 Weeks

```
Week 1-3:  Phase 1 - MVP with XLSTransfer + Database setup
Week 4-6:  Phase 2 - Multi-tool integration
Week 7-8:  Phase 3 - Polish & advanced features
Week 9-10: Phase 4 - Production ready
```

---

## Technology Stack Summary

### Client Application
| Technology | Purpose | Version |
|------------|---------|---------|
| Python | Runtime | 3.10+ |
| Gradio | UI Framework | 4.x |
| PyInstaller | Executable builder | 6.x |
| sentence-transformers | ML models | Latest |
| FAISS | Vector search | Latest |
| pandas | Data processing | Latest |
| openpyxl | Excel manipulation | Latest |
| requests | HTTP client | Latest |

### Server
| Technology | Purpose | Version |
|------------|---------|---------|
| Python | Runtime | 3.10+ |
| FastAPI | Web framework | 0.100+ |
| SQLAlchemy | ORM | 2.x |
| PostgreSQL | Database (prod) | 15+ |
| SQLite | Database (dev) | 3.x |
| uvicorn | ASGI server | Latest |
| Gradio | Admin dashboard | 4.x |

---

## Risk Management

### Potential Challenges & Solutions

**Challenge 1**: Large executable size (1GB+)
- **Solution**: Optimize PyInstaller configuration, use lazy model loading

**Challenge 2**: Slow first-time startup (model loading)
- **Solution**: Add splash screen, cache models, show progress

**Challenge 3**: Users behind firewall (logging fails)
- **Solution**: Queue logs locally, retry with exponential backoff, offline mode

**Challenge 4**: Server downtime affects client
- **Solution**: Client works fully offline, logs queue until server available

**Challenge 5**: Update distribution bandwidth
- **Solution**: Delta updates only, CDN for downloads

---

## Success Criteria

The project is successful when:

- [ ] 80%+ of target users have installed the app
- [ ] Daily active usage of at least 50%
- [ ] All tools report usage correctly
- [ ] Admin dashboard shows accurate real-time data
- [ ] Updates deploy smoothly without user friction
- [ ] Management sees clear value in usage reports
- [ ] Users prefer unified app over individual tools

---

## Development Guidelines

### 🧹 Clean Code Policy (CRITICAL!)

**STRICT RULE**: Keep the project CLEAN at all times. This is NON-NEGOTIABLE.

**Why Cleanliness Matters**:
- Professional presentation to management
- Easy maintenance and debugging
- Quick onboarding for new developers
- Scalable codebase as project grows
- **Demonstrates attention to detail**

**ARCHIVE Folder Usage**:
- Create `ARCHIVE/` folder for ALL temporary/experimental code
- After solving issues with test scripts → Move to `ARCHIVE/test_scripts/`
- Old code versions during refactoring → Move to `ARCHIVE/old_code/`
- Experiments that don't work out → Move to `ARCHIVE/experiments/`
- Debug scripts once resolved → Move to `ARCHIVE/test_scripts/`

**Never leave clutter**:
- No orphaned test files in main directories
- No `temp.py`, `test123.py`, `debug_something.py` in working folders
- Every file has a purpose or gets archived

**Resources**:
- `RessourcesForCodingTheProject/` contains all original scripts and test data
- Reference this for validation and testing
- Don't modify - use as read-only reference

**Important Documentation**:
- `Claude.md` - Complete project documentation with clean code policy
- `STATS_DASHBOARD_SPEC.md` - Comprehensive analytics dashboard specification
- `database_schema.sql` - Complete PostgreSQL schema with all tables

### Update System Details

**Version Management**:
- All versions tracked in `app_versions` table
- Mark new versions as `is_latest=TRUE`
- Optional updates: `is_mandatory=FALSE`
- Force updates: `is_mandatory=TRUE` (critical fixes)

**Update Flow**:
1. User opens app
2. App calls `GET /api/version/latest`
3. Server responds with version info
4. App shows update notification
5. User clicks "Update Now"
6. Auto-download and install
7. Logged in `update_history` table

**Push Announcements**:
- Use `announcements` table to notify users
- Show banners in app for maintenance, news, tips
- Target specific users or all users
- Set display timeframes

## Next Immediate Steps

1. ✅ Design PostgreSQL schema with all tables
2. ✅ Update documentation (Claude.md, Roadmap.md)
3. ✅ Define clean code policy
4. **Set up project structure with ARCHIVE folder** (Day 1)
5. **Install dependencies and cache models** (Day 1)
6. **Build basic Gradio interface** (Day 2-3)
7. **Set up PostgreSQL/SQLite database** (Day 3-4)
8. **Implement XLSTransfer Create Dictionary function** (Day 4-5)
9. **Set up central server with authentication** (Day 5-6)
10. **Connect client logging to server** (Day 7)
11. **Continue with remaining XLSTransfer functions** (Day 8-12)

Let's start building!
