import os
import re
import sys
import threading
import queue
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
from langdetect import detect
from lxml import etree
import time
import unicodedata
import ahocorasick
    
# --- AI ERROR PHRASE BANKS (per language) ---
AI_ERROR_PHRASES = {
    'en': [
        # Single power keywords (instant flags)
        "guidelines", "translate", "translation", "openai", "anthropic", "translat",
        "training data", "programming", "parameters", "language model", "english",
        "mise-en-scène", "mise-en-scene", "mise en scene", "mise en scène",
        
        # Fulfill patterns
        "cannot fulfill this request", "can't fulfill this request", 
        "unable to fulfill this request", "cannot fulfill your request",
        "can't fulfill your request", "unable to fulfill your request",
        "i cannot fulfill", "i can't fulfill", "i am unable to fulfill",
        "assist with that request",
        
        # AI self-reference
        "as an ai", "as a language model", "as an artificial intelligence",
        "i'm an ai", "i am an ai", "as a chatbot", "as an assistant",
        
        # Training/guidelines references
        "my training data", "my guidelines", "my programming", "my parameters",
        "against my guidelines", "my ethical guidelines", "my safety protocols",
        "violates my usage policies", "against my policies", "content policy",
        
        # Translation-specific errors
        "cannot translate this", "unable to translate", "translation request",
        "cannot provide translation", "translate this content", "translation of this",
        "translate the following", "translation service", "machine translation",
        
        # Combined refusal patterns
        "i cannot assist with this request", "i'm unable to help with this",
        "i cannot generate", "i cannot create", "i cannot produce",
        "unable to process this request", "cannot process this request",
        
        # Policy/restriction phrases
        "restricted from", "not permitted to", "programmed not to", 
        "designed not to", "trained to", "programmed to",
        
        # Compliance patterns
        "i must decline", "i have to decline", "cannot comply with",
        "unable to comply", "cannot accommodate this request",
        "cannot complete this request", "unable to complete"
    ],
    
    'fr': [
        # Single keywords
        "directives", "traduire", "traduction", "programmation", "tradu", "france", "français",
        
        # Full phrases
        "en tant qu'ia", "en tant que modèle de langage", "en tant qu'intelligence artificielle",
        "je suis une ia", "comme assistant ia", "mes données d'entraînement",
        "mes directives", "ma programmation", "contre mes directives",
        "mes paramètres", "mes directives éthiques", "mes protocoles",
        "ne peux pas traduire ceci", "impossible de traduire", "demande de traduction",
        "ne peux pas fournir de traduction", "traduire ce contenu",
        "ne peux pas répondre à cette demande", "ne peux pas traiter cette demande",
        "ne peux pas satisfaire cette demande", "impossible de satisfaire",
        "ne peux pas générer", "ne peux pas créer", "contre mes politiques",
        "pas autorisé à", "programmé pour ne pas", "mes limitations",
        "je dois refuser", "je ne peux pas accepter"
    ],
    
    'de': [
        # Single keywords
        "richtlinien", "übersetzen", "übersetzung", "programmierung", "deutsch",
        
        # Full phrases
        "als ki", "als sprachmodell", "als künstliche intelligenz",
        "ich bin eine ki", "als ki-assistent", "meine trainingsdaten",
        "meine richtlinien", "meine programmierung", "gegen meine richtlinien",
        "meine parameter", "meine ethischen richtlinien",
        "kann dies nicht übersetzen", "übersetzung nicht möglich", "übersetzungsanfrage",
        "kann keine übersetzung bereitstellen", "diesen inhalt übersetzen",
        "kann diese anfrage nicht bearbeiten", "kann nicht generieren",
        "kann nicht erstellen", "gegen meine richtlinien", "nicht berechtigt zu",
        "programmiert nicht zu", "meine beschränkungen",
        "muss ablehnen", "kann nicht erfüllen"
    ],
    
    'es': [
        # Single keywords
        "directrices", "traducir", "traducción", "programación", "Español",
        
        # Full phrases
        "como ia", "como modelo de lenguaje", "como inteligencia artificial",
        "soy una ia", "como asistente ia", "mis datos de entrenamiento",
        "mis directrices", "mi programación", "contra mis directrices",
        "mis parámetros", "mis directrices éticas",
        "no puedo traducir esto", "imposible traducir", "solicitud de traducción",
        "no puedo proporcionar traducción", "traducir este contenido",
        "no puedo procesar esta solicitud", "no puedo generar",
        "no puedo crear", "contra mis políticas", "no autorizado para",
        "programado para no", "mis limitaciones",
        "debo rechazar", "no puedo cumplir"
    ],
    
    'es-mx': [
        # Single keywords
        "lineamientos", "traducir", "traducción", "programación", "Español",
        
        # Full phrases
        "como ia", "como modelo de lenguaje", "como inteligencia artificial",
        "soy una ia", "como asistente ia", "mis datos de entrenamiento",
        "mis lineamientos", "mi programación", "contra mis lineamientos",
        "mis parámetros", "mis lineamientos éticos",
        "no puedo traducir esto", "imposible traducir", "solicitud de traducción",
        "no puedo proporcionar traducción", "traducir este contenido",
        "no puedo procesar esta petición", "no puedo generar",
        "no puedo crear", "contra mis políticas", "no autorizado para",
        "programado para no", "mis limitaciones",
        "debo rechazar", "no puedo cumplir"
    ],
    
    'pt': [
        # Single keywords
        "diretrizes", "traduzir", "tradução", "programação", "português",
        
        # Full phrases
        "como ia", "como modelo de linguagem", "como inteligência artificial",
        "sou uma ia", "como assistente ia", "meus dados de treinamento",
        "minhas diretrizes", "minha programação", "contra minhas diretrizes",
        "meus parâmetros", "minhas diretrizes éticas",
        "não posso traduzir isto", "impossível traduzir", "solicitação de tradução",
        "não posso fornecer tradução", "traduzir este conteúdo",
        "não posso processar esta solicitação", "não posso gerar",
        "não posso criar", "contra minhas políticas", "não autorizado para",
        "programado para não", "minhas limitações",
        "devo recusar", "não posso cumprir", "não posso atender"
    ],
    
    'ru': [
        # Single keywords
        "инструкции", "перевести", "перевод", "программа", "Русский",
        
        # Full phrases
        "как ии", "как языковая модель", "как искусственный интеллект",
        "я ии", "как ии-ассистент", "мои обучающие данные",
        "мои инструкции", "моя программа", "против моих инструкций",
        "мои параметры", "мои этические принципы",
        "не могу перевести это", "невозможно перевести", "запрос на перевод",
        "не могу предоставить перевод", "перевести этот контент",
        "не могу обработать этот запрос", "не могу сгенерировать",
        "не могу создать", "против моей политики", "не уполномочен",
        "запрограммирован не", "мои ограничения",
        "должен отказать", "не могу выполнить"
    ],
    
    'zh-cn': [
        # Single keywords
        "指导方针", "翻译", "训练数据", "编程", "中文",
        
        # Full phrases
        "作为ai", "作为人工智能", "作为语言模型", "我是ai",
        "作为ai助手", "我的训练数据", "我的指导方针", "我的编程",
        "违反我的准则", "我的参数", "我的道德准则",
        "无法翻译此内容", "无法提供翻译", "翻译请求",
        "无法处理此请求", "无法生成", "无法创建", "违反政策",
        "未被授权", "被编程为不", "我的限制",
        "必须拒绝", "无法满足", "无法完成"
    ],
    
    'zh-tw': [
        # Single keywords
        "指導方針", "翻譯", "訓練數據", "編程", "中文",
        
        # Full phrases
        "作為ai", "作為人工智慧", "作為語言模型", "我是ai",
        "作為ai助手", "我的訓練數據", "我的指導方針", "我的編程",
        "違反我的準則", "我的參數", "我的道德準則",
        "無法翻譯此內容", "無法提供翻譯", "翻譯請求",
        "無法處理此請求", "無法生成", "無法創建", "違反政策",
        "未被授權", "被編程為不", "我的限制",
        "必須拒絕", "無法滿足", "無法完成"
    ],
    
    'ja': [
        # Single keywords
        "ガイドライン", "翻訳", "トレーニングデータ", "プログラミング", "日本語",
        "ミザンセーヌ",
        
        # Full phrases
        "aiとして", "人工知能として", "言語モデルとして", "私はaiです",
        "aiアシスタントとして", "私のトレーニングデータ", "私のガイドライン",
        "私のプログラミング", "ガイドラインに違反", "私のパラメータ",
        "私の倫理的ガイドライン", "これを翻訳できません",
        "翻訳を提供できません", "翻訳リクエスト", "このリクエストを処理できません",
        "生成できません", "作成できません", "ポリシーに違反", "許可されていません",
        "プログラムされていません", "私の制限",
        "お断りしなければ", "要望にお応えできません"
    ],
    
    'tr': [
        # Single keywords
        "yönergeler", "çeviri", "eğitim verileri", "programlama", "Türkçe",
        
        # Full phrases
        "bir yapay zeka olarak", "dil modeli olarak", "yapay zeka olarak",
        "ben bir yapay zekayım", "ai asistan olarak", "eğitim verilerim",
        "yönergelerim", "programlamam", "yönergelerime aykırı",
        "parametrelerim", "etik yönergelerim",
        "bunu çeviremem", "çeviri yapamam", "çeviri talebi",
        "çeviri sağlayamam", "bu içeriği çevir", "bu talebi işleyemem",
        "oluşturamam", "yaratamam", "politikalara aykırı", "yetkilendirilmedim",
        "programlanmadım", "sınırlamalarım",
        "reddetmeliyim", "yerine getiremem"
    ],
    
    'pl': [
        # Single keywords
        "wytyczne", "tłumaczenie", "dane treningowe", "programowanie", "Polski",
        
        # Full phrases
        "jako ai", "jako model językowy", "jako sztuczna inteligencja",
        "jestem ai", "jako asystent ai", "moje dane treningowe",
        "moje wytyczne", "moje programowanie", "przeciw moim wytycznym",
        "moje parametry", "moje wytyczne etyczne",
        "nie mogę tego przetłumaczyć", "niemożliwe do przetłumaczenia",
        "prośba o tłumaczenie", "nie mogę dostarczyć tłumaczenia",
        "nie mogę przetworzyć tego żądania", "nie mogę wygenerować",
        "nie mogę utworzyć", "przeciw polityce", "nie upoważniony do",
        "zaprogramowany aby nie", "moje ograniczenia",
        "muszę odmówić", "nie mogę spełnić"
    ],
    
    'it': [
        # Single keywords
        "linee guida", "traduzione", "dati di addestramento", "programmazione", "Italiano",
        
        # Full phrases
        "come ia", "come modello linguistico", "come intelligenza artificiale",
        "sono un'ia", "come assistente ia", "i miei dati di addestramento",
        "le mie linee guida", "la mia programmazione", "contro le mie linee guida",
        "i miei parametri", "le mie linee guida etiche",
        "non posso tradurre questo", "impossibile tradurre", "richiesta di traduzione",
        "non posso fornire traduzione", "tradurre questo contenuto",
        "non posso elaborare questa richiesta", "non posso generare",
        "non posso creare", "contro le politiche", "non autorizzato a",
        "programmato per non", "le mie limitazioni",
        "devo rifiutare", "non posso soddisfare"
    ]
}

