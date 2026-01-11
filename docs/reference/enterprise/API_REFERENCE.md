# API Reference

**Purpose:** API endpoints for integrations, dashboards, and external systems

---

## Base URL

```
http://SERVER_IP:8888/api
```

---

## Authentication

### Login

```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "john.doe",
  "password": "password123"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "id": 1,
    "username": "john.doe",
    "email": "john.doe@company.com",
    "role": "translator"
  }
}
```

### Using Token

All authenticated endpoints require:
```http
Authorization: Bearer <access_token>
```

---

## Health & Status

### Health Check

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "database_type": "postgresql",
  "local_mode": false,
  "version": "25.1216.1626"
}
```

### Connection Status

```http
GET /api/status
```

**Response:**
```json
{
  "api_server": "connected",
  "database": "connected",
  "database_type": "postgresql",
  "local_mode": false,
  "websocket": "connected"
}
```

---

## Users (Admin Only)

### List Users

```http
GET /api/users
Authorization: Bearer <admin_token>
```

**Response:**
```json
{
  "users": [
    {
      "id": 1,
      "username": "admin",
      "email": "admin@company.com",
      "role": "admin",
      "is_active": true,
      "created_at": "2025-12-16T10:00:00Z"
    }
  ],
  "total": 1
}
```

### Create User

```http
POST /api/users
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "username": "john.doe",
  "email": "john.doe@company.com",
  "password": "TempPass123!",
  "role": "translator"
}
```

### Get User

```http
GET /api/users/{username}
Authorization: Bearer <admin_token>
```

### Update User

```http
PATCH /api/users/{username}
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "role": "reviewer",
  "is_active": true
}
```

### Delete User

```http
DELETE /api/users/{username}
Authorization: Bearer <admin_token>
```

### Reset Password

```http
POST /api/users/{username}/reset-password
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "new_password": "NewTempPass123!"
}
```

---

## Server Configuration

### Get Config

```http
GET /api/server-config
```

**Response:**
```json
{
  "postgres_host": "10.10.30.50",
  "postgres_port": 5432,
  "postgres_user": "locanext_app",
  "postgres_db": "locanext",
  "postgres_password_set": true,
  "config_file_exists": true,
  "database_mode": "auto",
  "active_database_type": "postgresql"
}
```

### Save Config

```http
POST /api/server-config
Content-Type: application/json

{
  "postgres_host": "10.10.30.50",
  "postgres_port": 5432,
  "postgres_user": "locanext_app",
  "postgres_password": "password",
  "postgres_db": "locanext"
}
```

### Test Connection

```http
POST /api/server-config/test
Content-Type: application/json

{
  "postgres_host": "10.10.30.50",
  "postgres_port": 5432,
  "postgres_user": "locanext_app",
  "postgres_password": "password",
  "postgres_db": "locanext"
}
```

**Response:**
```json
{
  "reachable": true,
  "auth_ok": true,
  "message": "Connection successful"
}
```

### Go Online

```http
POST /api/go-online
```

---

## Projects

### List Projects

```http
GET /api/ldm/projects
Authorization: Bearer <token>
```

**Response:**
```json
{
  "projects": [
    {
      "id": 1,
      "name": "Game Localization",
      "description": "Main game strings",
      "created_at": "2025-12-16T10:00:00Z",
      "file_count": 5
    }
  ]
}
```

### Create Project

```http
POST /api/ldm/projects
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "New Project",
  "description": "Project description"
}
```

### Get Project

```http
GET /api/ldm/projects/{id}
Authorization: Bearer <token>
```

### Delete Project

```http
DELETE /api/ldm/projects/{id}
Authorization: Bearer <token>
```

---

## Files

### List Files in Project

```http
GET /api/ldm/projects/{project_id}/files
Authorization: Bearer <token>
```

### Upload File

```http
POST /api/ldm/files/upload
Authorization: Bearer <token>
Content-Type: multipart/form-data

