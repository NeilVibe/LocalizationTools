#!/usr/bin/env python3
# Remove XML declaration and DOCTYPE
import os
import sys
import re
import logging
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from lxml import etree
import shutil
import datetime
import html
import openpyxl
import stat


# Remove XML declaration and DOCTYPE
# --- XML Utilities ---

def fix_bad_entities(xml_text):
    return re.sub(r'&(?!lt;|gt;|amp;|apos;|quot;)', '&amp;', xml_text)

def replace_newlines_text(text):
    """Replace newlines with proper XML representation for any text"""
    if text is None:
        return text
    # Replace literal newlines
    cleaned = text.replace('\n', '&lt;br/&gt;')
    # Replace escaped newlines
    cleaned = cleaned.replace('\\n', '&lt;br/&gt;')
    return cleaned

def preprocess_tmx_content(raw_content):
    """
    Pre-process TMX content with simple regex replacements
    This happens BEFORE any XML parsing
    """
    # Replace newlines inside <seg> tags with &lt;br/&gt;
    def replace_in_seg(match):
        seg_content = match.group(1)
        # Replace newlines with &lt;br/&gt;
        cleaned = seg_content.replace('\n', '&lt;br/&gt;')
        cleaned = cleaned.replace('\\n', '&lt;br/&gt;')
        return f'<seg>{cleaned}</seg>'
    
    # Apply regex to find and clean all <seg> contents
    cleaned_content = re.sub(
        r'<seg>(.*?)</seg>', 
        replace_in_seg, 
        raw_content, 
        flags=re.DOTALL
    )
    
    return cleaned_content

def make_file_writable(path):
    try:
        os.chmod(path, 0o666)
    except Exception:
        pass
        
def get_all_xml_files(input_folder):
    xml_files = []
    for dirpath, _, filenames in os.walk(input_folder):
        for file in filenames:
            if file.lower().endswith(".xml"):
                xml_files.append(os.path.join(dirpath, file))
    return xml_files

def parse_xml_file(file_path):
    import re
    try:
        txt = open(file_path, encoding='utf-8').read()
    except Exception as e:
        print(f"[ERROR] Error reading {file_path!r}: {e}")
        return None
    txt = re.sub(r'&(?!lt;|gt;|amp;|apos;|quot;)', '&amp;', txt)
    wrapped = "<ROOT>\n" + txt + "\n</ROOT>"
    rec_parser = etree.XMLParser(recover=True)
    try:
        recovered = etree.fromstring(wrapped.encode('utf-8'), parser=rec_parser)
    except etree.XMLSyntaxError as e:
        print(f"[ERROR] Fatal parse error (recover mode) on {file_path!r}: {e}")
        return None
    strict_parser = etree.XMLParser(recover=False)
    blob = etree.tostring(recovered, encoding='utf-8')
    try:
        return etree.fromstring(blob, parser=strict_parser)
    except etree.XMLSyntaxError:
        return recovered

def is_korean(text):
    if not text:
        return False
    return bool(re.search(r'[\uac00-\ud7af\u1100-\u11ff\u3130-\u318f]', text))

def postprocess_tmx_string(xml_str):
    """
    1. NEW rule for {Staticinfo:Knowledge ... # ... } → <bpt>/<ept> (per-segment counter)
       – runs BEFORE generic {...} placeholder conversion
    2. Existing placeholder conversions → <ph>
    3. Minor clean-ups (spaces after <ph> br etc.)
    4. NEW: Trim trailing whitespace at the end of each <seg> content
    """
    import re
    import html

    # ------------------------------------------------------------------
    # Helper : apply regex *only* outside already-made <ph> ... </ph> tags
    # ------------------------------------------------------------------
    def replace_outside_ph(pattern, repl, text):
        parts = []
        last = 0
        for m in re.finditer(r'<ph>.*?</ph>', text, flags=re.DOTALL):
            gap = text[last:m.start()]
            parts.append(re.sub(pattern, repl, gap))
            parts.append(m.group(0))          # keep the <ph> block untouched
            last = m.end()
        parts.append(re.sub(pattern, repl, text[last:]))  # tail
        return ''.join(parts)

    # -------------------------------------------------------
    # 1.  NEW Staticinfo:Knowledge  →  <bpt>/<ept> PAIRS
    # -------------------------------------------------------
    sk_pattern = re.compile(r'\{Staticinfo:Knowledge:([^#}]+)#([^}]+)\}')

    seg_pattern = re.compile(r'(<seg[^>]*>)(.*?)(</seg>)', re.DOTALL)

    def seg_repl(seg_match):
        open_tag, content, close_tag = seg_match.groups()
        counter = {'i': 0}  # local counter per segment

        def sk_repl(m):
            counter['i'] += 1
            i = counter['i']
            ident = m.group(1)
            inner_txt = m.group(2)

            bpt = (
                f"<bpt i='{i}'>&lt;mq:rxt displaytext=&quot;"
                f"{html.escape(ident)}&quot; "
                f"val=&quot;{{Staticinfo:Knowledge:{html.escape(ident)}#&quot;&gt;</bpt>"
            )
            ept = (
                f"<ept i='{i}'>&lt;/mq:rxt displaytext=&quot;}}&quot; "
                f"val=&quot;}}&quot;&gt;</ept>"
            )
            return f"{bpt}{inner_txt}{ept}"

        new_content = replace_outside_ph(sk_pattern, sk_repl, content)
        return f"{open_tag}{new_content}{close_tag}"

    xml_str = seg_pattern.sub(seg_repl, xml_str)

    # -------------------------
    # 2.  <ph>  PLACEHOLDERS
    # -------------------------
    # 2-A  %N#
    def _repl_pct(m):
        num = m.group(1)
        return f'<ph>&lt;mq:rxt-req displaytext="Param{num}" val="%{num}#" /&gt;</ph>'
    xml_str = replace_outside_ph(r'%(\d)#', _repl_pct, xml_str)

    # 2-B  {...}  — exclude Staticinfo:Knowledge so it’s not double-processed
    def _repl_br(m):
        inner = m.group(1)
        return f'<ph>&lt;mq:rxt-req displaytext="{inner}" val="{{{inner}}}" /&gt;</ph>'
    xml_str = replace_outside_ph(r'\{(?!Staticinfo:Knowledge:)([^}]+)\}', _repl_br, xml_str)

    # 2-C  \X
    def _repl_bs(m):
        c = m.group(1)
        return f'<ph>&lt;mq:rxt displaytext="\\{c}" val="\\{c}" /&gt;</ph>'
    xml_str = replace_outside_ph(r'\\(\w)', _repl_bs, xml_str)

    # 2-D  &lt;br/&gt;
    xml_str = replace_outside_ph(
        r'&lt;br/&gt;',
        lambda _: '<ph>&lt;mq:rxt displaytext="br" val="&lt;br/&gt;" /&gt;</ph>',
        xml_str
    )

    # 2-E  &amp;desc;
    xml_str = replace_outside_ph(
        r'&amp;desc;',
        lambda _: '<ph>&lt;mq:rxt-req displaytext="desc" val="&amp;desc;" /&gt;</ph>',
        xml_str
    )

    # -------------------------------------------------
    # 3.  Clean-up: spaces after <ph> &lt;br/&gt;  → fmt
    # -------------------------------------------------
    def _repl_spaces(m):
        br_ph, spaces, nxt = m.groups()
        return f"{br_ph}<ph type='fmt'>{spaces}</ph>{nxt}"

    xml_str = re.sub(
        r'(<ph>&lt;mq:rxt displaytext="br" val="&lt;br/&gt;" /&gt;</ph>)(\s{2,})(\S)',
        _repl_spaces,
        xml_str
    )

    # -------------------------------------------------
    # 4.  NEW: Trim trailing whitespace at end of <seg>
    # -------------------------------------------------
    def trim_trailing_ws_in_seg(m):
        open_tag, content, close_tag = m.groups()
        return f"{open_tag}{content.rstrip()}{close_tag}"

    xml_str = re.sub(r'(<seg[^>]*>)(.*?)(</seg>)', trim_trailing_ws_in_seg, xml_str, flags=re.DOTALL)

    return xml_str