# --- LANGUAGE MAPPING ---
LANGUAGES = {
    "English (EN)": ("en", 1.3),
    "French (FR)": ("fr", 1.4),
    "German (DE)": ("de", 1.4),
    "Russian (RU)": ("ru", 1.2),
    "Portuguese (PT)": ("pt", 1.3),
    "European Spanish (ES-ES)": ("es", 1.3),
    "Latin American Spanish (ES-MX)": ("es-mx", 1.3),
    "Simplified Chinese (CN)": ("zh-cn", 0.5),
    "Traditional Chinese (TW)": ("zh-tw", 0.5),
    "Turkish (TR)": ("tr", 1.2),
    "Polish (PL)": ("pl", 1.3),
    "Italian (IT)": ("it", 1.3),
    "Japanese (JP)": ("ja", 0.8)
}

WORD_RATIO_MIN = 0.1
WORD_RATIO_MAX = 4
CHAR_RATIO_MIN = 0.3
CHAR_RATIO_MAX = 3

# --- XML PARSING UTILS ---

def parse_xml_file(file_path):
    """Parse XML file with better error handling"""
    try:
        # Try direct parsing first
        parser = etree.XMLParser(remove_blank_text=True, recover=True)
        tree = etree.parse(file_path, parser)
        return tree.getroot()
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        # Fallback to the original method
        try:
            txt = open(file_path, encoding='utf-8').read()
            txt = re.sub(r'&(?!lt;|gt;|amp;|apos;|quot;)', '&amp;', txt)
            wrapped = "<ROOT>
" + txt + "
</ROOT>"
            rec_parser = etree.XMLParser(recover=True)
            recovered = etree.fromstring(wrapped.encode('utf-8'), parser=rec_parser)
            return recovered
        except Exception:
            return None

def get_all_xml_files(input_folder):
    xml_files = []
    for dirpath, _, filenames in os.walk(input_folder):
        for file in filenames:
            if file.lower().endswith(".xml"):
                xml_files.append(os.path.join(dirpath, file))
    return xml_files

# --- DATA EXTRACTION AND PREPROCESSING ---

