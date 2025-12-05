"""
Script Name: cell_parser.py
Created: 2025-12-05
Purpose: Parse cells with <<header::value>> format and expand into columns

Input: Excel file with cells containing <<header::value>><<header2::value2>>...
Output: Excel file with headers as columns, values expanded, nice formatting

Usage:
    python cell_parser.py

    - File dialog opens automatically
    - Select Excel file
    - Output saved as [filename]_parsed.xlsx

Dependencies:
    pip install openpyxl
"""

import re
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
except ImportError:
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("Missing Dependency", "openpyxl not installed!\n\nRun: pip install openpyxl")
    sys.exit(1)


def parse_cell(cell_value):
    """Parse <<header::value>> patterns from cell text"""
    if not cell_value:
        return {}

    pattern = r'<<([^:]+)::([^>]*)>>'
    matches = re.findall(pattern, str(cell_value))

    return {header.strip(): value.strip() for header, value in matches}


def get_headers_from_first_row(ws):
    """Extract headers from first row to determine column order"""
    first_cell = ws.cell(row=1, column=1).value

    if not first_cell:
        return []

    pattern = r'<<([^:]+)::'
    matches = re.findall(pattern, str(first_cell))

    return [h.strip() for h in matches]


def apply_styles(ws, num_headers):
    """Apply nice formatting to the worksheet"""
    green_fill = PatternFill(start_color="90EE90", end_color="90EE90", fill_type="solid")
    orange_fill = PatternFill(start_color="FFD699", end_color="FFD699", fill_type="solid")

    header_font = Font(bold=True, size=11)

    thick_border = Border(
        left=Side(style='medium'),
        right=Side(style='medium'),
        top=Side(style='medium'),
        bottom=Side(style='medium')
    )
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )

    # Header row
    for col in range(1, num_headers + 1):
        cell = ws.cell(row=1, column=col)
        cell.fill = green_fill
        cell.font = header_font
        cell.border = thick_border
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

    # Data rows
    for row in range(2, ws.max_row + 1):
        for col in range(1, num_headers + 1):
            cell = ws.cell(row=row, column=col)
            cell.border = thin_border
            cell.alignment = Alignment(vertical='top', wrap_text=True)
            if row % 2 == 0:
                cell.fill = orange_fill

    # Column widths
    for col in range(1, num_headers + 1):
        max_length = 0
        column_letter = openpyxl.utils.get_column_letter(col)

        for row in range(1, min(ws.max_row + 1, 50)):  # Sample first 50 rows
            cell = ws.cell(row=row, column=col)
            if cell.value:
                max_length = max(max_length, len(str(cell.value)))

        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column_letter].width = max(adjusted_width, 15)


def process_file(input_file):
    """Process the Excel file and return result info"""

    # Load workbook
    try:
        wb_in = openpyxl.load_workbook(input_file)
    except Exception as e:
        return False, f"Cannot open file:\n{e}"

    ws_in = wb_in.active

    # Check if file has data
    if ws_in.max_row < 1:
        return False, "File is empty!"

    # Get headers from first row
    headers = get_headers_from_first_row(ws_in)

    if not headers:
        # Fallback: try to detect any <<...::...>> pattern in any cell
        for row in range(1, min(ws_in.max_row + 1, 10)):
            for col in range(1, ws_in.max_column + 1):
                cell_val = ws_in.cell(row=row, column=col).value
                if cell_val and '<<' in str(cell_val) and '::' in str(cell_val):
                    pattern = r'<<([^:]+)::'
                    matches = re.findall(pattern, str(cell_val))
                    if matches:
                        headers = [h.strip() for h in matches]
                        break
            if headers:
                break

    if not headers:
        return False, "No <<header::value>> pattern found!\n\nExpected format:\n<<Korean::안녕>><<English::Hello>>"

    # Create header to column mapping
    header_to_col = {header: idx + 1 for idx, header in enumerate(headers)}

    # Create output workbook
    wb_out = openpyxl.Workbook()
    ws_out = wb_out.active
    ws_out.title = "Parsed"

    # Write headers
    for header, col in header_to_col.items():
        ws_out.cell(row=1, column=col, value=header)

    # Process rows
    out_row = 2
    rows_processed = 0

    for row in range(1, ws_in.max_row + 1):
        for col in range(1, ws_in.max_column + 1):
            cell_value = ws_in.cell(row=row, column=col).value

            if not cell_value:
                continue

            parsed = parse_cell(cell_value)

            if not parsed:
                continue

            # Write values
            for header, value in parsed.items():
                if header in header_to_col:
                    ws_out.cell(row=out_row, column=header_to_col[header], value=value)

            out_row += 1
            rows_processed += 1

    if rows_processed == 0:
        return False, "No data rows found with <<header::value>> pattern!"

    # Apply styles
    apply_styles(ws_out, len(headers))

    # Save output
    output_file = Path(input_file).stem + "_parsed.xlsx"
    output_path = Path(input_file).parent / output_file

    try:
        wb_out.save(output_path)
    except Exception as e:
        return False, f"Cannot save output:\n{e}"

    return True, f"Success!\n\nHeaders: {len(headers)}\nRows: {rows_processed}\n\nSaved to:\n{output_path}"


def main():
    """Main - launches file dialog immediately"""

    # Setup tkinter
    root = tk.Tk()
    root.withdraw()

    # Show file dialog
    input_file = filedialog.askopenfilename(
        title="Select Excel file with <<header::value>> cells",
        filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
    )

    if not input_file:
        # User cancelled
        sys.exit(0)

    # Process
    success, message = process_file(input_file)

    # Show result
    if success:
        messagebox.showinfo("Done", message)
    else:
        messagebox.showerror("Error", message)


if __name__ == "__main__":
    main()
