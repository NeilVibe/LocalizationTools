# Frontend Monitoring & Debugging Guide

## ✅ SIMPLE MONITORING - What You CAN See

### 1. Vite Dev Server Logs (MOST IMPORTANT!)
**Location**: `/tmp/admin-dashboard.log`

This file contains:
- ✅ SvelteKit warnings (prop warnings, unused exports)
- ✅ Svelte plugin warnings
- ✅ Compilation errors
- ✅ HMR (Hot Module Reload) updates
- ✅ Unused CSS selectors
- ✅ Build errors

**Monitor in real-time:**
```bash
# Watch all warnings/errors
tail -f /tmp/admin-dashboard.log | grep -E "warning|error|vite-plugin-svelte"

# Check for specific SvelteKit warnings
tail -50 /tmp/admin-dashboard.log | grep "vite-plugin-svelte"

# Check recent compilation errors
tail -100 /tmp/admin-dashboard.log | grep -i error
```

**Example warnings you'll see:**
```
[vite-plugin-svelte] Layout has unused export property 'data'
[vite-plugin-svelte] Unused CSS selector ".success-badge"
```

### 2. Browser Console Errors (User Reports)
When user reports browser console errors:
1. User sees error in DevTools Console
2. Search for error pattern in code
3. Fix the issue
4. User refreshes to verify

Common patterns:
- `TypeError: Cannot read properties of undefined` → Missing null checks
- `ReferenceError` → Missing imports or variables
- `Network errors` → Backend API issues

## Common Issues & Fixes

### 1. `.toFixed()` Errors
**Problem**: Calling `.toFixed()` on undefined/null values
**Solution**: Always use safe navigation and fallbacks
```javascript
// ❌ BAD
{user.success_rate.toFixed(1)}

// ✅ GOOD
{(user?.success_rate || 0).toFixed(1)}
```

### 2. Icons Too Big
**Problem**: Emoji icons displaying too large
**Solution**: Add proper CSS sizing
```css
.stat-icon {
  font-size: 1.5rem;
  margin-bottom: 0.75rem;
  opacity: 0.8;
}
```

### 3. Layout Overflow
**Problem**: Content not fitting window
**Solution**: Proper flex layout with overflow
```css
.admin-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.admin-content {
  flex: 1;
  overflow-y: auto;
}
```

### 4. API Response Mismatch
**Problem**: Frontend expects fields that API doesn't return
**Solution**: Check actual API response first
```bash
# Test API endpoint
curl -s 'http://localhost:8888/api/v2/admin/rankings/users?period=monthly&limit=3' | jq '.'

# Compare with frontend code
```

## Backend API Monitoring

### Monitor Backend Logs
```bash
# Watch backend errors in real-time
tail -f server/logs/app.log | grep ERROR

# Check recent backend activity
tail -100 server/logs/app.log

# Monitor specific API endpoints
tail -f server/logs/app.log | grep "api/v2/admin"
```

## Automated Checks

### Quick Health Check Script
```bash
#!/bin/bash
echo "=== Frontend Monitoring ==="
echo "Vite Warnings:"
tail -20 /tmp/admin-dashboard.log | grep "vite-plugin-svelte" || echo "  No warnings"

echo -e "\n=== Backend Monitoring ==="
curl -s http://localhost:8888/health | jq .status

echo -e "\n=== Frontend Status ==="
curl -s -o /dev/null -w "Admin Dashboard: HTTP %{http_code}\n" http://localhost:5174
```

### Test API Data Structure
```bash
# Create test script
cat > /tmp/test_api_structure.sh << 'EOF'
#!/bin/bash
echo "Testing Admin API Data Structures"
echo "=================================="

echo -e "\n1. Overview Stats:"
curl -s http://localhost:8888/api/v2/admin/stats/overview | jq 'keys'

echo -e "\n2. Daily Stats:"
curl -s 'http://localhost:8888/api/v2/admin/stats/daily?days=7' | jq '.data[0] | keys'

echo -e "\n3. User Rankings:"
curl -s 'http://localhost:8888/api/v2/admin/rankings/users?period=monthly&limit=3' | jq '.rankings[0] | keys'

echo -e "\n4. Tool Popularity:"
curl -s 'http://localhost:8888/api/v2/admin/stats/tools/popularity?days=30' | jq '.tools[0] | keys'
EOF

chmod +x /tmp/test_api_structure.sh
/tmp/test_api_structure.sh
```

