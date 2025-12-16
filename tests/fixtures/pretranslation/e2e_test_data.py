#!/usr/bin/env python3
"""
E2E Test Data Generator for Pretranslation Tests

Generates ~500 rows of test data for each pretranslation engine,
covering ALL possible cases each logic should handle.

Based on real patterns from:
- sampleofLanguageData.txt
- closetotest.txt
"""

import random


# =============================================================================
# XLS TRANSFER TEST DATA
# =============================================================================

XLS_TRANSFER_CASES = {
    # Case 1: Plain text (no codes)
    "plain_text": [
        ("연금 스킬 경험치가 증가합니다.", "Augmente l'EXP de compétence d'alchimie."),
        ("고급 식용벌꿀 지식을 습득할 수 있습니다.", "Obtention de connaissances : Miel de cuisine."),
        ("카이아 어선 뱃머리", "Proue de bateau de pêche de Kaia"),
        ("해방된 마력의 갑옷", "Armure de magie libérée"),
        ("녹아내린 보석 조각", "Éclat de pierre précieuse fondu"),
        ("단풍나무 각목을 이용해 만든 샹들리에", "Un lustre en bois d'érable"),
        ("특제 곡물 수프", "Soupe de céréales spéciale"),
        ("마고리아 고래 둥근 램프이다", "Une Lampe ronde de Baleine de Margoria"),
    ],

    # Case 2: {Code} at start
    "code_at_start": [
        ("{ItemID}특제 곡물 수프를 획득했습니다", "Vous avez obtenu la Soupe spéciale"),
        ("{Amount}개의 아이템을 획득했습니다", "objets obtenus"),
        ("{NpcName}에게 말을 걸어보세요", "Parlez à"),
        ("{QuestName} 의뢰를 완료했습니다", "Quête terminée"),
        ("{SkillName} 스킬을 습득했습니다", "Compétence acquise"),
    ],

    # Case 3: Multiple codes at start
    "multiple_codes_start": [
        ("{ItemID}{Amount}개의 아이템 획득", "objets obtenus"),
        ("{NpcName}{Location}에서 만나세요", "Rendez-vous à"),
        ("{ItemID}{Grade}{Amount}개 획득", "objets obtenus"),
    ],

    # Case 4: Code in middle of text
    "code_in_middle": [
        ("아이템 {Amount}개를 사용하세요", "Utilisez objets"),
        ("레벨 {Level}에 도달했습니다", "Niveau atteint"),
        ("퀘스트 {QuestID}를 완료하세요", "Terminez la quête"),
    ],

    # Case 5: <PAColor> at start (without PAOldColor)
    "pacolor_start": [
        ("<PAColor>경고 메시지입니다", "Message d'avertissement"),
        ("<PAColor>중요한 정보", "Information importante"),
    ],

    # Case 6: <PAColor0xHEX> with hex code
    "pacolor_hex": [
        ("<PAColor0xffe9bd23>2시간 동안 행운 잠재력을 1단계<PAOldColor>", "Chance +1 pendant 2 heures"),
        ("<PAColor0xffe9bd23>세트 효과 발동<PAOldColor>", "Bonus de set activé"),
        ("<PAColor0xFFf3d900>사용 방법<PAOldColor>", "Utilisation"),
        ("<PAColor0xff00c0ff>아이템 효과<PAOldColor>", "Effet d'objet"),
        ("<PAColor0xffb793ff>강화할 수 있습니다<PAOldColor>", "Peut être optimisé"),
    ],

    # Case 7: Color wrapper with text before
    "color_wrapper_with_prefix": [
        ("짐칸 : <PAColor0xffe9bd23>11칸<PAOldColor>", "Emplacements : 11"),
        ("가속 : <PAColor0xffe9bd23>100%<PAOldColor>", "Accélération : 100%"),
        ("속도 : <PAColor0xffe9bd23>115%<PAOldColor>", "Vitesse : 115%"),
        ("지속 시간 : <PAColor0xffe9bd23>90분<PAOldColor>", "Durée : 90 min"),
        ("재사용 시간 : <PAColor0xffe9bd23>30분<PAOldColor>", "Temps de recharge : 30 min"),
    ],

    # Case 8: Multiple PAColor segments
    "multiple_pacolor": [
        ("짐칸 : <PAColor0xffe9bd23>11칸<PAOldColor>, 가속 : <PAColor0xffe9bd23>100%<PAOldColor>",
         "Emplacements : 11, Accélération : 100%"),
        ("<PAColor0xffe9bd23>숙련 Lv.9<PAOldColor> 이상이면 <PAColor0xffe9bd23>미트 파스타<PAOldColor>를 제작",
         "Niveau Qualifié 9 ou supérieur pour préparer des Pâtes"),
    ],

    # Case 9: {TextBind} codes
    "textbind_codes": [
        ("{TextBind:CLICK_ON_RMB_ONLY}해서 사용", "Cliquez pour utiliser"),
        ("{TextBind:USING_CLICK_RMB} 사용하세요", "Utilisez"),
        ("{TextBind:REGISTER_PALETTE_CLICK_RMB} 사용하면 된다", "Utilisation"),
        ("가방을 열어 {TextBind:CLICK_ON_RMB} 팔레트가 열린다", "Ouvrez l'inventaire, la palette s'ouvre"),
    ],

    # Case 10: Mixed codes and colors
    "mixed_codes_colors": [
        ("{TextBind:CLICK_ON_RMB_ONLY}해서 <PAColor0xffe9bd23>선착장<PAOldColor>으로 이동",
         "Cliquez pour rejoindre les quais"),
        ("<PAColor0xffe9bd23>{TextBind:USING_CLICK_RMB}<PAOldColor> 강화를 진행",
         "pour commencer l'optimisation"),
    ],

    # Case 11: Text with newlines
    "with_newlines": [
        ("첫 번째 줄\\n두 번째 줄", "Première ligne\\nDeuxième ligne"),
        ("효과\\n- 행운 +1\\n- 속도 +10%", "Effet\\n- Chance +1\\n- Vitesse +10%"),
        ("사용 방법\\n1. 클릭\\n2. 확인", "Utilisation\\n1. Cliquer\\n2. Confirmer"),
    ],

    # Case 12: _x000D_ removal
    "x000d_removal": [
        ("텍스트_x000D_가 있습니다", "Texte présent"),
        ("여러_x000D_줄_x000D_입니다", "Plusieurs lignes"),
    ],

    # Case 13: Complex real-world examples
    "complex_real": [
        (
            "화산암 장식이 된 서랍장이다. 사용 시 <PAColor0xffe9bd23>2시간 동안 행운 잠재력을 1단계<PAOldColor> 높여준다.\\n- <PAColor0xffe9bd23>9 세트 효과 : 인테리어 포인트 +500<PAOldColor>",
            "Une commode ornée de roches volcaniques. Chance +1 pendant 2 heures en cas d'utilisation.\\n– Bonus de set 9 pièces : points d'intérieur +500"
        ),
        (
            "마을의 선착장에서 찾을 수 있는 소유권을 증명함.\\n- 짐칸 : <PAColor0xffe9bd23>11칸<PAOldColor>\\n{TextBind:CLICK_ON_RMB_ONLY}해서 이동",
            "Certificat de propriété.\\n– Emplacements : 11\\nCliquez pour rejoindre"
        ),
    ],
}


