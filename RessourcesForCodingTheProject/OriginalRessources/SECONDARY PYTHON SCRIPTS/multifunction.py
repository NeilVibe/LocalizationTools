#!/usr/bin/env python3
import os
import sys
import datetime
import tkinter as tk
from tkinter import filedialog, messagebox
import xml.etree.ElementTree as ET
import xml.dom.minidom
import pandas as pd
import re

# NEW IMPORTS FOR EMBEDDING+FAISS BASED MATCHING
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

# Set the environment variable for offline mode
os.environ["TRANSFORMERS_OFFLINE"] = "1"

# ------------------ Global Embedding Model ------------------
# Use the local path to load your model. Use raw string format or double backslashes for Windows paths.
local_model_path = r"C:\Users\PEARL\Desktop\KRTransformer"
model = SentenceTransformer(local_model_path)

# ------------------ Utility Functions ------------------
def normalize_kr_text(text):
    """
    If the text contains a colon (:), remove everything before the colon (including the colon)
    and then trim the whitespace. Otherwise, just trim the whitespace.
    Example:
      "마스터 두: 중요해 보일 지라도 그 속에 본질은 없네." becomes "중요해 보일 지라도 그 속에 본질은 없네."
    """
    if ":" in text:
        text = text.split(":", 1)[1]
    return text.strip()

# NEW Helper functions for mis-formatted Excel parsing.
def detect_language(text):
    """
    A simple language detector.
    Returns "KR" if any Hangul character is found;
    otherwise returns "EN" if any Latin letter is found;
    otherwise returns "UNKNOWN".
    Note: if a text has mixed content, we return "KR" (since we check Hangul first).
    """
    for char in text:
        if "가" <= char <= "힣":
            return "KR"
    for char in text:
        if char.isalpha() and char in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ":
            return "EN"
    return "UNKNOWN"

def parse_text_generalized(text):
    """
    Parses the input text into translation pairs.
    
    New logic:
    • The input is split into paragraphs.
    • Each paragraph’s language is determined by detect_language.
    • For every English paragraph, we look upward and downward (within MAX_WINDOW)
      for a valid Korean paragraph.
        – We scan upward (EN index - 1, -2, ...) to get the first valid KR candidate.
        – We scan downward (EN index + 1, +2, ...) to get the first valid KR candidate.
        – If both exist, we compare the absolute differences between the English 
          text length and each candidate's length, and choose the candidate where the
          difference is the smallest.
    • If a match is found, the pair (with a sequential Pair ID) is output.
      Otherwise, the EN paragraph is output with "NO KR FOUND".
    • Finally, any remaining unpaired KR paragraphs are output as "NO EN FOUND".
    """
    raw_paragraphs = re.split(r'\n\s*\n', text)
    paragraphs = []
    for i, para in enumerate(raw_paragraphs):
        para_clean = para.strip()
        if para_clean:
            paragraphs.append({
                'index': i,
                'text': para_clean,
                'lang': detect_language(para_clean)
            })
    
    n = len(paragraphs)
    used = set()  # indices of paragraphs that have been paired
    pairs = []
    pair_id = 1
    MAX_WINDOW = 10          # max paragraphs upward/downward to search
    MIN_KR_LENGTH = 10       # skip very short KR paragraphs (names, coordinates, etc.)
    
    # Process every English paragraph.
    for para in paragraphs:
        idx = para['index']
        if para['lang'] == "EN" and idx not in used:
            en_text = para['text']
            up_candidate = None
            for offset in range(1, MAX_WINDOW + 1):
                j = idx - offset
                if j < 0:
                    break
                if j in used:
                    continue
                if paragraphs[j]['lang'] == "KR":
                    cand_text = paragraphs[j]['text']
                    if len(cand_text) < MIN_KR_LENGTH:
                        continue
                    up_candidate = j
                    break  # first valid upward candidate found
            
            down_candidate = None
            for offset in range(1, MAX_WINDOW + 1):
                j = idx + offset
                if j >= n:
                    break
                if j in used:
                    continue
                if paragraphs[j]['lang'] == "KR":
                    cand_text = paragraphs[j]['text']
                    if len(cand_text) < MIN_KR_LENGTH:
                        continue
                    down_candidate = j
                    break  # first valid downward candidate found

            if up_candidate is None and down_candidate is None:
                used.add(idx)
                pairs.append({
                    "Block": f"Pair_{pair_id}",
                    "KR": "NO KR FOUND",
                    "EN": en_text
                })
                pair_id += 1
            else:
                if up_candidate is not None and down_candidate is not None:
                    diff_up = abs(len(en_text) - len(paragraphs[up_candidate]['text']))
                    diff_down = abs(len(en_text) - len(paragraphs[down_candidate]['text']))
                    best_candidate_index = up_candidate if diff_up <= diff_down else down_candidate
                elif up_candidate is not None:
                    best_candidate_index = up_candidate
                else:
                    best_candidate_index = down_candidate

                chosen_kr = paragraphs[best_candidate_index]['text']
                used.add(idx)
                used.add(best_candidate_index)
                pairs.append({
                    "Block": f"Pair_{pair_id}",
                    "KR": chosen_kr,
                    "EN": en_text
                })
                pair_id += 1

    for para in paragraphs:
        idx = para['index']
        if idx not in used and para['lang'] == "KR":
            used.add(idx)
            pairs.append({
                "Block": f"Pair_{pair_id}",
                "KR": para['text'],
                "EN": "NO EN FOUND"
            })
            pair_id += 1

    for para in paragraphs:
        idx = para['index']
        if idx not in used:
            if para['lang'] == "EN":
                pairs.append({
                    "Block": f"Pair_{pair_id}",
                    "KR": "NO KR FOUND",
                    "EN": para['text']
                })
            else:
                pairs.append({
                    "Block": f"Pair_{pair_id}",
                    "KR": para['text'],
                    "EN": "NO EN FOUND"
                })
            pair_id += 1

    return pairs

