import pandas as pd
import re

# Load your Excel file (no header)
input_file = 'CH CD MASTER GLOSSARY 0612 MEGADONE.xlsx'
output_file = 'CH CD MASTER GLOSSARY 0612 noKR.xlsx'

# Read the Excel file with no header
df = pd.read_excel(input_file, header=None)

# Assume the second column is index 1 (0-based)
col = 1

# Lists to hold rows
korean_rows = []
other_rows = []

# Regex patterns
arrow_pattern = re.compile(r'^[^=]+=>\s*(.+)$')
# This pattern matches if there is ANY Korean character in the string
any_korean_pattern = re.compile(r'[\u3131-\u318F\uAC00-\uD7A3]')

for idx, row in df.iterrows():
    cell = str(row[col]).strip()
    # Check for 'KR => CN' pattern
    arrow_match = arrow_pattern.match(cell)
    if arrow_match:
        # Replace with CN part only
        row_copy = row.copy()
        row_copy[col] = arrow_match.group(1).strip()
        cell = row_copy[col]
    else:
        row_copy = row.copy()
    # Check if ANY Korean character is present
    if any_korean_pattern.search(str(cell)):
        korean_rows.append(row_copy)
    else:
        other_rows.append(row_copy)

# Combine: Korean-containing rows at the top
cleaned_df = pd.DataFrame(korean_rows + other_rows, columns=df.columns)

# Save to Excel with no header and no index
cleaned_df.to_excel(output_file, index=False, header=False)

print(f"Done! Cleaned file saved as {output_file}")