# =============================================================================
# KR SIMILAR TEST DATA
# =============================================================================

KR_SIMILAR_CASES = {
    # Case 1: Plain text (no markers)
    "plain_text": [
        ("안녕하세요, 모험가님.", "Hello, adventurer."),
        ("오늘 날씨가 좋습니다.", "The weather is nice today."),
        ("마을에 오신 것을 환영합니다.", "Welcome to the village."),
        ("무엇을 도와드릴까요?", "How can I help you?"),
        ("조심히 가세요.", "Take care."),
    ],

    # Case 2: Single triangle marker
    "single_triangle": [
        ("▶안녕하세요, 모험가님.", "Hello, adventurer."),
        ("▶무엇을 찾으시나요?", "What are you looking for?"),
        ("▶이 물건을 가져다 주세요.", "Please bring me this item."),
    ],

    # Case 3: Multiple triangle markers (multi-line dialogue)
    "multiple_triangles": [
        (
            "▶첫 번째 대사입니다.\\n▶두 번째 대사입니다.\\n▶세 번째 대사입니다.",
            "First line.\\nSecond line.\\nThird line."
        ),
        (
            "▶네. 선생님,\\n오늘도 촌장님께선 파란 안개꽃을 사가셨습니다.\\n▶어디로 갔는지 아시냐고요?",
            "Yes, teacher.\\nThe village chief bought blue flowers again today.\\nDo you know where he went?"
        ),
        (
            "▶무슨 일이 있어도 꼭 가셔요.\\n▶심지어 지난번에 산군이 창귀를 마을까지 끌고왔을 때 있잖아요?",
            "You must go no matter what.\\nRemember when the mountain spirit brought the ghost to the village?"
        ),
    ],

    # Case 4: With <Scale> tags
    "scale_tags": [
        ("<Scale:1.2>중요한 텍스트<Scale:1>", "Important text"),
        ("<Scale:1.5>크게 표시<Scale:1>", "Display large"),
        ("일반 텍스트 <Scale:1.2>강조<Scale:1> 일반", "Normal text emphasized normal"),
    ],

    # Case 5: With <color> tags
    "color_tags": [
        ("<color:1,0.7,0.2,1>황금색 텍스트<color:1,1,1,1>", "Golden text"),
        ("<color:1,0,0,1>빨간색 경고<color:1,1,1,1>", "Red warning"),
        ("일반 <color:0,1,0,1>녹색<color:1,1,1,1> 텍스트", "Normal green text"),
    ],

    # Case 6: Mixed Scale and color
    "mixed_scale_color": [
        (
            "<Scale:1.2><color:1,0.7,0.2,1>강조된 황금색<color:1,1,1,1><Scale:1>",
            "Emphasized golden"
        ),
        (
            "▶이 자는 <Scale:1.2><color:1,0.7,0.2,1>돈 욕심<color:1,1,1,1><Scale:1>이라고는 없는 자요.",
            "This person has no greed for money."
        ),
    ],

    # Case 7: Triangle with mixed tags
    "triangle_with_tags": [
        (
            "▶죄인은 무단으로 <Scale:1.2><color:1,0.7,0.2,1>뱀<color:1,1,1,1><Scale:1>을 양식하였다!",
            "The criminal raised snakes without permission!"
        ),
        (
            "▶그 덕에 관청에 허가받은 <Scale:1.2><color:1,0.7,0.2,1>땅꾼<color:1,1,1,1><Scale:1>들이 배를 곯았다!",
            "Because of that, the licensed hunters went hungry!"
        ),
    ],

    # Case 8: Empty lines in structure
    "empty_lines": [
        ("첫 번째\\n\\n세 번째", "First\\n\\nThird"),
        ("▶대사1\\n\\n▶대사2", "Dialogue1\\n\\nDialogue2"),
    ],

    # Case 9: Structure adaptation cases (different line counts)
    "structure_adaptation": [
        # Source has 2 lines, translation is 1 long sentence
        ("첫 번째 문장.\\n두 번째 문장.", "First sentence. Second sentence."),
        # Source has 3 lines
        ("첫째.\\n둘째.\\n셋째.", "First. Second. Third."),
        # Source has 4 lines
        ("하나.\\n둘.\\n셋.\\n넷.", "One. Two. Three. Four."),
    ],

    # Case 10: Complex multi-line with all features
    "complex_multiline": [
        (
            "▶죄인은 푸줏간 백정 변가놈과 공모하여, 무단으로 <Scale:1.2><color:1,0.7,0.2,1>뱀<color:1,1,1,1><Scale:1>을 양식하였다!\\n▶그 덕에 관청에 허가받은 <Scale:1.2><color:1,0.7,0.2,1>땅꾼<color:1,1,1,1><Scale:1>들이 배를 곯았다!\\n▶현감 나으리. 딱히 이자를 두둔하려는 건 아니오나.",
            "The criminal conspired with the butcher to raise snakes!\\nBecause of that, the licensed hunters went hungry!\\nYour Honor, I'm not defending him."
        ),
    ],
}


