#!/usr/bin/env python3
"""
LocaNext CLI Debug Toolkit
==========================
Direct API access to all LocaNext operations. No browser needed.
Designed for Claude to debug, test, and operate LocaNext via terminal.

Usage:
    python3 scripts/locanext_cli.py <command> [args...]

Examples:
    python3 scripts/locanext_cli.py status              # Health + connection
    python3 scripts/locanext_cli.py platforms            # List platforms
    python3 scripts/locanext_cli.py tree BDO             # Show file tree
    python3 scripts/locanext_cli.py tm list              # List TMs
    python3 scripts/locanext_cli.py tm tree              # Full TM tree
    python3 scripts/locanext_cli.py tm assign 186 52     # Assign TM to folder
    python3 scripts/locanext_cli.py tm activate 186      # Activate TM
    python3 scripts/locanext_cli.py tm deactivate 186    # Deactivate TM
    python3 scripts/locanext_cli.py folder create 154 "MyFolder"  # Create folder
    python3 scripts/locanext_cli.py file rows 5          # Get rows for file 5
    python3 scripts/locanext_cli.py row update 42 "New translation"
    python3 scripts/locanext_cli.py qa check 5           # Run QA on file
    python3 scripts/locanext_cli.py search "warrior"     # Semantic search
    python3 scripts/locanext_cli.py e2e-tm               # Full TM E2E test
"""
from __future__ import annotations

import sys
import json
import time
import requests
import argparse
from typing import Optional

API_BASE = "http://localhost:8888"

# ============================================================================
# HTTP helpers
# ============================================================================

def api(method: str, path: str, params: dict = None, data: dict = None, quiet: bool = False) -> dict:
    """Make API call and return JSON response."""
    url = f"{API_BASE}{path}"
    try:
        r = requests.request(method, url, params=params, json=data, timeout=30)
        if not quiet:
            status_icon = "✓" if r.ok else "✗"
            print(f"  {status_icon} {method.upper()} {path} → {r.status_code}")
        if r.status_code == 204:
            return {"success": True}
        return r.json()
    except requests.ConnectionError:
        print(f"  ✗ Connection refused — is backend running?")
        sys.exit(1)
    except Exception as e:
        print(f"  ✗ {e}")
        return {"error": str(e)}


def ok(result: dict) -> bool:
    """Check if API result is successful."""
    return "error" not in result and "detail" not in result


def pp(data, indent: int = 2):
    """Pretty print JSON."""
    print(json.dumps(data, indent=indent, default=str))


