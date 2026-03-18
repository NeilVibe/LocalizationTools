"""
Mock TM Loader for Phase 42 Showcase Demo.

Creates:
1. "Showcase Demo" project (if not exists)
2. Uploads 3 mock files (xlsx, txt, xml)
3. Creates "Showcase TM" with 30+ entries (exact, fuzzy, semantic)

Usage: python3 server/tools/ldm/services/mock_tm_loader.py
"""
from __future__ import annotations

import os
import sys
import json
import requests
from loguru import logger

API_BASE = "http://localhost:8888"
USERNAME = "admin"
PASSWORD = "admin123"

FIXTURES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))),
    "tests", "fixtures", "mock_gamedata", "localization"
)


def login() -> str:
    """Authenticate and return access token."""
    r = requests.post(f"{API_BASE}/api/auth/login", json={"username": USERNAME, "password": PASSWORD})
    r.raise_for_status()
    token = r.json()["access_token"]
    logger.info(f"Authenticated as {USERNAME}")
    return token


def get_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def find_or_create_project(token: str, name: str = "Showcase Demo") -> int:
    """Find existing or create new project."""
    h = get_headers(token)
    projects = requests.get(f"{API_BASE}/api/ldm/projects", headers=h).json()
    for p in projects:
        if p.get("name") == name:
            logger.info(f"Project '{name}' already exists (id={p['id']})")
            return p["id"]

    # Get first platform
    platforms = requests.get(f"{API_BASE}/api/ldm/platforms", headers=h).json()
    platform_list = platforms.get("platforms", platforms) if isinstance(platforms, dict) else platforms
    platform_id = None
    for p in platform_list:
        if p.get("name") != "Offline Storage":
            platform_id = p["id"]
            break

    r = requests.post(
        f"{API_BASE}/api/ldm/projects",
        headers=h,
        json={"name": name, "description": "3-format showcase for LDM demo", "platform_id": platform_id}
    )
    r.raise_for_status()
    pid = r.json()["id"]
    logger.info(f"Created project '{name}' (id={pid})")
    return pid


def upload_file(token: str, project_id: int, filepath: str, **kwargs) -> int | None:
    """Upload a file to the project. Returns file_id or None."""
    h = get_headers(token)
    filename = os.path.basename(filepath)

    # Check if already uploaded
    files = requests.get(f"{API_BASE}/api/ldm/projects/{project_id}/files", headers=h).json()
    for f in files:
        if f.get("original_filename") == filename or f.get("name") == filename:
            logger.info(f"File '{filename}' already uploaded (id={f['id']})")
            return f["id"]

    data = {"project_id": str(project_id), "storage": "server", **{k: str(v) for k, v in kwargs.items()}}
    with open(filepath, "rb") as fp:
        r = requests.post(
            f"{API_BASE}/api/ldm/files/upload",
            headers=h,
            files={"file": (filename, fp)},
            data=data
        )

    if r.status_code == 200:
        fid = r.json().get("id")
        logger.info(f"Uploaded '{filename}' (id={fid})")
        return fid
    else:
        logger.error(f"FAILED to upload '{filename}': {r.status_code} {r.text[:200]}")
        return None


def find_or_create_tm(token: str, name: str = "Showcase TM") -> int:
    """Find existing or create TM."""
    h = get_headers(token)
    tms = requests.get(f"{API_BASE}/api/ldm/tm", headers=h).json()
    tm_list = tms if isinstance(tms, list) else tms.get("tms", [])
    for tm in tm_list:
        if tm.get("name") == name:
            logger.info(f"TM '{name}' already exists (id={tm['id']})")
            return tm["id"]

    r = requests.post(
        f"{API_BASE}/api/ldm/tm",
        headers=h,
        json={"name": name, "source_language": "en", "target_language": "ko", "description": "Showcase demo TM with exact/fuzzy/semantic entries"}
    )
    r.raise_for_status()
    tid = r.json()["id"]
    logger.info(f"Created TM '{name}' (id={tid})")
    return tid


