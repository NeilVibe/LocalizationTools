# DEV Testing Efficiency Report

**Generated:** 2025-12-28 | **Status:** EFFECTIVE

---

## What Works Well

### 1. Instant Feedback Loop
```
Code change → Vite HMR → Browser refresh → Verify
Time: < 2 seconds
```

### 2. Playwright Headless Tests
- Login: 2s
- Navigate to LDM: 2s
- Load file: 5s
- Type search: 1s
- **Total test: ~12-15s**

### 3. Real Data Testing
- File: `sample_language_data.txt`
- Rows: 63 real Korean/French entries
- Features: PAColor tags, TextBind, special chars
- **Much better than synthetic data**

---

## Patterns That Work

### Database Access
```python
# CORRECT: Use server config
import sys
sys.path.insert(0, '/home/neil1988/LocalizationTools/server')
from config import DATABASE_URL
engine = create_engine(DATABASE_URL)
```

### API Access
```python
import requests
resp = requests.post('http://localhost:8888/api/auth/login',
    json={'username': 'admin', 'password': 'admin123'})
token = resp.json().get('access_token')
```

### Svelte 5 Input Handling
```svelte
<!-- NO bind:value - use oninput only -->
<input oninput={(e) => { state = e.target.value; }} />
```

### Effect with Previous Value Tracking
```javascript
let previousValue = $state(null);
$effect(() => {
  if (value && value !== previousValue) {
    previousValue = value;
    doSomething();
  }
});
```

---

## Patterns That DON'T Work

| Pattern | Problem | Solution |
|---------|---------|----------|
| Hardcoded DB credentials | Wrong password | Use server config |
| `bind:value` with `$state` | Playwright can't set value | Use `oninput` |
| Effect without previous tracking | Runs on every change | Track previous value |
| TypeScript in non-TS Svelte | Compile error | Remove TS syntax |

---

## Testing Checklist

### Before Each Test
- [ ] Backend running: `curl localhost:8888/health`
- [ ] Frontend running: `http://localhost:5173`
- [ ] Real data uploaded (63 rows)

### Test Types
1. **Unit test**: Single component behavior
2. **Integration test**: Login → Navigate → Action
3. **E2E test**: Full user flow with verification

### Verification Methods
- Screenshot: `await page.screenshot({ path: '/tmp/test.png' })`
- Console logs: `page.on('console', msg => ...)`
- Element count: `await page.$$('.selector')`
- Text content: `await page.textContent('.selector')`

---

## Efficiency Metrics

| Task | DEV Testing | Windows Build |
|------|-------------|---------------|
| Code change | 1s (HMR) | 15+ min |
| Run test | 12-15s | 5+ min |
| Debug cycle | 30s | 20+ min |
| Full verify | 1 min | 30+ min |

**DEV Testing is 20-30x faster for UI development.**

---

## Recommended Workflow

```
1. Make code change
2. Check Vite console for errors
3. Run Playwright test: npx playwright test tests/xxx.spec.ts
4. If fail: Check console, add logging, fix
5. If pass: Commit, push to Git
6. Only BUILD when milestone reached
```

---

## Test File Structure

```
testing_toolkit/dev_tests/
├── helpers/
│   ├── login.ts         # Login, navigate, API token
│   ├── ldm-actions.ts   # Project/file selection, search
│   ├── database.py      # DB access (server config)
│   ├── api.py           # REST API helper
│   └── index.ts         # Export all
├── EFFICIENCY_REPORT.md # This file
└── README.md            # Overview
```

---

*DEV Testing = Fast iteration = Better code quality*