def extract_all_locstrs_from_folder(folder):
    """Extract LocStr elements with better debugging"""
    rows = []
    xml_files = get_all_xml_files(folder)
    
    print(f"DEBUG: Found {len(xml_files)} XML files in folder")
    
    for file_path in xml_files:
        print(f"DEBUG: Processing {os.path.basename(file_path)}")
        root = parse_xml_file(file_path)
        if root is None:
            print(f"DEBUG: Failed to parse {file_path}")
            continue
            
        # Find all LocStr elements regardless of depth
        locstrs = root.xpath('.//LocStr')
        print(f"DEBUG: Found {len(locstrs)} LocStr elements in {os.path.basename(file_path)}")
        
        for loc in locstrs:
            strorigin = loc.get("StrOrigin", "")
            strval = loc.get("Str", "")
            stringid = loc.get("StringId", "")
            
            # Debug specific entries
            if strval and (strval.startswith("灰鬃") or strval.startswith("Mitglied")):
                print(f"DEBUG: Found entry - StringId: {stringid}, Str starts with: {strval[:20]}...")
            
            rows.append({
                "File": file_path,
                "StringId": stringid,
                "StrOrigin": strorigin,
                "Str": strval
            })
    
    print(f"DEBUG: Total LocStr entries extracted: {len(rows)}")
    df = pd.DataFrame(rows)
    return df

def is_mixed_korean_english(text):
    if not isinstance(text, str):
        return False
    has_korean = bool(re.search(r'[\uac00-\ud7af]', text))
    has_english = bool(re.search(r'[A-Za-z]', text))
    return has_korean and has_english

def preprocess_dataframe(df):
    original_count = len(df)
    print(f"DEBUG: Starting preprocessing with {original_count} entries")
    
    # Remove null StrOrigin
    df = df[-df["StrOrigin"].isnull()]
    print(f"DEBUG: After removing null StrOrigin: {len(df)} entries")
    
    # Remove empty StrOrigin
    df = df[df["StrOrigin"].str.strip() != ""]
    print(f"DEBUG: After removing empty StrOrigin: {len(df)} entries")
    
    # Remove empty Str
    df = df[df["Str"].str.strip() != ""]
    print(f"DEBUG: After removing empty Str: {len(df)} entries")
    
    # Remove duplicates
    duplicates = df[df.duplicated(subset=["StringId"], keep=False)]
    if len(duplicates) > 0:
        print(f"DEBUG: Found {len(duplicates)} entries with duplicate StringIds")
    df = df.drop_duplicates(subset=["StringId"])
    print(f"DEBUG: After removing duplicates: {len(df)} entries")
    
    # --- ESSENTIAL REGEX PREPROCESS: Remove {...} pattern codes from Str and StrOrigin ---
    # This will remove ALL substrings like {Key:Key_DialTurnR}, {Anything:Anything}, etc.
    pattern = re.compile(r'\{[^{}]*\}')
    df["StrOrigin"] = df["StrOrigin"].apply(lambda x: pattern.sub('', str(x)))
    df["Str"] = df["Str"].apply(lambda x: pattern.sub('', str(x)))
    
    df = df.reset_index(drop=True)
    return df


# --- IMPROVED SCRIPT DETECTION ---

def is_latin_char(char):
    """Check if a character is Latin alphabet (including extended Latin)"""
    if 'A' <= char <= 'Z' or 'a' <= char <= 'z':
        return True
    if ord(char) in range(0x00C0, 0x024F):  # Latin Extended-A and B
        return True
    if ord(char) in range(0x1E00, 0x1EFF):  # Latin Extended Additional
        return True
    return False

def is_cyrillic_char(char):
    """Check if a character is Cyrillic (including basic and extended)"""
    code = ord(char)
    # Cyrillic: U+0400–U+04FF, Cyrillic Supplement: U+0500–U+052F, Cyrillic Extended-A/B: U+2DE0–U+2DFF, U+A640–U+A69F
    return (
        0x0400 <= code <= 0x04FF or
        0x0500 <= code <= 0x052F or
        0x2DE0 <= code <= 0x2DFF or
        0xA640 <= code <= 0xA69F
    )

def detect_non_latin_characters(text):
    """
    Detects all non-Latin alphabetic characters in text.
    Returns a list of tuples: (character, position, script_name)
    """
    non_latin_chars = []
    for i, char in enumerate(text):
        if not char.isalpha():
            continue
        if not is_latin_char(char):
            script_name = "Unknown"
            if '\u0400' <= char <= '\u04ff':
                script_name = "Cyrillic"
            elif '\u4e00' <= char <= '\u9fff':
                script_name = "Chinese"
            elif '\u3040' <= char <= '\u309f':
                script_name = "Japanese (Hiragana)"
            elif '\u30a0' <= char <= '\u30ff':
                script_name = "Japanese (Katakana)"
            elif '\uac00' <= char <= '\ud7af':
                script_name = "Korean"
            elif '\u0370' <= char <= '\u03ff':
                script_name = "Greek"
            elif '\u0600' <= char <= '\u06ff':
                script_name = "Arabic"
            elif '\u0590' <= char <= '\u05ff':
                script_name = "Hebrew"
            elif '\u0e00' <= char <= '\u0e7f':
                script_name = "Thai"
            elif '\u0900' <= char <= '\u097f':
                script_name = "Devanagari"
            non_latin_chars.append((char, i, script_name))
    return non_latin_chars

def detect_non_latin_cyrillic_characters(text):
    """
    Detects all characters that are NOT Latin and NOT Cyrillic.
    Returns a list of tuples: (character, position, script_name)
    """
    non_latin_cyrillic_chars = []
    for i, char in enumerate(text):
        if not char.isalpha():
            continue
        if not is_latin_char(char) and not is_cyrillic_char(char):
            script_name = "Unknown"
            code = ord(char)
            if 0x4E00 <= code <= 0x9FFF:
                script_name = "Chinese"
            elif 0x3040 <= code <= 0x309F:
                script_name = "Japanese (Hiragana)"
            elif 0x30A0 <= code <= 0x30FF:
                script_name = "Japanese (Katakana)"
            elif 0xAC00 <= code <= 0xD7AF:
                script_name = "Korean"
            elif 0x0370 <= code <= 0x03FF:
                script_name = "Greek"
            elif 0x0600 <= code <= 0x06FF:
                script_name = "Arabic"
            elif 0x0590 <= code <= 0x05FF:
                script_name = "Hebrew"
            elif 0x0E00 <= code <= 0x0E7F:
                script_name = "Thai"
            elif 0x0900 <= code <= 0x097F:
                script_name = "Devanagari"
            non_latin_cyrillic_chars.append((char, i, script_name))
    return non_latin_cyrillic_chars

# --- Utility: Load character sets for Chinese/Japanese ---

def load_simplified_chinese_set():
    # GB2312 range: U+4E00–U+9FA5 (but not all are used)
    # We'll use a static set for practical purposes (common range)
    # For full coverage, you may want to load from a file or use OpenCC
    # Here, we use a typical GB2312 range
    return set(chr(i) for i in range(0x4E00, 0x9FA6))

def load_traditional_chinese_set():
    # Big5 range: U+4E00–U+9FFF, but not all are traditional
    # We'll use a static set of common traditional characters
    # For full coverage, you may want to load from a file or use OpenCC
    # Here, we use a typical Big5 range
    return set(chr(i) for i in range(0x4E00, 0x9FFF))

