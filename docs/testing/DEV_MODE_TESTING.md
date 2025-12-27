# Dev Mode Testing (Linux)

**Quick testing via Vite dev server - no Windows build needed**

---

## Start Servers

```bash
# Terminal 1: Backend (with rate limit disabled)
cd /home/neil1988/LocalizationTools
DEV_MODE=true python3 server/main.py

# Terminal 2: Frontend
cd /home/neil1988/LocalizationTools/locaNext
npm run dev
```

**URLs:**
- Frontend: http://localhost:5173
- Backend: http://localhost:8888
- API Docs: http://localhost:8888/docs

---

## Login

| User | Password |
|------|----------|
| admin | admin123 |

---

## Quick Check Commands

```bash
# Check servers running
ps aux | grep -E "(vite|python3 server/main)" | grep -v grep

# Check backend health
curl -s http://localhost:8888/health | jq

# Kill all servers
pkill -f "vite dev" ; pkill -f "python3 server/main"
```

---

## Test Features Manually

1. Open http://localhost:5173 in browser
2. Login: admin / admin123
3. Navigate to LDM
4. Open a file
5. Test features:
   - **Search bar**: Type text, wait 300ms for results
   - **Color tags**: Look for colored text in cells
   - **Hover**: Mouse over rows for highlight
   - **Edit**: Double-click target cell

---

## Browser Console Debugging

Open DevTools (F12) → Console tab

**Search bar logs:**
```
searchTerm changed via effect {from: "", to: "test"}
handleSearch triggered {searchTerm: "test"}
handleSearch executing search {searchTerm: "test"}
```

**Color parser logs:**
```
ColorText rendering: {text: "<PAColor0xffe9bd23>100%<PAOldColor>", segments: [...]}
```

---

## Import Test Data

To test color tags, import a file with PAColor patterns:
- Test file: `tests/fixtures/sample_language_data.txt`
- Or use: `C:\NEIL_PROJECTS_WINDOWSBUILD\LocaNextProject\TestFilesForLocaNext\sampleofLanguageData.txt`

---

## Playwright Headless Tests

```bash
cd /home/neil1988/LocalizationTools/locaNext
npx playwright test --grep "health" --reporter=list
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Rate limited | Restart backend with `DEV_MODE=true` |
| Port in use | `pkill -f vite` or `pkill -f python3` |
| No data in LDM | Import a file via Upload |
| Search not working | Check console for errors |

---

*Dev testing doc | No Windows build required*
