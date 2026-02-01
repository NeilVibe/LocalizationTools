#!/usr/bin/env python3
import os
import sys
import re
import logging
import threading
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from io import StringIO

from lxml import etree
import xml.dom.minidom
from openpyxl import Workbook

# Create a global XML parser with recovery enabled.
XML_PARSER = etree.XMLParser(recover=True, remove_blank_text=True)

def fix_malformed_xml(xml_text):
    """
    Fixes a common malformation: occurrences of mismatched closing tags like "</>".
    The function tokenizes the XML text and maintains a stack of open tags.
    When a malformed closing tag is encountered it is replaced with a proper closing tag
    taken from the last opened tag.
    (Note: This is a simple fix and assumes the only malformation is a missing element name.)
    """
    # Split text into parts that are either tags or not.
    tokens = re.split(r"(<[^>]+>)", xml_text)
    open_tags = []
    fixed_tokens = []

    # Regular expressions to detect tags.
    open_tag_pattern = re.compile(r"<\s*([A-Za-z0-9_:\-\.]+)(\s|>|/)")
    proper_close_pattern = re.compile(r"<\s*/\s*([A-Za-z0-9_:\-\.]+)\s*>")
    self_close_pattern = re.compile(r"<\s*([A-Za-z0-9_:\-\.]+)([^>]*)/>\s*$")
    malformed_close_pattern = re.compile(r"<\s*/\s*>")  # Matches just </> (or with spaces)

    for token in tokens:
        if token.startswith("<") and token.endswith(">"):
            # Check if token is a malformed closing tag.
            if malformed_close_pattern.fullmatch(token.strip()):
                if open_tags:
                    tag = open_tags.pop()  # get the last open tag name
                    fixed_tokens.append(f"</{tag}>")
                else:
                    # nothing to match, skip this tag
                    pass
            # If it is a proper closing tag.
            elif token.startswith("</"):
                m_close = proper_close_pattern.match(token)
                if m_close:
                    tag_name = m_close.group(1)
                    # If our stack contains this tag at the top, pop it.
                    if open_tags and open_tags[-1] == tag_name:
                        open_tags.pop()
                    else:
                        # In cases of mismatched order, try to remove it from the stack.
                        if tag_name in open_tags:
                            # Remove the last occurrence.
                            idx = len(open_tags) - 1 - open_tags[::-1].index(tag_name)
                            del open_tags[idx]
                    fixed_tokens.append(token)
                else:
                    # Not matching our simple proper close pattern, append as-is.
                    fixed_tokens.append(token)
            # Check if self closing tag; if so no push to open_tags.
            elif self_close_pattern.match(token):
                fixed_tokens.append(token)
            else:
                # Likely an opening tag.
                m_open = open_tag_pattern.match(token)
                if m_open:
                    tag_name = m_open.group(1)
                    open_tags.append(tag_name)
                fixed_tokens.append(token)
        else:
            fixed_tokens.append(token)
    # Append closing tags for any still-open elements.
    while open_tags:
        tag = open_tags.pop()
        fixed_tokens.append(f"</{tag}>")
    return "".join(fixed_tokens)