def load_japanese_kanji_set():
    # Japanese Kanji: U+4E00–U+9FFF (CJK Unified Ideographs)
    return set(chr(i) for i in range(0x4E00, 0x9FFF))

def is_hiragana(char):
    return '\u3040' <= char <= '\u309F'

def is_katakana(char):
    return '\u30A0' <= char <= '\u30FF'

def is_japanese_kanji(char):
    return '\u4E00' <= char <= '\u9FFF'

def is_japanese_char(char):
    return is_hiragana(char) or is_katakana(char) or is_japanese_kanji(char)

# --- Detection Functions ---

def detect_non_simplified_chinese_characters(text):
    """
    Detects all characters NOT in the Simplified Chinese (GB2312) set.
    Returns a list of tuples: (character, position, script_name)
    """
    allowed = load_simplified_chinese_set()
    non_simp = []
    for i, char in enumerate(text):
        if not char.isalpha():
            continue
        if char not in allowed:
            # Try to classify
            code = ord(char)
            if 0x4E00 <= code <= 0x9FFF:
                script = "CJK (possibly Traditional)"
            elif 0x3040 <= code <= 0x309F:
                script = "Japanese (Hiragana)"
            elif 0x30A0 <= code <= 0x30FF:
                script = "Japanese (Katakana)"
            elif 0xAC00 <= code <= 0xD7AF:
                script = "Korean"
            else:
                script = "Other"
            non_simp.append((char, i, script))
    return non_simp

def detect_non_traditional_chinese_characters(text):
    """
    Detects all characters NOT in the Traditional Chinese (Big5) set.
    Returns a list of tuples: (character, position, script_name)
    """
    allowed = load_traditional_chinese_set()
    non_trad = []
    for i, char in enumerate(text):
        if not char.isalpha():
            continue
        if char not in allowed:
            code = ord(char)
            if 0x4E00 <= code <= 0x9FFF:
                script = "CJK (possibly Simplified)"
            elif 0x3040 <= code <= 0x309F:
                script = "Japanese (Hiragana)"
            elif 0x30A0 <= code <= 0x30FF:
                script = "Japanese (Katakana)"
            elif 0xAC00 <= code <= 0xD7AF:
                script = "Korean"
            else:
                script = "Other"
            non_trad.append((char, i, script))
    return non_trad

def detect_non_japanese_characters(text):
    """
    Detects all characters NOT in Japanese scripts (Hiragana, Katakana, Kanji).
    Returns a list of tuples: (character, position, script_name)
    """
    non_jp = []
    for i, char in enumerate(text):
        if not char.isalpha():
            continue
        if not is_japanese_char(char):
            code = ord(char)
            if 0xAC00 <= code <= 0xD7AF:
                script = "Korean"
            elif 0x4E00 <= code <= 0x9FFF:
                script = "CJK (Non-Japanese Kanji?)"
            elif 0x3400 <= code <= 0x4DBF:
                script = "CJK Extension A"
            elif 0x20000 <= code <= 0x2A6DF:
                script = "CJK Extension B"
            elif 0x2A700 <= code <= 0x2B73F:
                script = "CJK Extension C"
            elif 0x2B740 <= code <= 0x2B81F:
                script = "CJK Extension D"
            elif 0x2B820 <= code <= 0x2CEAF:
                script = "CJK Extension E"
            elif 0x2CEB0 <= code <= 0x2EBEF:
                script = "CJK Extension F"
            elif 0x3040 <= code <= 0x309F:
                script = "Japanese (Hiragana)"
            elif 0x30A0 <= code <= 0x30FF:
                script = "Japanese (Katakana)"
            else:
                script = "Other"
            non_jp.append((char, i, script))
    return non_jp

