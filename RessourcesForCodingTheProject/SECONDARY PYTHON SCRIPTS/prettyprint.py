import xml.dom.minidom as minidom
from tkinter import Tk, filedialog
import os

def pretty_print_xml_with_dialog():
    # Hide root Tkinter window
    Tk().withdraw()

    # Ask user to select XML file
    input_file = filedialog.askopenfilename(
        title="Select XML file",
        filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
    )

    if not input_file:
        print("No file selected.")
        return

    # Read XML content
    with open(input_file, "r", encoding="utf-8") as f:
        xml_content = f.read()

    # Parse and pretty print
    dom = minidom.parseString(xml_content)
    pretty_xml = dom.toprettyxml(indent="  ", encoding="utf-8")

    # Create output file path
    base, ext = os.path.splitext(input_file)
    output_file = f"{base}_prettyprint{ext}"

    # Save pretty-printed XML
    with open(output_file, "wb") as f:
        f.write(pretty_xml)

    print(f"Pretty-printed XML saved to: {output_file}")

if __name__ == "__main__":
    pretty_print_xml_with_dialog()