# 05 - User Management

**Purpose:** Creating users, managing permissions, password policies

---

## Overview

LocaNext user management:
- Users stored in central PostgreSQL
- Role-based access (admin, translator, reviewer)
- Password hashing with bcrypt
- JWT token authentication
- Session management

---

## User Roles

| Role | Permissions |
|------|-------------|
| **admin** | Full access: user management, all tools, settings |
| **translator** | Use all translation tools, edit own work |
| **reviewer** | Use tools, review others' work, read-only for some features |
| **viewer** | Read-only access, view projects and files |

---

## Creating Users

### Method 1: Admin Dashboard (Recommended)

1. Open Admin Dashboard: `http://10.10.30.50:5175` (or local)
2. Login as admin
3. Navigate to Users > Add User
4. Fill in:
   - Username
   - Email
   - Temporary password
   - Role
5. Click "Create"
6. Share credentials with user securely

### Method 2: API

```bash
# Login as admin first
TOKEN=$(curl -s -X POST http://10.10.30.50:8888/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "ADMIN_PASSWORD"}' \
  | jq -r '.access_token')

# Create user
curl -X POST http://10.10.30.50:8888/api/users \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "username": "john.doe",
    "email": "john.doe@company.com",
    "password": "TempPassword123!",
    "role": "translator"
  }'
```

### Method 3: CLI Script

```bash
cd ~/LocaNext
source venv/bin/activate

# Interactive
python3 scripts/create_user.py

# Or direct
python3 -c "
from server.auth.user_manager import UserManager
um = UserManager()
um.create_user(
    username='john.doe',
    email='john.doe@company.com',
    password='TempPassword123!',
    role='translator'
)
print('User created successfully')
"
```

### Method 4: Bulk Import

Create CSV file `users.csv`:
```csv
username,email,password,role
john.doe,john.doe@company.com,TempPass1!,translator
jane.smith,jane.smith@company.com,TempPass2!,translator
bob.admin,bob.admin@company.com,TempPass3!,admin
```

Import script:
```python
import csv
from server.auth.user_manager import UserManager

um = UserManager()

with open('users.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        um.create_user(
            username=row['username'],
            email=row['email'],
            password=row['password'],
            role=row['role']
        )
        print(f"Created: {row['username']}")
```

---

## Password Policies

### Default Policy

```python
# In server/auth/password_policy.py (create if needed)
PASSWORD_MIN_LENGTH = 8
PASSWORD_REQUIRE_UPPERCASE = True
PASSWORD_REQUIRE_LOWERCASE = True
PASSWORD_REQUIRE_DIGIT = True
PASSWORD_REQUIRE_SPECIAL = False  # Set True for stricter policy
PASSWORD_MAX_AGE_DAYS = 90  # Force change after 90 days, 0 = never
```

### Enforcing Password Policy

```python
import re

def validate_password(password: str) -> tuple[bool, str]:
    """Validate password against policy. Returns (valid, message)."""

    if len(password) < PASSWORD_MIN_LENGTH:
        return False, f"Password must be at least {PASSWORD_MIN_LENGTH} characters"

    if PASSWORD_REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"

    if PASSWORD_REQUIRE_LOWERCASE and not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"

    if PASSWORD_REQUIRE_DIGIT and not re.search(r'\d', password):
        return False, "Password must contain at least one digit"

    if PASSWORD_REQUIRE_SPECIAL and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"

    return True, "Password valid"
```

---

## User Password Change

### User Changes Own Password

Users can change their password in the app:

1. Click user icon (top right)
2. Select "Change Password"
3. Enter current password
4. Enter new password (twice)
5. Click "Change"

### Admin Resets User Password

```bash
# Via API
curl -X POST http://10.10.30.50:8888/api/users/john.doe/reset-password \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"new_password": "NewTempPass123!"}'
```

### Force Password Change on Next Login

```sql
-- In PostgreSQL
UPDATE users SET must_change_password = TRUE WHERE username = 'john.doe';
```

---

## User Workflow

### New User Onboarding

```
1. Admin creates user account
   └─ Username, email, temp password, role

2. Admin sends credentials to user (securely)
   └─ Email, Teams, in-person

3. User installs LocaNext
   └─ Downloads from Gitea, runs installer

4. User launches app, enters credentials
   └─ Temp password works

5. User prompted to change password (if policy requires)
   └─ Sets personal password

6. User accesses tools based on role
   └─ Ready to work
```

### Offboarding

```bash
# Disable user (keeps data, prevents login)
curl -X PATCH http://10.10.30.50:8888/api/users/john.doe \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"is_active": false}'

# Or delete user (removes user, keeps their work)
curl -X DELETE http://10.10.30.50:8888/api/users/john.doe \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

---

## Session Management

### Session Configuration

```python
# In server/config.py
JWT_EXPIRE_MINUTES = 1440  # 24 hours
REFRESH_TOKEN_EXPIRE_DAYS = 7
MAX_SESSIONS_PER_USER = 5  # Limit concurrent sessions
```

### View Active Sessions

```bash
curl http://10.10.30.50:8888/api/users/john.doe/sessions \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### Revoke All Sessions (Force Logout)

```bash
curl -X DELETE http://10.10.30.50:8888/api/users/john.doe/sessions \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

---

## Listing Users

### All Users

```bash
curl http://10.10.30.50:8888/api/users \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq
```

### Filter by Role

```bash
curl "http://10.10.30.50:8888/api/users?role=translator" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq
```

### User Details

```bash
curl http://10.10.30.50:8888/api/users/john.doe \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq
```

---

## Audit Logging

User actions are logged:

```sql
-- View recent logins
SELECT * FROM user_activity_log
WHERE action = 'login'
ORDER BY created_at DESC
LIMIT 20;

-- View user's activity
SELECT * FROM user_activity_log
WHERE user_id = (SELECT id FROM users WHERE username = 'john.doe')
ORDER BY created_at DESC;
```

---

## Local/Offline Mode Users

When app runs offline (SQLite):

- **LOCAL** user auto-created
- No authentication required
- Single-user mode
- All data stored locally

When user goes online:
- Must authenticate with real credentials
- Local data can be synced (future feature)

---

## Troubleshooting

### User Can't Login

1. Check username/password correct
2. Check user is active: `SELECT is_active FROM users WHERE username = 'X'`
3. Check network reaches server
4. Check server is running

### Forgot Password

Admin must reset:
```bash
python3 -c "
from server.auth.user_manager import UserManager
UserManager().reset_password('john.doe', 'NewTempPass!')
"
```

### Too Many Sessions

```bash
# Clear old sessions
curl -X DELETE http://10.10.30.50:8888/api/users/john.doe/sessions \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

---

## Next Step

Users configured. Proceed to [06_NETWORK_SECURITY.md](06_NETWORK_SECURITY.md) for IP restrictions and firewall rules.
