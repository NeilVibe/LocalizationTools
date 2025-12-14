# P27: Full Stack Modernization

**Created:** 2025-12-14 | **Status:** PLANNING
**Priority:** Medium | **Effort:** 1-2 days
**Goal:** Upgrade to Svelte 5 + latest ecosystem for performance, security, and future-proofing

---

## Why Modernize?

### Svelte 5 Benefits (The Hype Is Real)

| Feature | Improvement |
|---------|-------------|
| **Runes** | Explicit reactivity - no more magic `$:` |
| **Performance** | Fine-grained reactivity = faster updates |
| **Bundle size** | 10-20% smaller |
| **TypeScript** | First-class support |
| **Debugging** | Clearer data flow |
| **Future-proof** | Svelte 4 will be deprecated |

### Security Fixes Included

| Package | Vulnerability Fixed |
|---------|---------------------|
| Electron 39 | ASAR integrity bypass |
| Vite 7 | Dev server request leak |
| esbuild | Dev server vulnerabilities |

---

## Current vs Target Versions

| Package | Current | Target | Jump |
|---------|---------|--------|------|
| **svelte** | 4.2.8 | 5.46.0 | MAJOR |
| **@sveltejs/kit** | 2.0.0 | 2.49.2 | Minor |
| **@sveltejs/vite-plugin-svelte** | 3.0.0 | 6.2.1 | MAJOR |
| **@sveltejs/adapter-static** | 3.0.1 | 3.0.10 | Patch |
| **vite** | 5.0.8 | 7.2.7 | MAJOR |
| **electron** | 28.0.0 | 39.2.7 | MAJOR |
| **electron-builder** | 24.9.1 | 26.0.12 | MAJOR |
| **carbon-components-svelte** | 0.85.0 | 0.95.2 | Minor |
| **carbon-icons-svelte** | 12.8.0 | Latest | Check |

---

## Codebase Analysis

### Components to Convert

| Metric | Count |
|--------|-------|
| Total .svelte files | 22 |
| Files with `$:` statements | 14 |
| Total `$:` reactive statements | 33 |
| Store subscriptions (`$store`) | 129 |
| Event handlers (`on:`) | 240 |

### Conversion Patterns

```svelte
// BEFORE (Svelte 4)
<script>
  export let name;           // prop
  let count = 0;             // state
  $: doubled = count * 2;    // derived
  $: console.log(count);     // effect
  $: if (count > 10) reset(); // effect with condition
</script>

// AFTER (Svelte 5)
<script>
  let { name } = $props();           // prop
  let count = $state(0);             // state
  let doubled = $derived(count * 2); // derived
  $effect(() => console.log(count)); // effect
  $effect(() => { if (count > 10) reset(); }); // effect
</script>
```

### What Still Works (No Change Needed)

- `$store` auto-subscriptions ✅
- `on:click` event handlers ✅ (deprecated but works)
- `<slot>` elements ✅
- CSS scoping ✅
- Transitions/animations ✅

---

## Migration Strategy

### Phase 1: Environment Setup (30 min)

```bash
# Create new branch
git checkout -b feature/svelte5-migration

# Backup current state
cp package.json package.json.svelte4
cp package-lock.json package-lock.json.svelte4
```

### Phase 2: Update Dependencies (1 hour)

```bash
cd locaNext

# Update Svelte ecosystem
npm install svelte@latest
npm install @sveltejs/kit@latest
npm install @sveltejs/vite-plugin-svelte@latest
npm install @sveltejs/adapter-static@latest

# Update Vite
npm install vite@latest

# Update Electron
npm install electron@latest
npm install electron-builder@latest

# Update Carbon
npm install carbon-components-svelte@latest
npm install carbon-icons-svelte@latest

# Update dev tools
npm install @playwright/test@latest
```

### Phase 3: Fix Build Config (30 min)

Files to check/update:
- [ ] `vite.config.js` - Vite 7 compatibility
- [ ] `svelte.config.js` - Svelte 5 settings
- [ ] `electron/main.js` - Electron 39 API changes
- [ ] `electron/preload.js` - Context isolation changes

### Phase 4: Component Migration (3-4 hours)

#### Priority Order (by complexity)

**Tier 1 - Simple Components (Quick wins)**
Convert components with 0-2 reactive statements first.

**Tier 2 - Medium Components**
Components with stores and derived values.

**Tier 3 - Complex Components**
- LDMGrid.svelte (largest, most complex)
- EditModal.svelte (lots of state)
- TMManager.svelte (stores + effects)

#### Component Checklist