def unwrap_list(data, keys=("platforms", "projects", "folders", "files", "items", "rows", "tms", "results")):
    """Unwrap API responses — some return {key: [...], total: N}, others return [...]."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for k in keys:
            if k in data and isinstance(data[k], list):
                return data[k]
    return data

# ============================================================================
# Status
# ============================================================================

def cmd_status():
    """Show server health and connection status."""
    print("=== LocaNext Status ===")
    health = api("get", "/api/ldm/health", quiet=True)
    print(f"  Backend:    {'✓ Online' if ok(health) else '✗ Down'}")

    # DB check
    platforms = unwrap_list(api("get", "/api/ldm/platforms", quiet=True))
    if isinstance(platforms, list):
        print(f"  Database:   ✓ {len(platforms)} platforms")
    else:
        print(f"  Database:   ✗ {platforms}")

    # TM check
    tms = api("get", "/api/ldm/tm", quiet=True)
    if isinstance(tms, list):
        total_entries = sum(t.get("entry_count", 0) for t in tms)
        print(f"  TMs:        {len(tms)} TMs, {total_entries:,} entries")

    # Offline check
    offline = api("get", "/api/ldm/offline/status", quiet=True)
    if ok(offline):
        print(f"  Offline:    {offline.get('mode', 'unknown')}")

# ============================================================================
# Platforms / Projects / Folders / Files
# ============================================================================

def cmd_platforms():
    """List all platforms."""
    data = unwrap_list(api("get", "/api/ldm/platforms"))
    if isinstance(data, list):
        print(f"\n{'ID':>5}  {'Name':<30}  Projects")
        print("-" * 55)
        for p in data:
            print(f"{p['id']:>5}  {p['name']:<30}  {p.get('project_count', '?')}")

def cmd_projects(platform_id: Optional[int] = None):
    """List projects, optionally filtered by platform."""
    params = {"platform_id": platform_id} if platform_id else {}
    data = unwrap_list(api("get", "/api/ldm/projects", params=params))
    if isinstance(data, list):
        print(f"\n{'ID':>5}  {'Name':<30}  {'Platform':<15}  Files")
        print("-" * 70)
        for p in data:
            print(f"{p['id']:>5}  {p['name']:<30}  {p.get('platform_name', '?'):<15}  {p.get('file_count', '?')}")

def cmd_tree(platform_name: str = None):
    """Show full file tree for a platform or all."""
    platforms = api("get", "/api/ldm/platforms", quiet=True)
    if not isinstance(platforms, list):
        return

    for p in platforms:
        if platform_name and p["name"].lower() != platform_name.lower():
            continue
        print(f"\n📁 {p['name']} (id={p['id']})")
        projects = api("get", "/api/ldm/projects", params={"platform_id": p["id"]}, quiet=True)
        if not isinstance(projects, list):
            continue
        for proj in projects:
            print(f"  📂 {proj['name']} (id={proj['id']})")
            tree = api("get", f"/api/ldm/projects/{proj['id']}/tree", quiet=True)
            if isinstance(tree, dict):
                _print_tree(tree.get("folders", []), tree.get("files", []), indent=4)

def _print_tree(folders: list, files: list, indent: int = 0):
    """Recursively print folder/file tree."""
    prefix = " " * indent
    for f in folders:
        print(f"{prefix}📁 {f['name']} (id={f['id']})")
        _print_tree(f.get("children", []), f.get("files", []), indent + 2)
    for f in files:
        rows = f.get("row_count", "?")
        print(f"{prefix}📄 {f['name']} (id={f['id']}, {rows} rows)")

def cmd_folder_create(project_id: int, name: str):
    """Create a folder in a project."""
    data = api("post", "/api/ldm/folders", data={"name": name, "project_id": project_id})
    if ok(data):
        print(f"  Created folder '{name}' → id={data.get('id')}")
    else:
        pp(data)

def cmd_folder_list(project_id: int):
    """List folders in a project."""
    tree = api("get", f"/api/ldm/projects/{project_id}/tree", quiet=True)
    if isinstance(tree, dict):
        _print_tree(tree.get("folders", []), [], indent=0)

# ============================================================================
# Files & Rows
# ============================================================================

def cmd_files(project_id: int):
    """List files in a project."""
    data = api("get", f"/api/ldm/projects/{project_id}/files")
    if isinstance(data, list):
        print(f"\n{'ID':>5}  {'Name':<40}  {'Rows':>6}  Type")
        print("-" * 65)
        for f in data:
            print(f"{f['id']:>5}  {f['name']:<40}  {f.get('row_count', '?'):>6}  {f.get('file_type', '?')}")

def cmd_rows(file_id: int, limit: int = 10):
    """Get rows for a file."""
    data = api("get", f"/api/ldm/files/{file_id}/rows", params={"limit": limit})
    if isinstance(data, dict):
        rows = data.get("rows", data.get("items", []))
        print(f"\n  {len(rows)} rows (of {data.get('total', '?')} total)")
        for r in rows[:limit]:
            src = (r.get("source_text") or "")[:50]
            tgt = (r.get("target_text") or "")[:50]
            sid = r.get("string_id", "")[:20]
            print(f"  [{r.get('id'):>5}] {sid:<20} | {src:<50} → {tgt}")

def cmd_row_update(row_id: int, target_text: str):
    """Update a row's target text."""
    data = api("put", f"/api/ldm/rows/{row_id}", data={"target_text": target_text})
    if ok(data):
        print(f"  Row {row_id} updated")
    else:
        pp(data)

# ============================================================================
# TM Operations
# ============================================================================

def cmd_tm_list():
    """List all TMs."""
    data = api("get", "/api/ldm/tm")
    if isinstance(data, list):
        print(f"\n{'ID':>5}  {'Name':<30}  {'Entries':>8}  Status")
        print("-" * 60)
        for tm in data:
            print(f"{tm['id']:>5}  {tm['name']:<30}  {tm.get('entry_count', 0):>8}  {tm.get('status', '?')}")

