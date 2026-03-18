"""
Generate showcase localization data for Phase 42 demo.
Creates 3 files: Excel (.xlsx), TXT (tab-separated), XML (.loc.xml)
Plus a mock TM loader script.
"""
from __future__ import annotations

import os
import sys

# ── Excel: UI Strings ──────────────────────────────────────────────
def generate_excel():
    """Generate showcase_ui_strings.xlsx with xlsxwriter."""
    import xlsxwriter

    path = os.path.join(os.path.dirname(__file__), "showcase_ui_strings.xlsx")
    wb = xlsxwriter.Workbook(path)
    ws = wb.add_worksheet("UI Strings")

    # Header
    headers = ["StringID", "Source", "Translation", "Status", "Translator", "ReviewState"]
    header_fmt = wb.add_format({"bold": True, "bg_color": "#2a2a2a", "font_color": "#ffffff"})
    for i, h in enumerate(headers):
        ws.write(0, i, h, header_fmt)

    rows = [
        ("UI_MENU_FILE", "File", "파일", "Human-Reviewed", "Park_JH", "Approved"),
        ("UI_MENU_EDIT", "Edit", "편집", "Human-Reviewed", "Park_JH", "Approved"),
        ("UI_MENU_VIEW", "View", "보기", "Human-Reviewed", "Park_JH", "Approved"),
        ("UI_MENU_TOOLS", "Tools", "도구", "Human-Reviewed", "Park_JH", "Approved"),
        ("UI_BTN_SAVE", "Save", "저장", "Human-Reviewed", "Kim_YS", "Approved"),
        ("UI_BTN_CANCEL", "Cancel", "취소", "Human-Reviewed", "Kim_YS", "Approved"),
        ("UI_BTN_CONFIRM", "Confirm Translation", "번역 확인", "AI-Translated", "Qwen3-8B", "Needs-Review"),
        ("UI_BTN_SEARCH", "Search All Entries", "모든 항목 검색", "AI-Translated", "Qwen3-8B", "Needs-Review"),
        ("UI_BTN_EXPORT", "Export to Excel", "엑셀로 내보내기", "Machine-Translated", "DeepL", "Needs-Review"),
        ("UI_MSG_WELCOME", "Welcome to the Realm of Stars", "별의 왕국에 오신 것을 환영합니다", "Human-Reviewed", "Lee_MJ", "Approved"),
        ("UI_MSG_LOGOUT", "Are you sure you want to log out?", "정말 로그아웃하시겠습니까?", "Human-Reviewed", "Lee_MJ", "Approved"),
        ("UI_MSG_SAVE_SUCCESS", "Your progress has been saved successfully.", "진행 상황이 성공적으로 저장되었습니다.", "AI-Translated", "Qwen3-8B", "Approved"),
        ("UI_MSG_NO_RESULTS", "No matching results found. Try a different search term.", "일치하는 결과를 찾을 수 없습니다. 다른 검색어를 시도해 보세요.", "AI-Translated", "Qwen3-8B", "Needs-Review"),
        ("UI_TIP_SEARCH", "Press Ctrl+K to open the command palette", "Ctrl+K를 눌러 명령 팔레트를 여세요", "Human-Reviewed", "Kim_YS", "Approved"),
        ("UI_TIP_SHORTCUT", "Use keyboard shortcuts to speed up your workflow", "키보드 단축키를 사용하여 작업 속도를 높이세요", "AI-Translated", "Qwen3-8B", "Approved"),
        ("UI_LABEL_SOURCE", "Source Language", "원본 언어", "Human-Reviewed", "Park_JH", "Approved"),
        ("UI_LABEL_TARGET", "Target Language", "대상 언어", "Human-Reviewed", "Park_JH", "Approved"),
        ("UI_LABEL_STATUS", "Translation Status", "번역 상태", "Human-Reviewed", "Park_JH", "Approved"),
        ("UI_LABEL_PROGRESS", "Translation Progress", "번역 진행률", "Machine-Translated", "DeepL", "Needs-Review"),
        ("UI_LABEL_TM_MATCH", "Translation Memory Match", "번역 메모리 일치", "Machine-Translated", "DeepL", "Needs-Review"),
        ("UI_ERR_CONNECTION", "Connection to server lost. Retrying...", "서버 연결이 끊어졌습니다. 재시도 중...", "Human-Reviewed", "Lee_MJ", "Approved"),
        ("UI_ERR_PERMISSION", "You do not have permission to edit this file.", "이 파일을 편집할 권한이 없습니다.", "AI-Translated", "Qwen3-8B", "Approved"),
        ("UI_DIALOG_DELETE", "This action cannot be undone. Delete permanently?", "이 작업은 취소할 수 없습니다. 영구적으로 삭제하시겠습니까?", "Human-Reviewed", "Kim_YS", "Approved"),
        ("UI_TOAST_COPIED", "Copied to clipboard", "클립보드에 복사됨", "Human-Reviewed", "Kim_YS", "Approved"),
        ("UI_LOADING_AI", "Generating AI translation suggestion...", "AI 번역 제안을 생성하는 중...", "AI-Translated", "Qwen3-8B", "Needs-Review"),
        ("UI_BADGE_NEW", "New", "신규", "Human-Reviewed", "Park_JH", "Approved"),
        ("UI_BADGE_REVIEWED", "Reviewed", "검토 완료", "Human-Reviewed", "Park_JH", "Approved"),
        ("UI_BADGE_LOCKED", "Locked by another translator", "다른 번역가가 잠금 중", "Machine-Translated", "DeepL", "Needs-Review"),
    ]

    for i, (sid, src, tgt, status, translator, review) in enumerate(rows, start=1):
        ws.write(i, 0, sid)
        ws.write(i, 1, src)
        ws.write(i, 2, tgt)
        ws.write(i, 3, status)
        ws.write(i, 4, translator)
        ws.write(i, 5, review)

    # Column widths
    ws.set_column(0, 0, 25)
    ws.set_column(1, 1, 45)
    ws.set_column(2, 2, 45)
    ws.set_column(3, 3, 18)
    ws.set_column(4, 4, 15)
    ws.set_column(5, 5, 15)

    wb.close()
    print(f"  Excel: {path} ({len(rows)} rows)")
    return rows


