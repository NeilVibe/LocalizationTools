#!/usr/bin/env python3
"""Generate JPN, DEU, ESP language data files from Korean source.

Reads languagedata_kor.xml and languagedata_eng.xml, then creates
translated versions for Japanese, German, and Spanish.
"""
from __future__ import annotations

import os
import random
from lxml import etree

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
random.seed(42)  # reproducible

# ---- Translation dictionaries ----
# These map English terms to target languages for realistic fixture content.

JPN_NAMES = {
    "Elder Varon": "長老バロン", "Warrior Kira": "戦士キラ",
    "Sorcerer Drakmar": "魔術師ドラクマール", "Scout Rune": "斥候ルーネ",
    "Blacksmith Grimjo": "鍛冶師グリムジョ", "Merchant Hana": "商人ハナ",
    "Sage Mir": "賢者ミル", "Archer Sera": "弓使いセラ",
    "Healer Yura": "治癒師ユラ", "Knight Kael": "騎士カエル",
    "Thief Jin": "盗賊ジン", "Bard Aria": "吟遊詩人アリア",
    "Witch Norna": "魔女ノルナ", "Guardian Bellion": "守護者ベリオン",
    "Alchemist Kor": "錬金術師コル", "Hunter Taka": "狩人タカ",
    "Gladiator Rex": "剣闘士レックス", "Shaman Oka": "呪術師オカ",
    "Dancer Lina": "舞姫リナ", "Scholar Aiden": "学者エイデン",
}

DEU_NAMES = {
    "Elder Varon": "Ältester Varon", "Warrior Kira": "Kriegerin Kira",
    "Sorcerer Drakmar": "Zauberer Drakmar", "Scout Rune": "Späher Rune",
    "Blacksmith Grimjo": "Schmied Grimjo", "Merchant Hana": "Händlerin Hana",
    "Sage Mir": "Weiser Mir", "Archer Sera": "Bogenschützin Sera",
    "Healer Yura": "Heilerin Yura", "Knight Kael": "Ritter Kael",
    "Thief Jin": "Dieb Jin", "Bard Aria": "Bardin Aria",
    "Witch Norna": "Hexe Norna", "Guardian Bellion": "Wächter Bellion",
    "Alchemist Kor": "Alchemist Kor", "Hunter Taka": "Jäger Taka",
    "Gladiator Rex": "Gladiator Rex", "Shaman Oka": "Schamane Oka",
    "Dancer Lina": "Tänzerin Lina", "Scholar Aiden": "Gelehrter Aiden",
}

ESP_NAMES = {
    "Elder Varon": "Anciano Varon", "Warrior Kira": "Guerrera Kira",
    "Sorcerer Drakmar": "Hechicero Drakmar", "Scout Rune": "Explorador Rune",
    "Blacksmith Grimjo": "Herrero Grimjo", "Merchant Hana": "Comerciante Hana",
    "Sage Mir": "Sabio Mir", "Archer Sera": "Arquera Sera",
    "Healer Yura": "Sanadora Yura", "Knight Kael": "Caballero Kael",
    "Thief Jin": "Ladrón Jin", "Bard Aria": "Barda Aria",
    "Witch Norna": "Bruja Norna", "Guardian Bellion": "Guardián Bellion",
    "Alchemist Kor": "Alquimista Kor", "Hunter Taka": "Cazador Taka",
    "Gladiator Rex": "Gladiador Rex", "Shaman Oka": "Chamán Oka",
    "Dancer Lina": "Bailarina Lina", "Scholar Aiden": "Erudito Aiden",
}

