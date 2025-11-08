# Admin Setup Guide

## Initial Setup

### 1. Create Default Admin User

Run the initialization script to create the default admin user and initial database:

```bash
python3 scripts/create_admin.py
```

This will:
- Setup the database (create all tables)
- Create default admin user
- Create initial app version record

### 2. Default Admin Credentials

**⚠️ IMPORTANT: Change these credentials immediately in production!**

```
Username: admin
Password: admin123
Role: superadmin
```

### 3. Test Admin Login

Verify the admin credentials work:

```bash
python3 scripts/test_admin_login.py
```

This will test:
- User lookup in database
- Password verification (bcrypt)
- JWT token creation
- JWT token verification
- Complete login flow

## Starting the System

### Start the API Server

```bash
python3 server/main.py
```

Server will run on: `http://localhost:8888`

API Documentation: `http://localhost:8888/docs`

### Start the Admin Dashboard

```bash
python3 run_admin_dashboard.py
```

Dashboard will run on: `http://localhost:8885`

## Admin Dashboard Features

### Overview Tab
- Real-time statistics (users, operations, success rate, active sessions)
- Tool usage statistics
- Performance metrics

### Logs Tab
- Recent activity logs
- Filter by tool
- Configurable display limit

### Users Tab
- User list with statistics
- Operation counts per user
- Last login tracking
- Active/inactive status

### Errors Tab
- Recent error logs
- Error type and message display
- Troubleshooting information

### Settings Tab
- Server configuration
- Database information
- Version info

## Creating Additional Users

### Via API (Recommended)

1. Login as admin to get JWT token:
```bash
curl -X POST http://localhost:8888/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

2. Use the returned token to create new user:
```bash
curl -X POST http://localhost:8888/api/auth/register \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{
    "username": "newuser",
    "password": "securepassword",
    "email": "user@company.com",
    "full_name": "John Doe",
    "department": "Localization"
  }'
```

### Via Database (Not Recommended)

Only for emergency access. Use API whenever possible.

## Security Best Practices

1. **Change default password immediately**
2. **Use strong passwords** (minimum 12 characters, mixed case, numbers, symbols)
3. **Enable HTTPS** in production (configure reverse proxy)
4. **Restrict admin dashboard access** (firewall, VPN)
5. **Rotate JWT secret key** regularly (update `SECRET_KEY` in config)
6. **Monitor error logs** for suspicious activity
7. **Regular database backups**
8. **Update app versions** when available

## Troubleshooting

### Can't login?

1. Verify admin user exists:
```bash
python3 scripts/test_admin_login.py
```

2. Recreate admin user (if needed):
```bash
python3 scripts/create_admin.py
```

### Database issues?

1. Check database file exists:
```bash
ls -la server/data/localizationtools.db
```

2. Verify database schema:
```bash
python3 -m server.database.db_setup
```

### Server won't start?

1. Check port availability:
```bash
lsof -i :8888
lsof -i :8885
```

2. Check logs:
```bash
tail -f server/data/logs/server.log
```

## Production Deployment

### Environment Variables

Set these in production:

```bash
export DATABASE_TYPE="postgresql"
export POSTGRES_HOST="your-db-host"
export POSTGRES_USER="your-db-user"
export POSTGRES_PASSWORD="secure-password"
export POSTGRES_DB="localization_tools_db"
export SECRET_KEY="your-very-secure-secret-key"
export DEBUG="false"
export ENABLE_DOCS="false"
```

### PostgreSQL Setup

1. Create database:
```sql
CREATE DATABASE localization_tools_db;
CREATE USER localization_admin WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE localization_tools_db TO localization_admin;
```

2. Run initialization:
```bash
python3 scripts/create_admin.py
```

### Reverse Proxy (nginx)

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # API Server
    location /api/ {
        proxy_pass http://localhost:8888;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Admin Dashboard
    location /admin/ {
        proxy_pass http://localhost:8885;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Support

For issues or questions:
1. Check logs: `server/data/logs/server.log`
2. Review error logs in admin dashboard
3. Run diagnostic scripts in `scripts/` folder