def parse_xml_file(file_path):
    """
    Reads XML from file_path, applies fix_malformed_xml to correct common malformations,
    and returns a parsed XML element (root) using lxml.
    Returns None if the file cannot be read or parsed.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
    except Exception as e:
        logging.error(f"Error reading XML file {file_path}: {e}", exc_info=True)
        return None

    # Fix malformed closing tags (and similar issues)
    fixed_text = fix_malformed_xml(text)
    try:
        # Use fromstring to get the root element.
        root = etree.fromstring(fixed_text.encode("utf-8"), parser=XML_PARSER)
        return root
    except Exception as e:
        logging.error(f"Error parsing fixed XML file {file_path}: {e}", exc_info=True)
        return None

def get_all_xml_files(input_folder):
    """
    Returns a list of full paths to all XML files (filename ending with .xml) 
    under input_folder (recursively).
    """
    xml_files = []
    for dirpath, _, filenames in os.walk(input_folder):
        for file in filenames:
            if file.lower().endswith(".xml"):
                xml_files.append(os.path.join(dirpath, file))
    return xml_files

def clean_static_key_file(static_key_file):
    """
    Reads the static key XML file as text, fixes malformed tags if needed,
    removes extra XML declarations and DOCTYPEs, and wraps the content in a single root element.
    This preprocessing ensures that multiple <StringKeyTable> sections are wrapped in one valid root.
    """
    try:
        with open(static_key_file, "r", encoding="utf-8") as f:
            contents = f.read()
    except Exception as e:
        logging.error(f"Error reading static key file {static_key_file}: {e}", exc_info=True)
        return None

    # Fix malformed tags if any.
    contents = fix_malformed_xml(contents)
    # Remove XML declaration if any.
    contents = re.sub(r'<\?xml.*?\?>', '', contents)
    # Remove DOCTYPE declaration if exists.
    contents = re.sub(r'<!DOCTYPE[^>]*>', '', contents)
    contents = contents.strip()
    # Wrap the entire content in a single root element.
    wrapped = "<root>" + contents + "</root>"
    return wrapped

def combine_xmls_to_tmx(input_folder, output_file, target_language):
    """
    Processes XML files in the input_folder, extracts translation units from <LocStr> elements,
    and writes them into a combined TMX file.

    Source language is fixed to Korean ("ko") and target language is provided.
    """
    logging.info(f"Starting to process input folder: {input_folder}")
    xml_files = get_all_xml_files(input_folder)
    total_files = len(xml_files)
    print(f"[TMX] Total XML files found: {total_files}")
    file_counter = 0

    # Build the TMX structure.
    tmx = etree.Element("tmx", version="1.4")
    header_attr = {
        "creationtool": "CombinedXMLConverter",
        "creationtoolversion": "1.0",
        "segtype": "sentence",
        "o-tmf": "UTF-8",
        "adminlang": "en",
        "srclang": "ko",
        "datatype": "PlainText"
    }
    etree.SubElement(tmx, "header", header_attr)
    body = etree.SubElement(tmx, "body")

    tu_count = 0

    for xml_file_path in xml_files:
        file_counter += 1
        print(f"[TMX] Processing file {file_counter} of {total_files}: {xml_file_path}")
        logging.info(f"Processing file: {xml_file_path}")

        # Check if file is empty.
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

        # Use the XML root attribute "FileName" if available, else use the base filename.
        doc_name = xml_root.get("FileName") or os.path.basename(xml_file_path)
        logging.debug(f"Using document name: {doc_name}")

        for loc in xml_root.iter("LocStr"):
            korean_text = (loc.get("StrOrigin") or "").strip()
            target_text = (loc.get("Str") or "").strip()
            string_id = (loc.get("StringId") or "").strip()

            if not (korean_text or target_text):
                continue

            tu = etree.SubElement(body, "tu", {"creationid": "CombinedConversion", "changeid": "CombinedConversion"})
            # Korean variant.
            tuv_ko = etree.SubElement(tu, "tuv", {"xml:lang": "ko"})
            seg_ko = etree.SubElement(tuv_ko, "seg")
            seg_ko.text = korean_text
            # Target language variant.
            tuv_target = etree.SubElement(tu, "tuv", {"xml:lang": target_language})
            seg_target = etree.SubElement(tuv_target, "seg")
            seg_target.text = target_text

            # Additional properties.
            prop_doc = etree.SubElement(tu, "prop", {"type": "x-document"})
            prop_doc.text = doc_name
            prop_ctx = etree.SubElement(tu, "prop", {"type": "x-context"})
            prop_ctx.text = (loc.get("StringId") or "").strip() or "NoStringId"

            tu_count += 1
            if tu_count % 10 == 0:
                logging.info(f"Processed {tu_count} translation units so far...")

    if tu_count == 0:
        msg = "No translation units (LocStr elements) were found in the XML files under the selected folder."
        logging.error(msg)
        print(msg)
        return False

    rough_string = etree.tostring(tmx, encoding="utf-8")
    reparsed = xml.dom.minidom.parseString(rough_string)
    pretty_xml = reparsed.toprettyxml(indent=" ")

    pretty_lines = pretty_xml.split('\n')
    if pretty_lines and pretty_lines[0].strip().startswith("<?xml"):
        pretty_xml = '\n'.join(pretty_lines[1:]).strip() + "\n"

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write('<!DOCTYPE tmx SYSTEM "tmx14.dtd">\n')
            f.write(pretty_xml)
        logging.info(f"Successfully combined {tu_count} translation units into: {output_file}")
        print(f"[TMX] Successfully combined {tu_count} translation units into:\n{output_file}")
        return True
    except Exception as e:
        logging.error(f"Error writing combined TMX file: {output_file}\nError: {e}", exc_info=True)
        print(f"[TMX] Error writing combined TMX file: {output_file}\nError: {e}")
        return False

def get_search_results(search_key, input_folder, limit_results=True):
    """
    Recursively searches for <LocStr> elements with CharacterKey exactly matching search_key.
    Returns a list of tuples (StrOrigin, Str, Name) or an error message string.
    """
    logging.info(f"Starting search for CharacterKey: {search_key} in folder: {input_folder}")
    results = []
    xml_files = get_all_xml_files(input_folder)
    total_files = len(xml_files)
    file_counter = 0

    for xml_file_path in xml_files:
        try:
            if os.path.getsize(xml_file_path) == 0:
                logging.debug(f"Skipping empty XML file during search: {xml_file_path}")
                continue
        except Exception as e:
            logging.error(f"Error checking file size for {xml_file_path}: {e}", exc_info=True)
            continue
        file_counter += 1
        print(f"[Search] Searching in file {file_counter} of {total_files}: {xml_file_path}")
        logging.info(f"Searching in file: {xml_file_path}")
        xml_root = parse_xml_file(xml_file_path)
        if xml_root is None:
            logging.debug(f"XML file is empty or failed to parse during search: {xml_file_path}")
            continue

        for loc in xml_root.iter("LocStr"):
            character_key = (loc.get("CharacterKey") or "").strip()
            if character_key == search_key:
                str_origin = (loc.get("StrOrigin") or "").strip()
                str_text = (loc.get("Str") or "").strip()
                name_attr = (loc.get("Name") or "").strip() or "XXX"
                if not (str_origin or str_text):
                    continue
                results.append((str_origin, str_text, name_attr))

    if not results:
        msg = f"No matching entries found for CharacterKey: {search_key}"
        logging.error(msg)
        return msg

    results_sorted = sorted(results, key=lambda x: len(x[1]))
    results_to_show = results_sorted[:10] if limit_results else results_sorted

    return results_to_show

def contains_korean(text):
    """
    Returns True if the text contains any Korean characters.
    """
    return bool(re.search(r'[가-힣]', text))

def build_translation_lookup(input_folder):
    """
    Builds a lookup dictionary mapping StrOrigin -> translation from all XML files.
    Uses a pre-built XML file list.
    """
    lookup = {}
    logging.info(f"Building translation lookup from folder: {input_folder}")
    xml_files = get_all_xml_files(input_folder)
    file_count = 0
    for xml_file_path in xml_files:
        try:
            if os.path.getsize(xml_file_path) == 0:
                logging.debug(f"Skipping empty XML file during lookup: {xml_file_path}")
                continue
        except Exception as e:
            logging.error(f"Error checking file size for {xml_file_path}: {e}", exc_info=True)
            continue

        file_count += 1
        xml_root = parse_xml_file(xml_file_path)
        if xml_root is None:
            logging.debug(f"XML file failed to parse during lookup: {xml_file_path}")
            continue

        for loc in xml_root.iter("LocStr"):
            key = (loc.get("StrOrigin") or "").strip()
            if key:
                translation = (loc.get("Str") or "").strip()
                if key not in lookup:
                    lookup[key] = translation
    logging.info(f"Translation lookup completed from {file_count} files. Total entries: {len(lookup)}")
    return lookup

def get_translation_by_name(name, lookup):
    """
    Retrieves the translation using the Name attribute as key in the lookup.
    """
    return lookup.get(name, "")

def extract_category_info_new(category, input_folder, static_key_file):
    """
    NEW EXTRACTION LOGIC WITH REGEX:

    1. Preprocess the static key file so that it has a single root.
    2. For each mapping row in the static file:
         - Extract the original StrKey attribute.
         - Then, instead of using XML parsing, read each XML file line by line and look for any row
           that contains the attribute "StrKey" along with the category-specific attribute (ItemName for Item,
           CharacterName for Character, Name for Knowledge) using regex.
         - From those rows, extract the StrKey and name.
    3. Using that name, do a quick lookup search (via XML parsing) against all LocStr nodes for an exact match
         on StrOrigin; retrieve the corresponding StringId and translation (Str).
    4. Return a list of tuples:
         (in_game_key, original static StrKey, name, translation, string_id, mod_time)
    5. Deduplicate entries by name (keeping the one with the latest modification time), filter out numeric in‐game
         keys below 400, then sort the result.
    """
    import re

    logging.info(f"=== Start NEW extraction for category '{category}' ===")

    # Preprocess the static key file.
    cleaned_xml = clean_static_key_file(static_key_file)
    if cleaned_xml is None:
        logging.error("Failed to clean the static key file.")
        return []
    try:
        key_root = etree.fromstring(cleaned_xml.encode("utf-8"), parser=XML_PARSER)
    except Exception as e:
        logging.error(f"Error parsing cleaned static key file: {e}", exc_info=True)
        return []

    # Get all rows from the static key file.
    key_maps = key_root.xpath("//StringKeyMap")
    logging.info(f"Static key file read: {len(key_maps)} StringKeyMap rows found.")

    # Build a lookup for category-specific nodes using regex scanning line by line.
    # node_lookup maps lower(StrKey) to a tuple: (extracted name, modification time)
    node_lookup = {}
    xml_files = []
    for root_dir, dirs, files in os.walk(input_folder):
        for f in files:
            if f.lower().endswith(".xml"):
                xml_files.append(os.path.join(root_dir, f))

    # Define regex patterns according to category.
    if category.lower() == "item":
        # Look for a row that contains both StrKey and ItemName
        strkey_pattern = re.compile(r'StrKey="([^"]+)"')
        name_pattern   = re.compile(r'ItemName="([^"]+)"')
    elif category.lower() == "character":
        strkey_pattern = re.compile(r'StrKey="([^"]+)"')
        name_pattern   = re.compile(r'CharacterName="([^"]+)"')
    elif category.lower() == "knowledge":
        strkey_pattern = re.compile(r'StrKey="([^"]+)"')
        name_pattern   = re.compile(r'Name="([^"]+)"')
    else:
        # Fallback (should not really occur) try to get StrKey and Name
        strkey_pattern = re.compile(r'StrKey="([^"]+)"')
        name_pattern   = re.compile(r'Name="([^"]+)"')

    for xml_file in xml_files:
        try:
            if os.path.getsize(xml_file) == 0:
                continue
        except Exception:
            continue
        try:
            mod_time = os.path.getmtime(xml_file)
        except Exception:
            mod_time = 0
        try:
            with open(xml_file, "r", encoding="utf-8") as f:
                for line in f:
                    # Only process lines that mention StrKey
                    if "StrKey=" in line:
                        m_key = strkey_pattern.search(line)
                        m_name = name_pattern.search(line)
                        if m_key and m_name:
                            str_key_val = m_key.group(1).strip()
                            name_val    = m_name.group(1).strip()
                            lower_key = str_key_val.lower()
                            # Save the data if this key is new or if this file is newer
                            if lower_key not in node_lookup or mod_time > node_lookup[lower_key][1]:
                                node_lookup[lower_key] = (name_val, mod_time)
        except Exception as e:
            logging.error(f"Error reading file {xml_file} for regex extraction: {e}", exc_info=True)
            continue

    logging.info(f"Category '{category}': Built node lookup with {len(node_lookup)} keys based on regex search.")

    # Build a lookup dictionary for LocStr nodes using regular XML parsing.
    # loc_lookup maps StrOrigin -> (loc_node, modification time)
    loc_lookup = {}
    for xml_file in xml_files:
        try:
            if os.path.getsize(xml_file) == 0:
                continue
        except Exception:
            continue
        xml_root = parse_xml_file(xml_file)
        if xml_root is None:
            continue
        try:
            mod_time = os.path.getmtime(xml_file)
        except Exception:
            mod_time = 0
        for loc in xml_root.iter("LocStr"):
            origin = (loc.get("StrOrigin") or "").strip()
            if origin:
                if origin not in loc_lookup or mod_time > loc_lookup[origin][1]:
                    loc_lookup[origin] = (loc, mod_time)

    results = []
    mapping_counter = 0
    for key_map in key_maps:
        mapping_counter += 1
        in_game_key = (key_map.get("Key") or "").strip()
        db_key_std  = (key_map.get("StrKey") or "").strip()
        if not (in_game_key and db_key_std):
            continue
        lower_db_key = db_key_std.lower()
        if lower_db_key in node_lookup:
            # Instead of accessing an XML node, we now have the extracted name
            name_attr, node_mod_time = node_lookup[lower_db_key]
            if not name_attr:
                logging.debug(f"Mapping {mapping_counter}: Regex extraction returned an empty name for DB key '{db_key_std}'.")
                continue

            if name_attr in loc_lookup:
                loc_node, loc_mod_time = loc_lookup[name_attr]
                string_id_found = (loc_node.get("StringId") or "").strip()
                translation     = (loc_node.get("Str") or "").strip()
            else:
                logging.debug(f"Mapping {mapping_counter}: No LocStr found for name '{name_attr}'.")
                string_id_found = ""
                translation     = ""
            results.append((in_game_key, db_key_std, name_attr, translation, string_id_found, node_mod_time))
        else:
            logging.debug(f"Mapping {mapping_counter}: No regex extracted entry with StrKey '{db_key_std}' was found.")
    logging.info(f"Mapping phase completed. Found {len(results)} matching mappings before duplicate elimination.")

    # Duplicate elimination: keep only the latest entry (by modification time) for each name.
    deduped = {}
    for row in results:
        name_attr = row[2]
        if name_attr in deduped:
            if row[5] > deduped[name_attr][5]:
                deduped[name_attr] = row
        else:
            deduped[name_attr] = row
    results = list(deduped.values())
    logging.info(f"After duplicate elimination, {len(results)} results remain.")

    # Filter out rows whose in-game key (if numeric) is below 400.
    filtered_results = []
    for row in results:
        eng_key = row[0]
        if eng_key.isdigit() and int(eng_key) < 400:
            logging.debug(f"Filtering out row with in-game key below 400: {eng_key}")
            continue
        filtered_results.append(row)

    def sort_key(row):
        key_val = row[0]
        if not key_val or not key_val.isdigit():
            return (0, 0)
        else:
            return (1, int(key_val))
    sorted_results = sorted(filtered_results, key=sort_key)
    logging.info(f"Category extraction completed. {len(sorted_results)} sorted results for category '{category}'.")
    return sorted_results

def write_category_results_excel(results, category, input_folder):
    """
    Writes the extracted category information to an Excel file.

    Expected tuple per row: (Engine Key, DB Key, Name, Translation, StringId, mod_time)
    The Excel header contains: "Engine Key", "DB Key", "Name", "Translation", "StringId".
    The output file is named '<category>_datetime.xlsx'.
    Even if no data rows are present, an Excel file with header will be created.

    Update:
    1. If a row has any empty cell (in any of the first five columns), drop the whole row.
    2. If the DB Key (column 2) starts with "dev_", drop the whole row.
    """
    now = datetime.now()
    output_file = f"{category}_{now.strftime('%Y%m%d_%H%M%S')}.xlsx"

    wb = Workbook()
    ws = wb.active
    ws.title = f"{category} Data"

    header = ["Engine Key", "DB Key", "Name", "Translation", "StringId"]
    ws.append(header)

    for row in results:
        eng_key, db_key, name_attr, translation, string_id, mod_time = row
        # Drop row if any of the required cells is empty.
        if not (eng_key and db_key and name_attr and translation and string_id):
            continue
        # Drop row if DB Key starts with "dev_".
        if db_key.startswith("dev_"):
            continue
        ws.append([eng_key, db_key, name_attr, translation, string_id])

    try:
        wb.save(output_file)
        logging.info(f"Category data written to Excel file: {output_file}")
    except Exception as e:
        logging.error(f"Error writing category results to Excel file: {output_file}\nError: {e}", exc_info=True)
        output_file = ""
    return output_file

class ConverterGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("XML to TMX Converter")
        self.geometry("800x750")
        self.resizable(False, False)

        # Folder selection variables.
        self.selected_folder = tk.StringVar()
        self.folder_chosen = False

        self.target_language = tk.StringVar()
        self.search_key = tk.StringVar()
        self.category_choice = tk.StringVar(value="Item")
        self.search_option = tk.StringVar(value="10")

        self.language_options = {
            "English (US)": "en-US",
            "French (FR)": "fr-FR",
            "German (DE)": "de-DE",
            "Traditional Chinese (TW)": "zh-TW",
            "Simplified Chinese (CH)": "zh-CN",
            "Japanese (JP)": "ja-JP",
            "Spanish (ES)": "es-ES",
            "Italian (IT)": "it-IT",
            "Portuguese (PT)": "pt-PT"
        }
        self.target_language.set("English (US)")

        # Set the static key file to be in the same folder as the script.
        self.static_key_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "StaticInfo_StringKeyTable.xml")
        if not os.path.exists(self.static_key_file):
            messagebox.showerror("Error", f"Static key file not found:\n{self.static_key_file}\nPlease ensure it is located with the script.")
            sys.exit(1)

        self.create_widgets()

    def create_widgets(self):
        padding_options = {'padx': 10, 'pady': 10}

        # Folder selection frame.
        folder_frame = tk.Frame(self)
        folder_frame.pack(fill="x", **padding_options)

        select_folder_button = tk.Button(folder_frame, text="Select Folder", command=self.select_folder)
        select_folder_button.grid(row=0, column=0, sticky="w")
        self.select_folder_button = select_folder_button

        self.folder_label = tk.Label(folder_frame, text="No folder selected", wraplength=500)
        self.folder_label.grid(row=0, column=1, sticky="w", padx=10)

        # Language selection frame.
        lang_frame = tk.Frame(self)
        lang_frame.pack(fill="x", **padding_options)

        lang_label = tk.Label(lang_frame, text="Select Target Language:")
        lang_label.grid(row=0, column=0, sticky="w")

        lang_dropdown = ttk.OptionMenu(lang_frame, self.target_language, self.target_language.get(), *self.language_options.keys())
        lang_dropdown.grid(row=0, column=1, sticky="w", padx=10)

        convert_button = tk.Button(self, text="Convert to TMX", command=self.convert)
        convert_button.pack(**padding_options)

        separator1 = ttk.Separator(self, orient='horizontal')
        separator1.pack(fill='x', padx=10, pady=10)

        search_frame = tk.Frame(self)
        search_frame.pack(fill="x", **padding_options)

        search_label = tk.Label(search_frame, text="Enter CharacterKey:")
        search_label.grid(row=0, column=0, sticky="w")

        search_entry = tk.Entry(search_frame, textvariable=self.search_key, width=40)
        search_entry.grid(row=0, column=1, sticky="w", padx=10)

        search_button = tk.Button(search_frame, text="Search Translations", command=self.search_translations)
        search_button.grid(row=0, column=2, sticky="w", padx=10)

        option_label = tk.Label(search_frame, text="Search Results:")
        option_label.grid(row=1, column=0, sticky="w")
        radio_top10 = tk.Radiobutton(search_frame, text="Top 10", value="10", variable=self.search_option)
        radio_top10.grid(row=1, column=1, sticky="w", padx=10)
        radio_all = tk.Radiobutton(search_frame, text="All", value="all", variable=self.search_option)
        radio_all.grid(row=1, column=2, sticky="w", padx=10)

        results_container = tk.Frame(self)
        results_container.pack(fill="both", expand=True, padx=10, pady=(0,10))

        self.results_canvas = tk.Canvas(results_container)
        self.results_canvas.pack(side="left", fill="both", expand=True)

        vsb = ttk.Scrollbar(results_container, orient="vertical", command=self.results_canvas.yview)
        vsb.pack(side="right", fill="y")
        self.results_canvas.configure(yscrollcommand=vsb.set)

        self.results_inner = tk.Frame(self.results_canvas)
        self.results_inner.bind(
            "<Configure>",
            lambda event: self.results_canvas.configure(scrollregion=self.results_canvas.bbox("all"))
        )
        self.results_canvas.create_window((0, 0), window=self.results_inner, anchor="nw")

        separator2 = ttk.Separator(self, orient='horizontal')
        separator2.pack(fill='x', padx=10, pady=10)

        # Category extraction frame.
        cat_frame = tk.Frame(self)
        cat_frame.pack(fill="x", **padding_options)

        cat_label = tk.Label(cat_frame, text="Select Category (for extraction):")
        cat_label.grid(row=0, column=0, sticky="w")

        category_dropdown = ttk.OptionMenu(cat_frame, self.category_choice, self.category_choice.get(), "Item", "Character", "Knowledge")
        category_dropdown.grid(row=0, column=1, sticky="w", padx=10)

        extract_button = tk.Button(cat_frame, text="Extract Category", command=self.extract_category_gui)
        extract_button.grid(row=0, column=2, sticky="w", padx=10)

    def select_folder(self):
        folder = filedialog.askdirectory(title="Select Parent Folder Containing XML Files")
        if folder:
            self.selected_folder.set(folder)
            self.folder_label.config(text=folder)
            self.select_folder_button.config(bg="green")
            self.folder_chosen = True

    def convert(self):
        if not self.folder_chosen:
            messagebox.showerror("Error", "Please select a folder first.")
            return

        output_file = filedialog.asksaveasfilename(
            title="Save Combined TMX File As",
            defaultextension=".tmx",
            filetypes=[("TMX Files", "*.tmx"), ("All Files", "*.*")]
        )
        if not output_file:
            messagebox.showinfo("Info", "No output file selected. Conversion cancelled.")
            return

        # Configure logging to both console and file.
        output_dir = os.path.dirname(output_file)
        log_file = os.path.join(output_dir, "error_log.txt")
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler(log_file, mode='w', encoding='utf-8')
            ]
        )
        logging.info("Logging is set up")
        logging.info(f"Log file is located at: {log_file}")

        target_lang_key = self.target_language.get()
        target_lang_code = self.language_options.get(target_lang_key, "en-US")

        threading.Thread(target=self.threaded_convert, args=(output_file, target_lang_code), daemon=True).start()

    def threaded_convert(self, output_file, target_lang_code):
        success = combine_xmls_to_tmx(self.selected_folder.get(), output_file, target_lang_code)
        if success:
            self.after(0, lambda: messagebox.showinfo("Success", f"Combined TMX file created successfully:\n{output_file}"))
        else:
            self.after(0, lambda: messagebox.showerror("Error", "Failed to create the combined TMX file. See log for details."))

    def search_translations(self):
        if not self.folder_chosen:
            messagebox.showerror("Error", "Please select a folder first.")
            return

        search_key = self.search_key.get().strip()
        if not search_key:
            messagebox.showerror("Error", "Please enter a CharacterKey to search for.")
            return

        limit_results = True if self.search_option.get() == "10" else False

        threading.Thread(target=self.threaded_search, args=(search_key, limit_results), daemon=True).start()

    def threaded_search(self, search_key, limit_results):
        logging.info(f"Starting search for key: {search_key}")
        results = get_search_results(search_key, self.selected_folder.get(), limit_results)
        self.after(0, lambda: self.update_search_results(results))

    def update_search_results(self, results):
        for widget in self.results_inner.winfo_children():
            widget.destroy()

        if isinstance(results, str):
            error_label = tk.Label(self.results_inner, text=results, wraplength=750, fg="red")
            error_label.grid(row=0, column=0, columnspan=3, sticky="w", padx=5, pady=5)
            return

        header_bg = "#cccccc"
        headers = ["StrOrigin", "Str", "Name"]
        for col, header in enumerate(headers):
            label = tk.Label(self.results_inner, text=header, bg=header_bg, relief="ridge", wraplength=250, font=('Helvetica', 10, 'bold'))
            label.grid(row=0, column=col, sticky="nsew", padx=1, pady=1)
            self.results_inner.grid_columnconfigure(col, weight=1)

        for i, (str_origin, str_text, name_attr) in enumerate(results, start=1):
            lbl_origin = tk.Label(self.results_inner, text=str_origin, relief="ridge", wraplength=250, anchor="w", justify="left")
            lbl_origin.grid(row=i, column=0, sticky="nsew", padx=1, pady=1)
            lbl_str = tk.Label(self.results_inner, text=str_text, relief="ridge", wraplength=250, anchor="w", justify="left")
            lbl_str.grid(row=i, column=1, sticky="nsew", padx=1, pady=1)
            lbl_name = tk.Label(self.results_inner, text=f"Name={name_attr}", relief="ridge", wraplength=250, anchor="w", justify="left")
            lbl_name.grid(row=i, column=2, sticky="nsew", padx=1, pady=1)

    def extract_category_gui(self):
        if not self.folder_chosen:
            messagebox.showerror("Error", "Please select a folder first.")
            return

        category = self.category_choice.get().strip()
        if not category:
            messagebox.showerror("Error", "Please select a Category for extraction.")
            return

        logging.info(f"Starting new extraction for Category: {category}")
        threading.Thread(target=self.threaded_extract_category, args=(category,), daemon=True).start()

    def threaded_extract_category(self, category):
        results = extract_category_info_new(category, self.selected_folder.get(), self.static_key_file)
        output_file = write_category_results_excel(results, category, self.selected_folder.get())
        if results:
            self.after(0, lambda: messagebox.showinfo("Success", f"Category data saved to Excel file:\n{output_file}"))
        else:
            self.after(0, lambda: messagebox.showwarning(
                "Warning", f"No matching entries were found for category '{category}'.\nAn Excel file with header has been created:\n{output_file}"))

def main():
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    logging.info("Starting XML Converter Application")
    app = ConverterGUI()
    app.mainloop()
    sys.exit(0)

if __name__ == "__main__":
    main()