# Common game description translations with br-tags
JPN_DESCS = [
    "古い村の守護者。<br/>戦争を避けて隠遁中。",
    "北部の前哨基地から来た勇敢な戦士。<br/>黒い星の秘密を追っている。",
    "古代の知識を探求する魔術師。<br/>禁じられた魔法の危険性を警告する。",
    "森の道を知る斥候。<br/>危険な地域を安全に案内する。",
    "伝説的な武器を作る職人。<br/>黒い星金属の秘密を知っている。",
    "珍しい品物を扱う旅の商人。",
    "古代文献を解読する賢者。<br/>忘れられた言語を唯一読める。",
    "精密な弓術で有名な弓使い。<br/>百発百中の実力を誇る。",
    "神聖な力で負傷者を癒やす。<br/>戦場の守護天使と呼ばれている。",
    "王国の精鋭騎士団出身。<br/>名誉のために戦う。",
    "闇の中で活動する盗賊。<br/>情報収集に長けている。",
    "伝説の歌を歌う吟遊詩人。<br/>その歌には魔法が宿っている。",
    "禁じられた魔法を研究する魔女。<br/>危険だが強力な同盟者。",
    "城壁を守る守護者。<br/>いかなる敵も突破できない防御を誇る。",
    "様々な薬物を製造する錬金術師。<br/>治療薬から毒薬まで作れる。",
    "山野を駆ける熟練の狩人。<br/>野生動物の習性を熟知している。",
    "闘技場のチャンピオンである剣闘士。<br/>観衆の熱狂的な支持を受ける。",
    "精霊と交感する呪術師。<br/>自然の力を操る。",
    "魅惑的な踊りで敵を幻惑する舞姫。<br/>踊りには戦闘技術が隠されている。",
    "膨大な知識を持つ学者。<br/>すべてを記録する癖がある。",
]

DEU_DESCS = [
    "Hüter des alten Dorfes.<br/>Lebt zurückgezogen, um dem Krieg zu entgehen.",
    "Ein tapferer Krieger vom nördlichen Vorposten.<br/>Verfolgt das Geheimnis des Schwarzen Sterns.",
    "Ein Zauberer, der uraltes Wissen erforscht.<br/>Warnt vor den Gefahren verbotener Magie.",
    "Ein Späher, der die Waldwege kennt.<br/>Führt sicher durch gefährliche Gebiete.",
    "Ein Handwerker, der legendäre Waffen schmiedet.<br/>Kennt das Geheimnis des Schwarzsternmetalls.",
    "Ein reisender Händler, der seltene Waren führt.",
    "Ein Weiser, der alte Schriften entziffert.<br/>Kann als Einziger die vergessene Sprache lesen.",
    "Eine Bogenschützin, berühmt für ihre Präzision.<br/>Trifft jedes Ziel ohne Fehl.",
    "Heilt Verwundete mit heiliger Kraft.<br/>Wird als Schutzengel des Schlachtfelds bezeichnet.",
    "Ehemaliges Mitglied des königlichen Ritterordens.<br/>Kämpft für die Ehre.",
    "Ein Dieb, der im Verborgenen agiert.<br/>Geschickt in der Informationsbeschaffung.",
    "Ein Barde, der Lieder der Legende singt.<br/>Seinen Liedern wohnt Magie inne.",
    "Eine Hexe, die verbotene Magie erforscht.<br/>Gefährlich, aber ein mächtiger Verbündeter.",
    "Ein Wächter, der die Mauern schützt.<br/>Seine Verteidigung ist unüberwindbar.",
    "Ein Alchemist, der verschiedene Tränke braut.<br/>Von Heilmitteln bis zu Giften.",
    "Ein erfahrener Jäger, der durch die Wildnis streift.<br/>Kennt die Gewohnheiten aller Wildtiere.",
    "Champion der Arena.<br/>Genießt die begeisterte Unterstützung der Zuschauer.",
    "Ein Schamane, der mit Geistern kommuniziert.<br/>Beherrscht die Kräfte der Natur.",
    "Eine Tänzerin, die Feinde mit ihrem Tanz betört.<br/>In ihrem Tanz sind Kampfkünste verborgen.",
    "Ein Gelehrter mit umfassendem Wissen.<br/>Hat die Angewohnheit, alles aufzuzeichnen.",
]