# =============================================================================
# STANDARD TM TEST DATA (5-Tier Cascade)
# =============================================================================

TM_STANDARD_CASES = {
    # Case 1: Exact match (100%)
    "exact_match": [
        ("저장하시겠습니까?", "Voulez-vous sauvegarder ?"),
        ("취소", "Annuler"),
        ("확인", "Confirmer"),
        ("닫기", "Fermer"),
        ("열기", "Ouvrir"),
    ],

    # Case 2: Near-exact (punctuation difference)
    "punctuation_diff": [
        ("저장하시겠습니까?", "저장하시겠습니까"),  # Question mark removed
        ("완료되었습니다!", "완료되었습니다"),  # Exclamation removed
        ("게임을 종료합니다...", "게임을 종료합니다"),  # Ellipsis removed
    ],

    # Case 3: High similarity (>90%)
    "high_similarity": [
        ("파일을 저장하시겠습니까?", "문서를 저장하시겠습니까?"),  # One word diff
        ("게임을 시작합니다", "게임을 종료합니다"),  # Similar structure
    ],

    # Case 4: Medium similarity (70-90%)
    "medium_similarity": [
        ("새 게임을 시작하시겠습니까?", "새 파일을 만드시겠습니까?"),
        ("레벨이 상승했습니다", "경험치가 상승했습니다"),
    ],

    # Case 5: Low similarity (below threshold)
    "low_similarity": [
        ("날씨가 좋습니다", "무기를 강화합니다"),  # Completely different
        ("안녕하세요", "전투를 시작합니다"),  # Unrelated
    ],

    # Case 6: Multi-line with line-by-line matching
    "multiline_match": [
        ("첫 번째 줄\\n두 번째 줄", "First line\\nSecond line"),
        ("효과 설명\\n- 공격력 증가\\n- 방어력 증가", "Effect\\n- ATK increase\\n- DEF increase"),
    ],
}