# ── TXT: Character Dialogue ────────────────────────────────────────
def generate_txt():
    """Generate showcase_dialogue.txt as tab-separated with 7+ columns for txt_handler."""
    path = os.path.join(os.path.dirname(__file__), "showcase_dialogue.txt")

    # TXT handler expects: cols 0-4 = StringID parts, col 5 = source, col 6 = target
    # We'll use: col0=StringID, col1-4=empty, col5=source, col6=target
    lines = [
        ("DLG_VARON_001", "", "", "", "", "The stars speak of a great darkness approaching.", "별들이 다가오는 거대한 어둠에 대해 이야기합니다."),
        ("DLG_VARON_002", "", "", "", "", "I have guarded this village for three hundred years. I will not abandon it now.", "나는 300년간 이 마을을 지켜왔습니다. 지금 포기하지 않겠습니다."),
        ("DLG_VARON_003", "", "", "", "", "The Blackstar Sword was forged in an age when gods still walked among mortals.", "흑성검은 신들이 아직 필멸자들 사이를 걸어다니던 시대에 단조되었습니다."),
        ("DLG_VARON_004", "", "", "", "", "Trust is earned through deeds, not words, young one.", "신뢰는 말이 아닌 행동으로 얻는 것이다, 젊은이여."),
        ("DLG_VARON_005", "", "", "", "", "When the last star falls, even the elders must fight.", "마지막 별이 떨어질 때, 장로들도 싸워야 합니다."),
        ("DLG_KIRA_001", "", "", "", "", "My arrows never miss. Want me to prove it?", "내 화살은 절대 빗나가지 않아. 증명해 볼까?"),
        ("DLG_KIRA_002", "", "", "", "", "The forest has eyes, and they are watching us.", "숲에는 눈이 있고, 그들이 우리를 지켜보고 있어."),
        ("DLG_KIRA_003", "", "", "", "", "I scout ahead. Stay close and stay quiet.", "내가 앞서 정찰할게. 가까이 있고 조용히 해."),
        ("DLG_KIRA_004", "", "", "", "", "Drakmar's spells leave traces in the air. I can track him.", "드라크마르의 주문은 공기 중에 흔적을 남겨. 추적할 수 있어."),
        ("DLG_KIRA_005", "", "", "", "", "Even the swiftest arrow cannot outrun fate.", "가장 빠른 화살도 운명을 앞지를 수는 없어."),
        ("DLG_GRIMJAW_001", "", "", "", "", "This blade needs more fire. Bring me volcanic ore.", "이 칼날에 불이 더 필요해. 화산 광석을 가져와."),
        ("DLG_GRIMJAW_002", "", "", "", "", "I forged the Moonstone Amulet during the Third Eclipse.", "나는 세 번째 일식 때 월석 부적을 단조했다."),
        ("DLG_GRIMJAW_003", "", "", "", "", "Every weapon tells a story. This hammer has told a thousand.", "모든 무기에는 이야기가 있어. 이 망치는 천 개의 이야기를 했지."),
        ("DLG_GRIMJAW_004", "", "", "", "", "Steel remembers the hand that shaped it.", "강철은 자신을 만든 손을 기억한다."),
        ("DLG_GRIMJAW_005", "", "", "", "", "The forge burns eternal. As long as it does, hope remains.", "대장간의 불은 영원히 타오른다. 그것이 타오르는 한, 희망은 남아 있다."),
        ("DLG_LUNE_001", "", "", "", "", "I mapped every shadow in the Forgotten Fortress.", "나는 잊혀진 요새의 모든 그림자를 지도에 기록했어."),
        ("DLG_LUNE_002", "", "", "", "", "Information is the sharpest weapon. Remember that.", "정보가 가장 날카로운 무기야. 기억해."),
        ("DLG_LUNE_003", "", "", "", "", "Three routes to the summit. Two are trapped. Choose wisely.", "정상으로 가는 세 갈래 길. 둘은 함정이야. 현명하게 선택해."),
        ("DLG_LUNE_004", "", "", "", "", "The merchant guild knows more than they reveal.", "상인 길드는 드러내는 것보다 더 많은 것을 알고 있어."),
        ("DLG_LUNE_005", "", "", "", "", "Every map I draw brings us closer to the truth.", "내가 그리는 모든 지도는 우리를 진실에 더 가까이 데려다줘."),
        ("DLG_DRAKMAR_001", "", "", "", "", "The ancient spells are not lost. They are hidden.", "고대의 주문은 잃어버린 것이 아니다. 숨겨져 있을 뿐이다."),
        ("DLG_DRAKMAR_002", "", "", "", "", "Power without wisdom is a curse, not a blessing.", "지혜 없는 힘은 축복이 아니라 저주다."),
        ("DLG_DRAKMAR_003", "", "", "", "", "I sense dark magic emanating from the eastern ruins.", "동쪽 폐허에서 어둠의 마법이 흘러나오는 것을 감지합니다."),
        ("DLG_DRAKMAR_004", "", "", "", "", "The Plague Cure requires ingredients from all five regions.", "역병 치료제에는 다섯 지역 모두의 재료가 필요합니다."),
        ("DLG_DRAKMAR_005", "", "", "", "", "When magic fades from this world, so does all that we cherish.", "이 세상에서 마법이 사라지면, 우리가 소중히 여기는 모든 것도 사라집니다."),
        ("DLG_VARON_006", "", "", "", "", "The Moonstone Amulet protects its bearer from shadow corruption.", "월석 부적은 착용자를 그림자 부패로부터 보호합니다."),
        ("DLG_KIRA_006", "", "", "", "", "We move at dawn. Pack light — speed is our advantage.", "새벽에 이동해. 가볍게 챙겨 — 속도가 우리의 장점이야."),
        ("DLG_GRIMJAW_006", "", "", "", "", "The Blackstar Sword... I forged it with tears of a dying star.", "흑성검... 나는 그것을 죽어가는 별의 눈물로 단조했다."),
    ]

    with open(path, "w", encoding="utf-8") as f:
        for parts in lines:
            f.write("\t".join(parts) + "\n")

    print(f"  TXT:   {path} ({len(lines)} lines)")
    return lines