ESP_DESCS = [
    "Guardián de la aldea antigua.<br/>Vive recluido para evitar la guerra.",
    "Un valiente guerrero del puesto avanzado del norte.<br/>Rastrea el secreto de la Estrella Negra.",
    "Un hechicero que explora el conocimiento antiguo.<br/>Advierte sobre los peligros de la magia prohibida.",
    "Un explorador que conoce los caminos del bosque.<br/>Guía con seguridad por zonas peligrosas.",
    "Un artesano que forja armas legendarias.<br/>Conoce el secreto del metal de la Estrella Negra.",
    "Un comerciante ambulante que vende artículos raros.",
    "Un sabio que descifra textos antiguos.<br/>El único que puede leer la lengua olvidada.",
    "Una arquera famosa por su puntería.<br/>Nunca falla un disparo.",
    "Cura heridos con poder sagrado.<br/>Conocida como el ángel del campo de batalla.",
    "Miembro de la orden de caballeros reales.<br/>Lucha por el honor.",
    "Un ladrón que opera en las sombras.<br/>Hábil en la recopilación de información.",
    "Una barda que canta canciones legendarias.<br/>Sus canciones contienen magia.",
    "Una bruja que investiga magia prohibida.<br/>Peligrosa pero poderosa aliada.",
    "Un guardián que protege las murallas.<br/>Su defensa es impenetrable.",
    "Un alquimista que elabora diversas pociones.<br/>Desde remedios hasta venenos.",
    "Un cazador experimentado que recorre la naturaleza.<br/>Conoce las costumbres de toda criatura salvaje.",
    "Campeón de la arena.<br/>Goza del apoyo entusiasta del público.",
    "Un chamán que se comunica con los espíritus.<br/>Domina las fuerzas de la naturaleza.",
    "Una bailarina que cautiva enemigos con su danza.<br/>En su baile se ocultan técnicas de combate.",
    "Un erudito con vasto conocimiento.<br/>Tiene la costumbre de registrar todo.",
]

# Item-related translations
JPN_ITEMS = [
    "伝説の剣", "闇の鎧", "炎の盾", "氷の指輪", "雷のネックレス",
    "聖なる弓", "影の短剣", "風の杖", "大地のハンマー", "光のローブ",
    "毒のマント", "水晶の兜", "竜鱗の手袋", "魔法のブーツ", "古代のベルト",
]
DEU_ITEMS = [
    "Legendäres Schwert", "Rüstung der Dunkelheit", "Feuerschild", "Eisring", "Blitzhalskette",
    "Heiliger Bogen", "Schattendolch", "Windstab", "Erdhammer", "Lichtgewand",
    "Giftmantel", "Kristallhelm", "Drachenschuppenhandschuhe", "Magische Stiefel", "Uralter Gürtel",
]
ESP_ITEMS = [
    "Espada Legendaria", "Armadura de Oscuridad", "Escudo de Fuego", "Anillo de Hielo", "Collar de Rayo",
    "Arco Sagrado", "Daga de Sombra", "Bastón de Viento", "Martillo de Tierra", "Túnica de Luz",
    "Capa de Veneno", "Yelmo de Cristal", "Guantes de Escama de Dragón", "Botas Mágicas", "Cinturón Antiguo",
]

# Region descriptions with br-tags
JPN_REGIONS = [
    "古代の遺跡が眠る地域。<br/>危険なモンスターが徘徊している。",
    "広大な平原が広がる穏やかな地域。<br/>初心者の冒険に最適。",
    "深い森に覆われた神秘的な場所。<br/>精霊が住んでいると言われている。",
    "灼熱の砂漠地帯。<br/>水の確保が生存の鍵。<br/>夜は凍てつく寒さ。",
    "氷と雪に閉ざされた北方。<br/>強力なドラゴンの住処。",
    "にぎやかな港町。<br/>世界中の商人が集まる貿易の拠点。",
    "火山活動が活発な危険地帯。<br/>レアな鉱石が採掘できる。",
    "巨大な湖に囲まれた浮島。<br/>古代の図書館がある。",
    "暗黒の地下迷宮。<br/>多くの冒険者が帰らぬ人となった。<br/>伝説の宝が眠る。",
    "天空にそびえる城。<br/>王国の権力の中心地。",
]

