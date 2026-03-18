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
    """Load 50+ TM entries with exact, fuzzy, semantic, dialogue, quest, and multi-line matches."""
    h = {**get_headers(token), "Content-Type": "application/json"}

    # Check existing entry count
    r = requests.get(f"{API_BASE}/api/ldm/tm/{tm_id}", headers=h)
    if r.ok:
        info = r.json()
        count = info.get("entry_count", 0)
        if count >= 45:
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

        # ── Multi-line content with <br/> (5) ──
        {"source": "A blade forged in the heart of a dying star.<br/>Its edge cuts through both flesh and shadow.", "target": "죽어가는 별의 심장에서 단조된 검.<br/>그 날은 살과 그림자를 모두 베어냅니다.", "context": "Item"},
        {"source": "The Sealed Library holds ancient knowledge.<br/>Only the Sage Order may enter its halls.", "target": "봉인된 도서관은 고대의 지식을 간직하고 있다.<br/>현자의 결사만이 그 전당에 들어갈 수 있다.", "context": "Region"},
        {"source": "Sacred Flame purifies darkness.<br/>It has been passed down for generations.", "target": "성스러운 불꽃은 어둠을 정화한다.<br/>대대로 전승되어 온 마법이다.", "context": "Skill"},
        {"source": "The mist never lifts in this ancient forest.<br/>Strange creatures lurk in the shadows.", "target": "이 고대 숲에서는 안개가 걷히지 않는다.<br/>기이한 생물들이 그림자 속에 도사리고 있다.", "context": "Region"},
        {"source": "Grimjaw's forge burns day and night.<br/>The sound of his hammer echoes through the village.", "target": "그림죠의 대장간은 밤낮으로 타오른다.<br/>그의 망치 소리가 마을 전체에 울려 퍼진다.", "context": "Dialogue"},

        # ── Dialogue-related entries (5) ──
        {"source": "Welcome to the Sealed Library, traveler.", "target": "봉인된 도서관에 오신 것을 환영합니다, 여행자여.", "context": "Dialogue"},
        {"source": "The Dark Cult grows stronger each day.", "target": "어둠의 교단은 날마다 강해지고 있습니다.", "context": "Dialogue"},
        {"source": "Take this scroll to Elder Varon.", "target": "이 두루마리를 장로 바론에게 가져가세요.", "context": "Dialogue"},
        {"source": "Be careful in the Mist Forest at night.", "target": "밤에 안개의 숲에서는 조심하세요.", "context": "Dialogue"},
        {"source": "The blackstar ore can only be found in the volcanic zone.", "target": "검은별 광석은 화산 지대에서만 찾을 수 있습니다.", "context": "Dialogue"},

        # ── Near-duplicate fuzzy pairs (3, 95%+ match with existing) ──
        {"source": "Welcome to the Realm of the Stars!", "target": "별의 왕국에 오신 것을 환영합니다!", "context": "UI"},
        {"source": "The Blackstar Sword", "target": "흑성검", "context": "Item"},
        {"source": "Elder Varon the Sage", "target": "현자 장로 바론", "context": "Character"},

        # ── Quest context entries (2) ──
        {"source": "Find the ancient scroll in the Sealed Library.", "target": "봉인된 도서관에서 고대 두루마리를 찾으세요.", "context": "Quest"},
        {"source": "Collect volcanic ore for the blacksmith.", "target": "대장장이를 위해 화산 광석을 수집하세요.", "context": "Quest"},
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