def load_tm_entries(token: str, tm_id: int):
    """Load 30+ TM entries with exact, fuzzy, and semantic matches."""
    h = {**get_headers(token), "Content-Type": "application/json"}

    # Check existing entry count
    r = requests.get(f"{API_BASE}/api/ldm/tm/{tm_id}", headers=h)
    if r.ok:
        info = r.json()
        count = info.get("entry_count", 0)
        if count >= 30:
            logger.info(f"TM already has {count} entries, skipping")
            return

    entries = [
        # ── Exact matches (10) ──
        {"source": "Welcome to the Realm of Stars", "target": "별의 왕국에 오신 것을 환영합니다", "context": "UI"},
        {"source": "Save", "target": "저장", "context": "UI"},
        {"source": "Cancel", "target": "취소", "context": "UI"},
        {"source": "Confirm Translation", "target": "번역 확인", "context": "UI"},
        {"source": "Blackstar Sword", "target": "흑성검", "context": "Item"},
        {"source": "Moonstone Amulet", "target": "월석 부적", "context": "Item"},
        {"source": "Plague Cure", "target": "역병 치료제", "context": "Item"},
        {"source": "Elder Varon", "target": "장로 바론", "context": "Character"},
        {"source": "Shadow Ranger", "target": "그림자 레인저", "context": "Character"},
        {"source": "Starfall Strike", "target": "별 떨어지는 일격", "context": "Skill"},

        # ── Fuzzy matches (10) — similar but not identical ──
        {"source": "Welcome to the Realm of the Stars", "target": "별들의 왕국에 오신 것을 환영합니다", "context": "UI"},
        {"source": "Save All Changes", "target": "모든 변경 사항 저장", "context": "UI"},
        {"source": "Cancel Edit", "target": "편집 취소", "context": "UI"},
        {"source": "The Blackstar Blade", "target": "흑성 칼날", "context": "Item"},
        {"source": "Amulet of Moonstone", "target": "월석의 부적", "context": "Item"},
        {"source": "Cure for the Plague", "target": "역병의 치료법", "context": "Item"},
        {"source": "Varon the Elder", "target": "장로 바론", "context": "Character"},
        {"source": "Kira the Shadow Ranger", "target": "그림자 레인저 키라", "context": "Character"},
        {"source": "Grimjaw the Blacksmith", "target": "대장장이 그림죠", "context": "Character"},
        {"source": "Strike of the Falling Stars", "target": "떨어지는 별들의 일격", "context": "Skill"},

        # ── Semantic matches (10) — same meaning, different words ──
        {"source": "Greetings, traveler! You have arrived at the Star Kingdom.", "target": "인사드립니다, 여행자여! 별의 왕국에 도착하셨습니다.", "context": "UI"},
        {"source": "Store your work", "target": "작업을 저장하세요", "context": "UI"},
        {"source": "Abort current operation", "target": "현재 작업을 중단합니다", "context": "UI"},
        {"source": "A legendary sword infused with stellar energy", "target": "별의 에너지가 깃든 전설의 검", "context": "Item"},
        {"source": "A protective charm crafted from lunar stones", "target": "달의 돌로 만들어진 보호 부적", "context": "Item"},
        {"source": "An antidote against the dark pestilence", "target": "어둠의 전염병에 대한 해독제", "context": "Item"},
        {"source": "The wise elder who protects the village", "target": "마을을 지키는 지혜로운 장로", "context": "Character"},
        {"source": "A swift archer who moves through shadows", "target": "그림자 속을 움직이는 빠른 궁수", "context": "Character"},
        {"source": "Master of the forge and ancient metalwork", "target": "대장간과 고대 금속 세공의 달인", "context": "Character"},
        {"source": "A devastating attack powered by celestial energy", "target": "천체 에너지로 구동되는 파괴적인 공격", "context": "Skill"},

        # ── Bonus entries for richer demo ──
        {"source": "Search All Entries", "target": "모든 항목 검색", "context": "UI"},
        {"source": "Export to Excel", "target": "엑셀로 내보내기", "context": "UI"},
        {"source": "Shadow Essence", "target": "그림자 정수", "context": "Item"},
        {"source": "Volcanic Ore", "target": "화산 광석", "context": "Item"},
        {"source": "Blackstar Village", "target": "흑성 마을", "context": "Region"},
    ]

    success = 0
    for entry in entries:
        r = requests.post(
            f"{API_BASE}/api/ldm/tm/{tm_id}/entries",
            headers=h,
            json=entry
        )
        if r.ok:
            success += 1
        else:
            logger.warning(f"Entry failed: {r.status_code} - {entry['source'][:40]}")

    logger.info(f"Loaded {success}/{len(entries)} TM entries")


def main():
    logger.info("=" * 60)
    logger.info("Phase 42 — Showcase Demo Data Loader")
    logger.info("=" * 60)

    # 1. Auth
    logger.info("1. Authentication")
    token = login()

    # 2. Project
    logger.info("2. Project Setup")
    project_id = find_or_create_project(token)

    # 3. Upload files
    logger.info("3. File Uploads")
    xlsx_path = os.path.join(FIXTURES_DIR, "showcase_ui_strings.xlsx")
    txt_path = os.path.join(FIXTURES_DIR, "showcase_dialogue.txt")
    xml_path = os.path.join(FIXTURES_DIR, "showcase_items.loc.xml")

    upload_file(token, project_id, xlsx_path, source_col=1, target_col=2, stringid_col=0, has_header="true")
    upload_file(token, project_id, txt_path)
    upload_file(token, project_id, xml_path)

    # 4. TM
    logger.info("4. Translation Memory")
    tm_id = find_or_create_tm(token)
    load_tm_entries(token, tm_id)

    # 5. Verify
    logger.info("5. Verification")
    h = get_headers(token)
    files = requests.get(f"{API_BASE}/api/ldm/projects/{project_id}/files", headers=h).json()
    logger.info(f"Files in project: {len(files)}")
    for f in files:
        logger.info(f"  - {f['name']} ({f.get('row_count', '?')} rows, {f.get('format', '?')})")

    tm_info = requests.get(f"{API_BASE}/api/ldm/tm/{tm_id}", headers=h).json()
    logger.info(f"TM entries: {tm_info.get('entry_count', '?')}")

    logger.success("Showcase Demo data loaded successfully!")


if __name__ == "__main__":
    main()