def combine_xmls_to_tmx(input_folder, output_file, target_language, postprocess=True):
    """
    Combines all XML files in `input_folder` into a TMX file.

    •  Main string TUs:
         –  Keep ONLY the newest duplicate (based on “file-mtime”) for each
            (StrOrigin , StringId) pair.
         –  StrOrigin *may be empty* – we now allow empty Korean source text
            as long as BOTH Str (translation) and StringId are non-empty.
         –  Translation (Str) must NOT contain Korean.

    •  Description TUs:
         –  NO de-duplication – every valid description TU is kept.
    """
    try:
        logging.info(f"Starting to process input folder: {input_folder}")
        xml_files = get_all_xml_files(input_folder)
        total_files = len(xml_files)
        print(f"[TMX] Total XML files found: {total_files}")

        if not xml_files:
            logging.error("[TMX] No XML files found.")
            return False

        # ------------------------------------------------------------------
        # Build empty TMX skeleton
        # ------------------------------------------------------------------
        tmx = etree.Element("tmx", version="1.4")
        header_attr = {
            "creationtool":        "CombinedXMLConverter",
            "creationtoolversion": "1.1",
            "segtype":             "sentence",
            "o-tmf":               "UTF-8",
            "adminlang":           "en",
            "srclang":             "ko",
            "datatype":            "PlainText"
        }
        etree.SubElement(tmx, "header", **header_attr)
        body = etree.SubElement(tmx, "body")

        XML_NS = "http://www.w3.org/XML/1998/namespace"
        target_lang_code = target_language.lower()

        # --------------------------------------------------------------
        #   Containers for main / description TUs
        # --------------------------------------------------------------
        main_tu_map = {}   # (korean_text, string_id) → (mtime, tu_element)
        desc_tu_list = []  # keep ALL description TUs (no de-dup)

        # --------------------------------------------------------------
        #   Walk through every XML file
        # --------------------------------------------------------------
        for idx, xml_file_path in enumerate(xml_files, 1):
            print(f"[TMX] Processing file {idx} of {total_files}: {xml_file_path}")

            try:
                if os.path.getsize(xml_file_path) == 0:
                    continue
            except OSError:
                continue

            xml_root = parse_xml_file(xml_file_path)
            if xml_root is None:
                continue

            doc_name  = os.path.basename(xml_file_path)
            file_mtime = os.path.getmtime(xml_file_path)

            for loc in xml_root.iter("LocStr"):
                string_id   = (loc.get("StringId") or "").strip()
                korean_text = replace_newlines_text(loc.get("StrOrigin", ""))
                target_text = replace_newlines_text(loc.get("Str", ""))
                desc_origin = replace_newlines_text(loc.get("DescOrigin", "").strip())
                desc_text   = replace_newlines_text(loc.get("Desc",       "").strip())

                # Clean up legacy “&desc;” markers inside Str/StrOrigin
                korean_text = korean_text.replace("&amp;desc;", "").replace("&desc;", "")
                target_text = target_text.replace("&amp;desc;", "").replace("&desc;", "")

                # ──────────────────────────────────────────
                #  MAIN TRANSLATION UNIT  (with new rules)
                # ──────────────────────────────────────────
                #  –  ALLOW korean_text == "" (empty)
                #  –  REQUIRE translation text (non-empty, non-Korean)
                #  –  REQUIRE non-empty StringId
                if (target_text
                        and string_id
                        and not is_korean(target_text)):
                    tu = etree.Element(
                        "tu",
                        creationid="CombinedConversion",
                        changeid="CombinedConversion"
                    )

                    # Source (KO) – may be empty string
                    tuv_ko = etree.SubElement(
                        tu, "tuv", **{f"{{{XML_NS}}}lang": "ko"}
                    )
                    etree.SubElement(tuv_ko, "seg").text = korean_text or ""

                    # Target
                    tuv_tgt = etree.SubElement(
                        tu, "tuv", **{f"{{{XML_NS}}}lang": target_lang_code}
                    )
                    etree.SubElement(tuv_tgt, "seg").text = target_text

                    etree.SubElement(tu, "prop", type="x-document").text = doc_name
                    etree.SubElement(tu, "prop", type="x-context").text  = string_id

                    # De-duplication key ― note: korean_text may be ""
                    key = (korean_text, string_id)

                    # Keep the NEWEST TU for each key
                    if key not in main_tu_map or file_mtime > main_tu_map[key][0]:
                        main_tu_map[key] = (file_mtime, tu)

                # ──────────────────────────────────────────
                #  DESCRIPTION TRANSLATION UNIT  (unchanged)
                # ──────────────────────────────────────────
                if (string_id
                        and desc_origin
                        and desc_text
                        and not is_korean(desc_text)):

                    # Skip pure “&desc;” placeholders
                    if (desc_origin.strip() in ("&desc;", "&amp;desc;")
                            and desc_text.strip() in ("&desc;", "&amp;desc;")):
                        continue

                    # Ensure Korean side has the &desc; prefix
                    if (not desc_origin.startswith("&desc;")
                            and not desc_origin.startswith("&amp;desc;")):
                        desc_origin = "&desc;" + desc_origin

                    desc_tu = etree.Element(
                        "tu",
                        creationid="PAAT",
                        changeid="PAAT"
                    )

                    tuv_ko_d = etree.SubElement(
                        desc_tu, "tuv", **{f"{{{XML_NS}}}lang": "ko"}
                    )
                    tuv_tgt_d = etree.SubElement(
                        desc_tu, "tuv", **{f"{{{XML_NS}}}lang": target_lang_code}
                    )

                    if postprocess:
                        # MemoQ placeholder wrapping
                        seg_ko = etree.SubElement(tuv_ko_d, "seg")
                        ph_ko = etree.SubElement(seg_ko, "ph")
                        ph_ko.text = '<mq:rxt-req displaytext="desc" val="&amp;desc;" />'
                        ph_ko.tail = desc_origin.replace("&amp;desc;", "").replace("&desc;", "")

                        seg_tgt = etree.SubElement(tuv_tgt_d, "seg")
                        ph_tgt = etree.SubElement(seg_tgt, "ph")
                        ph_tgt.text = '<mq:rxt-req displaytext="desc" val="&amp;desc;" />'
                        ph_tgt.tail = desc_text.replace("&amp;desc;", "").replace("&desc;", "")
                    else:
                        etree.SubElement(tuv_ko_d,  "seg").text = desc_origin
                        etree.SubElement(tuv_tgt_d, "seg").text = desc_text

                    etree.SubElement(desc_tu, "prop", type="x-document").text = doc_name
                    etree.SubElement(desc_tu, "prop", type="x-context").text  = string_id
                    desc_tu_list.append(desc_tu)

        # ------------------------------------------------------------------
        #  WRITE OUT TMX
        # ------------------------------------------------------------------
        for _, tu in main_tu_map.values():
            body.append(tu)
        for tu in desc_tu_list:
            body.append(tu)

        xml_bytes = etree.tostring(
            tmx, pretty_print=True, encoding='UTF-8', xml_declaration=True
        )
        xml_str = xml_bytes.decode('utf-8')

        if postprocess:
            xml_str = postprocess_tmx_string(xml_str)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(xml_str)

        print(f"[TMX] Successfully combined into: {output_file}")
        return True

    except Exception as e:
        logging.error(f"[TMX] Error during combination: {e}", exc_info=True)
        print(f"[TMX] Error during combination: {e}")
        return False
        
        
def batch_normal_tmx_from_folders(input_folders, output_dir, target_language):
    """
    For each folder in input_folders, create a NORMAL TMX (no postprocess)
    and save it to output_dir with the name <FOLDERNAME>.tmx.
    Returns a list of (input_folder, output_file, success) tuples.
    """
    results = []
    for folder in input_folders:
        folder_name = os.path.basename(os.path.normpath(folder))
        out_file = os.path.join(output_dir, f"{folder_name}.tmx")
        print(f"[BATCH] Processing: {folder} -> {out_file}")
        ok = combine_xmls_to_tmx(folder, out_file, target_language, postprocess=False)
        results.append((folder, out_file, ok))
    return results

        
        
def extract_korean_or_empty_translation(input_folder, output_file):
    logging.info(f"Extracting all LocStr with Korean in Str OR StrOrigin non-empty and Str empty from: {input_folder}")
    xml_files = get_all_xml_files(input_folder)
    total_files = len(xml_files)
    file_counter = 0
    count = 0
    root = etree.Element("AllKoreanOrEmptyLocStr")
    unique_strorigins = set()
    for xml_file_path in xml_files:
        file_counter += 1
        logging.info(f"[KOR-OR-EMPTY-EXTRACT] Processing file {file_counter} of {total_files}: {xml_file_path}")
        try:
            if os.path.getsize(xml_file_path) == 0:
                logging.debug(f"Skipping empty XML file: {xml_file_path}")
                continue
        except Exception as e:
            logging.error(f"Error getting file size for {xml_file_path}: {e}", exc_info=True)
            continue
        xml_root = parse_xml_file(xml_file_path)
        if xml_root is None:
            logging.debug(f"Skipping file due to parse error: {xml_file_path}")
            continue
        for loc in xml_root.iter("LocStr"):
            str_val = (loc.get("Str") or "")
            str_origin_val = (loc.get("StrOrigin") or "")
            if is_korean(str_val):
                root.append(etree.fromstring(etree.tostring(loc)))
                count += 1
                if str_origin_val:
                    unique_strorigins.add(str_origin_val)
            elif str_val == "" and str_origin_val != "":
                root.append(etree.fromstring(etree.tostring(loc)))
                count += 1
                unique_strorigins.add(str_origin_val)
    if count == 0:
        msg = "No <LocStr> with Korean in Str or StrOrigin non-empty and Str empty found."
        logging.error(msg)
        print(msg)
        return False
    concatenated = " ".join(unique_strorigins)
    word_list = concatenated.split()
    total_word_count = len(word_list)
    print(f"[KOR-OR-EMPTY-EXTRACT] TOTAL UNIQUE StrOrigin STRINGS: {len(unique_strorigins)}")
    print(f"[KOR-OR-EMPTY-EXTRACT] TOTAL WORD COUNT (unique StrOrigin, whitespace split): {total_word_count}")
    xml_bytes = etree.tostring(root, pretty_print=True, encoding='UTF-8', xml_declaration=False)
    xml_str   = xml_bytes.decode('utf-8')
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(xml_str)
        logging.info(f"Extracted {count} LocStrs into: {output_file}")
        print(f"[KOR-OR-EMPTY-EXTRACT] Successfully extracted {count} LocStrs into:\n{output_file}")
        return True
    except Exception as e:
        logging.error(f"Error writing extracted XML {output_file}: {e}", exc_info=True)
        print(f"[KOR-OR-EMPTY-EXTRACT] Error writing extracted XML {output_file}: {e}")
        return False

# --- NEW TMX FIX MULTI-FILE LOGIC ---

def fix_and_combine_tmx_files(input_tmx_paths, output_tmx_path):
    """
    Fixes one or more TMX files, combines them, and filters out TUs where the translation contains Korean.
    """
    logging.info(f"[TMX-FIX] Fixing and combining TMX files: {input_tmx_paths}")
    all_tus = []
    header_attrs = None
    target_langs = set()
    for tmx_path in input_tmx_paths:
        try:
            with open(tmx_path, "r", encoding="utf-8") as f:
                tmx_content = f.read()
        except Exception as e:
            logging.error(f"Error reading TMX file {tmx_path}: {e}", exc_info=True)
            print(f"[TMX-FIX] Error reading TMX file {tmx_path}: {e}")
            continue
        
        # Pre-process: Clean newlines in TMX content
        tmx_content = preprocess_tmx_content(tmx_content)
        
        # Remove XML declaration and DOCTYPE
        tmx_content = re.sub(r'^<\?xml[^>]*\?>\s*', '', tmx_content, flags=re.MULTILINE)
        tmx_content = re.sub(r'<!DOCTYPE[^>]*>\s*', '', tmx_content, flags=re.MULTILINE)
        fixed_content = postprocess_tmx_string(tmx_content)
        try:
            parser = etree.XMLParser(recover=True)
            tmx_root = etree.fromstring(fixed_content.encode('utf-8'), parser=parser)
        except Exception as e:
            logging.error(f"Error parsing TMX file {tmx_path}: {e}", exc_info=True)
            print(f"[TMX-FIX] Error parsing TMX file {tmx_path}: {e}")
            continue
        # Find header and body
        header = tmx_root.find("header")
        if header is not None and header_attrs is None:
            header_attrs = dict(header.attrib)
        body = tmx_root.find("body")
        if body is None:
            # Sometimes body is not found due to namespace, try to find with wildcard
            for elem in tmx_root.iter():
                if elem.tag.endswith("body"):
                    body = elem
                    break
        if body is None:
            logging.warning(f"[TMX-FIX] No <body> found in {tmx_path}, skipping.")
            continue
        # Collect all <tu> elements
        for tu in body.findall("tu"):
            all_tus.append(tu)
        # Try also with wildcard (in case of namespace)
        if not all_tus:
            for tu in body.iter():
                if tu.tag.endswith("tu"):
                    all_tus.append(tu)
        # For filtering, try to find target language(s)
        for tu in body.iter():
            for tuv in tu.findall("tuv"):
                lang = tuv.attrib.get("{http://www.w3.org/XML/1998/namespace}lang")
                if lang:
                    target_langs.add(lang)
    if not all_tus:
        msg = "[TMX-FIX] No translation units found in the selected TMX files."
        logging.error(msg)
        print(msg)
        return False

    # --- Filter out TUs where the translation (target) contains Korean ---
    # Try to determine the target language (if more than one, use all)
    # We'll assume the first non-ko language is the target
    filtered_tus = []
    for tu in all_tus:
        tuv_ko = None
        tuv_tgt = None
        tuvs = tu.findall("tuv")
        if not tuvs:
            # Try with wildcard
            tuvs = [t for t in tu.iter() if t.tag.endswith("tuv")]
        lang_map = {}
        for tuv in tuvs:
            lang = tuv.attrib.get("{http://www.w3.org/XML/1998/namespace}lang")
            if lang:
                lang_map[lang] = tuv
        # Find ko and non-ko
        tgt_lang = None
        for lang in lang_map:
            if lang != "ko":
                tgt_lang = lang
                break
        if not tgt_lang:
            # fallback: if only one lang, use it
            if lang_map:
                tgt_lang = list(lang_map.keys())[0]
        tuv_tgt = lang_map.get(tgt_lang)
        if tuv_tgt is None:
            continue
        seg_tgt = tuv_tgt.find("seg")
        if seg_tgt is None or seg_tgt.text is None:
            continue
        if is_korean(seg_tgt.text):
            continue  # FILTER OUT if translation contains Korean
        filtered_tus.append(tu)

    if not filtered_tus:
        msg = "[TMX-FIX] All translation units were filtered out (Korean in translation slot)."
        logging.error(msg)
        print(msg)
        return False

    # --- Compose new TMX ---
    tmx = etree.Element("tmx", version="1.4")
    if header_attrs is None:
        header_attrs = {
            "creationtool": "TMXFixer",
            "creationtoolversion": "1.0",
            "segtype": "sentence",
            "o-tmf": "UTF-8",
            "adminlang": "en",
            "srclang": "ko",
            "datatype": "PlainText"
        }
    etree.SubElement(tmx, "header", header_attrs)
    body = etree.SubElement(tmx, "body")
    for tu in filtered_tus:
        # Deep copy to avoid lxml reference issues
        body.append(etree.fromstring(etree.tostring(tu)))
    xml_bytes = etree.tostring(tmx, pretty_print=True, encoding='UTF-8', xml_declaration=True)
    xml_str   = xml_bytes.decode('utf-8')
    xml_str = postprocess_tmx_string(xml_str)
    try:
        with open(output_tmx_path, "w", encoding="utf-8") as f:
            f.write(xml_str)
        logging.info(f"[TMX-FIX] Fixed and combined TMX written to: {output_tmx_path}")
        print(f"[TMX-FIX] Successfully fixed and combined TMX:\n{output_tmx_path}")
        return True
    except Exception as e:
        logging.error(f"Error writing fixed TMX {output_tmx_path}: {e}", exc_info=True)
        print(f"[TMX-FIX] Error writing fixed TMX {output_tmx_path}: {e}")
        return False