DEU_REGIONS = [
    "Eine Region, in der alte Ruinen schlummern.<br/>Gefährliche Monster streifen umher.",
    "Eine friedliche Region mit weiten Ebenen.<br/>Ideal für Abenteuer von Anfängern.",
    "Ein mystischer Ort, bedeckt von tiefem Wald.<br/>Man sagt, Geister leben hier.",
    "Eine glühend heiße Wüstenzone.<br/>Wasser ist der Schlüssel zum Überleben.<br/>Nachts herrscht eisige Kälte.",
    "Der eingefrorene Norden.<br/>Heimat mächtiger Drachen.",
    "Eine belebte Hafenstadt.<br/>Handelszentrum, wo sich Händler aus aller Welt treffen.",
    "Ein Gefahrengebiet mit aktiver Vulkantätigkeit.<br/>Seltene Erze können hier abgebaut werden.",
    "Eine schwebende Insel umgeben von einem riesigen See.<br/>Beherbergt eine alte Bibliothek.",
    "Ein dunkles Labyrinth unter der Erde.<br/>Viele Abenteurer kehrten nie zurück.<br/>Legendäre Schätze sollen hier liegen.",
    "Eine Burg, die in den Himmel ragt.<br/>Zentrum der königlichen Macht.",
]

ESP_REGIONS = [
    "Una región donde duermen ruinas antiguas.<br/>Monstruos peligrosos merodean por aquí.",
    "Una región pacífica con vastas llanuras.<br/>Ideal para aventuras de principiantes.",
    "Un lugar místico cubierto de bosque profundo.<br/>Se dice que los espíritus viven aquí.",
    "Una zona desértica abrasadora.<br/>El agua es clave para la supervivencia.<br/>Las noches son gélidas.",
    "El norte congelado.<br/>Hogar de poderosos dragones.",
    "Un animado puerto comercial.<br/>Punto de encuentro de mercaderes de todo el mundo.",
    "Una zona peligrosa con actividad volcánica.<br/>Se pueden extraer minerales raros.",
    "Una isla flotante rodeada por un lago enorme.<br/>Alberga una biblioteca antigua.",
    "Un oscuro laberinto subterráneo.<br/>Muchos aventureros nunca regresaron.<br/>Tesoros legendarios esperan aquí.",
    "Un castillo que se eleva hacia el cielo.<br/>Centro del poder real.",
]