def cmd_tm_tree():
    """Show full TM tree with assignments and active status."""
    data = api("get", "/api/ldm/tm-tree")
    if not ok(data):
        pp(data)
        return

    # Unassigned
    unassigned = data.get("unassigned", [])
    print(f"\n📋 Unassigned ({len(unassigned)} TMs)")
    for tm in unassigned:
        status = "🟢 Active" if tm.get("is_active") else "⚪ Inactive"
        print(f"  💾 {tm['tm_name']} ({tm.get('entry_count', 0):,} entries) [{status}]")

    # Platforms
    for p in data.get("platforms", []):
        p_tms = p.get("tms", [])
        print(f"\n📁 {p['name']} (id={p['id']}) [{len(p_tms)} TMs]")
        for tm in p_tms:
            status = "🟢 Active" if tm.get("is_active") else "⚪ Inactive"
            print(f"  💾 {tm['tm_name']} ({tm.get('entry_count', 0):,} entries) [{status}]")

        for proj in p.get("projects", []):
            pj_tms = proj.get("tms", [])
            print(f"  📂 {proj['name']} (id={proj['id']}) [{len(pj_tms)} TMs]")
            for tm in pj_tms:
                status = "🟢 Active" if tm.get("is_active") else "⚪ Inactive"
                print(f"    💾 {tm['tm_name']} ({tm.get('entry_count', 0):,} entries) [{status}]")

            _print_tm_folders(proj.get("folders", []), indent=4)

def _print_tm_folders(folders: list, indent: int = 0):
    """Print folder tree with TMs."""
    prefix = " " * indent
    for f in folders:
        f_tms = f.get("tms", [])
        print(f"{prefix}📁 {f['name']} (id={f['id']}) [{len(f_tms)} TMs]")
        for tm in f_tms:
            status = "🟢 Active" if tm.get("is_active") else "⚪ Inactive"
            print(f"{prefix}  💾 {tm['tm_name']} ({tm.get('entry_count', 0):,} entries) [{status}]")
        _print_tm_folders(f.get("children", []), indent + 2)

def cmd_tm_assign(tm_id: int, folder_id: int = None, project_id: int = None, platform_id: int = None):
    """Assign TM to a scope."""
    params = {}
    if folder_id: params["folder_id"] = folder_id
    elif project_id: params["project_id"] = project_id
    elif platform_id: params["platform_id"] = platform_id
    data = api("patch", f"/api/ldm/tm/{tm_id}/assign", params=params)
    pp(data)

def cmd_tm_activate(tm_id: int):
    """Activate a TM."""
    data = api("patch", f"/api/ldm/tm/{tm_id}/activate", params={"active": "true"})
    pp(data)

def cmd_tm_deactivate(tm_id: int):
    """Deactivate a TM."""
    data = api("patch", f"/api/ldm/tm/{tm_id}/activate", params={"active": "false"})
    pp(data)

def cmd_tm_assignment(tm_id: int):
    """Check TM assignment status."""
    data = api("get", f"/api/ldm/tm/{tm_id}/assignment")
    pp(data)

def cmd_tm_search(tm_id: int, query: str):
    """Search TM entries."""
    data = api("get", f"/api/ldm/tm/{tm_id}/search", params={"query": query})
    if isinstance(data, dict):
        results = data.get("results", [])
        print(f"\n  {len(results)} results (took {data.get('search_time_ms', '?')}ms)")
        for r in results[:10]:
            score = r.get("score", r.get("similarity", "?"))
            print(f"  [{score:>5}] {r.get('source_text', '')[:60]} → {r.get('target_text', '')[:60]}")

# ============================================================================
# QA Operations
# ============================================================================

def cmd_qa_check(file_id: int, check_type: str = "all"):
    """Run QA check on a file."""
    params = {}
    if check_type != "all":
        params["check_type"] = check_type
    data = api("post", f"/api/ldm/files/{file_id}/check-qa", data=params)
    if isinstance(data, dict):
        issues = data.get("issues", data.get("results", []))
        print(f"\n  {len(issues)} QA issues found")
        for issue in issues[:20]:
            print(f"  [{issue.get('check_type', '?'):>10}] Row {issue.get('row_id', '?')}: {issue.get('message', '')[:80]}")

# ============================================================================
# Search
# ============================================================================

def cmd_search(query: str, tm_id: int = None):
    """Semantic search across TMs."""
    params = {"query": query}
    if tm_id:
        params["tm_id"] = tm_id
    data = api("get", "/api/ldm/semantic-search", params=params)
    if isinstance(data, dict):
        results = data.get("results", [])
        print(f"\n  {len(results)} results (took {data.get('search_time_ms', '?')}ms)")
        for r in results[:10]:
            sim = r.get("similarity", "?")
            print(f"  [{sim:.3f}] {r.get('source_text', '')[:50]} → {r.get('target_text', '')[:50]}")

# ============================================================================
# E2E Tests
# ============================================================================