# --- Updated Language Consistency Check ---
def check_language_consistency(folder, lang_code, progress_queue=None, output_folder=None, lang_dropdown_name="", english_reference_path=None):
    def contains_korean(text):
        return bool(re.search(r'[\uac00-\ud7af]', str(text)))

    def is_newline_token(char, text):
        newline_tokens = ["<br/>", "&lt;br/&gt;", "<br>", "&lt;br&gt;"]
        return any(char in token and token in text for token in newline_tokens)

    def normalize(text):
        return unicodedata.normalize('NFKC', str(text)) if isinstance(text, str) else ""

    def is_japanese_char_extended(char):
        code = ord(char)
        return any([
            0x3040 <= code <= 0x309F,  # Hiragana
            0x30A0 <= code <= 0x30FF,  # Katakana
            0x4E00 <= code <= 0x9FFF,  # CJK Unified (Kanji)
            0x3000 <= code <= 0x303F,  # CJK Symbols and Punctuation
            0xFF00 <= code <= 0xFFEF,  # Halfwidth and Fullwidth Forms
            0x3200 <= code <= 0x32FF,  # Enclosed CJK Letters
            0x3300 <= code <= 0x33FF,  # CJK Compatibility
            0x31F0 <= code <= 0x31FF,  # Katakana Phonetic Extensions
            0x3220 <= code <= 0x3247,  # Parenthesized CJK
            0x3280 <= code <= 0x337F,  # CJK Squared/Circled
            char in '。、・「」『』（）〈〉《》【】〔〕［］｛｝！？：；／＼〜ー－―...‥･♪♫♬♩※※＊＃＆＠§¶†‡',
            char in '．，.、,',
            char in '０１２３４５６７８９',
            char in 'ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ',
            char in '　',
            char in '￥＄￠￡¢£',
            char in '＋－×÷＝≠≒≪≫',
            char in '↑↓←→⇒⇔',
            char in '♂♀',
            char == '々',
            char == 'ヽヾ',
            char == 'ゝゞ',
        ])

    def is_chinese_char_extended(char):
        code = ord(char)
        return any([
            0x4E00 <= code <= 0x9FFF,
            0x3400 <= code <= 0x4DBF,
            0x20000 <= code <= 0x2A6DF,
            0x2A700 <= code <= 0x2B73F,
            0x2B740 <= code <= 0x2B81F,
            0x2B820 <= code <= 0x2CEAF,
            0x2CEB0 <= code <= 0x2EBEF,
            0x3000 <= code <= 0x303F,
            0xFF00 <= code <= 0xFFEF,
            0x3200 <= code <= 0x32FF,
            0x3300 <= code <= 0x33FF,
            0xFE30 <= code <= 0xFE4F,
            0xF900 <= code <= 0xFAFF,
            char in '。，、；：？！...—·「」『』（）［］｛｝【】〈〉《》〔〕""\'\'',
            char in '．，.、,;:?!',
            char in '０１２３４５６７８９',
            char in 'ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ',
            char in '　',
            char in '￥＄￠￡¢£¥',
            char in '＋－×÷＝≠≈≤≥±∞',
            char in '％‰',
            char in '＃＆＠※＊',
            char in '↑↓←→↖↗↙↘⇒⇔',
   char in '■□▲△▼▽◆◇○◎☆★',
            char in '♂♀',
            char in '～〜',
            char in '／＼',
            char in '｜',
            char in '﹏＿',
            char in '°℃℉',
            char == '々',
        ])

    def extract_alphanumeric_tokens(text):
        return set(re.findall(r'[A-Za-z0-9]+', text))

    # Languages that should get the English word check (including Russian)
    english_check_languages = {'fr', 'de', 'es', 'es-mx', 'pt', 'it', 'tr', 'pl', 'ru'}
    # Languages that use the Latin script check
    latin_languages = {'en', 'fr', 'de', 'es', 'es-mx', 'pt', 'it', 'tr', 'pl'}


    df = extract_all_locstrs_from_folder(folder)
    df = preprocess_dataframe(df)
    if df.empty:
        return [], 0, 0, df, None

    # --- ULTRA-FAST ENGLISH WORD DETECTION WITH AHO-CORASICK ---
    automaton = None
    if lang_code in english_check_languages and english_reference_path:
        print("Building Aho-Corasick automaton for ultra-fast English word detection...")
        
        # Extract all unique words from English reference
        english_words = set()
        eng_root = parse_xml_file(english_reference_path)
        if eng_root is not None:
            for loc in eng_root.xpath('.//LocStr'):
                eng_str = loc.get("Str", "")
                if eng_str.strip():
                    # Extract all words (not just bigrams)
                    words = re.findall(r'\b[A-Za-z]+\b', eng_str)
                    # Add words of length X (to avoid too many false positives)
                    for word in words:
                        if len(word) >= 3:
                            english_words.add(word.lower())
        
        print(f"Found {len(english_words)} unique English words")
        
        # Build Aho-Corasick automaton
        automaton = ahocorasick.Automaton()
        for word in english_words:
            automaton.add_word(word, word)
        automaton.make_automaton()
        print("Aho-Corasick automaton built successfully!")

    results = []
    flagged_rows = []
    total_rows = len(df)
    last_print_time = time.time()

    for idx, row in df.iterrows():
        strval = str(row["Str"])
        strorigin = str(row["StrOrigin"])

        # --- Skip conditions ---
        # Skip if translation is exactly the same as origin
        # if strval == strorigin:
        #     continue

        # Skip if origin does NOT contain Korean characters
        # if not re.search(r'[\uac00-\ud7af]', strorigin):
        #     continue

        # Skip if origin contains underscores (likely placeholders/IDs)
        if "_" in strorigin:
            continue

        # You can add more skip rules here if needed
        # Example: skip if origin or translation is empty after stripping
        if not strval.strip():
            continue

        # --- ULTRA-FAST ENGLISH WORD CHECK (for Latin languages) ---
        if lang_code in english_check_languages and automaton:
            strval_lower = strval.lower()
            found_english_words = []
            
            # Extract words from strorigin to exclude
            origin_words = set(word.lower() for word in re.findall(r'\b[A-Za-z]+\b', strorigin))
            
            # Use Aho-Corasick to find all matches in one pass
            for end_index, word in automaton.iter(strval_lower):
                start_index = end_index - len(word) + 1
                
                # Check if it's a whole word (not part of a larger word)
                is_word_boundary_start = (start_index == 0 or not strval_lower[start_index-1].isalpha())
                is_word_boundary_end = (end_index == len(strval_lower) - 1 or not strval_lower[end_index+1].isalpha())
                
                if is_word_boundary_start and is_word_boundary_end:
                    found_english_words.append(word)
            

            if len(found_english_words) >= 3:  # how many word need match
                # Calculate percentage of text that is English words
                total_text_length = len(strval.replace(" ", ""))  # Total characters excluding spaces
                english_chars_length = sum(len(word) for word in found_english_words)
                english_percentage = (english_chars_length / total_text_length * 100) if total_text_length > 0 else 0
                
                # Only flag if ALSO X percent or more is English
                if english_percentage >= 70:
                    # Remove duplicates and get first examples
                    unique_words = list(dict.fromkeys(found_english_words))[:3]
                    results.append({
                        'row': idx + 2,
                        'file': row["File"],
                        'stringid': row["StringId"],
                        'strorigin': strorigin[:50] + '...' if len(strorigin) > 50 else strorigin,
                        'str': strval[:50] + '...' if len(strval) > 50 else strval,
                        'full_str': strval,
                        'reason': f"Contains English words ({english_percentage:.0f}% English): {', '.join(unique_words)}"
                    })
                    flagged_rows.append(row)
                    continue


        # --- Existing language checks ---
        origin_tokens = extract_alphanumeric_tokens(strorigin)
        norm_strval = normalize(strval)
        norm_strorigin = normalize(strorigin)
        origin_chars_lower = {c.lower() for c in norm_strorigin}

        if lang_code in latin_languages:
            non_latin_chars = detect_non_latin_characters(strval)
            filtered_non_latin = [
                (char, pos, script) for (char, pos, script) in non_latin_chars 
                if char != 'º' and char.lower() not in origin_chars_lower
            ]
            if filtered_non_latin:
                unique_scripts = set(script for _, _, script in filtered_non_latin)
                sample_chars = []
                for script in unique_scripts:
                    chars_of_script = [char for char, _, s in filtered_non_latin if s == script][:3]
                    sample_chars.append(f"{script}: {', '.join(chars_of_script)}")
                reason = f"Non-Latin characters found ({', '.join(sample_chars)})"
                results.append({
                    'row': idx + 2,
                    'file': row["File"],
                    'stringid': row["StringId"],
                    'strorigin': strorigin[:50] + '...' if len(strorigin) > 50 else strorigin,
                    'str': strval[:50] + '...' if len(strval) > 50 else strval,
                    'full_str': strval,
                    'reason': reason,
                    'non_latin_chars': filtered_non_latin
                })
                flagged_rows.append(row)

        elif lang_code == 'ru':
            non_latin_cyrillic_chars = detect_non_latin_cyrillic_characters(strval)
            filtered_chars = [
                (char, pos, script) for (char, pos, script) in non_latin_cyrillic_chars
                if char.lower() not in origin_chars_lower
            ]
            if filtered_chars:
                unique_scripts = set(script for _, _, script in filtered_chars)
                sample_chars = []
                for script in unique_scripts:
                    chars_of_script = [char for char, _, s in filtered_chars if s == script][:3]
                    sample_chars.append(f"{script}: {', '.join(chars_of_script)}")
                reason = f"Non-Latin/Non-Cyrillic characters found ({', '.join(sample_chars)})"
                results.append({
                    'row': idx + 2,
                    'file': row["File"],
                    'stringid': row["StringId"],
                    'strorigin': strorigin[:50] + '...' if len(strorigin) > 50 else strorigin,
                    'str': strval[:50] + '...' if len(strval) > 50 else strval,
                    'full_str': strval,
                    'reason': reason,
                    'non_latin_cyrillic_chars': filtered_chars
                })
                flagged_rows.append(row)

        elif lang_code == 'ja':
            non_jp_chars = []
            val_tokens = extract_alphanumeric_tokens(strval)
            for i, char in enumerate(strval):
                if not char.isalpha():
                    continue
                if is_japanese_char_extended(char):
                    continue
                in_origin_token = False
                # for token in val_tokens:
                    # if char in token and token in origin_tokens:
                        # in_origin_token = True
                        # break
                # if in_origin_token:
                    # continue
                # if char.lower() in origin_chars_lower:
                    # continue
                if char in '.-_/\\|@#$%^&*()+=[]{}:;"\'<>,?!-`　。、．，！？：；（）「」『』【】〈〉《》〔〕［］｛｝・...‥〜ー－―／＼＋－×÷＝♪※＊＃＆＠':
                    continue
                code = ord(char)
                if 0xAC00 <= code <= 0xD7AF:
                    script = "Korean"
                elif is_latin_char(char):
                    script = "Latin"
                elif is_cyrillic_char(char):
                    script = "Cyrillic"  
                else:
                    script = "Other"
                non_jp_chars.append((char, i, script))
            if non_jp_chars:
                unique_scripts = set(script for _, _, script in non_jp_chars)
                sample_chars = []
                for script in unique_scripts:
                    chars_of_script = [char for char, _, s in non_jp_chars if s == script][:3]
                    sample_chars.append(f"{script}: {', '.join(chars_of_script)}")
                reason = f"Non-Japanese characters found ({', '.join(sample_chars)})"
                results.append({
                    'row': idx + 2,
                    'file': row["File"],
                    'stringid': row["StringId"],
                    'strorigin': strorigin[:50] + '...' if len(strorigin) > 50 else strorigin,
                    'str': strval[:50] + '...' if len(strval) > 50 else strval,
                    'full_str': strval,
                    'reason': reason,
                    'non_japanese_chars': non_jp_chars
                })
                flagged_rows.append(row)

        elif lang_code in ['zh-cn', 'zh-tw']:
            non_chinese_chars = []
            val_tokens = extract_alphanumeric_tokens(strval)
            for i, char in enumerate(strval):
                if not char.isalpha():
                    continue
                if is_chinese_char_extended(char):
                    continue
                in_origin_token = False
                # for token in val_tokens:
                    # if char in token and token in origin_tokens:
                        # in_origin_token = True
                        # break
                # if in_origin_token:
                    # continue
                # if char.lower() in origin_chars_lower:
                    # continue
                if char in '.-_/\\|@#$%^&*()+=[]{}:;"\'<>,?!-`　。，、；：？！...—·「」『』（）［］｛｝【】〈〉《》〔〕""\'\'／＼＋－×÷＝％‰＃＆＠※＊°℃℉｜～〜﹏＿':
                    continue
                if is_newline_token(char, strval):
                    continue
                code = ord(char)
                if 0xAC00 <= code <= 0xD7AF:
                    script = "Korean"
                elif 0x3040 <= code <= 0x309F:
                    script = "Japanese (Hiragana)"
                elif 0x30A0 <= code <= 0x30FF:
                    script = "Japanese (Katakana)"
                elif is_latin_char(char):
                    script = "Latin"
                elif is_cyrillic_char(char):
                    script = "Cyrillic"
                else:
                    script = "Other"
                non_chinese_chars.append((char, i, script))
            if non_chinese_chars:
                unique_scripts = set(script for _, _, script in non_chinese_chars)
                sample_chars = []
                for script in unique_scripts:
                    chars_of_script = [char for char, _, s in non_chinese_chars if s == script][:3]
                    sample_chars.append(f"{script}: {', '.join(chars_of_script)}")
                reason = f"Non-Chinese characters found ({', '.join(sample_chars)})"
                results.append({
                    'row': idx + 2,
                    'file': row["File"],
                    'stringid': row["StringId"],
                    'strorigin': strorigin[:50] + '...' if len(strorigin) > 50 else strorigin,
                    'str': strval[:50] + '...' if len(strval) > 50 else strval,
                    'full_str': strval,
                    'reason': reason,
                    'non_chinese_chars': non_chinese_chars
                })
                flagged_rows.append(row)

        if progress_queue and ((idx+1) % 100 == 0 or (time.time() - last_print_time > 0.5)):
            percent = ((idx+1)/total_rows)*100
            progress_msg = f"Checking language consistency: {idx+1}/{total_rows} ({percent:.1f}%)