def generate_lang_file(lang: str, names: dict, descs: list, items: list, regions: list) -> None:
    """Generate a language data file matching Korean structure."""
    kor_tree = etree.parse(os.path.join(BASE_DIR, "languagedata_kor.xml"))
    eng_tree = etree.parse(os.path.join(BASE_DIR, "languagedata_eng.xml"))
    kor_entries = kor_tree.findall(".//LocStr")
    eng_entries = eng_tree.findall(".//LocStr")

    # Build eng lookup
    eng_map: dict[str, etree._Element] = {}
    for e in eng_entries:
        eng_map[e.get("StringId", "")] = e

    root = etree.Element("LocStrList")
    count = 0
    br_count = 0

    for i, kor_e in enumerate(kor_entries):
        sid = kor_e.get("StringId", "")
        kor_origin = kor_e.get("StrOrigin", "")
        eng_e = eng_map.get(sid)
        eng_str = eng_e.get("Str", "") if eng_e is not None else ""

        # Determine translation based on StringId patterns
        translated = ""
        has_br = False

        if "_KNOW_CHAR_" in sid:
            idx = i // 2  # NAME/DESC pairs
            if sid.endswith("_NAME"):
                # Use name dictionary or generate
                if eng_str in names:
                    translated = names[eng_str]
                else:
                    translated = _translate_name(eng_str, lang)
            else:  # DESC
                desc_idx = idx % len(descs)
                translated = descs[desc_idx]
                has_br = "<br/>" in translated
        elif "_KNOW_ITEM_" in sid:
            if sid.endswith("_NAME"):
                item_idx = (i // 2) % len(items)
                translated = items[item_idx]
            else:
                translated = _translate_item_desc(eng_str, lang, i)
                has_br = "<br/>" in translated
        elif "_KNOW_REGI_" in sid:
            if sid.endswith("_NAME"):
                translated = _translate_region_name(eng_str, lang)
            else:
                reg_idx = (i // 2) % len(regions)
                translated = regions[reg_idx]
                has_br = "<br/>" in translated
        elif "_KNOW_CONT_" in sid:
            translated = _translate_content(eng_str, lang, i)
            has_br = "<br/>" in translated
        elif "_ITEM_" in sid:
            if sid.endswith("_NAME"):
                item_idx = i % len(items)
                translated = items[item_idx]
            else:
                translated = _translate_item_desc(eng_str, lang, i)
                has_br = "<br/>" in translated
        elif "_CHAR_" in sid:
            translated = _translate_name(eng_str, lang) if eng_str else _generic_translate(kor_origin, lang, i)
        else:
            translated = _generic_translate(kor_origin, lang, i)
            has_br = "<br/>" in translated

        if has_br:
            br_count += 1

        el = etree.SubElement(root, "LocStr")
        el.set("StringId", sid)
        el.set("StrOrigin", kor_origin)
        el.set("Str", translated)
        el.set("DescOrigin", "")
        el.set("Desc", "")
        count += 1

    # Write
    tree = etree.ElementTree(root)
    path = os.path.join(BASE_DIR, f"languagedata_{lang}.xml")
    tree.write(path, encoding="UTF-8", xml_declaration=True, pretty_print=True)
    pct = (br_count / count * 100) if count else 0
    print(f"Created {path}: {count} entries, {br_count} with br-tags ({pct:.0f}%)")


def _translate_name(eng: str, lang: str) -> str:
    """Simple name translation."""
    if lang == "jpn":
        prefixes = {"Elder": "長老", "Warrior": "戦士", "Sorcerer": "魔術師",
                     "Scout": "斥候", "Knight": "騎士", "Healer": "治癒師",
                     "Archer": "弓使い", "Hunter": "狩人", "Merchant": "商人"}
        for en, jp in prefixes.items():
            if eng.startswith(en):
                return jp + " " + eng.split(" ", 1)[-1] if " " in eng else jp
        return eng + "（日本語）"
    elif lang == "deu":
        return eng  # German names often same
    else:  # esp
        prefixes = {"Elder": "Anciano", "Warrior": "Guerrero",
                     "Sorcerer": "Hechicero", "Scout": "Explorador",
                     "Knight": "Caballero", "Healer": "Sanador"}
        for en, es in prefixes.items():
            if eng.startswith(en):
                return es + " " + eng.split(" ", 1)[-1] if " " in eng else es
        return eng


def _translate_item_desc(eng: str, lang: str, idx: int) -> str:
    """Generate item descriptions with br-tags."""
    if lang == "jpn":
        descs = [
            "強力な武器。<br/>攻撃力が大幅に上昇する。",
            "防御力を高める防具。<br/>魔法ダメージも軽減。",
            "回復効果のあるアイテム。<br/>使用すると体力が回復する。",
            "特殊効果を持つアクセサリー。",
            "古代の力が宿る装備。<br/>セット効果で能力値上昇。<br/>強化可能。",
        ]
    elif lang == "deu":
        descs = [
            "Eine mächtige Waffe.<br/>Erhöht den Angriff erheblich.",
            "Rüstung, die die Verteidigung stärkt.<br/>Reduziert auch Magieschaden.",
            "Ein Gegenstand mit Heilwirkung.<br/>Stellt bei Benutzung Gesundheit wieder her.",
            "Ein Accessoire mit Sonderwirkung.",
            "Ausrüstung mit alter Kraft.<br/>Set-Bonus erhöht Attribute.<br/>Verstärkbar.",
        ]
    else:
        descs = [
            "Un arma poderosa.<br/>Aumenta el ataque significativamente.",
            "Armadura que fortalece la defensa.<br/>También reduce el daño mágico.",
            "Un objeto con efecto curativo.<br/>Restaura salud al usarse.",
            "Un accesorio con efecto especial.",
            "Equipo con poder antiguo.<br/>El bono de conjunto aumenta atributos.<br/>Mejorable.",
        ]
    return descs[idx % len(descs)]


def _translate_region_name(eng: str, lang: str) -> str:
    """Translate region names."""
    if lang == "jpn":
        return eng + "地域"
    elif lang == "deu":
        return eng + "-Region"
    else:
        return "Región de " + eng


def _translate_content(eng: str, lang: str, idx: int) -> str:
    """Generic content translation with occasional br-tags."""
    if lang == "jpn":
        texts = [
            "このコンテンツに関する情報。<br/>詳細は図鑑を参照。",
            "重要な知識情報。",
            "冒険に役立つ情報。<br/>地図で場所を確認できる。",
            "歴史的な記録。<br/>古代文明との関連がある。<br/>学者の研究対象。",
            "戦闘に関する知識。",
        ]
    elif lang == "deu":
        texts = [
            "Informationen zu diesem Inhalt.<br/>Details im Lexikon nachschlagen.",
            "Wichtige Wissensinformationen.",
            "Nützliche Informationen für Abenteuer.<br/>Ort auf der Karte überprüfbar.",
            "Historische Aufzeichnungen.<br/>Verbindung zu alten Zivilisationen.<br/>Forschungsgegenstand der Gelehrten.",
            "Kampfwissen.",
        ]
    else:
        texts = [
            "Información sobre este contenido.<br/>Consulta el códice para más detalles.",
            "Información de conocimiento importante.",
            "Información útil para aventuras.<br/>Puedes verificar la ubicación en el mapa.",
            "Registros históricos.<br/>Relacionados con civilizaciones antiguas.<br/>Objeto de estudio de eruditos.",
            "Conocimiento de combate.",
        ]
    return texts[idx % len(texts)]


def _generic_translate(kor: str, lang: str, idx: int) -> str:
    """Fallback generic translation preserving br-tags."""
    has_br = "<br/>" in kor
    if lang == "jpn":
        if has_br:
            parts = kor.split("<br/>")
            translated = [p + "（翻訳済み）" if p.strip() else p for p in parts]
            return "<br/>".join(translated)
        return kor + "（日本語翻訳）" if kor else ""
    elif lang == "deu":
        if has_br:
            parts = kor.split("<br/>")
            translated = [p + " (übersetzt)" if p.strip() else p for p in parts]
            return "<br/>".join(translated)
        return kor + " (Deutsch)" if kor else ""
    else:
        if has_br:
            parts = kor.split("<br/>")
            translated = [p + " (traducido)" if p.strip() else p for p in parts]
            return "<br/>".join(translated)
        return kor + " (Español)" if kor else ""


if __name__ == "__main__":
    generate_lang_file("jpn", JPN_NAMES, JPN_DESCS, JPN_ITEMS, JPN_REGIONS)
    generate_lang_file("deu", DEU_NAMES, DEU_DESCS, DEU_ITEMS, DEU_REGIONS)
    generate_lang_file("esp", ESP_NAMES, ESP_DESCS, ESP_ITEMS, ESP_REGIONS)
    print("All multilingual files generated.")