def generate_xls_transfer_test_data(target_count=500):
    """Generate ~500 rows of XLS Transfer test data."""
    test_data = []

    all_cases = []
    for case_type, examples in XLS_TRANSFER_CASES.items():
        for korean, translation in examples:
            all_cases.append({
                "type": case_type,
                "korean": korean,
                "translation": translation,
            })

    # Repeat to reach target count
    while len(test_data) < target_count:
        for case in all_cases:
            if len(test_data) >= target_count:
                break
            # Add variation by appending index
            test_data.append({
                "id": len(test_data) + 1,
                "type": case["type"],
                "korean": case["korean"],
                "translation": case["translation"],
            })

    return test_data


def generate_kr_similar_test_data(target_count=500):
    """Generate ~500 rows of KR Similar test data."""
    test_data = []

    all_cases = []
    for case_type, examples in KR_SIMILAR_CASES.items():
        for korean, translation in examples:
            all_cases.append({
                "type": case_type,
                "korean": korean,
                "translation": translation,
            })

    # Repeat to reach target count
    while len(test_data) < target_count:
        for case in all_cases:
            if len(test_data) >= target_count:
                break
            test_data.append({
                "id": len(test_data) + 1,
                "type": case["type"],
                "korean": case["korean"],
                "translation": case["translation"],
            })

    return test_data


def generate_tm_standard_test_data(target_count=500):
    """Generate ~500 rows of Standard TM test data."""
    test_data = []

    all_cases = []
    for case_type, examples in TM_STANDARD_CASES.items():
        for korean, translation in examples:
            all_cases.append({
                "type": case_type,
                "korean": korean,
                "translation": translation,
            })

    # Repeat to reach target count
    while len(test_data) < target_count:
        for case in all_cases:
            if len(test_data) >= target_count:
                break
            test_data.append({
                "id": len(test_data) + 1,
                "type": case["type"],
                "korean": korean,
                "translation": translation,
            })

    return test_data


if __name__ == "__main__":
    print("XLS Transfer Test Cases:")
    for case_type, examples in XLS_TRANSFER_CASES.items():
        print(f"  {case_type}: {len(examples)} examples")

    print("\nKR Similar Test Cases:")
    for case_type, examples in KR_SIMILAR_CASES.items():
        print(f"  {case_type}: {len(examples)} examples")

    print("\nTM Standard Test Cases:")
    for case_type, examples in TM_STANDARD_CASES.items():
        print(f"  {case_type}: {len(examples)} examples")

    # Generate test data
    xls_data = generate_xls_transfer_test_data(500)
    kr_data = generate_kr_similar_test_data(500)
    tm_data = generate_tm_standard_test_data(500)

    print(f"\nGenerated: {len(xls_data)} XLS Transfer rows")
    print(f"Generated: {len(kr_data)} KR Similar rows")
    print(f"Generated: {len(tm_data)} TM Standard rows")