# ------------------ Global Variables for File Paths & Widgets ------------------
scraped_file_path = None  # This will now be our Excel file path.
xml_file_path = None

# (global reference for the threshold-entry widget so that we can access it in process_files)
faiss_threshold_entry = None

# ------------------ Helper: Remove Namespace from Tag ------------------
def local_tag(tag):
    """Return the local part of an XML tag, stripping any namespace."""
    return tag.split("}")[-1]

# ------------------ GUI Functions ------------------
def upload_scraped_file():
    global scraped_file_path
    file_path = filedialog.askopenfilename(
        title="Select Excel File", 
        filetypes=[("Excel Files", "*.xlsx *.xls"), ("All Files", "*.*")]
    )
    if file_path:
        scraped_file_path = file_path
        btn_scraped.config(bg="green")
        status_label.config(text="Excel file selected.")
    update_process_button_state()

def upload_xml_file():
    global xml_file_path
    file_path = filedialog.askopenfilename(
        title="Select XML/TMX File",
        filetypes=[("TMX Files", "*.tmx"), ("XML Files", "*.xml"), ("All Files", "*.*")]
    )
    if file_path:
        xml_file_path = file_path
        btn_xml.config(bg="green")
        status_label.config(text="XML/TMX file selected.")
    update_process_button_state()

def update_process_button_state():
    """Enable the process button if both files have been selected."""
    if scraped_file_path and xml_file_path:
        btn_process.config(state="normal", bg="red")
        status_label.config(text="Both files uploaded. Ready to process.")
    else:
        btn_process.config(state="disabled", bg="grey")