def cmd_e2e_tm():
    """Full E2E TM workflow test. ZERO ERROR GOAL."""
    print("=" * 60)
    print("  E2E TM WORKFLOW TEST — ZERO ERROR GOAL")
    print("=" * 60)
    errors = []

    # Step 1: Check health
    print("\n[1/8] Health check")
    health = api("get", "/api/ldm/health", quiet=True)
    if not ok(health):
        errors.append("Health check failed")
        print("  ✗ FAIL")
    else:
        print("  ✓ Backend healthy")

    # Step 2: List platforms
    print("\n[2/8] List platforms")
    platforms = unwrap_list(api("get", "/api/ldm/platforms", quiet=True))
    if not isinstance(platforms, list) or len(platforms) == 0:
        errors.append("No platforms found")
        print("  ✗ FAIL")
        return
    # Skip Offline Storage, pick first real platform
    platform = next((p for p in platforms if p["name"] != "Offline Storage"), platforms[0])
    print(f"  ✓ Using platform '{platform['name']}' (id={platform['id']})")

    # Step 3: Get first project
    print("\n[3/8] Get project")
    projects = unwrap_list(api("get", "/api/ldm/projects", quiet=True))
    if not isinstance(projects, list):
        projects = []
    online_projects = [p for p in projects if p.get("platform_id") == platform["id"]]
    if not online_projects:
        errors.append("No projects in platform")
        print("  ✗ FAIL")
        return
    project = online_projects[0]
    print(f"  ✓ Using project '{project['name']}' (id={project['id']})")

    # Step 4: Create test folder
    print("\n[4/8] Create test folder")
    folder_name = f"E2E_TEST_{int(time.time())}"
    folder = api("post", "/api/ldm/folders", data={"name": folder_name, "project_id": project["id"]}, quiet=True)
    if not ok(folder):
        errors.append(f"Folder creation failed: {folder}")
        print(f"  ✗ FAIL: {folder}")
        return
    folder_id = folder["id"]
    print(f"  ✓ Created '{folder_name}' (id={folder_id})")

    # Step 5: Verify folder appears in TM tree
    print("\n[5/8] Verify TM tree mirrors folder")
    tree = api("get", "/api/ldm/tm-tree", quiet=True)
    found = _find_folder_in_tree(tree, folder_id)
    if found:
        print(f"  ✓ Folder '{folder_name}' found in TM tree")
    else:
        errors.append("Folder not mirrored in TM tree")
        print(f"  ✗ FAIL: Folder not in TM tree")

    # Step 6: List TMs and assign one
    print("\n[6/8] Assign TM to folder")
    tms = api("get", "/api/ldm/tm", quiet=True)
    if not isinstance(tms, list) or len(tms) == 0:
        errors.append("No TMs available")
        print("  ✗ FAIL: No TMs")
        return
    tm = tms[0]
    assign_result = api("patch", f"/api/ldm/tm/{tm['id']}/assign", params={"folder_id": folder_id}, quiet=True)
    if ok(assign_result):
        print(f"  ✓ Assigned '{tm['name']}' (id={tm['id']}) to folder {folder_id}")
    else:
        errors.append(f"TM assign failed: {assign_result}")
        print(f"  ✗ FAIL: {assign_result}")

    # Step 7: Activate/Deactivate/Activate cycle
    print("\n[7/8] Activate → Deactivate → Activate cycle")

    # Activate
    r1 = api("patch", f"/api/ldm/tm/{tm['id']}/activate", params={"active": "true"}, quiet=True)
    tree1 = api("get", "/api/ldm/tm-tree", quiet=True)
    active1 = _find_tm_active_in_tree(tree1, tm["id"])
    if active1 is True:
        print(f"  ✓ Activate: is_active=True (DB+API consistent)")
    else:
        errors.append(f"Activate returned is_active={active1}")
        print(f"  ✗ FAIL: is_active={active1} (expected True)")

    # Deactivate
    r2 = api("patch", f"/api/ldm/tm/{tm['id']}/activate", params={"active": "false"}, quiet=True)
    tree2 = api("get", "/api/ldm/tm-tree", quiet=True)
    active2 = _find_tm_active_in_tree(tree2, tm["id"])
    if active2 is False:
        print(f"  ✓ Deactivate: is_active=False (DB+API consistent)")
    else:
        errors.append(f"Deactivate returned is_active={active2}")
        print(f"  ✗ FAIL: is_active={active2} (expected False)")

    # Reactivate
    r3 = api("patch", f"/api/ldm/tm/{tm['id']}/activate", params={"active": "true"}, quiet=True)
    tree3 = api("get", "/api/ldm/tm-tree", quiet=True)
    active3 = _find_tm_active_in_tree(tree3, tm["id"])
    if active3 is True:
        print(f"  ✓ Reactivate: is_active=True (DB+API consistent)")
    else:
        errors.append(f"Reactivate returned is_active={active3}")
        print(f"  ✗ FAIL: is_active={active3} (expected True)")

    # Step 8: Cleanup — move TM back to unassigned
    print("\n[8/8] Cleanup — unassign TM")
    cleanup = api("patch", f"/api/ldm/tm/{tm['id']}/assign", quiet=True)
    if ok(cleanup):
        print(f"  ✓ TM moved back to unassigned")

    # Delete test folder
    delete = api("delete", f"/api/ldm/folders/{folder_id}", quiet=True)
    if ok(delete):
        print(f"  ✓ Test folder deleted")

    # Summary
    print("\n" + "=" * 60)
    if errors:
        print(f"  ✗ FAILED — {len(errors)} error(s):")
        for e in errors:
            print(f"    - {e}")
    else:
        print("  ✓ ALL PASSED — ZERO ERRORS")
    print("=" * 60)