"
            progress_msg += f"Mismatches found so far: {len(results)}
"
            progress_queue.put({'type': 'progress', 'text': progress_msg})
            last_print_time = time.time()

    xml_path = None
    if output_folder and results:
        xml_path = save_flagged_rows_as_xml(flagged_rows, output_folder, lang_dropdown_name)
    return results, len(df), len(results), df, xml_path

def save_flagged_rows_as_xml(flagged_rows, output_folder, lang_dropdown_name):
    """
    Saves flagged rows preserving the EXACT original element structure.
    Optimized: parses each file only once and caches LocStr elements.
    """
    from collections import defaultdict

    # Step 1: Build a mapping (file, StringId) -> LocStr element
    file_to_stringids = defaultdict(set)
    for row in flagged_rows:
        file_to_stringids[row["File"]].add(row["StringId"])

    file_stringid_to_elem = {}
    for file_path, stringids in file_to_stringids.items():
        try:
            parser = etree.XMLParser(remove_blank_text=True, recover=True)
            tree = etree.parse(file_path, parser)
            file_root = tree.getroot()
            for locstr in file_root.xpath('.//LocStr'):
                sid = locstr.get("StringId")
                if sid in stringids:
                    # Store a deep copy to avoid lxml reference issues
                    file_stringid_to_elem[(file_path, sid)] = etree.fromstring(etree.tostring(locstr))
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")

    # Step 2: Write all flagged LocStrs to the output XML
    root = etree.Element("root")
    for row in flagged_rows:
        key = (row["File"], row["StringId"])
        elem = file_stringid_to_elem.get(key)
        if elem is not None:
            root.append(elem)
        else:
            # Fallback: create minimal LocStr if not found
            fallback = etree.Element("LocStr")
            fallback.set("StringId", row["StringId"])
            fallback.set("StrOrigin", row.get("StrOrigin", ""))
            fallback.set("Str", row.get("Str", ""))
            root.append(fallback)

    # Step 3: Write the output XML
    safe_lang = re.sub(r'[\s()]+', '_', lang_dropdown_name).strip('_')
    xml_filename = f"{safe_lang}_langmismatch_flagged.xml"
    xml_path = os.path.join(output_folder, xml_filename)
    tree = etree.ElementTree(root)
    tree.write(xml_path, encoding="utf-8", xml_declaration=False, pretty_print=True)
    return xml_path

# --- HALLUCINATION DETECTION LOGIC ---

def count_words(text):
    text = str(text).strip()
    if not text:
        return 0
    return len(text.split())

def count_characters(text):
    text = str(text).strip()
    if not text:
        return 0
    return len(text.replace(" ", ""))

