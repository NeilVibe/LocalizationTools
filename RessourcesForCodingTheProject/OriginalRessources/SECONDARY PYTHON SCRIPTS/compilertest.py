import sys
import os
import re
from lxml import etree

# --- XML Utilities ---

def fix_bad_entities(xml_text):
    """Fix bad XML entities that are not predefined."""
    return re.sub(r'&(?!lt;|gt;|amp;|apos;|quot;)', '&amp;', xml_text)

def replace_newlines_text(text):
    """Replace newlines with proper XML representation for any text."""
    if text is None:
        return text
    cleaned = text.replace('\n', '&lt;br/&gt;')
    cleaned = cleaned.replace('\\n', '&lt;br/&gt;')
    return cleaned

def preprocess_tmx_content(raw_content):
    """Pre-process TMX content with simple regex replacements."""
    def replace_in_seg(match):
        seg_content = match.group(1)
        cleaned = seg_content.replace('\n', '&lt;br/&gt;')
        cleaned = cleaned.replace('\\n', '&lt;br/&gt;')
        return f'<seg>{cleaned}</seg>'
    return re.sub(r'<seg>(.*?)</seg>', replace_in_seg, raw_content, flags=re.DOTALL)

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

# --- Core XML Parsing ---

def parse_xml_file(file_path):
    """Parse XML file with recovery and strict validation."""
    try:
        txt = open(file_path, encoding='utf-8').read()
    except Exception as e:
        print(f"[ERROR] Error reading {file_path!r}: {e}")
        return None

    txt = fix_bad_entities(txt)
    wrapped = "<ROOT>\n" + txt + "\n</ROOT>"

    # First: recovery mode
    rec_parser = etree.XMLParser(recover=True)
    try:
        recovered = etree.fromstring(wrapped.encode('utf-8'), parser=rec_parser)
    except etree.XMLSyntaxError as e:
        print(f"[FATAL] Cannot recover {file_path!r}: {e}")
        return None

    # Second: strict mode
    strict_parser = etree.XMLParser(recover=False)
    blob = etree.tostring(recovered, encoding='utf-8')
    try:
        etree.fromstring(blob, parser=strict_parser)
        return True
    except etree.XMLSyntaxError as e:
        report_xml_error(file_path, e)
        return False

def report_xml_error(file_path, error):
    """Report XML syntax error with line/column and faulty line."""
    error_msg = str(error).strip()
    line, column = getattr(error, 'position', (None, None))
    print(f"❌ XML Parse Error in {file_path}")
    if line is not None:
        print(f"   → At line {line}, column {column}: {error_msg}")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if 1 <= line <= len(lines):
                    faulty_line = lines[line - 1].rstrip("\n")
                    print(f"     Faulty line {line}: {faulty_line}")
        except Exception as file_err:
            print(f"⚠ Could not read file to show faulty line: {file_err}")
    else:
        print(f"   → {error_msg}")

# --- Main Compiler ---

def compile_xml_path(path):
    if os.path.isdir(path):
        files = get_all_xml_files(path)
    else:
        files = [path]

    if not files:
        print(f"[INFO] No XML files found in {path}")
        return

    all_ok = True
    for file in files:
        print(f"🔍 Checking: {file}")
        ok = parse_xml_file(file)
        if ok:
            print(f"✅ {file} is valid XML.")
        else:
            all_ok = False
    if all_ok:
        print("\n🎉 All XML files are valid!")
    else:
        print("\n❌ Some XML files have errors.")

# --- Entry Point ---

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <xml_file_or_folder>")
        sys.exit(1)
    compile_xml_path(sys.argv[1])