# --- TMX CONCATENATE ONLY (FILTERED, DEDUPLICATED) ---
def concat_tmx_files_filtered(input_tmx_paths, output_tmx_path):
    """
    Concatenate TMX files: take all <tu> from all files, preserve first file's <header>.
    FILTER OUT any <tu> where the translation is empty or contains Korean.
    REMOVE DUPLICATE <tu> entries (based on source/target/context triple).
    If duplicate, keep the TU from the most recently modified file.
    """

    logging.info(f"[TMX-CONCAT] Concatenating TMX files (filtered, deduplicated, prefer most recent): {input_tmx_paths}")
    first_header_attrs = None
    tu_map = {}  # (src_text, tgt_text, string_id) -> (tu, file_mtime)
    found_header = False

    for idx, tmx_path in enumerate(input_tmx_paths):
        try:
            with open(tmx_path, "r", encoding="utf-8") as f:
                tmx_content = f.read()
        except Exception as e:
            logging.error(f"Error reading TMX file {tmx_path}: {e}", exc_info=True)
            print(f"[TMX-CONCAT] Error reading TMX file {tmx_path}: {e}")
            continue

        # Pre-process: Clean newlines in TMX content
        tmx_content = preprocess_tmx_content(tmx_content)

        # Important note : WE NEVER WANT XML declaration and DOCTYPE
        tmx_content = re.sub(r'^<\?xml[^>]*\?>\s*', '', tmx_content, flags=re.MULTILINE)
        tmx_content = re.sub(r'<!DOCTYPE[^>]*>\s*', '', tmx_content, flags=re.MULTILINE)
        try:
            parser = etree.XMLParser(recover=True)
            tmx_root = etree.fromstring(tmx_content.encode('utf-8'), parser=parser)
        except Exception as e:
            logging.error(f"Error parsing TMX file {tmx_path}: {e}", exc_info=True)
            print(f"[TMX-CONCAT] Error parsing TMX file {tmx_path}: {e}")
            continue
        # Find header and body
        if not found_header:
            header = tmx_root.find("header")
            if header is not None:
                first_header_attrs = dict(header.attrib)
                found_header = True
        body = tmx_root.find("body")
        if body is None:
            # Sometimes body is not found due to namespace, try to find with wildcard
            for elem in tmx_root.iter():
                if elem.tag.endswith("body"):
                    body = elem
                    break
        if body is None:
            logging.warning(f"[TMX-CONCAT] No <body> found in {tmx_path}, skipping.")
            continue
        # Collect all <tu> elements
        tus = []
        for tu in body.findall("tu"):
            tus.append(etree.fromstring(etree.tostring(tu)))
        # Try also with wildcard (in case of namespace)
        if not tus:
            for tu in body.iter():
                if tu.tag.endswith("tu"):
                    tus.append(etree.fromstring(etree.tostring(tu)))
        # FILTER: only keep <tu> where translation is not empty and does not contain Korean
        file_mtime = os.path.getmtime(tmx_path)
        for tu in tus:
            tuvs = tu.findall("tuv")
            if not tuvs:
                tuvs = [t for t in tu.iter() if t.tag.endswith("tuv")]
            lang_map = {}
            for tuv in tuvs:
                lang = tuv.attrib.get("{http://www.w3.org/XML/1998/namespace}lang")
                if lang:
                    lang_map[lang] = tuv
            tgt_lang = None
            for lang in lang_map:
                if lang != "ko":
                    tgt_lang = lang
                    break
            if not tgt_lang:
                if lang_map:
                    tgt_lang = list(lang_map.keys())[0]
            tuv_tgt = lang_map.get(tgt_lang)
            tuv_ko = lang_map.get("ko")
            if tuv_tgt is None or tuv_ko is None:
                continue
            seg_tgt = tuv_tgt.find("seg")
            seg_ko = tuv_ko.find("seg")
            if seg_tgt is None or seg_tgt.text is None:
                continue
            if not seg_tgt.text.strip():
                continue
            if is_korean(seg_tgt.text):
                continue
            src_text = seg_ko.text.strip() if seg_ko is not None and seg_ko.text else ""
            tgt_text = seg_tgt.text.strip()
            # --- Extract context (StringId) from <prop type="x-context"> ---
            string_id = ""
            for prop in tu.findall("prop"):
                if prop.attrib.get("type") == "x-context" and prop.text:
                    string_id = prop.text.strip()
                    break
            tu_key = (src_text, tgt_text, string_id)
            # Deduplication: keep the TU from the most recently modified file
            if tu_key in tu_map:
                prev_mtime = tu_map[tu_key][1]
                if file_mtime > prev_mtime:
                    tu_map[tu_key] = (tu, file_mtime)
            else:
                tu_map[tu_key] = (tu, file_mtime)

    all_tus = [v[0] for v in tu_map.values()]

    if not all_tus:
        msg = "[TMX-CONCAT] No translation units found in the selected TMX files (after filtering/deduplication)."
        logging.error(msg)
        print(msg)
        return False

    # Compose new TMX
    tmx = etree.Element("tmx", version="1.4")
    if first_header_attrs is None:
        first_header_attrs = {
            "creationtool": "TMXConcatenator",
            "creationtoolversion": "1.0",
            "segtype": "sentence",
            "o-tmf": "UTF-8",
            "adminlang": "en",
            "srclang": "ko",
            "datatype": "PlainText"
        }
    etree.SubElement(tmx, "header", first_header_attrs)
    body = etree.SubElement(tmx, "body")
    for tu in all_tus:
        body.append(tu)
    xml_bytes = etree.tostring(tmx, pretty_print=True, encoding='UTF-8', xml_declaration=True)
    xml_str   = xml_bytes.decode('utf-8')
    try:
        with open(output_tmx_path, "w", encoding="utf-8") as f:
            f.write(xml_str)
        logging.info(f"[TMX-CONCAT] Concatenated TMX written to: {output_tmx_path}")
        print(f"[TMX-CONCAT] Successfully concatenated TMX:\n{output_tmx_path}")
        return True
    except Exception as e:
        logging.error(f"[TMX-CONCAT] Error writing concatenated TMX {output_tmx_path}: {e}", exc_info=True)
        print(f"[TMX-CONCAT] Error writing concatenated TMX {output_tmx_path}: {e}")
        return False

# --- PAAT CHUNKED EXTRACTION ---

