#!/usr/bin/env python3
"""
P11 Platform Stability - Granular Debug Protocol
Tests all core operations: CRUD, trash, restore, offline mode
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8888"

def get_token():
    """Login and get auth token"""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    return resp.json().get("access_token")

def headers(token):
    return {"Authorization": f"Bearer {token}"}

def test_online_mode():
    """Test all operations in ONLINE mode (PostgreSQL)"""
    print("=" * 60)
    print("  P11 STABILITY TEST - ONLINE MODE (PostgreSQL)")
    print("=" * 60)
    print()

    token = get_token()
    if not token:
        print("ERROR: Could not get token")
        return False
    print("✓ Got auth token")

    results = {"passed": 0, "failed": 0, "errors": []}

    # Test 1: Create Platform
    print("\n[TEST 1] Create Platform")
    resp = requests.post(f"{BASE_URL}/api/ldm/platforms",
        headers=headers(token),
        json={"name": "P11 Test Platform", "description": "Stability test"})
    if resp.status_code in [200, 201] and resp.json().get("id"):
        platform_id = resp.json()["id"]
        print(f"  ✓ PASS - Platform ID: {platform_id}")
        results["passed"] += 1
    else:
        print(f"  ✗ FAIL - Status: {resp.status_code}, Body: {resp.text}")
        results["failed"] += 1
        results["errors"].append(f"Create Platform: {resp.status_code} - {resp.text}")
        platform_id = None

    # Test 2: Create Project
    print("\n[TEST 2] Create Project")
    resp = requests.post(f"{BASE_URL}/api/ldm/projects",
        headers=headers(token),
        json={"name": "P11 Test Project", "platform_id": platform_id})
    if resp.status_code == 200 and resp.json().get("id"):
        project_id = resp.json()["id"]
        print(f"  ✓ PASS - Project ID: {project_id}")
        results["passed"] += 1
    else:
        print(f"  ✗ FAIL - {resp.text}")
        results["failed"] += 1
        results["errors"].append(f"Create Project: {resp.text}")
        project_id = None

    # Test 3: Create Folder
    print("\n[TEST 3] Create Folder")
    resp = requests.post(f"{BASE_URL}/api/ldm/folders",
        headers=headers(token),
        json={"name": "P11 Test Folder", "project_id": project_id})
    if resp.status_code == 200 and resp.json().get("id"):
        folder_id = resp.json()["id"]
        print(f"  ✓ PASS - Folder ID: {folder_id}")
        results["passed"] += 1
    else:
        print(f"  ✗ FAIL - {resp.text}")
        results["failed"] += 1
        results["errors"].append(f"Create Folder: {resp.text}")
        folder_id = None

    # Test 4: Upload File
    print("\n[TEST 4] Upload File")
    test_content = "0\t1\t0\t0\t0\tHello World\tBonjour\n0\t2\t0\t0\t0\tGoodbye\tAu revoir\n0\t3\t0\t0\t0\tThank you\tMerci"
    files = {"file": ("test.txt", test_content, "text/plain")}
    data = {"project_id": project_id, "folder_id": folder_id}
    resp = requests.post(f"{BASE_URL}/api/ldm/files/upload",
        headers=headers(token), files=files, data=data)
    if resp.status_code == 200 and resp.json().get("id"):
        file_id = resp.json()["id"]
        row_count = resp.json().get("row_count", 0)
        print(f"  ✓ PASS - File ID: {file_id}, Rows: {row_count}")
        results["passed"] += 1
    else:
        print(f"  ✗ FAIL - {resp.text}")
        results["failed"] += 1
        results["errors"].append(f"Upload File: {resp.text}")
        file_id = None

    # Test 5: Read File Rows
    print("\n[TEST 5] Read File Rows")
    if file_id:
        resp = requests.get(f"{BASE_URL}/api/ldm/files/{file_id}/rows",
            headers=headers(token))
        if resp.status_code == 200:
            rows = resp.json().get("rows", [])
            print(f"  ✓ PASS - Got {len(rows)} rows")
            if rows:
                row_id = rows[0].get("id")
            results["passed"] += 1
        else:
            print(f"  ✗ FAIL - {resp.text}")
            results["failed"] += 1
            results["errors"].append(f"Read Rows: {resp.text}")
            row_id = None
    else:
        print("  ⊘ SKIP - No file to read")
        row_id = None

    # Test 6: Update Row
    print("\n[TEST 6] Update Row")
    if row_id:
        resp = requests.put(f"{BASE_URL}/api/ldm/rows/{row_id}",
            headers=headers(token),
            json={"target": "Bonjour le monde", "status": "reviewed"})
        if resp.status_code == 200 and resp.json().get("status") == "reviewed":
            print(f"  ✓ PASS - Row updated, status: reviewed")
            results["passed"] += 1
        else:
            print(f"  ✗ FAIL - {resp.text}")
            results["failed"] += 1
            results["errors"].append(f"Update Row: {resp.text}")
    else:
        print("  ⊘ SKIP - No row to update")

    # Test 7: Delete File (soft delete to trash)
    print("\n[TEST 7] Delete File (Soft)")
    if file_id:
        resp = requests.delete(f"{BASE_URL}/api/ldm/files/{file_id}",
            headers=headers(token))
        if resp.status_code == 200:
            print(f"  ✓ PASS - File moved to trash")
            results["passed"] += 1
        else:
            print(f"  ✗ FAIL - {resp.text}")
            results["failed"] += 1
            results["errors"].append(f"Delete File: {resp.text}")
    else:
        print("  ⊘ SKIP - No file to delete")

    # Test 8: Check Trash
    print("\n[TEST 8] Check Trash")
    resp = requests.get(f"{BASE_URL}/api/ldm/trash", headers=headers(token))
    if resp.status_code == 200:
        data = resp.json()
        items = data if isinstance(data, list) else data.get("items", [])
        print(f"  ✓ PASS - Trash has {len(items)} items")
        trash_id = items[0].get("id") if items else None
        results["passed"] += 1
    else:
        print(f"  ✗ FAIL - {resp.text}")
        results["failed"] += 1
        results["errors"].append(f"Check Trash: {resp.text}")
        trash_id = None

    # Test 9: Restore from Trash
    print("\n[TEST 9] Restore from Trash")
    restored_file_id = None
    if trash_id:
        resp = requests.post(f"{BASE_URL}/api/ldm/trash/{trash_id}/restore",
            headers=headers(token))
        if resp.status_code == 200:
            # Restore returns {success, message, item_type, restored_id}
            restored_data = resp.json()
            restored_file_id = restored_data.get("restored_id")
            print(f"  ✓ PASS - Item restored (new ID: {restored_file_id})")
            results["passed"] += 1
        else:
            print(f"  ✗ FAIL - {resp.text}")
            results["failed"] += 1
            results["errors"].append(f"Restore: {resp.text}")
    else:
        print("  ⊘ SKIP - No item to restore")

    # Test 10: Verify File Restored
    print("\n[TEST 10] Verify File Restored")
    check_id = restored_file_id or file_id  # Use restored ID if available
    if check_id:
        resp = requests.get(f"{BASE_URL}/api/ldm/files/{check_id}",
            headers=headers(token))
        if resp.status_code == 200 and resp.json().get("id"):
            print(f"  ✓ PASS - File verified: {resp.json().get('name')}")
            results["passed"] += 1
        else:
            print(f"  ✗ FAIL - {resp.text}")
            results["failed"] += 1
            results["errors"].append(f"Verify Restore: {resp.text}")
    else:
        print("  ⊘ SKIP - No file to verify")

    # Test 11: Search
    print("\n[TEST 11] Search")
    resp = requests.get(f"{BASE_URL}/api/ldm/search?q=P11",
        headers=headers(token))
    if resp.status_code == 200:
        count = resp.json().get("count", 0)
        print(f"  ✓ PASS - Search returned {count} results")
        results["passed"] += 1
    else:
        print(f"  ✗ FAIL - {resp.text}")
        results["failed"] += 1
        results["errors"].append(f"Search: {resp.text}")

    # Summary
    print("\n" + "=" * 60)
    print(f"  ONLINE MODE RESULTS: {results['passed']} passed, {results['failed']} failed")
    print("=" * 60)

    if results["errors"]:
        print("\nErrors:")
        for e in results["errors"]:
            print(f"  - {e[:80]}")

    return results["failed"] == 0

def test_offline_mode():
    """Test operations in OFFLINE mode (SQLite)"""
    print("\n" + "=" * 60)
    print("  P11 STABILITY TEST - OFFLINE MODE (SQLite)")
    print("=" * 60)
    print()

    # Use offline token
    offline_token = "OFFLINE_MODE_1234567890"
    h = {"Authorization": f"Bearer {offline_token}"}

    results = {"passed": 0, "failed": 0, "errors": []}

    # Test 1: List local files
    print("[TEST 1] List Local Files")
    resp = requests.get(f"{BASE_URL}/api/ldm/files", headers=h)
    if resp.status_code == 200:
        files_list = resp.json()
        print(f"  ✓ PASS - {len(files_list)} files found")
        results["passed"] += 1
    else:
        print(f"  ✗ FAIL - {resp.status_code}: {resp.text[:100]}")
        results["failed"] += 1
        results["errors"].append(f"List Files: {resp.status_code}")

    # Test 2: Upload to local storage
    print("\n[TEST 2] Upload to Offline Storage")
    test_content = "0\t1\t0\t0\t0\tOffline Test\tTest Hors Ligne\n0\t2\t0\t0\t0\tHello\tBonjour"
    files = {"file": ("offline_test.txt", test_content, "text/plain")}
    data = {"storage": "local"}
    resp = requests.post(f"{BASE_URL}/api/ldm/files/upload", headers=h, files=files, data=data)
    if resp.status_code == 200 and resp.json().get("id"):
        offline_file_id = resp.json()["id"]
        print(f"  ✓ PASS - File ID: {offline_file_id}")
        results["passed"] += 1
    else:
        print(f"  ✗ FAIL - {resp.text[:100]}")
        results["failed"] += 1
        results["errors"].append(f"Upload: {resp.text[:50]}")
        offline_file_id = None

    # Test 3: Get file by ID
    print("\n[TEST 3] Get File by ID")
    if offline_file_id:
        resp = requests.get(f"{BASE_URL}/api/ldm/files/{offline_file_id}", headers=h)
        if resp.status_code == 200 and resp.json().get("id"):
            print(f"  ✓ PASS - File: {resp.json().get('name')}")
            results["passed"] += 1
        else:
            print(f"  ✗ FAIL - {resp.text[:100]}")
            results["failed"] += 1
            results["errors"].append(f"Get File: {resp.text[:50]}")
    else:
        print("  ⊘ SKIP - No file ID")

    # Test 4: Read file rows
    print("\n[TEST 4] Read File Rows")
    if offline_file_id:
        resp = requests.get(f"{BASE_URL}/api/ldm/files/{offline_file_id}/rows", headers=h)
        if resp.status_code == 200:
            rows = resp.json().get("rows", [])
            print(f"  ✓ PASS - {len(rows)} rows found")
            results["passed"] += 1
            offline_row_id = rows[0].get("id") if rows else None
        else:
            print(f"  ✗ FAIL - {resp.text[:100]}")
            results["failed"] += 1
            results["errors"].append(f"Read Rows: {resp.text[:50]}")
            offline_row_id = None
    else:
        print("  ⊘ SKIP - No file ID")
        offline_row_id = None

    # Test 5: Update row
    print("\n[TEST 5] Update Row")
    if offline_row_id:
        resp = requests.put(f"{BASE_URL}/api/ldm/rows/{offline_row_id}",
            headers=h, json={"target": "Test Hors Ligne UPDATED", "status": "reviewed"})
        if resp.status_code == 200:
            print(f"  ✓ PASS - Row updated")
            results["passed"] += 1
        else:
            print(f"  ✗ FAIL - {resp.text[:100]}")
            results["failed"] += 1
            results["errors"].append(f"Update Row: {resp.text[:50]}")
    else:
        print("  ⊘ SKIP - No row ID")

    # Test 6: Delete file (soft)
    print("\n[TEST 6] Delete File (Soft)")
    if offline_file_id:
        resp = requests.delete(f"{BASE_URL}/api/ldm/files/{offline_file_id}", headers=h)
        if resp.status_code == 200:
            print(f"  ✓ PASS - File deleted")
            results["passed"] += 1
        else:
            print(f"  ✗ FAIL - {resp.text[:100]}")
            results["failed"] += 1
            results["errors"].append(f"Delete: {resp.text[:50]}")
    else:
        print("  ⊘ SKIP - No file ID")

    # Test 7: Check trash
    print("\n[TEST 7] Check Trash")
    resp = requests.get(f"{BASE_URL}/api/ldm/trash", headers=h)
    if resp.status_code == 200:
        trash_data = resp.json()
        items = trash_data if isinstance(trash_data, list) else trash_data.get("items", [])
        print(f"  ✓ PASS - Trash has {len(items)} items")
        results["passed"] += 1
    else:
        print(f"  ✗ FAIL - {resp.text[:100]}")
        results["failed"] += 1
        results["errors"].append(f"Trash: {resp.text[:50]}")

    # Summary
    print("\n" + "=" * 60)
    print(f"  OFFLINE MODE RESULTS: {results['passed']} passed, {results['failed']} failed")
    print("=" * 60)

    if results["errors"]:
        print("\nErrors:")
        for e in results["errors"]:
            print(f"  - {e[:80]}")

    return results["failed"] == 0

def check_sync_endpoints():
    """Check what sync endpoints exist"""
    print("\n" + "=" * 60)
    print("  SYNC ENDPOINTS CHECK")
    print("=" * 60)
    print()

    token = get_token()

    endpoints = [
        ("GET", "/api/ldm/offline/subscriptions", "List subscriptions"),
        ("POST", "/api/ldm/offline/subscribe", "Subscribe to item"),
        ("POST", "/api/ldm/offline/push-changes", "Push local changes"),
        ("POST", "/api/ldm/sync-to-central", "Sync to central"),
        ("POST", "/api/ldm/tm/sync-to-central", "Sync TM to central"),
    ]

    print("Sync endpoints available:")
    for method, path, desc in endpoints:
        url = f"{BASE_URL}{path}"
        if method == "GET":
            resp = requests.get(url, headers=headers(token))
        else:
            resp = requests.post(url, headers=headers(token), json={})

        status = "✓" if resp.status_code != 404 else "✗"
        print(f"  {status} {method} {path} - {resp.status_code} ({desc})")

if __name__ == "__main__":
    online_ok = test_online_mode()
    offline_ok = test_offline_mode()
    check_sync_endpoints()

    print("\n" + "=" * 60)
    print("  FINAL SUMMARY")
    print("=" * 60)
    print(f"  Online Mode:  {'PASS' if online_ok else 'FAIL'}")
    print(f"  Offline Mode: {'PASS' if offline_ok else 'FAIL'}")
    print("=" * 60)

    sys.exit(0 if online_ok else 1)
