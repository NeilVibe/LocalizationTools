import tkinter as tk
from tkinter import filedialog
import re
import os

def main():
    # Hide root Tkinter window
    root = tk.Tk()
    root.withdraw()

    # Ask user to select XML file
    file_path = filedialog.askopenfilename(
        title="Select XML File",
        filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
    )

    if not file_path:
        print("No file selected.")
        return

    print(f"Scanning file: {file_path}")

    # Regex for a correct <LocStr ... /> line
    # This assumes attributes are properly quoted and tag closes with />
    locstr_pattern = re.compile(
        r'^\s*<LocStr\s+'
        r'(?:\w+="[^"]*"\s*)+'
        r'/>\s*$'
    )

    flagged_lines = []

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        for lineno, line in enumerate(f, start=1):
            if "<LocStr" in line:
                if not locstr_pattern.match(line):
                    flagged_lines.append(f"Line {lineno}: {line.rstrip()}")

    if flagged_lines:
        print("❌ Found broken lines:")
        for fl in flagged_lines:
            print(fl)

        output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "flagged_lines.txt")
        with open(output_path, "w", encoding="utf-8") as out_f:
            for fl in flagged_lines:
                out_f.write(fl + "\n")

        print(f"\n📄 Flagged lines saved to: {output_path}")
    else:
        print("✅ All <LocStr> lines appear correctly formatted.")

if __name__ == "__main__":
    main()