| Component | `$:` Count | Priority | Status |
|-----------|------------|----------|--------|
| +page.svelte files | Low | Tier 1 | [ ] |
| Header.svelte | Low | Tier 1 | [ ] |
| Sidebar.svelte | Low | Tier 1 | [ ] |
| FileExplorer.svelte | Medium | Tier 2 | [ ] |
| ServerStatus.svelte | Low | Tier 1 | [ ] |
| Preferences.svelte | Medium | Tier 2 | [ ] |
| TMManager.svelte | Medium | Tier 2 | [ ] |
| TMUploadModal.svelte | Low | Tier 1 | [ ] |
| EditModal.svelte | High | Tier 3 | [ ] |
| LDMGrid.svelte | High | Tier 3 | [ ] |
| TaskManager.svelte | Medium | Tier 2 | [ ] |

### Phase 5: Testing (2 hours)

```bash
# Build test
npm run build

# Dev mode test
npm run dev

# Electron test
npm run electron:dev

# E2E tests
npm run test
```

#### Manual Test Checklist

- [ ] App launches
- [ ] Login works
- [ ] All 4 tools load (XLSTransfer, QuickSearch, KR Similar, LDM)
- [ ] LDM grid renders correctly
- [ ] File upload works
- [ ] Cell editing works
- [ ] WebSocket connects
- [ ] Real-time sync works
- [ ] Preferences persist
- [ ] TM panel works

### Phase 6: Cleanup (30 min)

- [ ] Remove backup files
- [ ] Update package.json version
- [ ] Commit with detailed message
- [ ] Test on Windows (CI)

---

## Detailed Component Migration Guide

### Pattern 1: Props

```svelte
// BEFORE
<script>
  export let title;
  export let count = 0;
</script>

// AFTER
<script>
  let { title, count = 0 } = $props();
</script>
```

### Pattern 2: Reactive State

```svelte
// BEFORE
<script>
  let items = [];
  let filter = '';
  $: filteredItems = items.filter(i => i.includes(filter));
</script>

// AFTER
<script>
  let items = $state([]);
  let filter = $state('');
  let filteredItems = $derived(items.filter(i => i.includes(filter)));
</script>
```

### Pattern 3: Side Effects

```svelte
// BEFORE
<script>
  let count;
  $: console.log('Count changed:', count);
  $: if (count > 100) alert('Too high!');
</script>

// AFTER
<script>
  let count = $state(0);

  $effect(() => {
    console.log('Count changed:', count);
  });

  $effect(() => {
    if (count > 100) alert('Too high!');
  });
</script>
```

### Pattern 4: Store Subscriptions

```svelte
// BEFORE & AFTER (no change needed!)
<script>
  import { userStore } from '$lib/stores';
</script>

<p>Hello {$userStore.name}</p>
```

### Pattern 5: Events (Optional Update)

```svelte
// BEFORE (still works!)
<button on:click={handleClick}>Click</button>

// AFTER (new style, optional)
<button onclick={handleClick}>Click</button>
```

---

## Risk Mitigation

### Rollback Plan

```bash
# If everything breaks
git checkout main
cd locaNext
rm -rf node_modules package-lock.json
npm install
```

### Incremental Testing

After each component:
1. `npm run build` - verify compile
2. Test that specific component manually
3. Commit if working

### Known Gotchas

| Issue | Solution |
|-------|----------|
| Carbon component errors | Update to 0.95.2+ |
| Electron preload errors | Check contextIsolation |
| Vite config errors | Check vite.config.js format |
| Store type errors | May need `$state.raw()` for complex objects |

---

## Time Estimate

| Phase | Duration |
|-------|----------|
| Setup & Dependencies | 1-1.5 hours |
| Build Config Fixes | 30 min - 1 hour |
| Component Migration | 3-4 hours |
| Testing & Debugging | 2-3 hours |
| Cleanup & Polish | 30 min |
| **Total** | **7-10 hours** |

---

## Success Criteria

- [ ] All 22 components converted to Svelte 5 runes
- [ ] `npm run build` passes
- [ ] `npm run electron:dev` works
- [ ] All 4 tools functional
- [ ] No console errors
- [ ] E2E tests pass
- [ ] `npm audit` shows improved security

---

## Commands Quick Reference

```bash
# Start migration
git checkout -b feature/svelte5-migration

# Update all packages
npm install svelte@latest @sveltejs/kit@latest @sveltejs/vite-plugin-svelte@latest vite@latest electron@latest electron-builder@latest carbon-components-svelte@latest

# Test build
npm run build

# Test dev
npm run electron:dev

# Run tests
npm run test

# If disaster - rollback
git checkout main && rm -rf node_modules && npm install
```

---

## References

- [Svelte 5 Migration Guide](https://svelte.dev/docs/svelte/v5-migration-guide)
- [Svelte 5 Runes Documentation](https://svelte.dev/docs/svelte/runes)
- [Carbon Svelte 5 Compatibility](https://github.com/carbon-design-system/carbon-components-svelte/discussions/1908)
- [Electron 39 Release Notes](https://www.electronjs.org/blog/electron-39-0)

---

*Created: 2025-12-14 | Ready to execute when approved*
