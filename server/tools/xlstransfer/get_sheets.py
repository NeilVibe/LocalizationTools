#!/usr/bin/env python3
"""
Get sheet names from Excel file
Usage: python get_sheets.py <excel_file>
"""

import sys
import json
import openpyxl


def main():
    try:
        if len(sys.argv) < 2:
            result = {
                "success": False,
                "error": "No file specified"
            }
            print(json.dumps(result))
            sys.exit(1)

        file_path = sys.argv[1]

        # Load workbook to get sheet names
        wb = openpyxl.load_workbook(file_path, read_only=True)
        sheet_names = wb.sheetnames
        wb.close()

        result = {
            "success": True,
            "sheets": sheet_names,
            "file": file_path
        }
        print(json.dumps(result))

    except Exception as e:
        import traceback
        result = {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc()
        }
        print(json.dumps(result))
        sys.exit(1)


if __name__ == "__main__":
    main()