def check_length_ratio(korean, translated, expected_ratio, lang_code):
    korean = str(korean).strip()
    translated = str(translated).strip()
    if not translated or not korean:
        return False
    if lang_code in ['zh-cn', 'zh-tw', 'ja']:
        korean_count = count_characters(korean)
        translated_count = count_characters(translated)
        min_ratio = CHAR_RATIO_MIN
        max_ratio = CHAR_RATIO_MAX
    else:
        korean_count = count_words(korean)
        translated_count = count_words(translated)
        min_ratio = WORD_RATIO_MIN
        max_ratio = WORD_RATIO_MAX
    if translated_count == 0 or korean_count == 0:
        return True
    ratio = translated_count / korean_count
    if ratio < min_ratio or ratio > max_ratio:
        return False
    return True

def check_newline_discrepancy(strorigin, strval):
    """
    Flags if the translation has MORE newline tokens (<br/>, &lt;br/&gt;, <br>, &lt;br&gt;)
    than the original text.
    """
    def count_br(text):
        return (
            text.count("<br/>") +
            text.count("&lt;br/&gt;") +
            text.count("<br>") +
            text.count("&lt;br&gt;")
        )

    origin_br_count = count_br(strorigin)
    trans_br_count = count_br(strval)

    return trans_br_count > origin_br_count

def check_ai_error_phrase(strval, lang_code):
    strval_lower = strval.lower()
    phrases = set(AI_ERROR_PHRASES.get('en', []))
    if lang_code in AI_ERROR_PHRASES and lang_code != 'en':
        phrases.update(AI_ERROR_PHRASES[lang_code])
    for phrase in phrases:
        if phrase in strval_lower:
            return True
    return False

def analyze_translation(strorigin, strval, lang_code, expected_ratio):
    issues = []
    if not check_length_ratio(strorigin, strval, expected_ratio, lang_code):
        issues.append("Length issue")
    if check_newline_discrepancy(strorigin, strval):
        issues.append("Unexpected newline or slash in translation")
    if check_ai_error_phrase(strval, lang_code):
        issues.append("AI error phrase detected")
    return issues

# --- MAIN ANALYSIS LOGIC ---

def analyze_folder(folder, lang_code, expected_ratio, progress_queue=None):
    df = extract_all_locstrs_from_folder(folder)
    df = preprocess_dataframe(df)
    results = []
    hallucination_count = 0
    total_rows = len(df)
    last_print_time = time.time()
    for idx, row in df.iterrows():
        strorigin = str(row["StrOrigin"])
        strval = str(row["Str"])
        issues = analyze_translation(strorigin, strval, lang_code, expected_ratio)
        if issues:
            hallucination_count += 1
            result_entry = {
                'row': idx + 2,
                'issues': issues,
                'file': row["File"],
                'stringid': row["StringId"],
                'strorigin': strorigin[:50] + '...' if len(strorigin) > 50 else strorigin,
                'str': strval[:50] + '...' if len(strval) > 50 else strval
            }
            results.append(result_entry)
        if progress_queue and ((idx+1) % 200 == 0 or (time.time() - last_print_time > 0.5)):
            percent = ((idx+1)/total_rows)*100
            progress_msg = f"Processing row {idx+1}/{total_rows} ({percent:.1f}%)
"
            progress_msg += f"Potential hallucinations found so far: {hallucination_count}
"
            progress_queue.put({'type': 'progress', 'text': progress_msg})
            last_print_time = time.time()
    return results, total_rows, hallucination_count, df

def save_results(results, df, output_folder):
    if not results:
        return
    output_data = []
    for r in results:
        row_idx = r['row'] - 2
        if 0 <= row_idx < len(df):
            row = df.iloc[row_idx]
            issues_formatted = '
'.join(r['issues'])
            output_data.append({
                'StringId': row["StringId"],
                'StrOrigin': row["StrOrigin"],
                'Str': row["Str"],
                'Issues': issues_formatted
            })
    output_df = pd.DataFrame(output_data)
    output_path = os.path.join(output_folder, 'hallucination_report.xlsx')
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        output_df.to_excel(writer, index=False, sheet_name='Flagged Translations')
        worksheet = writer.sheets['Flagged Translations']
        worksheet.column_dimensions['A'].width = 25
        worksheet.column_dimensions['B'].width = 40
        worksheet.column_dimensions['C'].width = 40
        worksheet.column_dimensions['D'].width = 25
        from openpyxl.styles import Alignment
        for row in worksheet.iter_rows(min_row=2, max_row=len(output_df)+1):
            for cell in row:
                cell.alignment = Alignment(wrap_text=True, vertical='top')
    return output_path

# --- GUI ---

class HallucinationDetectorXML:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Translation Hallucination Detector (XML Folder)")
        self.root.geometry("650x540")
        self.languages = LANGUAGES
        self.progress_queue = queue.Queue()
        self.setup_gui()

    def setup_gui(self):
        title = tk.Label(self.root, text="Translation Hallucination Detector (XML Folder)", font=("Arial", 16, "bold"))
        title.pack(pady=20)
        lang_frame = tk.Frame(self.root)
        lang_frame.pack(pady=10)
        tk.Label(lang_frame, text="Target Language:").pack(side=tk.LEFT, padx=5)
        self.lang_var = tk.StringVar(value="English (EN)")
        self.lang_dropdown = ttk.Combobox(lang_frame, textvariable=self.lang_var,
                                          values=list(self.languages.keys()),
                                          width=30, state="readonly")
        self.lang_dropdown.pack(side=tk.LEFT)
        folder_frame = tk.Frame(self.root)
        folder_frame.pack(pady=10)
        tk.Label(folder_frame, text="XML Folder:").pack(side=tk.LEFT, padx=5)
        self.folder_var = tk.StringVar()
        self.folder_entry = tk.Entry(folder_frame, textvariable=self.folder_var, width=50, state="readonly")
        self.folder_entry.pack(side=tk.LEFT)
        self.browse_btn = tk.Button(folder_frame, text="Browse", command=self.browse_folder)
        self.browse_btn.pack(side=tk.LEFT, padx=5)
        output_frame = tk.Frame(self.root)
        output_frame.pack(pady=10)
        tk.Label(output_frame, text="Output Folder:").pack(side=tk.LEFT, padx=5)
        self.output_var = tk.StringVar()
        self.output_entry = tk.Entry(output_frame, textvariable=self.output_var, width=50, state="readonly")
        self.output_entry.pack(side=tk.LEFT)
        self.output_browse_btn = tk.Button(output_frame, text="Browse", command=self.browse_output_folder)
        self.output_browse_btn.pack(side=tk.LEFT, padx=5)
        self.analyze_btn = tk.Button(self.root, text="Analyze XML Folder",
                                     command=self.process_folder_threaded,
                                     bg="#4CAF50", fg="white", font=("Arial", 12),
                                     width=25, height=2)
        self.analyze_btn.pack(pady=20)
        self.langcheck_btn = tk.Button(
            self.root, text="Check Language Consistency",
            command=self.process_langcheck_threaded,
            bg="#2196F3", fg="white", font=("Arial", 12),
            width=25, height=2
        )
        self.langcheck_btn.pack(pady=5)
        tk.Label(self.root, text="Results:", font=("Arial", 12)).pack()
        self.result_frame = tk.Frame(self.root)
        self.result_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        self.result_text = tk.Text(self.result_frame, height=12, width=80)
        scrollbar = tk.Scrollbar(self.result_frame, command=self.result_text.yview)
        self.result_text.config(yscrollcommand=scrollbar.set)
        self.result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def browse_folder(self):
        folder = filedialog.askdirectory(title="Select XML Folder")
        if folder:
            self.folder_var.set(folder)

    def browse_output_folder(self):
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_var.set(folder)

    def process_folder_threaded(self):
        folder = self.folder_var.get()
        output_folder = self.output_var.get()
        if not folder or not output_folder:
            messagebox.showerror("Error", "Please select both XML folder and output folder.")
            return
        self.analyze_btn.config(state=tk.DISABLED)
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, "Processing XML folder in background...

