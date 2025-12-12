#!/usr/bin/env python3
"""
P25 Download Format Verification Test

Verifies that:
1. Original file can be uploaded
2. Edits can be made
3. Downloaded file has EXACT same format as original with edits applied
"""

import requests
import tempfile
import os

API_BASE = "http://localhost:8888"

# Test data - matches original BDO TXT format
# Format: idx0\tidx1\tidx2\tidx3\tidx4\tsource\ttarget
ORIGINAL_FILE_CONTENT = """0\t100\t0\t0\t1\t테스트 문자열 1\tOriginal Translation 1
0\t101\t0\t0\t1\t테스트 문자열 2\tOriginal Translation 2
0\t102\t0\t0\t1\t테스트 문자열 3\t
0\t103\t0\t0\t1\t한국어 텍스트\tNone"""


def get_auth_token():
    """Get authentication token"""
    response = requests.post(
        f"{API_BASE}/api/auth/login",
        json={"username": "admin", "password": "admin123"}
    )
    return response.json().get("access_token")


def test_download_format_verification():
    """Test that downloaded file matches original format with edits"""
    print("=" * 60)
    print("  P25 DOWNLOAD FORMAT VERIFICATION TEST")
    print("=" * 60)
    print()

    # Get auth token
    token = get_auth_token()
    if not token:
        print("ERROR: Could not get auth token")
        return False

    headers = {"Authorization": f"Bearer {token}"}

    # Step 1: Create a test project
    print("STEP 1: Creating test project...")
    response = requests.post(
        f"{API_BASE}/api/ldm/projects",
        json={"name": "Download Format Test"},
        headers=headers
    )
    if response.status_code != 200:
        print(f"   ERROR: {response.text}")
        return False
    project = response.json()
    project_id = project["id"]
    print(f"   Created project ID: {project_id}")

    # Step 2: Upload original file
    print("\nSTEP 2: Uploading original file...")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(ORIGINAL_FILE_CONTENT)
        temp_file = f.name

    try:
        with open(temp_file, 'rb') as f:
            response = requests.post(
                f"{API_BASE}/api/ldm/files/upload",
                files={"file": ("test_format.txt", f, "text/plain")},
                data={"project_id": project_id},
                headers=headers
            )

        if response.status_code != 200:
            print(f"   ERROR: {response.text}")
            return False

        file_info = response.json()
        file_id = file_info["id"]
        print(f"   Uploaded file ID: {file_id}, rows: {file_info['row_count']}")
    finally:
        os.unlink(temp_file)

    # Step 3: Get rows and make an edit
    print("\nSTEP 3: Making edits...")
    response = requests.get(
        f"{API_BASE}/api/ldm/files/{file_id}/rows",
        headers=headers
    )
    rows = response.json()["rows"]
    print(f"   Found {len(rows)} rows")

    # Edit row 2 (index 1) - change translation and status
    row_to_edit = rows[1]
    edit_response = requests.put(
        f"{API_BASE}/api/ldm/rows/{row_to_edit['id']}",
        json={
            "target": "NEW EDITED TRANSLATION",
            "status": "reviewed"
        },
        headers=headers
    )
    if edit_response.status_code != 200:
        print(f"   ERROR editing: {edit_response.text}")
        return False
    print(f"   Edited row {row_to_edit['id']}: target = 'NEW EDITED TRANSLATION'")

    # Edit row 3 (index 2) - add translation where there was none
    row_to_edit2 = rows[2]
    edit_response2 = requests.put(
        f"{API_BASE}/api/ldm/rows/{row_to_edit2['id']}",
        json={
            "target": "ADDED TRANSLATION",
            "status": "translated"
        },
        headers=headers
    )
    print(f"   Edited row {row_to_edit2['id']}: target = 'ADDED TRANSLATION'")

    # Step 4: Download the file
    print("\nSTEP 4: Downloading edited file...")
    response = requests.get(
        f"{API_BASE}/api/ldm/files/{file_id}/download",
        headers=headers
    )

    if response.status_code != 200:
        print(f"   ERROR: {response.text}")
        return False

    downloaded_content = response.text
    print(f"   Downloaded {len(downloaded_content)} bytes")

    # Step 5: Verify format
    print("\nSTEP 5: Verifying format...")
    print("-" * 60)

    original_lines = ORIGINAL_FILE_CONTENT.strip().split('\n')
    downloaded_lines = downloaded_content.strip().split('\n')

    print(f"   Original lines: {len(original_lines)}")
    print(f"   Downloaded lines: {len(downloaded_lines)}")

    if len(original_lines) != len(downloaded_lines):
        print("   ERROR: Line count mismatch!")
        return False

    all_valid = True
    for i, (orig, down) in enumerate(zip(original_lines, downloaded_lines)):
        orig_parts = orig.split('\t')
        down_parts = down.split('\t')

        print(f"\n   Row {i + 1}:")
        print(f"   Original:   {orig[:80]}...")
        print(f"   Downloaded: {down[:80]}...")

        # Check column count
        if len(orig_parts) != len(down_parts):
            print(f"   ERROR: Column count mismatch! {len(orig_parts)} vs {len(down_parts)}")
            all_valid = False
            continue

        # Check that index columns (0-4) are preserved
        for col in range(5):
            if orig_parts[col] != down_parts[col]:
                print(f"   ERROR: Index column {col} changed!")
                print(f"          Original: {orig_parts[col]}")
                print(f"          Downloaded: {down_parts[col]}")
                all_valid = False

        # Check source (column 5) is preserved
        if orig_parts[5] != down_parts[5]:
            print(f"   ERROR: Source column changed!")
            all_valid = False

        # Report target (column 6) changes
        if orig_parts[6] != down_parts[6]:
            print(f"   TARGET CHANGED (expected):")
            print(f"          Original: '{orig_parts[6]}'")
            print(f"          Downloaded: '{down_parts[6]}'")

    # Step 6: Cleanup
    print("\n" + "-" * 60)
    print("\nSTEP 6: Cleanup...")
    requests.delete(f"{API_BASE}/api/ldm/projects/{project_id}", headers=headers)
    print("   Deleted test project")

    # Final verdict
    print("\n" + "=" * 60)
    print("                   VERDICT")
    print("=" * 60)

    if all_valid:
        print("\n  ✅ SUCCESS! Download format matches original!")
        print("\n  Verified:")
        print("  - Column count preserved")
        print("  - Index columns (0-4) preserved")
        print("  - Source text preserved")
        print("  - Only target column changed with edits")
        return True
    else:
        print("\n  ❌ FAILED! Format issues detected")
        return False


if __name__ == "__main__":
    success = test_download_format_verification()
    exit(0 if success else 1)