def _find_folder_in_tree(tree: dict, folder_id: int) -> bool:
    """Recursively find a folder in the TM tree."""
    if isinstance(tree, dict):
        for p in tree.get("platforms", []):
            for proj in p.get("projects", []):
                if _folder_in_list(proj.get("folders", []), folder_id):
                    return True
    return False

def _folder_in_list(folders: list, folder_id: int) -> bool:
    for f in folders:
        if f.get("id") == folder_id:
            return True
        if _folder_in_list(f.get("children", []), folder_id):
            return True
    return False

def _find_tm_active_in_tree(tree: dict, tm_id: int):
    """Find a TM in the tree and return its is_active status."""
    if isinstance(tree, dict):
        for tm in tree.get("unassigned", []):
            if tm.get("tm_id") == tm_id:
                return tm.get("is_active")
        for p in tree.get("platforms", []):
            result = _find_tm_in_platform(p, tm_id)
            if result is not None:
                return result
    return None

def _find_tm_in_platform(p: dict, tm_id: int):
    for tm in p.get("tms", []):
        if tm.get("tm_id") == tm_id:
            return tm.get("is_active")
    for proj in p.get("projects", []):
        for tm in proj.get("tms", []):
            if tm.get("tm_id") == tm_id:
                return tm.get("is_active")
        result = _find_tm_in_folders(proj.get("folders", []), tm_id)
        if result is not None:
            return result
    return None

def _find_tm_in_folders(folders: list, tm_id: int):
    for f in folders:
        for tm in f.get("tms", []):
            if tm.get("tm_id") == tm_id:
                return tm.get("is_active")
        result = _find_tm_in_folders(f.get("children", []), tm_id)
        if result is not None:
            return result
    return None

# ============================================================================
# CLI Parser
# ============================================================================

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1]
    args = sys.argv[2:]

    if cmd == "status":
        cmd_status()
    elif cmd == "platforms":
        cmd_platforms()
    elif cmd == "projects":
        cmd_projects(int(args[0]) if args else None)
    elif cmd == "tree":
        cmd_tree(args[0] if args else None)
    elif cmd == "folders":
        cmd_folder_list(int(args[0]))
    elif cmd == "files":
        cmd_files(int(args[0]))
    elif cmd == "rows":
        cmd_rows(int(args[0]), int(args[1]) if len(args) > 1 else 10)
    elif cmd == "row-update":
        cmd_row_update(int(args[0]), args[1])
    elif cmd == "folder-create":
        cmd_folder_create(int(args[0]), args[1])
    elif cmd == "tm":
        if not args:
            cmd_tm_list()
        elif args[0] == "list":
            cmd_tm_list()
        elif args[0] == "tree":
            cmd_tm_tree()
        elif args[0] == "assign":
            cmd_tm_assign(int(args[1]), folder_id=int(args[2]) if len(args) > 2 else None)
        elif args[0] == "activate":
            cmd_tm_activate(int(args[1]))
        elif args[0] == "deactivate":
            cmd_tm_deactivate(int(args[1]))
        elif args[0] == "assignment":
            cmd_tm_assignment(int(args[1]))
        elif args[0] == "search":
            cmd_tm_search(int(args[1]), args[2])
        else:
            print(f"Unknown tm subcommand: {args[0]}")
    elif cmd == "qa":
        if args[0] == "check":
            cmd_qa_check(int(args[1]), args[2] if len(args) > 2 else "all")
    elif cmd == "search":
        cmd_search(args[0], int(args[1]) if len(args) > 1 else None)
    elif cmd == "e2e-tm":
        cmd_e2e_tm()
    else:
        print(f"Unknown command: {cmd}")
        print("Run without args for usage.")

if __name__ == "__main__":
    main()