# ------------------ Main Processing Function ------------------
def process_files():
    global scraped_file_path, xml_file_path, faiss_threshold_entry, status_label

    # Read the Excel file with no headers.
    try:
        # Using header=None so that we read from the first row, where index 0 holds KR and index 1 holds Translation.
        df = pd.read_excel(scraped_file_path, header=None)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to read Excel file:\n{e}")
        print("Error reading Excel file:", e)
        return

    # Build a list of pairs (KR, EN) from the first two columns.
    pairs = []
    for idx, row in df.iterrows():
        kr_text = str(row.iloc[0]).strip() if pd.notnull(row.iloc[0]) else ""
        en_text = str(row.iloc[1]).strip() if pd.notnull(row.iloc[1]) else ""
        # Normalize KR text: if there is a colon, remove the portion before it.
        kr_text = normalize_kr_text(kr_text)
        if kr_text and en_text:
            pairs.append((kr_text, en_text))

    if not pairs:
        messagebox.showerror("Error", "The Excel file does not contain any valid KR/Translation pairs in the first two columns.")
        return

    # Load and parse the XML/TMX file.
    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
    except Exception as e:
        messagebox.showerror("Error", f"Failed to read XML file:\n{e}")
        print("Error reading XML file:", e)
        return

    # ------------------ Build Lookup from XML ------------------
    # First try to build from <tu> elements (TMX case).
    lookup = {}
    for tu in root.iter():
        if local_tag(tu.tag) != "tu":
            continue

        kr_text = None
        en_seg = None

        # Process each translation variant.
        for tuv in tu:
            if local_tag(tuv.tag) != "tuv":
                continue

            lang = (tuv.get("{http://www.w3.org/XML/1998/namespace}lang") or 
                    tuv.get("xml:lang") or 
                    tuv.get("lang"))
            if not lang:
                continue
            lang_lower = lang.lower()

            seg = None
            for child in tuv:
                if local_tag(child.tag) == "seg":
                    seg = child
                    break
            if seg is None:
                continue

            if lang_lower.startswith("ko"):
                kr_text = seg.text.strip() if seg.text else ""
            elif lang_lower.startswith("en"):
                en_seg = seg

        if kr_text and en_seg:
            lookup[kr_text] = en_seg

    # Fallback: If no <tu> elements, try <LocStr> elements.
    if not lookup:
        print("No <tu> translation units with valid KR/EN data found. Trying <LocStr> elements as fallback.")
        for element in root.iter():
            if local_tag(element.tag) != "LocStr":
                continue
            kr_text = element.get("StrOrigin", "").strip()
            if kr_text:
                lookup[kr_text] = element  # The element that holds the translation.
                
    if not lookup:
        messagebox.showerror("Error", "No translation units (tu) or LocStr elements with valid KR/EN data found in the XML file.")
        print("Error: No valid translation data found in the XML file.")
        return

    # ------------------ Build FAISS Index from XML KR strings ------------------
    try:
        xml_keys = list(lookup.keys())
        # Generate embeddings for all keys.
        xml_embeddings = model.encode(xml_keys, convert_to_numpy=True)
        faiss.normalize_L2(xml_embeddings)
        dim = xml_embeddings.shape[1]
        index_faiss = faiss.IndexFlatIP(dim)
        index_faiss.add(xml_embeddings)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to build FAISS index:\n{e}")
        print("Error building FAISS index:", e)
        return

    # ------------------ Process Each Excel Pair using FAISS Approximate Matching ------------------
    update_count = 0
    try:
        threshold_val = float(faiss_threshold_entry.get())
    except Exception as e:
        threshold_val = 0.94
        print("Error parsing threshold entry, using default 0.94:", e)

    for kr_scrap, en_scrap in pairs:
        query_text = kr_scrap.strip()
        if not query_text:
            continue

        try:
            # Encode the scraped KR and normalize.
            query_embedding = model.encode([query_text], convert_to_numpy=True)
            faiss.normalize_L2(query_embedding)
            distances, indices = index_faiss.search(query_embedding, 1)
            best_score = distances[0][0]
            best_index = indices[0][0]
        except Exception as e:
            print("Error during FAISS search for query:", query_text, e)
            continue

        # If similarity meets the threshold, update the corresponding node.
        if best_score >= threshold_val:
            matched_key = xml_keys[best_index]
            element = lookup[matched_key]
            if local_tag(element.tag) == "seg":
                element.text = en_scrap
            elif local_tag(element.tag) == "LocStr":
                element.set("Str", en_scrap)
            else:
                element.text = en_scrap
            update_count += 1

    if update_count == 0:
        messagebox.showinfo("Info", "No matching entries found in the XML for the Excel data.")
        print("Info: No matching entries found in the XML for the Excel data.")
    else:
        # Save a new file with a timestamped suffix.
        base, ext = os.path.splitext(xml_file_path)
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        new_filename = base + "_parsed_" + timestamp + ext
        try:
            tree.write(new_filename, encoding="utf-8", xml_declaration=True)
            messagebox.showinfo("Success",
                f"Processing complete. {update_count} entries updated.\nNew file saved as:\n{new_filename}")
            print(f"Success: {update_count} entries updated. New file saved as: {new_filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to write new XML file:\n{e}")
            print("Error writing new XML file:", e)
    
    status_label.config(text="Processing complete.")