")
        self.root.update()
        thread = threading.Thread(target=self.process_folder_worker, args=(folder, output_folder))
        thread.daemon = True
        thread.start()
        self.root.after(100, self.check_progress_queue)

    def process_langcheck_threaded(self):
        folder = self.folder_var.get()
        output_folder = self.output_var.get()
        if not folder or not output_folder:
            messagebox.showerror("Error", "Please select both XML folder and output folder.")
            return
        selected_lang = self.lang_var.get()
        lang_code, _ = self.languages[selected_lang]
        english_reference_path = None
        if lang_code in {'fr', 'de', 'es', 'es-mx', 'pt', 'it', 'tr', 'pl', 'ru'}:
            english_reference_path = filedialog.askopenfilename(
                title="Select English Reference XML",
                filetypes=[("XML files", "*.xml")]
            )
            if not english_reference_path:
                messagebox.showerror("Error", "English reference XML is required for this language check.")
                return
        self.langcheck_btn.config(state=tk.DISABLED)
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, "Checking language consistency in background...

")
        self.root.update()
        thread = threading.Thread(
            target=self.process_langcheck_worker,
            args=(folder, output_folder, english_reference_path)
        )
        thread.daemon = True
        thread.start()
        self.root.after(100, self.check_progress_queue)

    def check_progress_queue(self):
        try:
            while True:
                msg = self.progress_queue.get_nowait()
                if msg['type'] == 'progress':
                    self.result_text.delete(1.0, tk.END)
                    self.result_text.insert(tk.END, msg['text'])
                elif msg['type'] == 'done':
                    self.display_results(msg['results'], msg['total_rows'], msg['hallucination_count'], msg['output_path'])
                    self.analyze_btn.config(state=tk.NORMAL)
                elif msg['type'] == 'langcheck_done':
                    self.display_langcheck_results(
                        msg['results'],
                        msg['total_rows'],
                        msg['mismatch_count'],
                        msg.get('xml_path')
                    )
                    self.langcheck_btn.config(state=tk.NORMAL)
                elif msg['type'] == 'error':
                    messagebox.showerror("Error", msg['text'])
                    self.analyze_btn.config(state=tk.NORMAL)
                    self.langcheck_btn.config(state=tk.NORMAL)
        except queue.Empty:
            self.root.after(100, self.check_progress_queue)

    def process_folder_worker(self, folder, output_folder):
        try:
            selected_lang = self.lang_var.get()
            lang_code, expected_ratio = self.languages[selected_lang]
            results, total_rows, hallucination_count, df = analyze_folder(
                folder, lang_code, expected_ratio, self.progress_queue
            )
            output_path = None
            if hallucination_count > 0:
                output_path = save_results(results, df, output_folder)
            self.progress_queue.put({
                'type': 'done',
                'results': results,
                'total_rows': total_rows,
                'hallucination_count': hallucination_count,
                'output_path': output_path
            })
        except Exception as e:
            self.progress_queue.put({'type': 'error', 'text': f"Error processing folder: {str(e)}"})

    def process_langcheck_worker(self, folder, output_folder, english_reference_path=None):
        try:
            selected_lang = self.lang_var.get()
            lang_code, _ = self.languages[selected_lang]
            results, total_rows, mismatch_count, df, xml_path = check_language_consistency(
                folder, lang_code, self.progress_queue, output_folder, selected_lang, english_reference_path
            )
            self.progress_queue.put({
                'type': 'langcheck_done',
                'results': results,
                'total_rows': total_rows,
                'mismatch_count': mismatch_count,
                'xml_path': xml_path
            })
        except Exception as e:
            self.progress_queue.put({'type': 'error', 'text': f"Error in language check: {str(e)}"})

    def display_results(self, results, total_rows, hallucination_count, output_path):
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, f"Total LocStrs analyzed: {total_rows}
")
        self.result_text.insert(tk.END, f"Potential hallucinations found: {hallucination_count}
")
        self.result_text.insert(tk.END, f"Accuracy rate: {((total_rows-hallucination_count)/total_rows*100):.1f}%

")
        if results:
            self.result_text.insert(tk.END, "Issues found:
" + "="*60 + "

")
            for r in results[:10]:
                self.result_text.insert(tk.END, f"Row {r['row']} (File: {os.path.basename(r['file'])}, StringId: {r['stringid']}):
")
                self.result_text.insert(tk.END, f"Issues: {', '.join(r['issues'])}
")
                self.result_text.insert(tk.END, f"StrOrigin: {r['strorigin']}
")
                self.result_text.insert(tk.END, f"Str: {r['str']}
")
                self.result_text.insert(tk.END, "-"*60 + "
")
            if len(results) > 10:
                self.result_text.insert(tk.END, f"
...and {len(results)-10} more issues.
")
            if output_path:
                self.result_text.insert(tk.END, f"
Check '{output_path}' for full details.")
        else:
            self.result_text.insert(tk.END, "No hallucinations detected! ✓")

    def display_langcheck_results(self, results, total_rows, mismatch_count, xml_path=None):
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, f"Total LocStrs analyzed: {total_rows}
")
        self.result_text.insert(tk.END, f"Strings with language mismatch: {mismatch_count}

")
        if results:
            self.result_text.insert(tk.END, "Mismatches found:
" + "="*60 + "

")
            for r in results[:10]:
                self.result_text.insert(tk.END, f"Row {r['row']} (File: {os.path.basename(r['file'])}, StringId: {r['stringid']}):
")
                self.result_text.insert(tk.END, f"Issue: {r['reason']}
")
                self.result_text.insert(tk.END, f"StrOrigin: {r['strorigin']}
")
                self.result_text.insert(tk.END, f"Str: {r['str']}
")
                self.result_text.insert(tk.END, "-"*60 + "
")
            if len(results) > 10:
                self.result_text.insert(tk.END, f"
...and {len(results)-10} more mismatches.
")
            if xml_path:
                self.result_text.insert(tk.END, f"
Flagged entries XML: '{xml_path}'")
        else:
            self.result_text.insert(tk.END, "All translations are in the correct language! ✓")

# --- MAIN ---

def main():
    root = tk.Tk()
    app = HallucinationDetectorXML(root)
    root.mainloop()

if __name__ == "__main__":
    main()