def extract_korean_or_empty_for_paat(input_folder, output_base_folder=None, max_chunk_size=500*1024):
    logging.info(f"[PAAT-EXTRACT] Extracting for PAAT from: {input_folder}")
    script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    master_folder = os.path.join(script_dir, "TO_SEND_TO_PAAT")
    if not os.path.exists(master_folder):
        os.makedirs(master_folder, exist_ok=True)
        logging.info(f"[PAAT-EXTRACT] Created master folder: {master_folder}")

    xml_files = get_all_xml_files(input_folder)
    all_locs = []
    count = 0
    for xml_file_path in xml_files:
        try:
            if os.path.getsize(xml_file_path) == 0:
                continue
        except Exception:
            continue
        xml_root = parse_xml_file(xml_file_path)
        if xml_root is None:
            continue
        for loc in xml_root.iter("LocStr"):
            str_val = (loc.get("Str") or "")
            str_origin_val = (loc.get("StrOrigin") or "")
            if is_korean(str_val):
                all_locs.append(etree.fromstring(etree.tostring(loc)))
                count += 1
            elif str_val == "" and str_origin_val != "":
                all_locs.append(etree.fromstring(etree.tostring(loc)))
                count += 1
    if not all_locs:
        msg = "[PAAT-EXTRACT] No LocStrs found for PAAT extraction."
        logging.error(msg)
        print(msg)
        return False

    base_name = os.path.basename(os.path.normpath(input_folder))
    dt_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    paat_folder_name = f"{base_name}_toSendtoPAAT_{dt_str}"
    paat_folder = os.path.join(master_folder, paat_folder_name)
    os.makedirs(paat_folder, exist_ok=True)

    chunks = []
    current_chunk = []
    current_size = 0
    for loc in all_locs:
        temp_root = etree.Element("AllKoreanOrEmptyLocStr")
        for l in current_chunk:
            temp_root.append(l)
        temp_root.append(loc)
        xml_bytes = etree.tostring(temp_root, pretty_print=True, encoding='UTF-8', xml_declaration=False)
        total_size = len(xml_bytes)
        if total_size > max_chunk_size and current_chunk:
            chunks.append(list(current_chunk))
            current_chunk = [loc]
        else:
            current_chunk.append(loc)
    if current_chunk:
        chunks.append(list(current_chunk))

    for idx, chunk in enumerate(chunks, 1):
        folder_group = ((idx-1)//10)*10 + 1
        folder_group_end = folder_group + 9
        group_folder = os.path.join(paat_folder, f"{folder_group}to{folder_group_end}")
        os.makedirs(group_folder, exist_ok=True)
        out_file = os.path.join(group_folder, f"{idx}.xml")
        root = etree.Element("AllKoreanOrEmptyLocStr")
        for loc in chunk:
            root.append(loc)
        xml_bytes = etree.tostring(root, pretty_print=True, encoding='UTF-8', xml_declaration=False)
        xml_str = xml_bytes.decode('utf-8')
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(xml_str)
        logging.info(f"[PAAT-EXTRACT] Wrote chunk {idx} ({len(chunk)} LocStrs) to {out_file}")

    print(f"[PAAT-EXTRACT] Extraction complete. {len(chunks)} files written in {paat_folder}")
    return paat_folder

# --- FUZZY MATCHING UTILITIES ---

def extract_stringids_from_file(file_path):
    root = parse_xml_file(file_path)
    if root is None:
        return set()
    sids = set()
    for elem in root.iter():
        if 'StringId' in elem.attrib:
            sids.add(elem.attrib['StringId'])
    return sids

def build_lookup_file_map_with_stringids(lookup_folder):
    file_map = {}
    stringid_map = {}
    for dirpath, _, filenames in os.walk(lookup_folder):
        for fname in filenames:
            full = os.path.join(dirpath, fname)
            file_map.setdefault(fname.lower(), []).append(full)
            if fname.lower().endswith(".xml"):
                stringid_map[full] = extract_stringids_from_file(full)
    return file_map, stringid_map

def fuzzy_best_match(source_file, candidates, stringid_map, threshold=0.2):
    src_ids = extract_stringids_from_file(source_file)
    if not src_ids:
        return None, 0.0
    best_ratio = 0.0
    best_path = None
    for cand in candidates:
        cand_ids = stringid_map.get(cand, set())
        if not cand_ids:
            continue
        inter = len(src_ids & cand_ids)
        union = len(src_ids | cand_ids)
        if union == 0:
            continue
        ratio = inter / union
        if ratio > best_ratio:
            best_ratio = ratio
            best_path = cand
    if best_ratio >= threshold and best_path:
        return best_path, best_ratio
    return None, 0.0

def file_has_korean_or_empty_condition(xml_file_path):
    xml_root = parse_xml_file(xml_file_path)
    if xml_root is None:
        return False
    for loc in xml_root.iter("LocStr"):
        str_val = (loc.get("Str") or "")
        str_origin_val = (loc.get("StrOrigin") or "")
        if is_korean(str_val):
            return True
        elif str_val == "" and str_origin_val != "":
            return True
    return False

def extract_korean_or_empty_locs_from_xml(xml_file_path):
    xml_root = parse_xml_file(xml_file_path)
    if xml_root is None:
        return []
    result = []
    for loc in xml_root.iter("LocStr"):
        str_val = (loc.get("Str") or "")
        str_origin_val = (loc.get("StrOrigin") or "")
        if is_korean(str_val):
            result.append(etree.fromstring(etree.tostring(loc)))
        elif str_val == "" and str_origin_val != "":
            result.append(etree.fromstring(etree.tostring(loc)))
    return result

def extract_whole_files_with_structure(input_folder_or_file, lookup_folder, output_base_folder, mode="full", files_to_process=None):
    """
    Extracts full or filtered XML files from a unified XML file or a folder of XMLs,
    matching each LocStr back to its original file in lookup_folder by StringId.
    Preserves lookup_folder's folder structure in output_base_folder.
    mode = "full"     -> copy full original file
    mode = "filtered" -> copy only LocStrs that are Korean or empty translation
    """
    logging.info(f"[STRUCTURED-EXTRACT] Building lookup index from: {lookup_folder}")

    # Build StringId -> lookup file path map
    stringid_to_file = {}
    for lfile in get_all_xml_files(lookup_folder):
        root = parse_xml_file(lfile)
        if root is None:
            continue
        for loc in root.iter("LocStr"):
            sid = loc.get("StringId")
            if sid:
                stringid_to_file[sid] = lfile

    copied_files = 0
    filtered_files = 0
    skipped_files = 0
    error_files = 0

    # Determine if input is a single unified XML file or a folder
    if os.path.isfile(input_folder_or_file) and input_folder_or_file.lower().endswith(".xml"):
        xml_files = [input_folder_or_file]
    else:
        xml_files = get_all_xml_files(input_folder_or_file)

    for xml_file_path in xml_files:
        root = parse_xml_file(xml_file_path)
        if root is None:
            logging.error(f"[STRUCTURED-EXTRACT] Failed to parse: {xml_file_path}")
            error_files += 1
            continue

        # Group LocStrs by their original lookup file
        file_to_locs = {}
        for loc in root.iter("LocStr"):
            s_val = loc.get("Str") or ""
            o_val = loc.get("StrOrigin") or ""
            if not (is_korean(s_val) or (s_val == "" and o_val != "")):
                continue
            sid = loc.get("StringId")
            if not sid:
                continue
            lookup_path = stringid_to_file.get(sid)
            if not lookup_path:
                logging.warning(f"[STRUCTURED-EXTRACT] No lookup match for StringId={sid}")
                continue
            file_to_locs.setdefault(lookup_path, []).append(etree.fromstring(etree.tostring(loc)))

        # Write out grouped files
        for lookup_path, locs in file_to_locs.items():
            rel_path = os.path.relpath(lookup_path, lookup_folder)
            out_path = os.path.join(output_base_folder, rel_path)
            os.makedirs(os.path.dirname(out_path), exist_ok=True)

            if mode == "full":
                try:
                    shutil.copy2(lookup_path, out_path)
                    copied_files += 1
                    logging.info(f"[STRUCTURED-EXTRACT] Copied full: {out_path}")
                except Exception as e:
                    logging.error(f"[STRUCTURED-EXTRACT] Copy error: {e}")
                    error_files += 1
            elif mode == "filtered":
                try:
                    new_root = etree.Element("root")
                    for l in locs:
                        new_root.append(l)
                    xml_bytes = etree.tostring(new_root, pretty_print=True, encoding='UTF-8', xml_declaration=False)
                    with open(out_path, "wb") as f:
                        f.write(xml_bytes)
                    filtered_files += 1
                    logging.info(f"[STRUCTURED-EXTRACT] Wrote filtered: {out_path}")
                except Exception as e:
                    logging.error(f"[STRUCTURED-EXTRACT] Filter write error: {e}")
                    error_files += 1
            else:
                logging.error(f"[STRUCTURED-EXTRACT] Unknown mode: {mode}")
                error_files += 1

    print(f"[STRUCTURED-EXTRACT] Extraction complete.")
    print(f"  Files copied (full): {copied_files}")
    print(f"  Files filtered: {filtered_files}")
    print(f"  Files skipped: {skipped_files}")
    print(f"  Files with errors: {error_files}")
    return (mode == "full" and copied_files > 0) or (mode == "filtered" and filtered_files > 0)

# --- NEW UPDATE TMX FUNCTIONS ---

def parse_tmx_to_tu_map(tmx_path):
    """
    Parse a TMX file and return a map of (korean, translation, stringid) -> tu element
    """
    logging.info(f"[UPDATE-TMX] Parsing TMX file: {tmx_path}")
    tu_map = {}
    try:
        with open(tmx_path, "r", encoding="utf-8") as f:
            tmx_content = f.read()
    except Exception as e:
        logging.error(f"Error reading TMX file {tmx_path}: {e}", exc_info=True)
        return tu_map
    
    # Pre-process: Clean newlines in TMX content
    tmx_content = preprocess_tmx_content(tmx_content)
    
    # Remove XML declaration and DOCTYPE
    tmx_content = re.sub(r'^<\?xml[^>]*\?>\s*', '', tmx_content, flags=re.MULTILINE)
    tmx_content = re.sub(r'<!DOCTYPE[^>]*>\s*', '', tmx_content, flags=re.MULTILINE)
    
    try:
        parser = etree.XMLParser(recover=True)
        tmx_root = etree.fromstring(tmx_content.encode('utf-8'), parser=parser)
    except Exception as e:
        logging.error(f"Error parsing TMX file {tmx_path}: {e}", exc_info=True)
        return tu_map
    
    body = tmx_root.find("body")
    if body is None:
        for elem in tmx_root.iter():
            if elem.tag.endswith("body"):
                body = elem
                break
    
    if body is None:
        logging.warning(f"[UPDATE-TMX] No <body> found in {tmx_path}")
        return tu_map
    
    XML_NS = "{http://www.w3.org/XML/1998/namespace}"
    
    for tu in body.iter():
        if not tu.tag.endswith("tu"):
            continue
            
        korean_text = ""
        target_text = ""
        string_id = ""
        
        # Extract text from tuv elements
        for tuv in tu.findall("tuv"):
            lang = tuv.attrib.get(f"{XML_NS}lang")
            seg = tuv.find("seg")
            if seg is not None and seg.text:
                if lang == "ko":
                    korean_text = seg.text.strip()
                elif lang:  # Any non-ko language is target
                    target_text = seg.text.strip()
        
        # Extract StringId from prop elements
        for prop in tu.findall("prop"):
            if prop.attrib.get("type") == "x-context" and prop.text:
                string_id = prop.text.strip()
                break
        
        if korean_text and target_text:
            key = (korean_text, target_text, string_id)
            tu_map[key] = etree.fromstring(etree.tostring(tu))
    
    logging.info(f"[UPDATE-TMX] Found {len(tu_map)} translation units in existing TMX")
    return tu_map

def create_update_tmx(input_folder, existing_tmx_path, output_file, target_language, postprocess=True):
    """
    Create a TMX containing only new/modified translation units compared to existing TMX
    """
    logging.info(f"[UPDATE-TMX] Creating update TMX from: {input_folder}")
    logging.info(f"[UPDATE-TMX] Comparing against existing TMX: {existing_tmx_path}")
    
    # Parse existing TMX
    existing_tu_map = parse_tmx_to_tu_map(existing_tmx_path)
    
    # Process input folder to get all TUs
    xml_files = get_all_xml_files(input_folder)
    total_files = len(xml_files)
    print(f"[UPDATE-TMX] Total XML files found: {total_files}")
    
    tmx = etree.Element("tmx", version="1.4")
    header_attr = {
        "creationtool": "CombinedXMLConverter-Update",
        "creationtoolversion": "1.0",
        "segtype": "sentence",
        "o-tmf": "UTF-8",
        "adminlang": "en",
        "srclang": "ko",
        "datatype": "PlainText"
    }
    etree.SubElement(tmx, "header", header_attr)
    body = etree.SubElement(tmx, "body")
    
    new_count = 0
    modified_count = 0
    unchanged_count = 0
    file_counter = 0
    
    XML_NS = "http://www.w3.org/XML/1998/namespace"
    
    for xml_file_path in xml_files:
        file_counter += 1
        if file_counter % 10 == 0:
            print(f"[UPDATE-TMX] Processing file {file_counter} of {total_files}...")
            
        try:
            if os.path.getsize(xml_file_path) == 0:
                continue
        except Exception:
            continue
            
        xml_root = parse_xml_file(xml_file_path)
        if xml_root is None:
            continue
            
        doc_name = xml_root.get("FileName") or os.path.basename(xml_file_path)
        
        for loc in xml_root.iter("LocStr"):
            # Pre-process: Clean newlines in text from XML
            korean_text = replace_newlines_text((loc.get("StrOrigin") or ""))
            target_text = replace_newlines_text((loc.get("Str") or ""))
            string_id = (loc.get("StringId") or "")
            
            if is_korean(target_text):
                continue
            if not target_text:
                continue
            if not korean_text:
                continue
            
            # Check if this TU exists in the existing TMX
            key = (korean_text, target_text, string_id)
            if key in existing_tu_map:
                unchanged_count += 1
                continue
            
            # Check if it's a modification (same korean+stringid, different translation)
            is_modified = False
            for existing_key in existing_tu_map:
                if existing_key[0] == korean_text and existing_key[2] == string_id:
                    is_modified = True
                    modified_count += 1
                    break
            
            if not is_modified:
                new_count += 1
            
            # Add to update TMX
            tu = etree.SubElement(body, "tu", {
                "creationid": "CombinedConversion-Update",
                "changeid": "CombinedConversion-Update"
            })
            
            tuv_ko = etree.SubElement(tu, "tuv", {f"{{{XML_NS}}}lang": "ko"})
            seg_ko = etree.SubElement(tuv_ko, "seg")
            seg_ko.text = korean_text
            
            tuv_tgt = etree.SubElement(tu, "tuv", {f"{{{XML_NS}}}lang": target_language})
            seg_tgt = etree.SubElement(tuv_tgt, "seg")
            seg_tgt.text = target_text
            
            prop_doc = etree.SubElement(tu, "prop", {"type": "x-document"})
            prop_doc.text = doc_name
            
            prop_ctx = etree.SubElement(tu, "prop", {"type": "x-context"})
            prop_ctx.text = string_id or "NoStringId"
    
    total_changes = new_count + modified_count
    
    if total_changes == 0:
        msg = "No new or modified translation units found."
        logging.info(msg)
        print(f"[UPDATE-TMX] {msg}")
        print(f"[UPDATE-TMX] Unchanged units: {unchanged_count}")
        return False
    
    # Write TMX
    xml_bytes = etree.tostring(tmx, pretty_print=True, encoding='UTF-8', xml_declaration=True)
    xml_str = xml_bytes.decode('utf-8')
    
    if postprocess:
        xml_str = postprocess_tmx_string(xml_str)
    
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(xml_str)
        logging.info(f"[UPDATE-TMX] Update TMX created with {total_changes} changes")
        print(f"[UPDATE-TMX] Successfully created update TMX:")
        print(f"  New units: {new_count}")
        print(f"  Modified units: {modified_count}")
        print(f"  Unchanged units: {unchanged_count}")
        print(f"  Output file: {output_file}")
        return True
    except Exception as e:
        logging.error(f"Error writing update TMX {output_file}: {e}", exc_info=True)
        print(f"[UPDATE-TMX] Error writing update TMX: {e}")
        return False

        
        
        
def concatenate_all_xmls_to_single_xml(input_folder, output_file):
    """
    Recursively walks input_folder, finds all .xml files, and concatenates all <LocStr> elements
    into a single XML file with a clean structure. 
    The root is <root FileName="nameofthefolderdata.xml"> ... </root> (no XML declaration).
    """
    import logging
    from lxml import etree
    import os

    logging.info(f"[CONCAT-XML] Scanning folder: {input_folder}")
    xml_files = []
    for dirpath, _, filenames in os.walk(input_folder):
        for fname in filenames:
            if fname.lower().endswith(".xml"):
                xml_files.append(os.path.join(dirpath, fname))
    if not xml_files:
        logging.error("[CONCAT-XML] No XML files found in the selected folder.")
        print("[CONCAT-XML] No XML files found in the selected folder.")
        return False

    # Use <root FileName="nameofthefolderdata.xml"> as the output root
    output_filename = os.path.basename(output_file)
    root = etree.Element("root", FileName=output_filename)
    total_locs = 0

    for xml_file in xml_files:
        try:
            parser = etree.XMLParser(recover=True)
            tree = etree.parse(xml_file, parser)
            xml_root = tree.getroot()
        except Exception as e:
            logging.warning(f"[CONCAT-XML] Failed to parse {xml_file}: {e}")
            continue
        for loc in xml_root.iter("LocStr"):
            # Deep copy to avoid lxml reference issues
            root.append(etree.fromstring(etree.tostring(loc)))
            total_locs += 1

    if total_locs == 0:
        logging.error("[CONCAT-XML] No <LocStr> elements found in any XML file.")
        print("[CONCAT-XML] No <LocStr> elements found in any XML file.")
        return False


    xml_bytes = etree.tostring(root, pretty_print=True, encoding='UTF-8', xml_declaration=False)
    xml_str = xml_bytes.decode('utf-8')

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(xml_str)


            logging.info(f"[CONCAT-XML] Successfully concatenated {total_locs} LocStrs into: {output_file}")
        print(f"[CONCAT-XML] Successfully concatenated {total_locs} LocStrs into:\n{output_file}")
        return True
    except Exception as e:
        logging.error(f"[CONCAT-XML] Error writing output XML: {e}")
        print(f"[CONCAT-XML] Error writing output XML: {e}")
        return False
        


def clean_xml_folder_data(input_folder):
    """
    Cleans all .xml files in the input_folder (recursively) by:
    - Removes ALL &amp;desc; and &desc; from the entire file (or converts if desired)
    - For every <LocStr> element:
        - Replace literal \n and \\n with &lt;br/&gt;
        - Replace &amp;lt;br/&amp;gt; and literal <br/> with &lt;br/&gt;
        - Remove zero-width Unicode characters (\u200B, \u200C, \u200D)
        - Replace &amp;#10; and &#10; with &lt;br/&gt;
    - Makes files writable before saving.
    """

    zero_width_pattern = re.compile('[\u200B\u200C\u200D]')
    str_attr_pattern = re.compile(r'(Str\s*=\s*")((?:[^"\\]|\\.)*)"', re.DOTALL)

    def make_file_writable(fpath):
        os.chmod(fpath, stat.S_IWRITE)

    for dirpath, _, filenames in os.walk(input_folder):
        for fname in filenames:
            if not fname.lower().endswith(".xml"):
                continue
            fpath = os.path.join(dirpath, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    raw = f.read()

                # Start from raw ONCE
                new_raw = raw

                new_raw = new_raw.replace('&desc;', '&amp;desc;')

                new_raw = new_raw.replace('&amp;lt;br/&amp;gt;', '&lt;br/&gt;')

                # Replace literal <br/> with &lt;br/&gt; inside Str attributes
                def replace_br_in_attr(match):
                    before = match.group(1)
                    value = match.group(2)
                    value_clean = value.replace('<br/>', '&lt;br/&gt;')
                    return before + value_clean + '"'
                new_raw = str_attr_pattern.sub(replace_br_in_attr, new_raw)

                # Remove zero-width chars inside Str attributes
                def remove_zwc_in_attr(match):
                    before = match.group(1)
                    value = match.group(2)
                    value_clean = zero_width_pattern.sub('', value)
                    return before + value_clean + '"'
                new_raw = str_attr_pattern.sub(remove_zwc_in_attr, new_raw)

                # Replace &amp;#10; and &#10; with &lt;br/&gt;
                new_raw = new_raw.replace('&amp;#10;', '&lt;br/&gt;')
                new_raw = new_raw.replace('&#10;', '&lt;br/&gt;')

                # Parse XML
                parser = etree.XMLParser(recover=True, remove_blank_text=False)
                root = etree.fromstring(new_raw.encode("utf-8"), parser=parser)

                changed = False
                for loc in root.iter("LocStr"):
                    str_val = loc.get("Str")
                    if str_val is not None:
                        new_val = str_val.replace('\n', '&lt;br/&gt;').replace('\\n', '&lt;br/&gt;')
                        new_val = zero_width_pattern.sub('', new_val)
                        if new_val != str_val:
                            loc.set("Str", new_val)
                            changed = True

                if new_raw != raw or changed:
                    make_file_writable(fpath)
                    xml_bytes = etree.tostring(root, pretty_print=True, encoding='UTF-8', xml_declaration=False)
                    with open(fpath, "wb") as f:
                        f.write(xml_bytes)
                    print(f"[CLEAN] Cleaned: {fpath}")
                else:
                    print(f"[CLEAN] No changes needed: {fpath}")

            except Exception as e:
                print(f"[CLEAN] Error cleaning {fpath}: {e}")



def clean_tmx_folder_data(input_folder):
    import os, re, html, stat, logging
    from lxml import etree

    logging.info(f"[CLEAN-TMX] Cleaning TMX files in: {input_folder}")

    # regexes & helpers (unchanged)
    SEG_RE = re.compile(r'(<seg[^>]*>)(.*?)(</seg>)', re.DOTALL | re.IGNORECASE)
    ZERO_WIDTH_RE = re.compile(r'[\u200B\u200C\u200D]')
    BPT_EPT_RE = re.compile(
        r'<bpt\b[^>]*>'
        r'&lt;mq:rxt\s+displaytext=&quot;(.*?)&quot;\s+val=&quot;\{Staticinfo:Knowledge:[^#}]+#&quot;&gt;</bpt>'
        r'(.*?)'
        r'<ept\b[^>]*>.*?</ept>',
        flags=re.DOTALL | re.IGNORECASE
    )
    PH_RE = re.compile(
        r'<ph\b(?![^>]*\btype=[\'"]fmt[\'"])[^>]*>(.*?)</ph>',
        flags=re.DOTALL | re.IGNORECASE
    )

    def make_writable(path):
        try:
            os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
        except Exception:
            pass

    def detect_and_read(path):
        raw = open(path, 'rb').read()
        if raw.startswith(b'\xff\xfe') or raw.startswith(b'\xfe\xff'):
            enc = 'utf-16'
        elif raw.startswith(b'\xef\xbb\xbf'):
            enc = 'utf-8-sig'
        else:
            enc = 'utf-8'
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            return raw.decode('utf-8', errors='replace')

    def _clean_segment(match):
        open_tag, content, close_tag = match.groups()
        # 1) strip zero-width
        content = ZERO_WIDTH_RE.sub('', content)
        # 2) reverse Staticinfo bpt/ept → {Staticinfo:Knowledge:ID#inner}
        def _bpt_repl(m):
            ident, inner = m.group(1), m.group(2)
            return f'{{Staticinfo:Knowledge:{ident}#{inner}}}'
        content = BPT_EPT_RE.sub(_bpt_repl, content)
        # 3) reverse non-fmt <ph>→ their val
        def _ph_repl(m):
            ph_inner = m.group(1)
            decoded = html.unescape(ph_inner)
            vm = re.search(r'val="([^"]+)"', decoded)
            return vm.group(1) if vm else ''
        content = PH_RE.sub(_ph_repl, content)
        # 4) drop any fmt placeholders
        content = re.sub(
            r'<ph\b[^>]*\btype=[\'"]fmt[\'"][^>]*>.*?</ph>',
            '',
            content,
            flags=re.DOTALL | re.IGNORECASE
        )
        # 5) normalize newlines → &lt;br/&gt;
        content = re.sub(r'\r\n|\r|\n', '&lt;br/&gt;', content)
        content = content.replace('\\n', '&lt;br/&gt;')
        # 6) normalize <br> variants → &lt;br/&gt;
        content = re.sub(r'&amp;lt;br\s*/&amp;gt;', '&lt;br/&gt;', content, flags=re.IGNORECASE)
        content = re.sub(r'<\s*br\s*/?\s*>', '&lt;br/&gt;', content, flags=re.IGNORECASE)
        content = content.replace('<br/', '&lt;br/&gt;')
        content = re.sub(r'\bbr/\b', '&lt;br/&gt;', content, flags=re.IGNORECASE)
        return f"{open_tag}{content}{close_tag}"

    # Walk all .tmx files
    for dirpath, _, files in os.walk(input_folder):
        for fn in files:
            if not fn.lower().endswith(".tmx"):
                continue
            fpath = os.path.join(dirpath, fn)
            try:
                raw_text = detect_and_read(fpath)
            except Exception as e:
                logging.error(f"[CLEAN-TMX] Cannot read {fpath}: {e}", exc_info=True)
                continue

            # STEP 1: Regex-based cleanup
            cleaned = SEG_RE.sub(_clean_segment, raw_text)

            # STEP 2: ALWAYS re-structure & pretty-print
            # strip existing decl & doctype
            body_only = re.sub(r'^<\?xml[^>]*\?>\s*', '', cleaned, flags=re.MULTILINE)
            body_only = re.sub(r'<!DOCTYPE[^>]*>\s*', '', body_only, flags=re.IGNORECASE)

            parser = etree.XMLParser(remove_blank_text=True, recover=True)
            try:
                root = etree.fromstring(body_only.encode('utf-8'), parser=parser)
            except Exception:
                # fallback: just write cleaned text
                make_writable(fpath)
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(cleaned)
                print(f"[CLEAN-TMX] Cleaned (no restructure due to parse error): {fpath}")
                continue

            make_writable(fpath)
            tree = etree.ElementTree(root)
            tree.write(
                fpath,
                encoding="UTF-8",
                xml_declaration=True,
                pretty_print=True,
                doctype='<!DOCTYPE tmx SYSTEM "tmx14.dtd">'
            )
            print(f"[CLEAN-TMX] Cleaned and restructured: {fpath}")

    print("[CLEAN-TMX] TMX cleaning (and restructuring) completed.")


def extract_non_korean_and_non_empty_locs_from_xml(xml_file_path):
    xml_root = parse_xml_file(xml_file_path)
    if xml_root is None:
        return []
    result = []
    for loc in xml_root.iter("LocStr"):
        str_val = (loc.get("Str") or "")
        if str_val and not is_korean(str_val):
            result.append(etree.fromstring(etree.tostring(loc)))
    return result

def extract_non_korean_and_non_empty_with_structure(input_folder, lookup_folder, output_base_folder, files_to_process=None):
    """
    Extract ONLY LocStr elements where Str is non-empty and does NOT contain Korean.
    Output is filtered XMLs preserving folder structure from lookup_folder.
    """
    logging.info(f"[STRUCTURED-EXTRACT-NON-KR-NON-EMPTY] Building lookup file map for: {lookup_folder}")
    lookup_map, stringid_map = build_lookup_file_map_with_stringids(lookup_folder)

    if files_to_process is not None:
        xml_files = files_to_process
    else:
        xml_files = get_all_xml_files(input_folder)

    copied_files = 0
    skipped_files = 0
    error_files = 0
    fuzzy_used = 0

    for xml_file_path in xml_files:
        fname = os.path.basename(xml_file_path)
        try:
            if os.path.getsize(xml_file_path) == 0:
                skipped_files += 1
                continue
        except Exception:
            error_files += 1
            continue

        # Extract only matching LocStrs
        matching_locs = []
        try:
            xml_root = parse_xml_file(xml_file_path)
            if xml_root is None:
                error_files += 1
                continue
            for loc in xml_root.iter("LocStr"):
                str_val = (loc.get("Str") or "").strip()
                if str_val and not is_korean(str_val):
                    matching_locs.append(etree.fromstring(etree.tostring(loc)))
        except Exception as e:
            logging.error(f"Error parsing {xml_file_path}: {e}")
            error_files += 1
            continue

        if not matching_locs:
            skipped_files += 1
            continue

        # Find corresponding lookup file for structure
        matches = lookup_map.get(fname.lower(), [])
        if not matches:
            error_files += 1
            continue
        if len(matches) == 1:
            lookup_path = matches[0]
        else:
            best_path, best_ratio = fuzzy_best_match(xml_file_path, matches, stringid_map, threshold=0.2)
            if not best_path:
                error_files += 1
                continue
            lookup_path = best_path
            fuzzy_used += 1

        rel_path = os.path.relpath(lookup_path, lookup_folder)
        out_path = os.path.join(output_base_folder, rel_path)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        # Write filtered LocStrs only
        try:
            new_root = etree.Element("root")
            for l in matching_locs:
                new_root.append(l)
            xml_bytes = etree.tostring(new_root, pretty_print=True, encoding='UTF-8', xml_declaration=False)
            with open(out_path, "wb") as f:
                f.write(xml_bytes)
            copied_files += 1
        except Exception as e:
            logging.error(f"Error writing filtered file {out_path}: {e}")
            error_files += 1

    print(f"[STRUCTURED-EXTRACT-NON-KR-NON-EMPTY] Extraction complete.")
    print(f"  Files written (filtered): {copied_files}")
    print(f"  Files skipped (no matches): {skipped_files}")
    print(f"  Files with errors: {error_files}")
    print(f"  Files using fuzzy match: {fuzzy_used}")
    return copied_files > 0
    

def extract_translated_with_kr_in_desc_with_structure(input_folder, lookup_folder, output_base_folder, mode="filtered", files_to_process=None):
    """
    Extracts files where:
      - Str is translated (non-empty, not Korean)
      - Desc contains Korean (excluding empty or &desc;/&amp;desc;)
    Preserves folder structure from lookup_folder into output_base_folder.

    mode = "filtered" -> output only matching LocStrs
    mode = "full"     -> copy full original file from lookup_folder
    """
    logging.info(f"[STRUCTURED-EXTRACT-TRANSLATED-KR-DESC] Building lookup index from: {lookup_folder}")

    # Build StringId -> lookup file path map
    stringid_to_file = {}
    for lfile in get_all_xml_files(lookup_folder):
        root = parse_xml_file(lfile)
        if root is None:
            continue
        for loc in root.iter("LocStr"):
            sid = loc.get("StringId")
            if sid:
                stringid_to_file[sid] = lfile

    copied_files = 0
    filtered_files = 0
    error_files = 0

    # Determine files to process
    if files_to_process is not None:
        xml_files = files_to_process
    else:
        xml_files = get_all_xml_files(input_folder)

    for xml_file_path in xml_files:
        root = parse_xml_file(xml_file_path)
        if root is None:
            logging.error(f"[STRUCTURED-EXTRACT-TRANSLATED-KR-DESC] Failed to parse: {xml_file_path}")
            error_files += 1
            continue

        # Group LocStrs by their original lookup file
        file_to_locs = {}
        for loc in root.iter("LocStr"):
            str_val = (loc.get("Str") or "")
            desc_val = (loc.get("Desc") or "")

            # Skip if Desc is empty or just &desc;/&amp;desc;
            if not desc_val.strip() or desc_val.strip() in ("&desc;", "&amp;desc;"):
                continue

            if str_val and not is_korean(str_val) and is_korean(desc_val):
                sid = loc.get("StringId")
                if not sid:
                    continue
                lookup_path = stringid_to_file.get(sid)
                if not lookup_path:
                    logging.warning(f"[STRUCTURED-EXTRACT-TRANSLATED-KR-DESC] No lookup match for StringId={sid}")
                    continue
                file_to_locs.setdefault(lookup_path, []).append(etree.fromstring(etree.tostring(loc)))

        # Write out grouped files
        for lookup_path, locs in file_to_locs.items():
            rel_path = os.path.relpath(lookup_path, lookup_folder)
            out_path = os.path.join(output_base_folder, rel_path)
            os.makedirs(os.path.dirname(out_path), exist_ok=True)

            try:
                if mode == "full":
                    shutil.copy2(lookup_path, out_path)
                    copied_files += 1
                    logging.info(f"[STRUCTURED-EXTRACT-TRANSLATED-KR-DESC] Copied full: {out_path}")
                elif mode == "filtered":
                    new_root = etree.Element("root")
                    for l in locs:
                        new_root.append(l)
                    xml_bytes = etree.tostring(new_root, pretty_print=True, encoding='UTF-8', xml_declaration=False)
                    with open(out_path, "wb") as f:
                        f.write(xml_bytes)
                    filtered_files += 1
                    logging.info(f"[STRUCTURED-EXTRACT-TRANSLATED-KR-DESC] Wrote filtered: {out_path}")
                else:
                    logging.error(f"[STRUCTURED-EXTRACT-TRANSLATED-KR-DESC] Unknown mode: {mode}")
                    error_files += 1
            except Exception as e:
                logging.error(f"[STRUCTURED-EXTRACT-TRANSLATED-KR-DESC] Write error: {e}")
                error_files += 1

    print(f"[STRUCTURED-EXTRACT-TRANSLATED-KR-DESC] Extraction complete.")
    print(f"  Files copied (full): {copied_files}")
    print(f"  Files filtered: {filtered_files}")
    print(f"  Files with errors: {error_files}")
    return (mode == "full" and copied_files > 0) or (mode == "filtered" and filtered_files > 0)


    
        
# --- GUI ---

class ConverterGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("XML to TMX Converter")
        self.geometry("700x700")
        self.resizable(False, False)
        self.selected_folder = tk.StringVar()
        self.folder_chosen   = False
        self.target_language = tk.StringVar()
        self.language_options = {
            "English (US)":              "en-US",
            "French (FR)":               "fr-FR",
            "German (DE)":               "de-DE",
            "Traditional Chinese (TW)":  "zh-TW",
            "Simplified Chinese (CN)":   "zh-CN",
            "Japanese (JP)":             "ja-JP",
            "Italian (IT)":              "it-IT",
            "Portuguese (Brazil)":       "pt-BR",
            "Russian (RU)":              "ru-RU",
            "European Spanish (ES)":     "es-ES",
            "Latin American Spanish (MX)": "es-MX",
            "Polish (PL)":               "pl-PL",
            "Turkish (TR)":              "tr-TR"
        }
        self.target_language.set("English (US)")
        self.create_widgets()

    def create_widgets(self):
        pad = {'padx': 10, 'pady': 10}
        frm = tk.Frame(self)
        frm.pack(fill="x", **pad)
        btn = tk.Button(frm, text="Select Folder", command=self.select_folder)
        btn.grid(row=0, column=0, sticky="w")
        self.select_folder_button = btn
        lbl = tk.Label(frm, text="No folder selected", wraplength=500)
        lbl.grid(row=0, column=1, sticky="w", padx=10)
        self.folder_label = lbl
        frm2 = tk.Frame(self)
        frm2.pack(fill="x", **pad)
        tk.Label(frm2, text="Select Target Language:").grid(row=0, column=0, sticky="w")
        ttk.OptionMenu(
            frm2, 
            self.target_language, 
            self.target_language.get(),
            *self.language_options.keys()
        ).grid(row=0, column=1, sticky="w", padx=10)
        btn_frame = tk.Frame(self)
        btn_frame.pack(fill="x", **pad)
        # --- NEW BUTTONS ---
        tk.Button(btn_frame, text="Convert to MemoQ-TMX", command=self.convert_memoq).grid(row=0, column=0, padx=5)
        tk.Button(btn_frame, text="Update MemoQ-TMX", command=self.update_memoq).grid(row=0, column=1, padx=5)
        tk.Button(btn_frame, text="Convert to NORMAL TMX", command=self.convert_normal).grid(row=0, column=2, padx=5)


        tk.Button(
            btn_frame,
            text="NORMAL TMX (BATCH)",
            command=self.normal_tmx_batch_gui
        ).grid(row=0, column=3, padx=5)


        tk.Button(btn_frame, text="Extract KR/Empty in One File", command=self.extract_korean_or_empty).grid(row=1, column=0, padx=5)
        tk.Button(btn_frame, text="TMX Fix", command=self.tmx_fix).grid(row=1, column=1, padx=5)




        tk.Button(
            btn_frame,
            text="Extract All Strings that Contains KR or Empty with Folder Structure",
            command=self.extract_korean_or_empty_with_structure
        ).grid(row=2, column=0, columnspan=3, pady=10, sticky="ew")
        tk.Button(
            btn_frame,
            text="Extract string to translate for PAAT",
            command=self.extract_korean_or_empty_for_paat_gui
        ).grid(row=3, column=0, columnspan=3, pady=10, sticky="ew")
        # --- NEW BUTTON: TMX CONCATENATE ONLY (FILTERED) ---
        tk.Button(
            btn_frame,
            text="TMX Concatenate Only (No KR or Empty in Translation)",
            command=self.tmx_concat_only_filtered
        ).grid(row=4, column=0, columnspan=3, pady=10, sticky="ew")

        tk.Button(
            btn_frame,
            text="Concatenate All XMLs to Single XML",
            command=self.concatenate_all_xmls_gui
        ).grid(row=5, column=0, columnspan=3, pady=10, sticky="ew")

        tk.Button(
            btn_frame,
            text="Clean/Regex-Normalize XML Folder Data",
            command=self.clean_xml_folder_data_gui
        ).grid(row=6, column=0, columnspan=3, pady=10, sticky="ew")


        tk.Button(
            btn_frame,
            text="Clean/Regex-Normalize TMX Folder Data",
            command=self.clean_tmx_folder_data_gui
        ).grid(row=9, column=0, columnspan=3, pady=10, sticky="ew")


        tk.Button(
            btn_frame,
            text="Extract all strings that don't contain KR or not Empty with folder structure",
            command=self.extract_non_korean_and_non_empty_with_structure_gui
        ).grid(row=7, column=0, columnspan=3, pady=10, sticky="ew")        



        tk.Button(
            btn_frame,
            text="Extract Translated Strings with KR in Desc (Folder Structure)",
            command=self.extract_translated_with_kr_in_desc_with_structure_gui
        ).grid(row=8, column=0, columnspan=3, pady=10, sticky="ew")

        
    def select_folder(self):
        fld = filedialog.askdirectory(
            title="Select Parent Folder Containing XML Files"
        )
        if fld:
            # --- Make all files in the folder writable ---
            for dirpath, _, filenames in os.walk(fld):
                for fname in filenames:
                    fpath = os.path.join(dirpath, fname)
                    try:
                        make_file_writable(fpath)
                    except Exception as e:
                        print(f"[ERROR] Could not set writable permissions for {fpath}: {e}")
            self.selected_folder.set(fld)
            self.folder_label.config(text=fld)
            self.select_folder_button.config(bg="green")
            self.folder_chosen = True

    def convert_memoq(self):
        self._convert(postprocess=True, label="MemoQ-TMX")

    def convert_normal(self):
        self._convert(postprocess=False, label="NORMAL TMX")

    def _convert(self, postprocess, label):
        if not self.folder_chosen:
            messagebox.showerror("Error", "Please select a folder first.")
            return
        out = filedialog.asksaveasfilename(
            title=f"Save Combined {label} File As",
            defaultextension=".tmx",
            filetypes=[("TMX Files", "*.tmx"), ("All Files", "*.*")]
        )
        if not out:
            messagebox.showinfo("Info", "No output file selected. Conversion cancelled.")
            return
        outdir = os.path.dirname(out)

        tgt_key  = self.target_language.get()
        tgt_code = self.language_options.get(tgt_key, "en-US")
        threading.Thread(
            target=self.threaded_convert,
            args=(out, tgt_code, postprocess, label),
            daemon=True
        ).start()

    def threaded_convert(self, out_file, tgt_lang, postprocess, label):
        ok = combine_xmls_to_tmx(self.selected_folder.get(), out_file, tgt_lang, postprocess=postprocess)
        if ok:
            self.after(0, lambda: messagebox.showinfo(
                "Success",
                f"Combined {label} created:\n{out_file}"
            ))
        else:
            self.after(0, lambda: messagebox.showerror(
                "Error",
                f"Failed to create the {label}. See log for details."
            ))

    def update_memoq(self):
        """Handle Update MemoQ-TMX button click"""
        if not self.folder_chosen:
            messagebox.showerror("Error", "Please select a folder first.")
            return
        
        # First, select existing TMX to compare against
        existing_tmx = filedialog.askopenfilename(
            title="Select Existing MemoQ-TMX File to Compare Against",
            filetypes=[("TMX Files", "*.tmx"), ("All Files", "*.*")]
        )
        if not existing_tmx:
            messagebox.showinfo("Info", "No existing TMX selected. Update cancelled.")
            return
        
        # Then, select output file for update TMX
        out = filedialog.asksaveasfilename(
            title="Save Update MemoQ-TMX File As",
            defaultextension=".tmx",
            filetypes=[("TMX Files", "*.tmx"), ("All Files", "*.*")]
        )
        if not out:
            messagebox.showinfo("Info", "No output file selected. Update cancelled.")
            return
        
        outdir = os.path.dirname(out)
        
        tgt_key = self.target_language.get()
        tgt_code = self.language_options.get(tgt_key, "en-US")
        
        threading.Thread(
            target=self.threaded_update_memoq,
            args=(existing_tmx, out, tgt_code),
            daemon=True
        ).start()

    def threaded_update_memoq(self, existing_tmx, out_file, tgt_lang):
        """Thread function for creating update TMX"""
        ok = create_update_tmx(
            self.selected_folder.get(), 
            existing_tmx, 
            out_file, 
            tgt_lang, 
            postprocess=True
        )
        if ok:
            self.after(0, lambda: messagebox.showinfo(
                "Success",
                f"Update MemoQ-TMX created:\n{out_file}"
            ))
        else:
            self.after(0, lambda: messagebox.showinfo(
                "Info",
                "No new or modified translation units found.\nThe existing TMX is up to date."
            ))

    def extract_korean_or_empty(self):
        if not self.folder_chosen:
            messagebox.showerror("Error", "Please select a folder first.")
            return
        out = filedialog.asksaveasfilename(
            title="Save Extracted Korean-or-Empty XML As",
            defaultextension=".xml",
            filetypes=[("XML Files", "*.xml"), ("All Files", "*.*")]
        )
        if not out:
            messagebox.showinfo("Info", "No output file selected. Extraction cancelled.")
            return
        outdir = os.path.dirname(out)

        threading.Thread(
            target=self.threaded_extract_korean_or_empty,
            args=(out,),
            daemon=True
        ).start()

    def threaded_extract_korean_or_empty(self, out_file):
        ok = extract_korean_or_empty_translation(self.selected_folder.get(), out_file)
        if ok:
            self.after(0, lambda: messagebox.showinfo(
                "Success",
                f"Extracted all LocStr with Korean in Str or StrOrigin non-empty and Str empty into:\n{out_file}"
            ))
        else:
            self.after(0, lambda: messagebox.showerror(
                "Error",
                "Failed to extract. See log for details."
            ))


    def tmx_fix(self):
        in_tmxs = filedialog.askopenfilenames(
            title="Select TMX File(s) to Fix and Combine",
            filetypes=[("TMX Files", "*.tmx"), ("All Files", "*.*")]
        )
        if not in_tmxs:
            messagebox.showinfo("Info", "No TMX file selected. TMX Fix cancelled.")
            return
        out_tmx = filedialog.asksaveasfilename(
            title="Save Fixed/Combined TMX File As",
            defaultextension=".tmx",
            filetypes=[("TMX Files", "*.tmx"), ("All Files", "*.*")]
        )
        if not out_tmx:
            messagebox.showinfo("Info", "No output file selected. TMX Fix cancelled.")
            return
        outdir = os.path.dirname(out_tmx)

        threading.Thread(
            target=self.threaded_tmx_fix_multi,
            args=(in_tmxs, out_tmx),
            daemon=True
        ).start()

    def threaded_tmx_fix_multi(self, in_tmxs, out_tmx):
        ok = fix_and_combine_tmx_files(in_tmxs, out_tmx)
        if ok:
            self.after(0, lambda: messagebox.showinfo(
                "Success",
                f"Fixed and combined TMX written to:\n{out_tmx}"
            ))
        else:
            self.after(0, lambda: messagebox.showerror(
                "Error",
                "Failed to fix/combine TMX. See log for details."
            ))

    def extract_korean_or_empty_with_structure(self):
        if not self.folder_chosen:
            messagebox.showerror("Error", "Please select a folder first.")
            return

        xml_files = get_all_xml_files(self.selected_folder.get())
        files_to_extract = []
        for xml_file_path in xml_files:
            try:
                if os.path.getsize(xml_file_path) == 0:
                    continue
            except Exception:
                continue
            if file_has_korean_or_empty_condition(xml_file_path):
                files_to_extract.append(xml_file_path)

        if not files_to_extract:
            messagebox.showinfo(
                "Nothing to Extract",
                "No Korean Found in Translation and No Empty Translation found. All good !"
            )
            return

        lookup_folder = filedialog.askdirectory(
            title="Select LOOKUP Folder (reference for folder structure)"
        )
        if not lookup_folder:
            messagebox.showinfo("Info", "No LOOKUP folder selected. Operation cancelled.")
            return
        output_folder_name = simpledialog.askstring(
            "Output Folder Name",
            "Enter the name for the output folder (will be created in the same folder as this script):"
        )
        if not output_folder_name:
            messagebox.showinfo("Info", "No output folder name provided. Operation cancelled.")
            return

        mode = self.ask_extract_mode_clean()
        if mode is None:
            messagebox.showinfo("Info", "No extraction mode selected. Operation cancelled.")
            return

        script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        output_base_folder = os.path.join(script_dir, output_folder_name)
        if os.path.exists(output_base_folder):
            if not messagebox.askyesno(
                "Overwrite Confirmation",
                f"Output folder '{output_base_folder}' already exists.\n"
                "Continue and overwrite files inside?"
            ):
                return

        threading.Thread(
            target=self.threaded_extract_korean_or_empty_with_structure,
            args=(lookup_folder, output_base_folder, mode, files_to_extract),
            daemon=True
        ).start()

    def ask_extract_mode_clean(self):
        win = tk.Toplevel(self)
        win.title("Extraction Mode")
        win.geometry("400x180")
        win.resizable(False, False)
        win.grab_set()
        win.transient(self)
        result = {"mode": None}

        label = tk.Label(win, text="Choose extraction mode:", font=("Arial", 13), pady=20)
        label.pack()

        def choose_full():
            result["mode"] = "full"
            win.destroy()
        def choose_filtered():
            result["mode"] = "filtered"
            win.destroy()

        btn_full = tk.Button(
            win, text="Extract Full Raw Files", width=28, height=2,
            font=("Arial", 12, "bold"), bg="#f0f0f0", command=choose_full
        )
        btn_full.pack(pady=5)
        btn_filtered = tk.Button(
            win, text="Extract Filtered Files", width=28, height=2,
            font=("Arial", 12, "bold"), bg="#e0e0ff", command=choose_filtered
        )
        btn_filtered.pack(pady=5)

        win.protocol("WM_DELETE_WINDOW", lambda: win.destroy())
        self.wait_window(win)
        return result["mode"]

    def threaded_extract_korean_or_empty_with_structure(self, lookup_folder, output_base_folder, mode, files_to_extract):
        ok = extract_whole_files_with_structure(
            self.selected_folder.get(),
            lookup_folder,
            output_base_folder,
            mode=mode,
            files_to_process=files_to_extract
        )
        if ok:
            self.after(0, lambda: messagebox.showinfo(
                "Success",
                f"Extraction complete.\nOutput folder:\n{output_base_folder}"
            ))
        else:
            self.after(0, lambda: messagebox.showerror(
                "Error",
                "No files extracted or an error occurred. See log for details."
            ))

    def extract_korean_or_empty_for_paat_gui(self):
        if not self.folder_chosen:
            messagebox.showerror("Error", "Please select a folder first.")
            return

        script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        master_folder = os.path.join(script_dir, "TO_SEND_TO_PAAT")
        os.makedirs(master_folder, exist_ok=True)
        threading.Thread(
            target=self.threaded_extract_korean_or_empty_for_paat,
            daemon=True
        ).start()

    def threaded_extract_korean_or_empty_for_paat(self):
        paat_folder = extract_korean_or_empty_for_paat(self.selected_folder.get())
        if paat_folder:
            self.after(0, lambda: messagebox.showinfo(
                "Success",
                f"Extraction for PAAT complete.\nSee the folder:\n{paat_folder}\ninside the 'TO_SEND_TO_PAAT' master folder in your script directory."
            ))
        else:
            # POSITIVE message if nothing to extract (no Korean found)
            self.after(0, lambda: messagebox.showinfo(
                "All Translations Done!",
                "No Korean detected in any translation.\nAll translations have been applied!\nNo more strings to extract for PAAT. 🎉"
            ))

    # --- TMX CONCATENATE ONLY GUI FUNCTION (FILTERED) ---
    def tmx_concat_only_filtered(self):
        in_tmxs = filedialog.askopenfilenames(
            title="Select TMX File(s) to Concatenate",
            filetypes=[("TMX Files", "*.tmx"), ("All Files", "*.*")]
        )
        if not in_tmxs:
            messagebox.showinfo("Info", "No TMX file selected. Concatenation cancelled.")
            return
        out_tmx = filedialog.asksaveasfilename(
            title="Save Concatenated TMX File As",
            defaultextension=".tmx",
            filetypes=[("TMX Files", "*.tmx"), ("All Files", "*.*")]
        )
        if not out_tmx:
            messagebox.showinfo("Info", "No output file selected. Concatenation cancelled.")
            return
        outdir = os.path.dirname(out_tmx)
        threading.Thread(
            target=self.threaded_tmx_concat_only_filtered,
            args=(in_tmxs, out_tmx),
            daemon=True
        ).start()

    def threaded_tmx_concat_only_filtered(self, in_tmxs, out_tmx):
        ok = concat_tmx_files_filtered(in_tmxs, out_tmx)
        if ok:
            self.after(0, lambda: messagebox.showinfo(
                "Success",
                f"Concatenated TMX written to:\n{out_tmx}"
            ))
        else:
            self.after(0, lambda: messagebox.showerror(
                "Error",
                "Failed to concatenate TMX. See log for details."
            ))


    def concatenate_all_xmls_gui(self):
        if not self.folder_chosen:
            messagebox.showerror("Error", "Please select a folder first.")
            return
        out = filedialog.asksaveasfilename(
            title="Save Concatenated XML As",
            defaultextension=".xml",
            filetypes=[("XML Files", "*.xml"), ("All Files", "*.*")]
        )
        if not out:
            messagebox.showinfo("Info", "No output file selected. Concatenation cancelled.")
            return
        outdir = os.path.dirname(out)

        threading.Thread(
            target=self.threaded_concatenate_all_xmls,
            args=(out,),
            daemon=True
        ).start()

    def threaded_concatenate_all_xmls(self, out_file):
        ok = concatenate_all_xmls_to_single_xml(self.selected_folder.get(), out_file)
        if ok:
            self.after(0, lambda: messagebox.showinfo(
                "Success",
                f"All XMLs concatenated into:\n{out_file}"
            ))
        else:
            self.after(0, lambda: messagebox.showerror(
                "Error",
                "Failed to concatenate XMLs. See log for details."
            ))


            
            
    def normal_tmx_batch_gui(self):
        # Use the new multi-folder selection dialog
        input_folders = self.ask_subfolders_multiple(
            title="Select Parent Folder and Subfolders to Batch Convert to NORMAL TMX"
        )
        if not input_folders:
            messagebox.showinfo("Info", "No folders selected. Batch cancelled.")
            return

        # Select output directory
        output_dir = filedialog.askdirectory(
            title="Select Output Directory for TMX Files"
        )
        if not output_dir:
            messagebox.showinfo("Info", "No output directory selected. Batch cancelled.")
            return

        tgt_key = self.target_language.get()
        tgt_code = self.language_options.get(tgt_key, "en-US")


        threading.Thread(
            target=self.threaded_normal_tmx_batch,
            args=(input_folders, output_dir, tgt_code),
            daemon=True
        ).start()

    def threaded_normal_tmx_batch(self, input_folders, output_dir, tgt_code):
        results = batch_normal_tmx_from_folders(input_folders, output_dir, tgt_code)
        summary = []
        for folder, out_file, ok in results:
            status = "OK" if ok else "FAILED"
            summary.append(f"{os.path.basename(folder)}: {status} ({out_file})")
        msg = "Batch NORMAL TMX complete:\n\n" + "\n".join(summary)
        self.after(0, lambda: messagebox.showinfo(
            "Batch Complete",
            msg
        ))
            
            
    def ask_subfolders_multiple(self, title="Select Folders"):
        """
        Pops up a dialog to select a parent folder, then lets the user select multiple subfolders.
        Returns a list of selected subfolder paths.
        """
        parent_dir = filedialog.askdirectory(title=title)
        if not parent_dir:
            return []

        # Find all immediate subfolders
        subdirs = []
        for item in os.listdir(parent_dir):
            item_path = os.path.join(parent_dir, item)
            if os.path.isdir(item_path):
                subdirs.append((item, item_path))

        if not subdirs:
            messagebox.showwarning("No Folders", "No subdirectories found in the selected directory.")
            return []

        # Sub-GUI for multi-selection
        win = tk.Toplevel(self)
        win.title("Select Subfolders (Ctrl+Click for multiple)")
        win.geometry("500x600")
        win.grab_set()
        win.transient(self)

        tk.Label(win, text="Select subfolders:", font=("Arial", 10, "bold")).pack(pady=10)

        list_frame = tk.Frame(win)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED, yscrollcommand=scrollbar.set)
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=listbox.yview)

        folder_map = {}
        for name, path in sorted(subdirs):
            listbox.insert(tk.END, name)
            folder_map[listbox.size() - 1] = path

        selected_folders = []

        def on_confirm():
            selections = listbox.curselection()
            for idx in selections:
                folder_path = folder_map[idx]
                selected_folders.append(folder_path)
            win.destroy()

        def on_select_all():
            listbox.select_set(0, tk.END)

        button_frame = tk.Frame(win)
        button_frame.pack(pady=10)

        tk.Button(button_frame, text="Select All", command=on_select_all).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Confirm", command=on_confirm,
                  bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Cancel", command=win.destroy).pack(side=tk.LEFT, padx=5)

        win.wait_window()
        return selected_folders
            
            
            
    def clean_xml_folder_data_gui(self):
        if not self.folder_chosen:
            messagebox.showerror("Error", "Please select a folder first.")
            return
        folder = self.selected_folder.get()
        if not os.path.isdir(folder):
            messagebox.showerror("Error", "Selected folder does not exist.")
            return
        # Confirm
        if not messagebox.askyesno(
            "Confirm Clean",
            f"Are you sure you want to clean ALL .xml files in:\n{folder}\n\n"
            "This will remove specific placeholders and replace all newlines with &lt;br/&gt; (xml newlines)."
        ):
            return
            
        threading.Thread(
            target=self.threaded_clean_xml_folder_data,
            args=(folder,),
            daemon=True
        ).start()

    def threaded_clean_xml_folder_data(self, folder):
        try:
            clean_xml_folder_data(folder)
            self.after(0, lambda: messagebox.showinfo(
                "Success",
                f"XML folder cleaned successfully!"
            ))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror(
                "Error",
                f"Error cleaning XML folder:\n{e}"
            ))


    def extract_non_korean_and_non_empty_with_structure_gui(self):
        if not self.folder_chosen:
            messagebox.showerror("Error", "Please select a folder first.")
            return

        xml_files = get_all_xml_files(self.selected_folder.get())
        files_to_extract = []
        for xml_file_path in xml_files:
            try:
                if os.path.getsize(xml_file_path) == 0:
                    continue
            except Exception:
                continue
            locs = extract_non_korean_and_non_empty_locs_from_xml(xml_file_path)
            if locs:
                files_to_extract.append(xml_file_path)

        if not files_to_extract:
            messagebox.showinfo(
                "Nothing to Extract",
                "No non-Korean, non-empty translations found."
            )
            return

        lookup_folder = filedialog.askdirectory(
            title="Select LOOKUP Folder (reference for folder structure)"
        )
        if not lookup_folder:
            messagebox.showinfo("Info", "No LOOKUP folder selected. Operation cancelled.")
            return
        output_folder_name = simpledialog.askstring(
            "Output Folder Name",
            "Enter the name for the output folder (will be created in the same folder as this script):"
        )
        if not output_folder_name:
            messagebox.showinfo("Info", "No output folder name provided. Operation cancelled.")
            return

        script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        output_base_folder = os.path.join(script_dir, output_folder_name)
        if os.path.exists(output_base_folder):
            if not messagebox.askyesno(
                "Overwrite Confirmation",
                f"Output folder '{output_base_folder}' already exists.\n"
                "Continue and overwrite files inside?"
            ):
                return

        threading.Thread(
            target=self.threaded_extract_non_korean_and_non_empty_with_structure,
            args=(lookup_folder, output_base_folder, files_to_extract),
            daemon=True
        ).start()

    def threaded_extract_non_korean_and_non_empty_with_structure(self, lookup_folder, output_base_folder, files_to_extract):
        ok = extract_non_korean_and_non_empty_with_structure(
            self.selected_folder.get(),
            lookup_folder,
            output_base_folder,
            files_to_process=files_to_extract
        )
        if ok:
            self.after(0, lambda: messagebox.showinfo(
                "Success",
                f"Extraction complete.\nOutput folder:\n{output_base_folder}"
            ))
        else:
            self.after(0, lambda: messagebox.showerror(
                "Error",
                "No files extracted or an error occurred. See log for details."
            ))



    def extract_translated_with_kr_in_desc_with_structure_gui(self):
        if not self.folder_chosen:
            messagebox.showerror("Error", "Please select a folder first.")
            return

        xml_files = get_all_xml_files(self.selected_folder.get())
        files_to_extract = []
        for xml_file_path in xml_files:
            try:
                if os.path.getsize(xml_file_path) == 0:
                    continue
            except Exception:
                continue
            root = parse_xml_file(xml_file_path)
            if root is None:
                continue
            for loc in root.iter("LocStr"):
                str_val = (loc.get("Str") or "")
                desc_val = (loc.get("Desc") or "")
                if str_val and not is_korean(str_val) and is_korean(desc_val):
                    files_to_extract.append(xml_file_path)
                    break

        if not files_to_extract:
            messagebox.showinfo(
                "Nothing to Extract",
                "No translated strings with Korean in Desc found."
            )
            return

        lookup_folder = filedialog.askdirectory(
            title="Select LOOKUP Folder (reference for folder structure)"
        )
        if not lookup_folder:
            messagebox.showinfo("Info", "No LOOKUP folder selected. Operation cancelled.")
            return
        output_folder_name = simpledialog.askstring(
            "Output Folder Name",
            "Enter the name for the output folder (will be created in the same folder as this script):"
        )
        if not output_folder_name:
            messagebox.showinfo("Info", "No output folder name provided. Operation cancelled.")
            return

        # Ask for extraction mode (Filtered vs Full Raw File)
        mode = self.ask_extract_mode_clean()
        if mode is None:
            messagebox.showinfo("Info", "No extraction mode selected. Operation cancelled.")
            return

        script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        output_base_folder = os.path.join(script_dir, output_folder_name)
        if os.path.exists(output_base_folder):
            if not messagebox.askyesno(
                "Overwrite Confirmation",
                f"Output folder '{output_base_folder}' already exists.\n"
                "Continue and overwrite files inside?"
            ):
                return

        threading.Thread(
            target=self.threaded_extract_translated_with_kr_in_desc_with_structure,
            args=(lookup_folder, output_base_folder, files_to_extract, mode),
            daemon=True
        ).start()


    def threaded_extract_translated_with_kr_in_desc_with_structure(self, lookup_folder, output_base_folder, files_to_extract, mode):
        ok = extract_translated_with_kr_in_desc_with_structure(
            self.selected_folder.get(),
            lookup_folder,
            output_base_folder,
            mode=mode,
            files_to_process=files_to_extract
        )
        if ok:
            self.after(0, lambda: messagebox.showinfo(
                "Success",
                f"Extraction complete.\nOutput folder:\n{output_base_folder}"
            ))
        else:
            self.after(0, lambda: messagebox.showerror(
                "Error",
                "No files extracted or an error occurred. See log for details."
            ))


    def clean_tmx_folder_data_gui(self):
        if not self.folder_chosen:
            messagebox.showerror("Error", "Please select a folder first.")
            return
        folder = self.selected_folder.get()
        if not os.path.isdir(folder):
            messagebox.showerror("Error", "Selected folder does not exist.")
            return
        # Confirm
        if not messagebox.askyesno(
            "Confirm Clean",
            f"Are you sure you want to clean ALL .tmx files in:\n{folder}\n\n"
            "This will normalise <seg> contents (line-breaks, placeholders, etc.)."
        ):
            return
        threading.Thread(
            target=self.threaded_clean_tmx_folder_data,
            args=(folder,),
            daemon=True
        ).start()

    def threaded_clean_tmx_folder_data(self, folder):
        try:
            clean_tmx_folder_data(folder)
            self.after(0, lambda: messagebox.showinfo(
                "Success",
                f"TMX folder cleaned successfully!"
            ))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror(
                "Error",
                f"Error cleaning TMX folder:\n{e}"
            ))
            
def main():
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    logging.info("Starting XML→TMX Converter")
    app = ConverterGUI()
    app.mainloop()
    sys.exit(0)

if __name__ == "__main__":
    main()