# ------------------ New Function 1: Convert Excel to TMX ------------------
def convert_excel_to_tmx_file():
    """
    Opens an Excel file that contains KR and Translation in the first two columns
    and converts it into a TMX file using the same format as our XML->TMX conversion.
    Each row becomes a translation unit with:
      • Korean text in the first column (normalized via normalize_kr_text),
      • English text in the second column,
      • x-context property set to the row index.
    The x-document property is set using the Excel file's base name.
    """
    file_path = filedialog.askopenfilename(
        title="Select Excel File to Convert to TMX",
        filetypes=[("Excel Files", "*.xlsx *.xls"), ("All Files", "*.*")]
    )
    
    if not file_path:
        return

    try:
        df = pd.read_excel(file_path, header=None)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to read Excel file:\n{e}")
        print("Error reading Excel file for TMX conversion:", e)
        return

    # Build the TMX structure.
    tmx = ET.Element("tmx", version="1,4")
    header_attr = {
        "creationtool": "Translate Toolkit",
        "creationtoolversion": "3.13.1",
        "segtype": "sentence",
        "o-tmf": "UTF-8",
        "adminlang": "en",
        "srclang": "ko",
        "datatype": "PlainText"
    }
    ET.SubElement(tmx, "header", header_attr)
    body = ET.SubElement(tmx, "body")

    doc_name = os.path.basename(file_path)

    # Process each row.
    for idx, row in df.iterrows():
        kr_text = str(row.iloc[0]).strip() if pd.notnull(row.iloc[0]) else ""
        en_text = str(row.iloc[1]).strip() if pd.notnull(row.iloc[1]) else ""
        if not (kr_text or en_text):
            continue
        kr_text = normalize_kr_text(kr_text)
        tu = ET.SubElement(body, "tu", {"creationid": "ExcelConvert", "changeid": "ExcelConvert"})
        tuv_ko = ET.SubElement(tu, "tuv", {"xml:lang": "ko"})
        seg_ko = ET.SubElement(tuv_ko, "seg")
        seg_ko.text = kr_text
        tuv_en = ET.SubElement(tu, "tuv", {"xml:lang": "en-us"})
        seg_en = ET.SubElement(tuv_en, "seg")
        seg_en.text = en_text
        # Use the row index as context.
        prop_doc = ET.SubElement(tu, "prop", {"type": "x-document"})
        prop_doc.text = doc_name
        prop_ctx = ET.SubElement(tu, "prop", {"type": "x-context"})
        prop_ctx.text = f"Row_{idx+1}"

    rough_string = ET.tostring(tmx, encoding="utf-8")
    reparsed = xml.dom.minidom.parseString(rough_string)
    pretty_xml = reparsed.toprettyxml(indent="  ")
    pretty_lines = pretty_xml.split('\n')
    if pretty_lines[0].strip().startswith("<?xml"):
        pretty_xml = '\n'.join(pretty_lines[1:]).strip() + "\n"

    base, _ = os.path.splitext(file_path)
    new_tmx_path = base + "_converted.tmx"
    try:
        with open(new_tmx_path, "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write('<!DOCTYPE tmx SYSTEM "tmx14.dtd">\n')
            f.write(pretty_xml)
        messagebox.showinfo("Success", f"Successfully converted Excel to TMX.\nNew file saved as:\n{new_tmx_path}")
        print(f"Successfully converted Excel to TMX. File: {new_tmx_path}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to write TMX file:\n{e}")
        print("Error writing TMX file from Excel:", e)

# ------------------ New Function 2: Parse Misformatted Excel ------------------
def parse_misformatted_excel_file():
    """
    Opens an Excel file that was parsed incorrectly (with all data in Column 1).
    
    Steps:
      1. Preprocess: Remove all empty lines.
      2. Preprocess: Remove consecutive Korean rows—if there is a block of consecutive Korean rows,
         only the last in the block is kept.
      3. Then, match Korean to English from top to bottom by pairing each Korean row with the immediately following English row.
         If a KR row is not followed by an EN row, a placeholder "NO EN FOUND" is used.
         If an English row appears without a preceding Korean row (or becomes standalone), it is paired with "NO KR FOUND".
      4. The resulting pairs are saved to a new Excel file with two columns:
         "KR" - containing Korean text or placeholder; and
         "Translation" - containing English text or placeholder.
    
    Note: The function assumes an external function detect_language(text) exists in the global scope
    and returns a language indicator that is normalized to "KR" or "EN".
    """
    import os
    import pandas as pd
    from tkinter import filedialog, messagebox

    # Open a file dialog to ask for the misformatted Excel file.
    file_path = filedialog.askopenfilename(
        title="Select Misformatted Excel File",
        filetypes=[("Excel Files", "*.xlsx *.xls"), ("All Files", "*.*")]
    )
    if not file_path:
        return

    try:
        df = pd.read_excel(file_path, header=None)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to read Excel file:\n{e}")
        print("Error reading misformatted Excel file:", e)
        return

    # STEP 1: Preprocess – remove all empty lines.
    # We consider a row empty if the cell in Column 1 is either NaN or an empty string (after stripping).
    df = df.dropna(subset=[0])
    # Reset the index to preserve the order.
    df.reset_index(drop=True, inplace=True)

    # Build rows_data list: each element is a dictionary with keys: text and lang.
    rows_data = []
    for idx, row in df.iterrows():
        cell_val = row.iloc[0]
        text = str(cell_val).strip()
        if not text:
            continue
        # detect_language must exist in the global scope.
        lang = detect_language(text).upper()  # Expected to return "KR" or "EN"
        rows_data.append({
            "text": text,
            "lang": lang
        })

    if not rows_data:
        messagebox.showerror("Error", "No valid text found in the file.")
        return

    # STEP 2: Preprocess – remove consecutive Korean rows.
    # NEW LOGIC: If there is a block of consecutive Korean rows, only the last one is kept.
    filtered_rows = []
    n_rows = len(rows_data)
    for i, row in enumerate(rows_data):
        if row["lang"] != "KR":
            filtered_rows.append(row)
        else:
            # row is KR; check if it is the last of consecutive KR rows.
            # If this is the last row OR the next row is not KR, then keep this row.
            if i + 1 >= n_rows or rows_data[i + 1]["lang"] != "KR":
                filtered_rows.append(row)
            # Otherwise, skip it because it's not the last in the consecutive block.

    # STEP 3: Pairing logic: match Korean to English from top to bottom.
    result_pairs = []
    i = 0
    n = len(filtered_rows)
    while i < n:
        current = filtered_rows[i]
        if current["lang"] == "KR":
            # Check if the next available row exists and is English.
            if i + 1 < n and filtered_rows[i + 1]["lang"] == "EN":
                pair = {"KR": current["text"], "Translation": filtered_rows[i + 1]["text"]}
                i += 2  # Skip the next row as it is already paired.
            else:
                pair = {"KR": current["text"], "Translation": "NO EN FOUND"}
                i += 1
        else:  # current row is EN.
            pair = {"KR": "NO KR FOUND", "Translation": current["text"]}
            i += 1
        result_pairs.append(pair)

    if not result_pairs:
        messagebox.showerror("Error", "No valid translation pairs could be parsed from the file.")
        return

    # STEP 4: Save the resulting pairs to a new Excel file.
    result_df = pd.DataFrame(result_pairs)
    base, _ = os.path.splitext(file_path)
    new_excel_path = base + "_parsed.xlsx"
    try:
        result_df.to_excel(new_excel_path, index=False)
        messagebox.showinfo("Success", f"Successfully parsed misformatted Excel file.\nNew file saved as:\n{new_excel_path}")
        print(f"Successfully parsed misformatted Excel file. File saved as: {new_excel_path}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to write parsed Excel file:\n{e}")
        print("Error writing parsed Excel file:", e)

# ------------------ New Function 3: Convert XML to TMX ------------------
def convert_xml_to_tmx_file():
    """
    Opens an XML file using the company’s XML format (where each row is a <LocStr> element),
    then creates a TMX file that - row by row - converts each LocStr element into a translation unit.
    For each LocStr, the conversion is as follows:
      • Korean text is taken from the "StrOrigin" attribute.
      • English text is taken from the "Str" attribute.
      • The TMX <tu> contains two <tuv> elements (one per language).
      • Additional properties include the document name (from the root FileName attribute)
        and the StringId (from the LocStr element) as the x-context.
    The resulting TMX file has a correct header, DOCTYPE, and is pretty-printed.
    """
    
    file_path = filedialog.askopenfilename(
        title="Select XML File to Convert",
        filetypes=[("XML Files", "*.xml"), ("All Files", "*.*")]
    )
    
    if not file_path:
        return
    
    # Parse the input XML file.
    try:
        tree = ET.parse(file_path)
        xml_root = tree.getroot()
    except Exception as e:
        messagebox.showerror("Error", f"Failed to parse XML file:\n{e}")
        print("Error parsing XML file:", e)
        return

    # Get the document name from the root attribute "FileName".
    doc_name = xml_root.get("FileName", "ConvertedXML")
    
    # Get all <LocStr> elements from the root.
    locstr_list = xml_root.findall("LocStr")
    if not locstr_list:
        messagebox.showerror("Error", "No <LocStr> elements found in the XML file.")
        return

    # Build the TMX structure.
    tmx = ET.Element("tmx", version="1,4")
    header_attr = {
        "creationtool": "Translate Toolkit",
        "creationtoolversion": "3.13.1",
        "segtype": "sentence",
        "o-tmf": "UTF-8",
        "adminlang": "en",
        "srclang": "ko",
        "datatype": "PlainText"
    }
    ET.SubElement(tmx, "header", header_attr)
    body = ET.SubElement(tmx, "body")

    # Process each LocStr row and convert it into a translation unit.
    for loc in locstr_list:
        # Retrieve the Korean text from StrOrigin and English from Str.
        korean_text = loc.get("StrOrigin", "").strip()
        english_text = loc.get("Str", "").strip()
        string_id = loc.get("StringId", "").strip()
        
        # Skip the row if neither text is available.
        if not (korean_text or english_text):
            continue

        # Create the translation unit <tu>.
        tu = ET.SubElement(body, "tu", {"creationid": "WikiScrap", "changeid": "WikiScrap"})
        
        # Create the Korean translation variant.
        tuv_ko = ET.SubElement(tu, "tuv", {"xml:lang": "ko"})
        seg_ko = ET.SubElement(tuv_ko, "seg")
        seg_ko.text = korean_text
        
        # Create the English translation variant.
        tuv_en = ET.SubElement(tu, "tuv", {"xml:lang": "en-us"})
        seg_en = ET.SubElement(tuv_en, "seg")
        seg_en.text = english_text
        
        # Add additional properties.
        prop_doc = ET.SubElement(tu, "prop", {"type": "x-document"})
        prop_doc.text = doc_name
        prop_ctx = ET.SubElement(tu, "prop", {"type": "x-context"})
        prop_ctx.text = string_id

    # Generate a pretty-printed XML string.
    rough_string = ET.tostring(tmx, encoding="utf-8")
    reparsed = xml.dom.minidom.parseString(rough_string)
    pretty_xml = reparsed.toprettyxml(indent="  ")

    # Remove the extra XML declaration that minidom inserts.
    pretty_lines = pretty_xml.split('\n')
    if pretty_lines[0].strip().startswith("<?xml"):
        pretty_xml = '\n'.join(pretty_lines[1:]).strip() + "\n"
    
    # Build the output file path.
    base, _ = os.path.splitext(file_path)
    new_tmx_path = base + "_converted.tmx"
    
    # Write the TMX file with proper headers.
    try:
        with open(new_tmx_path, "w", encoding="utf-8") as f:
            # Write XML header and DOCTYPE manually.
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write('<!DOCTYPE tmx SYSTEM "tmx14.dtd">\n')
            f.write(pretty_xml)
        messagebox.showinfo("Success", f"Successfully converted XML to TMX.\nNew file saved as:\n{new_tmx_path}")
        print(f"Successfully converted XML to TMX. File: {new_tmx_path}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to write TMX file:\n{e}")
        print("Error writing TMX file:", e)

# ------------------ New Function 4: Convert TMX to Excel ------------------
def convert_tmx_to_excel_file():
    """
    Opens a TMX file and converts it into an Excel file.
    For each translation unit (<tu>), the function extracts:
      • The Original text from one <tuv> (typically the source language),
      • The Translation text from the other <tuv>.
    These are then saved to an Excel file where:
      Column 1: TMX Original text,
      Column 2: TMX Translation text.
    
    If the TMX header specifies a source language (srclang), the <tuv> element with that language
    is considered the Original text. If not, the first <tuv> is considered Original and the second as Translation.
    """
    file_path = filedialog.askopenfilename(
        title="Select TMX File to Convert to Excel",
        filetypes=[("TMX Files", "*.tmx"), ("XML Files", "*.xml"), ("All Files", "*.*")]
    )
    
    if not file_path:
        return
    
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
    except Exception as e:
        messagebox.showerror("Error", f"Failed to parse TMX file:\n{e}")
        print("Error parsing TMX file:", e)
        return

    # Determine the source language from header if available.
    header = root.find("header")
    srclang = "ko"  # default source language
    if header is not None:
        srclang = header.get("srclang", srclang).lower()

    body = root.find("body")
    if body is None:
        messagebox.showerror("Error", "TMX file does not contain a body element.")
        return

    # Prepare list to store extracted pairs.
    tmx_pairs = []
    for tu in body.findall("tu"):
        tuv_elements = tu.findall("tuv")
        original_text = None
        translation_text = None

        # Try to find the <tuv> with source language.
        for tuv in tuv_elements:
            lang = (tuv.get("{http://www.w3.org/XML/1998/namespace}lang") or 
                    tuv.get("xml:lang") or "")
            if lang.lower() == srclang:
                seg = tuv.find("seg")
                if seg is not None and seg.text:
                    original_text = seg.text.strip()
                break

        # If original_text was not found using srclang, default to the first tuv.
        if original_text is None and len(tuv_elements) > 0:
            seg = tuv_elements[0].find("seg")
            if seg is not None and seg.text:
                original_text = seg.text.strip()

        # For translation_text, choose a different <tuv> than the one chosen as original.
        for tuv in tuv_elements:
            lang = (tuv.get("{http://www.w3.org/XML/1998/namespace}lang") or 
                    tuv.get("xml:lang") or "")
            if original_text is not None:
                # If using srclang based matching, skip that one.
                if lang.lower() == srclang:
                    continue
            seg = tuv.find("seg")
            if seg is not None and seg.text:
                translation_text = seg.text.strip()
                break

        # If there is only one tuv, assign a placeholder for translation_text.
        if original_text is None and translation_text is None and len(tuv_elements) == 1:
            seg = tuv_elements[0].find("seg")
            if seg is not None and seg.text:
                original_text = seg.text.strip()
            translation_text = "NO Translation Found"

        # Only add the pair if at least one of the texts is present.
        if original_text or translation_text:
            tmx_pairs.append({
                "Original Text": original_text if original_text else "",
                "Translation Text": translation_text if translation_text else ""
            })

    if not tmx_pairs:
        messagebox.showerror("Error", "No valid translation units found in the TMX file.")
        return

    # Save the pairs to an Excel file.
    result_df = pd.DataFrame(tmx_pairs)
    base, _ = os.path.splitext(file_path)
    new_excel_path = base + "_converted.xlsx"
    try:
        result_df.to_excel(new_excel_path, index=False)
        messagebox.showinfo("Success", f"Successfully converted TMX to Excel.\nNew file saved as:\n{new_excel_path}")
        print(f"Successfully converted TMX to Excel. File: {new_excel_path}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to write Excel file:\n{e}")
        print("Error writing Excel file from TMX:", e)

# ------------------ Main GUI ------------------
def main():
    global btn_scraped, btn_xml, btn_process, status_label, faiss_threshold_entry

    root = tk.Tk()
    root.title("TMX Parser and Updater with FAISS Matching")
    root.geometry("550x700")

    btn_scraped = tk.Button(root, text="Upload Excel File",
                            command=upload_scraped_file, width=30, height=2)
    btn_scraped.pack(pady=10)

    btn_xml = tk.Button(root, text="Upload XML/TMX File",
                        command=upload_xml_file, width=30, height=2)
    btn_xml.pack(pady=10)

    btn_process = tk.Button(root, text="Process", command=process_files,
                            state="disabled", bg="grey", width=30, height=2)
    btn_process.pack(pady=20)

    # Button for XML to TMX conversion.
    btn_convert = tk.Button(root, text="Convert XML to TMX",
                            command=convert_xml_to_tmx_file, width=30, height=2, bg="lightblue")
    btn_convert.pack(pady=10)

    # Button for Excel to TMX conversion.
    btn_excel2tmx = tk.Button(root, text="Convert Excel to TMX",
                              command=convert_excel_to_tmx_file, width=30, height=2, bg="lightgreen")
    btn_excel2tmx.pack(pady=10)

    # Button for misformatted Excel file parsing.
    btn_parse_misformatted = tk.Button(root, text="Parse Misformatted Excel",
                              command=parse_misformatted_excel_file, width=30, height=2, bg="lightyellow")
    btn_parse_misformatted.pack(pady=10)

    # NEW Button for TMX to Excel conversion.
    btn_tmx2excel = tk.Button(root, text="Convert TMX to Excel",
                              command=convert_tmx_to_excel_file, width=30, height=2, bg="orange")
    btn_tmx2excel.pack(pady=10)

    # New frame for threshold input.
    threshold_frame = tk.Frame(root)
    threshold_frame.pack(padx=10, pady=10)
    tk.Label(threshold_frame, text="최소 일치율").grid(row=0, column=0)
    faiss_threshold_entry = tk.Entry(threshold_frame, width=10)
    faiss_threshold_entry.grid(row=0, column=1)
    faiss_threshold_entry.insert(0, "0.91")

    status_label = tk.Label(root, text="Please upload the files.", fg="blue")
    status_label.pack(pady=10)

    root.mainloop()

if __name__ == "__main__":
    main()