# ── XML: Item/Character/Skill Strings ──────────────────────────────
def generate_xml():
    """Generate showcase_items.loc.xml with LocStr elements."""
    path = os.path.join(os.path.dirname(__file__), "showcase_items.loc.xml")

    entries = [
        # Items — names
        ("ITEM_BLACKSTAR_SWORD_NAME", "Blackstar Sword", "흑성검"),
        ("ITEM_MOONSTONE_AMULET_NAME", "Moonstone Amulet", "월석 부적"),
        ("ITEM_PLAGUE_CURE_NAME", "Plague Cure", "역병 치료제"),
        ("ITEM_VOLCANIC_ORE_NAME", "Volcanic Ore", "화산 광석"),
        ("ITEM_SHADOW_ESSENCE_NAME", "Shadow Essence", "그림자 정수"),
        ("ITEM_STARLIGHT_SHARD_NAME", "Starlight Shard", "별빛 파편"),
        ("ITEM_ELDER_SCROLL_NAME", "Elder Scroll of Wisdom", "지혜의 장로 두루마리"),
        # Items — descriptions (with <br/> tags)
        ("ITEM_BLACKSTAR_SWORD_DESC", "A blade forged in the heart of a dying star.&lt;br/&gt;Its edge cuts through both flesh and shadow.&lt;br/&gt;Only those deemed worthy may wield it.", "죽어가는 별의 심장에서 단조된 검.&lt;br/&gt;그 날은 살과 그림자를 모두 베어냅니다.&lt;br/&gt;자격이 있다고 인정된 자만이 휘두를 수 있습니다."),
        ("ITEM_MOONSTONE_AMULET_DESC", "Crafted during the Third Eclipse by the master smith Grimjaw.&lt;br/&gt;Protects its bearer from shadow corruption.&lt;br/&gt;Glows faintly under starlight.", "대장장이 그림죠가 세 번째 일식 때 만든 부적.&lt;br/&gt;착용자를 그림자 부패로부터 보호합니다.&lt;br/&gt;별빛 아래에서 희미하게 빛납니다."),
        ("ITEM_PLAGUE_CURE_DESC", "A rare potion that cures the Shadow Plague.&lt;br/&gt;Requires ingredients from all five regions.&lt;br/&gt;Drakmar holds the only known recipe.", "그림자 역병을 치료하는 희귀한 물약.&lt;br/&gt;다섯 지역 모두의 재료가 필요합니다.&lt;br/&gt;드라크마르만이 유일한 제조법을 가지고 있습니다."),
        # Characters
        ("CHAR_VARON_NAME", "Elder Varon", "장로 바론"),
        ("CHAR_VARON_TITLE", "Guardian of the Realm", "왕국의 수호자"),
        ("CHAR_KIRA_NAME", "Kira", "키라"),
        ("CHAR_KIRA_TITLE", "Shadow Ranger", "그림자 레인저"),
        ("CHAR_GRIMJAW_NAME", "Grimjaw", "그림죠"),
        ("CHAR_GRIMJAW_TITLE", "Master Blacksmith", "대장장이 장인"),
        ("CHAR_LUNE_NAME", "Lune", "루네"),
        ("CHAR_LUNE_TITLE", "Cartographer Scout", "지도 제작 정찰병"),
        ("CHAR_DRAKMAR_NAME", "Drakmar", "드라크마르"),
        ("CHAR_DRAKMAR_TITLE", "Arcane Scholar", "비전 학자"),
        # Regions
        ("REGION_BLACKSTAR_NAME", "Blackstar Village", "흑성 마을"),
        ("REGION_FORTRESS_NAME", "Forgotten Fortress", "잊혀진 요새"),
        ("REGION_IRONPEAK_NAME", "Ironpeak Mountains", "철봉 산맥"),
        ("REGION_SHADOWFEN_NAME", "Shadowfen Marshes", "그림자 늪지"),
        ("REGION_STARFALL_NAME", "Starfall Crater", "별 떨어진 분화구"),
        # Skills
        ("SKILL_STARFALL_STRIKE_NAME", "Starfall Strike", "별 떨어지는 일격"),
        ("SKILL_STARFALL_STRIKE_DESC", "Channels the power of falling stars to deliver a devastating blow.&lt;br/&gt;Damage increases with each consecutive hit.&lt;br/&gt;Cooldown: 12 seconds.", "떨어지는 별의 힘을 모아 파괴적인 일격을 가합니다.&lt;br/&gt;연속 타격마다 피해가 증가합니다.&lt;br/&gt;재사용 대기시간: 12초."),
        ("SKILL_SHADOW_STEP_NAME", "Shadow Step", "그림자 걸음"),
        ("SKILL_SHADOW_STEP_DESC", "Teleport through shadows to a nearby location.&lt;br/&gt;Grants brief invisibility after teleport.", "그림자를 통해 근처 위치로 순간이동합니다.&lt;br/&gt;순간이동 후 짧은 투명 효과를 부여합니다."),
    ]

    lines = ['<?xml version="1.0" encoding="utf-8"?>', "<LanguageData>"]
    for sid, eng, kr in entries:
        lines.append(f'  <LocStr StringID="{sid}" StrOrigin="{eng}" Str="{kr}"/>')
    lines.append("</LanguageData>")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"  XML:   {path} ({len(entries)} entries)")
    return entries


if __name__ == "__main__":
    print("Generating showcase localization data...")
    excel_rows = generate_excel()
    txt_lines = generate_txt()
    xml_entries = generate_xml()
    total = len(excel_rows) + len(txt_lines) + len(xml_entries)
    print(f"\nTotal: {total} strings across 3 files")