## Null Safety Patterns

### Always Use These Patterns

1. **Optional Chaining**:
```javascript
const value = data?.field?.subfield || defaultValue
```

2. **Array Map with Safety**:
```javascript
const values = array.map(item => item?.value || 0)
```

3. **Number Methods with Fallback**:
```javascript
{(number || 0).toFixed(2)}
{(percentage || 0).toFixed(1)}%
```

4. **Conditional Rendering**:
```svelte
{#if data && data.length > 0}
  <!-- Safe to use data -->
{/if}
```

## CSS Best Practices

### Modular Structure
```css
/* Component-specific */
.stat-card { }
.stat-icon { }
.stat-value { }

/* Layout */
.admin-layout { }
.admin-sidebar { }
.admin-main { }

/* Utilities */
.mb-1 { margin-bottom: 0.5rem; }
.flex { display: flex; }
```

### Responsive Design
```css
@media (max-width: 768px) {
  .admin-sidebar {
    display: none;
  }
  .stats-grid {
    grid-template-columns: 1fr;
  }
}
```

## Testing Checklist

Before committing frontend changes:

- [ ] Check browser console for errors
- [ ] Test all pages (/, /stats, /rankings, /users, /logs, /activity)
- [ ] Verify API responses match frontend expectations
- [ ] Test responsive design (resize browser)
- [ ] Check hover effects and animations
- [ ] Verify scrolling works properly
- [ ] Test with empty/loading states
- [ ] Check null/undefined handling

## Quick Fixes Reference

| Error | Location | Fix |
|-------|----------|-----|
| `.toFixed()` error | Any numeric display | Add `(value || 0)` wrapper |
| Icons too big | `.stat-icon` | Set `font-size: 1.5rem` |
| No scrolling | `body` or `.admin-layout` | Check `overflow` property |
| Data undefined | API calls | Add null checks with `?.` |
| Charts not rendering | Chart.js | Verify data arrays not empty |

## Complete Monitoring Setup

### Start Monitoring (Run These in Separate Terminals)

**Terminal 1: Frontend Warnings**
```bash
tail -f /tmp/admin-dashboard.log | grep -E "warning|error|vite-plugin-svelte"
```

**Terminal 2: Backend Errors**
```bash
tail -f server/logs/app.log | grep -E "ERROR|WARNING"
```

**Terminal 3: API Requests**
```bash
tail -f server/logs/app.log | grep -E "→|←"
```

### One-Command Health Check
```bash
# Complete system check
bash << 'EOF'
echo "=== SYSTEM HEALTH CHECK ==="
echo ""
echo "Backend:     $(curl -s http://localhost:8888/health | jq -r .status 2>/dev/null || echo 'DOWN')"
echo "Admin UI:    $(curl -s -o /dev/null -w '%{http_code}' http://localhost:5174 2>/dev/null)"
echo "LocaNext:    $(curl -s -o /dev/null -w '%{http_code}' http://localhost:5173 2>/dev/null)"
echo ""
echo "Recent Frontend Warnings:"
tail -20 /tmp/admin-dashboard.log | grep "vite-plugin-svelte" | tail -5 || echo "  None"
EOF
```

---

## Fixed Issues (2025-11-12)

1. ✅ TypeError with `.toFixed()` on undefined values
2. ✅ Emoji icons displaying too large
3. ✅ Layout overflow preventing scrolling
4. ✅ API response field mismatches (success_rate, avg_duration)
5. ✅ Added comprehensive null safety throughout

**All pages now load without errors!**