file: <binary>
project_id: 1
```

**Response:**
```json
{
  "id": 1,
  "name": "strings.xlsx",
  "project_id": 1,
  "row_count": 150,
  "created_at": "2025-12-16T10:00:00Z"
}
```

### Get File Info

```http
GET /api/ldm/files/{id}
Authorization: Bearer <token>
```

### Get File Rows

```http
GET /api/ldm/files/{id}/rows
Authorization: Bearer <token>
```

**Query Parameters:**
- `offset`: Start row (default 0)
- `limit`: Max rows (default 100)
- `search`: Search term
- `status`: Filter by status

### Export File

```http
GET /api/ldm/files/{id}/export?format=xlsx
Authorization: Bearer <token>
```

### Delete File

```http
DELETE /api/ldm/files/{id}
Authorization: Bearer <token>
```

---

## Rows

### Get Row

```http
GET /api/ldm/rows/{id}
Authorization: Bearer <token>
```

### Update Row

```http
PATCH /api/ldm/rows/{id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "target": "Translated text",
  "status": "reviewed"
}
```

### Batch Update Rows

```http
PATCH /api/ldm/rows/batch
Authorization: Bearer <token>
Content-Type: application/json

{
  "updates": [
    {"id": 1, "target": "Text 1", "status": "translated"},
    {"id": 2, "target": "Text 2", "status": "translated"}
  ]
}
```

---

## Translation Memory

### List TMs

```http
GET /api/ldm/tms
Authorization: Bearer <token>
```

### Create TM

```http
POST /api/ldm/tms
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Main TM",
  "source_lang": "en",
  "target_lang": "ko"
}
```

### Upload TM Entries

```http
POST /api/ldm/tms/{id}/entries
Authorization: Bearer <token>
Content-Type: multipart/form-data

file: <tmx or xlsx>
```

### Search TM

```http
POST /api/ldm/tms/{id}/search
Authorization: Bearer <token>
Content-Type: application/json

{
  "query": "Search text",
  "threshold": 0.7,
  "limit": 10
}
```

**Response:**
```json
{
  "matches": [
    {
      "source": "Original text",
      "target": "Translated text",
      "score": 0.95
    }
  ]
}
```

---

## Metrics (for Dashboard Integration)

### Get Metrics

```http
GET /api/metrics
Authorization: Bearer <admin_token>
```

**Response:**
```json
{
  "user_metrics": {
    "active_users": 15,
    "logins_today": 42,
    "total_users": 100
  },
  "translation_metrics": {
    "files_uploaded_today": 8,
    "total_rows": 150000,
    "rows_modified_today": 1250
  },
  "system_metrics": {
    "cpu_percent": 25.5,
    "memory_percent": 60.2,
    "db_connections": 15
  }
}
```

### Get User Activity

```http
GET /api/metrics/activity
Authorization: Bearer <admin_token>
```

**Query Parameters:**
- `start_date`: YYYY-MM-DD
- `end_date`: YYYY-MM-DD
- `user`: Filter by username

---

## WebSocket Events

### Connection

```javascript
const socket = io('http://SERVER_IP:8888', {
  auth: { token: 'access_token' }
});
```

### Events

| Event | Direction | Data |
|-------|-----------|------|
| `ldm_join_file` | Client → Server | `{file_id: 1}` |
| `file_joined` | Server → Client | `{file_id: 1, users: [...]}` |
| `ldm_lock_row` | Client → Server | `{file_id: 1, row_id: 5}` |
| `lock_granted` | Server → Client | `{row_id: 5, user: "john"}` |
| `lock_denied` | Server → Client | `{row_id: 5, holder: "jane"}` |
| `ldm_unlock_row` | Client → Server | `{file_id: 1, row_id: 5}` |
| `row_unlocked` | Server → Client | `{row_id: 5}` |
| `row_updated` | Server → Client | `{row_id: 5, data: {...}}` |

---

## Error Responses

### Standard Error Format

```json
{
  "error": "error_code",
  "message": "Human readable message",
  "details": {}
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `unauthorized` | 401 | Missing or invalid token |
| `forbidden` | 403 | Insufficient permissions |
| `not_found` | 404 | Resource not found |
| `validation_error` | 422 | Invalid request data |
| `internal_error` | 500 | Server error |

---

## Rate Limiting

Default limits:
- 100 requests per minute per user
- 1000 requests per minute per IP

Headers:
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1702732800
```

---

## Pagination

List endpoints support pagination:

```http
GET /api/ldm/files/1/rows?offset=100&limit=50
```

Response includes:
```json
{
  "data": [...],
  "total": 5000,
  "offset": 100,
  "limit": 50,
  "has_more": true
}
```

---

## Full API Documentation

Interactive API docs available at:
```
http://SERVER_IP:8888/docs
```

OpenAPI spec:
```
http://SERVER_IP:8888/openapi.json
```
