import pandas as pd
import openpyxl
from pathlib import Path
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import os
import shutil
from openpyxl.utils import get_column_letter
from openpyxl.styles import Font, Alignment
from difflib import SequenceMatcher
from functools import lru_cache
from collections import defaultdict
import numpy as np
from typing import Dict, List, Tuple, Set, Optional
import heapq
import time

# =====================================================
# STEP 1: ADVANCED INDEXING AND MATCHING SYSTEM
# =====================================================

class FuzzyMatcher:
    """Advanced fuzzy matching system with intelligent indexing - NO MULTIPROCESSING"""
    
    def __init__(self, threshold_col2=0.71, threshold_col3=0.11):
        self.threshold_col2 = threshold_col2
        self.threshold_col3 = threshold_col3
        self.exact_index = {}  # {normalized_value: [(sheet, row, mapped_val)]}
        self.char_ngram_index = defaultdict(set)  # {3-gram: set(row_ids)}
        self.length_buckets = defaultdict(list)  # {length: [(sheet, row, text, mapped_val)]}
        self.used_rows = set()  # Track (sheet, row) tuples already matched
        self.all_target_data = []  # Store all target data with unique IDs
        
        # Cache for similarity calculations
        self._similarity_cache = {}
        self.cache_hits = 0
        self.cache_misses = 0
    
    @lru_cache(maxsize=10000)
    def calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity with caching"""
        return SequenceMatcher(None, str1, str2).ratio()
    
    def get_ngrams(self, text: str, n: int = 3) -> set:
        """Generate character n-grams for fuzzy matching"""
        if len(text) < n:
            return {text}
        return {text[i:i+n] for i in range(len(text) - n + 1)}
    
    def build_indexes(self, all_sheets: Dict[str, pd.DataFrame]):
        """Build multiple indexes for efficient searching"""
        print("[INDEXING] Building advanced indexes...")
        start_time = time.time()
        
        row_id = 0
        for sheet_name, df in all_sheets.items():
            # Normalize all cells to strings
            df = df.fillna('')
            df = df.astype(str)
            
            for row_idx in range(len(df)):
                # Get the mapped value (Col4 or Col2 or 'N/A')
                if df.shape[1] > 3:
                    mapped_value = df.iloc[row_idx, 1]
                elif df.shape[1] > 1:
                    mapped_value = df.iloc[row_idx, 1]
                else:
                    mapped_value = 'N/A'
                
                # Process each cell in the row
                for col_idx in range(min(3, df.shape[1])):  # Only first 3 columns
                    cell_value = df.iloc[row_idx, col_idx].lower().strip()
                    
                    if not cell_value:
                        continue
                    
                    # Store complete data
                    data_entry = {
                        'id': row_id,
                        'sheet': sheet_name,
                        'row': row_idx,
                        'col': col_idx,
                        'value': cell_value,
                        'mapped': mapped_value,
                        'original_value': df.iloc[row_idx, col_idx]  # Keep original case
                    }
                    self.all_target_data.append(data_entry)
                    
                    # Build exact match index
                    if cell_value not in self.exact_index:
                        self.exact_index[cell_value] = []
                    self.exact_index[cell_value].append((sheet_name, row_idx, mapped_value))
                    
                    # Build length bucket index
                    length = len(cell_value)
                    self.length_buckets[length].append((sheet_name, row_idx, cell_value, mapped_value))
                    
                    # Build n-gram index for fuzzy matching
                    ngrams = self.get_ngrams(cell_value, 3)
                    for ngram in ngrams:
                        self.char_ngram_index[ngram].add(row_id)
                    
                    row_id += 1
        
        print(f"[INDEXING] Built indexes in {time.time() - start_time:.2f} seconds")
        print(f"  - Exact index: {len(self.exact_index)} unique values")
        print(f"  - N-gram index: {len(self.char_ngram_index)} unique 3-grams")
        print(f"  - Length buckets: {len(self.length_buckets)} different lengths")
        print(f"  - Total indexed entries: {len(self.all_target_data)}")
    
    def find_candidates_by_ngrams(self, search_text: str, max_candidates: int = 100) -> List[Dict]:
        """Find candidate matches using n-gram similarity"""
        search_ngrams = self.get_ngrams(search_text.lower().strip(), 3)
        if not search_ngrams:
            return []
        
        # Count how many n-grams each row shares with search text
        candidate_scores = defaultdict(int)
        for ngram in search_ngrams:
            if ngram in self.char_ngram_index:
                for row_id in self.char_ngram_index[ngram]:
                    candidate_scores[row_id] += 1
        
        # Get top candidates by shared n-gram count
        if not candidate_scores:
            return []
        
        # Sort by score and get top candidates
        top_candidates = heapq.nlargest(
            max_candidates, 
            candidate_scores.items(), 
            key=lambda x: x[1]
        )
        
        # Return the actual data for these candidates
        candidates = []
        for row_id, ngram_score in top_candidates:
            if row_id < len(self.all_target_data):
                candidate_data = self.all_target_data[row_id].copy()
                candidate_data['ngram_score'] = ngram_score
                candidates.append(candidate_data)
        
        return candidates
    
    def find_best_fuzzy_match(self, search_text: str, threshold: float = 0.6, 
                            exclude_used: bool = True, max_candidates: int = 50) -> Optional[Tuple]:
        """Find best fuzzy match using intelligent candidate selection"""
        search_text = search_text.lower().strip()
        if not search_text:
            return None
        
        # First try exact match
        if search_text in self.exact_index:
            for sheet, row, mapped in self.exact_index[search_text]:
                if not exclude_used or (sheet, row) not in self.used_rows:
                    return (sheet, row, mapped, 1.0)  # Perfect score
        
        # Get candidates using n-gram index
        candidates = self.find_candidates_by_ngrams(search_text, max_candidates)
        
        if not candidates:
            # Fallback to length-based search
            search_len = len(search_text)
            candidates = []
            for length in range(max(1, search_len - 5), search_len + 6):
                if length in self.length_buckets:
                    for sheet, row, value, mapped in self.length_buckets[length][:20]:
                        if not exclude_used or (sheet, row) not in self.used_rows:
                            candidates.append({
                                'sheet': sheet,
                                'row': row,
                                'value': value,
                                'mapped': mapped
                            })
        
        # Calculate actual similarities for candidates
        best_match = None
        best_score = threshold
        
        for candidate in candidates:
            if exclude_used and (candidate.get('sheet'), candidate.get('row')) in self.used_rows:
                continue
            
            # Calculate similarity
            score = self.calculate_similarity(search_text, candidate.get('value', ''))
            
            if score > best_score:
                best_score = score
                best_match = (
                    candidate.get('sheet'),
                    candidate.get('row'),
                    candidate.get('mapped'),
                    score
                )
        
        return best_match
    
    def find_combined_match(self, col2_text: str, col3_text: str, 
                          exclude_used: bool = True) -> Optional[Tuple]:
        """Find best match using combined Col2+Col3 fuzzy matching"""
        col2_text = col2_text.lower().strip()
        col3_text = col3_text.lower().strip()
        
        if not col2_text or not col3_text:
            return None
        
        # Get candidates for both col2 and col3
        candidates_col2 = self.find_candidates_by_ngrams(col2_text, 30)
        candidates_col3 = self.find_candidates_by_ngrams(col3_text, 30)
        
        # Create a set of (sheet, row) from both candidate lists
        candidate_locations = set()
        for c in candidates_col2:
            candidate_locations.add((c.get('sheet'), c.get('row')))
        for c in candidates_col3:
            candidate_locations.add((c.get('sheet'), c.get('row')))
        
        # Evaluate combined scores
        best_match = None
        best_combined_score = 0
        
        for sheet, row in candidate_locations:
            if exclude_used and (sheet, row) in self.used_rows:
                continue
            
            # Get all values from this row
            row_values = [d for d in self.all_target_data 
                         if d.get('sheet') == sheet and d.get('row') == row]
            
            if not row_values:
                continue
            
            # Calculate best scores for col2 and col3 against this row
            max_col2_score = 0
            max_col3_score = 0
            mapped_value = row_values[0].get('mapped', 'N/A')
            
            for entry in row_values:
                value = entry.get('value', '')
                col2_score = self.calculate_similarity(col2_text, value)
                col3_score = self.calculate_similarity(col3_text, value)
                
                max_col2_score = max(max_col2_score, col2_score)
                max_col3_score = max(max_col3_score, col3_score)
            
            # Check thresholds
            if max_col2_score >= self.threshold_col2 and max_col3_score >= self.threshold_col3:
                combined_score = (max_col2_score * 0.7 + max_col3_score * 0.3)  # Weight col2 more
                
                if combined_score > best_combined_score:
                    best_combined_score = combined_score
                    best_match = (sheet, row, mapped_value, combined_score)
        
        return best_match


def select_file(title, file_type="Excel"):
    """Open a file dialog to select a file"""
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    
    if file_type == "Excel":
        file_types = [("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
    else:
        file_types = [("All files", "*.*")]
    
    file_path = filedialog.askopenfilename(
        title=title,
        filetypes=file_types
    )
    
    root.destroy()
    return file_path


def create_output_filename(base_file_path):
    """Create output filename based on base file name"""
    base_path = Path(base_file_path)
    output_name = f"{base_path.stem}_result{base_path.suffix}"
    output_path = base_path.parent / output_name
    return str(output_path)


def show_completion_message(output_file, total_matches):
    """Show a completion message box"""
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    
    message = f"Processing complete!\n\nOutput file created:\n{output_file}\n\nTotal matches found: {total_matches}"
    messagebox.showinfo("Excel Mapping Complete", message)
    
    root.destroy()


def read_base_file(base_file_path):
    """Read the base Excel file containing at least 4 columns"""
    try:
        df = pd.read_excel(base_file_path, header=None)
        
        if df.shape[1] < 4:
            raise ValueError("Base file must have at least 4 columns")
        
        base_data = df.iloc[:, :4].copy()
        base_data.columns = ['Base_Col1', 'Base_Col2', 'Base_Col3', 'Base_Col4']
        
        print(f"✓ Loaded {len(base_data)} rows from base file")
        print(f"  - Col1 (independent search): {base_data['Base_Col1'].dropna().shape[0]} values")
        print(f"  - Col2 (needs confirmation): {base_data['Base_Col2'].dropna().shape[0]} values")
        print(f"  - Col3 (partial match/wrong filename): {base_data['Base_Col3'].dropna().shape[0]} values")
        print(f"  - Col4 (helper for missing Col2): {base_data['Base_Col4'].dropna().shape[0]} values")
        
        return base_data
    except Exception as e:
        print(f"Error reading base file: {e}")
        messagebox.showerror("Error", f"Error reading base file:\n{e}")
        return None


def search_in_target_file(target_file_path, base_data):
    """Search while preserving exact original row order and column order."""
    try:
        print("\n[INFO] Loading target file...")
        start_time = time.time()
        all_sheets = pd.read_excel(target_file_path, sheet_name=None, header=None)
        print(f"[INFO] Loaded {len(all_sheets)} sheets in {time.time() - start_time:.2f} seconds")

        matcher = FuzzyMatcher(threshold_col2=0.51, threshold_col3=0.11)
        matcher.build_indexes(all_sheets)

        results = []

        # Iterate over base_data in original order
        for idx, row in base_data.iterrows():
            mapped_value = ''
            tab_name = ''
            row_num = ''
            match_type = 'No_Match'

            # Stage 1: Col1 fuzzy match
            if pd.notna(row['Base_Col1']) and str(row['Base_Col1']).strip() != '':
                col1_val = str(row['Base_Col1']).strip()
                match = matcher.find_best_fuzzy_match(col1_val, threshold=0.51, exclude_used=True, max_candidates=50)
                if match:
                    sheet, row_idx, mapped, score = match
                    mapped_value = mapped
                    tab_name = sheet
                    row_num = row_idx + 1
                    match_type = f'Col1_Fuzzy_{score:.2f}'
                    matcher.used_rows.add((sheet, row_idx))

            # Stage 2: Col2 fuzzy match (only if not matched yet)
            if match_type == 'No_Match':
                if pd.isna(row['Base_Col2']) or str(row['Base_Col2']).strip() == '':
                    if pd.isna(row['Base_Col4']) or str(row['Base_Col4']).strip() == '':
                        col2_val = ''
                    else:
                        col2_val = str(row['Base_Col4']).strip()
                else:
                    col2_val = str(row['Base_Col2']).strip()

                if col2_val:
                    candidates = matcher.find_candidates_by_ngrams(col2_val, max_candidates=50)
                    scored_candidates = [(c['sheet'], c['row'], c['mapped'],
                                           matcher.calculate_similarity(col2_val.lower(), c['value']))
                                          for c in candidates
                                          if (c['sheet'], c['row']) not in matcher.used_rows]
                    scored_candidates = [sc for sc in scored_candidates if sc[3] >= 0.71]

                    if len(scored_candidates) == 1:
                        sheet, row_idx, mapped, score = scored_candidates[0]
                        mapped_value = mapped
                        tab_name = sheet
                        row_num = row_idx + 1
                        match_type = f'Col2_Fuzzy_{score:.2f}'
                        matcher.used_rows.add((sheet, row_idx))

            # Stage 3: Combined Col2+Col3 (only if still not matched)
            if match_type == 'No_Match':
                if pd.isna(row['Base_Col2']) or str(row['Base_Col2']).strip() == '':
                    if pd.isna(row['Base_Col4']) or str(row['Base_Col4']).strip() == '':
                        col2_val = ''
                    else:
                        col2_val = str(row['Base_Col4']).strip()
                else:
                    col2_val = str(row['Base_Col2']).strip()

                col3_val = '' if pd.isna(row['Base_Col3']) else str(row['Base_Col3']).strip()

                if col2_val and col3_val:
                    match = matcher.find_combined_match(col2_val, col3_val, exclude_used=True)
                    if match:
                        sheet, row_idx, mapped, score = match
                        mapped_value = mapped
                        tab_name = sheet
                        row_num = row_idx + 1
                        match_type = f'Col2+Col3_Combined_{score:.2f}'
                        matcher.used_rows.add((sheet, row_idx))

            # Append result for this row in same order
            results.append({**row.to_dict(),
                            'Mapped Value': mapped_value,
                            'Tab Name': tab_name,
                            'Row': row_num,
                            'Match Type': match_type})

        return results

    except Exception as e:
        print(f"Error during search: {e}")
        messagebox.showerror("Error", f"Error during search:\n{e}")
        return None


def write_output_file(results, output_file_path):
    """Write results preserving original base columns and order exactly."""
    try:
        if results:
            # Preserve original column order + new columns at the end
            base_columns = list(results[0].keys())
            # Ensure new columns are last in order
            for col in ['Mapped Value', 'Tab Name', 'Row', 'Match Type']:
                if col in base_columns:
                    base_columns.remove(col)
            final_columns = base_columns + ['Mapped Value', 'Tab Name', 'Row', 'Match Type']

            output_df = pd.DataFrame(results)[final_columns]
            output_df.to_excel(output_file_path, index=False)
            print(f"\n✓ Output file created: {output_file_path}")
            successful_matches = len(output_df[output_df['Mapped Value'] != ''])
            return successful_matches
        else:
            pd.DataFrame(columns=['Base_Col1', 'Base_Col2', 'Base_Col3', 'Base_Col4',
                                  'Mapped Value', 'Tab Name', 'Row', 'Match Type']).to_excel(output_file_path, index=False)
            return 0
    except Exception as e:
        print(f"Error writing output file: {e}")
        messagebox.showerror("Error", f"Error writing output file:\n{e}")
        return 0


def main():
    """STEP 1: Main function for Excel mapping with advanced fuzzy logic"""
    print("=" * 60)
    print("STEP 1: Excel Mapping Tool with Advanced Fuzzy Matching")
    print("=" * 60)
    
    # Select base file
    print("\n📁 Please select the BASE Excel file (3 columns)...")
    BASE_FILE = select_file("Select BASE Excel File (3 columns)")
    
    if not BASE_FILE:
        print("❌ No base file selected. Exiting.")
        return
    
    print(f"✓ Base file selected: {os.path.basename(BASE_FILE)}")
    
    # Select target file
    print("\n📁 Please select the TARGET Excel file (multi-tab file to search in)...")
    TARGET_FILE = select_file("Select TARGET Excel File (multi-tab file to search)")
    
    if not TARGET_FILE:
        print("❌ No target file selected. Exiting.")
        return
    
    print(f"✓ Target file selected: {os.path.basename(TARGET_FILE)}")
    
    # Create output filename
    OUTPUT_FILE = create_output_filename(BASE_FILE)
    print(f"\n📝 Output will be saved as: {os.path.basename(OUTPUT_FILE)}")
    
    print("\n" + "-" * 60)
    print("Starting processing...")
    print("-" * 60)
    
    # Read base file
    base_data = read_base_file(BASE_FILE)
    if base_data is None:
        return
    
    # Search in target file
    results = search_in_target_file(TARGET_FILE, base_data)
    if results is None:
        return
    
    # Write output file
    total_matches = write_output_file(results, OUTPUT_FILE)
    
    print("\n" + "=" * 60)
    print("✓ Processing complete!")
    print("=" * 60)
    
    # Show completion message
    show_completion_message(OUTPUT_FILE, total_matches)
    
    # Ask if user wants to open the output file
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    
    if messagebox.askyesno("Open File?", "Would you like to open the output file now?"):
        try:
            os.startfile(OUTPUT_FILE)  # Windows
        except:
            try:
                os.system(f'open "{OUTPUT_FILE}"')  # macOS
            except:
                os.system(f'xdg-open "{OUTPUT_FILE}"')  # Linux
    
    root.destroy()


# STEP 2 FUNCTIONS
def select_folder(title):
    """Open a folder dialog to select a folder"""
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    
    folder_path = filedialog.askdirectory(title=title)
    
    root.destroy()
    return folder_path


def search_files_in_folder(target_folder, search_values):
    """Search for files in target folder that match the search values"""
    matches = []
    search_values_lower = [str(val).lower().strip() for val in search_values if pd.notna(val)]
    
    print(f"\n🔍 Searching for {len(search_values_lower)} unique values in folder...")
    
    found_values = set()
    
    for root, dirs, files in os.walk(target_folder):
        for file in files:
            file_lower = file.lower()
            file_name_without_ext = os.path.splitext(file)[0].lower()
            
            for search_value in search_values_lower:
                if (search_value == file_lower or 
                    search_value == file_name_without_ext or
                    file_name_without_ext.startswith(search_value) or
                    search_value in file_name_without_ext):
                    
                    if search_value not in found_values:
                        full_path = os.path.join(root, file)
                        matches.append({
                            'search_value': search_value,
                            'file_name': file,
                            'full_path': full_path,
                            'relative_path': os.path.relpath(full_path, target_folder)
                        })
                        found_values.add(search_value)
                        print(f"  ✓ Found match: {file} for '{search_value}'")
                        break
    
    not_found = set(search_values_lower) - found_values
    if not_found:
        print(f"\n⚠ {len(not_found)} values were not found as files:")
        for value in list(not_found)[:10]:
            print(f"  - {value}")
        if len(not_found) > 10:
            print(f"  ... and {len(not_found) - 10} more")
    
    return matches


def copy_files_and_update_excel(excel_file_path, matches, output_folder):
    """Copy matched files to output folder and update Excel with hyperlinks"""
    output_folder_path = Path(excel_file_path).parent / output_folder
    output_folder_path.mkdir(exist_ok=True)
    
    print(f"\n📁 Creating/using output folder: {output_folder_path}")
    
    df = pd.read_excel(excel_file_path)
    df['Audio Link'] = ''
    
    match_dict = {}
    for match in matches:
        match_dict[match['search_value']] = match
    
    copied_count = 0
    for idx, row in df.iterrows():
        search_value = str(row['Base_Col3']).lower().strip() if pd.notna(row['Base_Col3']) else ''
        
        if search_value in match_dict:
            match = match_dict[search_value]
            
            source_file = Path(match['full_path'])
            dest_file = output_folder_path / match['file_name']
            
            try:
                shutil.copy2(source_file, dest_file)
                copied_count += 1
                
                relative_link = f"./{output_folder}/{match['file_name']}"
                df.at[idx, 'Audio Link'] = relative_link
                
                print(f"  📋 Copied: {match['file_name']}")
            except Exception as e:
                print(f"  ⚠ Error copying {match['file_name']}: {e}")
    
    output_file = Path(excel_file_path).parent / f"{Path(excel_file_path).stem}_with_audio.xlsx"
    
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
        
        workbook = writer.book
        worksheet = writer.sheets['Sheet1']
        
        audio_link_col = len(df.columns)
        
        for row_idx, row in df.iterrows():
            if pd.notna(row['Audio Link']) and row['Audio Link'] != '':
                cell = worksheet.cell(row=row_idx + 2, column=audio_link_col)
                
                abs_path = os.path.abspath(os.path.join(Path(output_file).parent, row['Audio Link']))
                
                cell.value = row['Audio Link']
                cell.hyperlink = abs_path
                cell.font = Font(color="0000FF", underline="single")
                cell.alignment = Alignment(horizontal='left')
    
    print(f"\n✓ Updated Excel saved as: {output_file}")
    print(f"✓ Copied {copied_count} audio files to {output_folder}")
    
    return output_file, copied_count


def second_step_process():
    """STEP 2: Audio File Mapping Process"""
    print("\n" + "=" * 60)
    print("STEP 2: Audio File Mapping Process")
    print("=" * 60)
    
    print("\n📁 Please select the OUTPUT Excel file from Step 1...")
    excel_file = select_file("Select Output Excel File from Step 1", "Excel")
    
    if not excel_file:
        print("❌ No Excel file selected. Exiting.")
        return
    
    print(f"✓ Excel file selected: {os.path.basename(excel_file)}")
    
    print("\n📁 Please select the TARGET FOLDER to search for audio files...")
    target_folder = select_folder("Select Target Folder with Audio Files")
    
    if not target_folder:
        print("❌ No folder selected. Exiting.")
        return
    
    print(f"✓ Target folder selected: {target_folder}")
    
    try:
        df = pd.read_excel(excel_file)
        
        if 'Base_Col3' not in df.columns:
            messagebox.showerror("Error", "The selected Excel file doesn't have a 'Base_Col3' column!")
            return
        
        search_values = df['Base_Col3'].dropna().unique().tolist()
        print(f"\n✓ Found {len(search_values)} unique wrong filenames to search for")
        
        matches = search_files_in_folder(target_folder, search_values)
        
        if not matches:
            messagebox.showwarning("No Matches", "No matching audio files were found in the selected folder.")
            return
        
        print(f"\n✓ Found {len(matches)} matching files")
        
        output_file, copied_count = copy_files_and_update_excel(excel_file, matches, "mapped_audio")
        
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        
        message = f"Step 2 Processing complete!\n\n"
        message += f"Files copied: {copied_count}\n"
        message += f"Output folder: mapped_audio\n"
        message += f"Updated Excel: {os.path.basename(output_file)}"
        
        messagebox.showinfo("Audio Mapping Complete", message)
        
        if messagebox.askyesno("Open File?", "Would you like to open the updated Excel file?"):
            try:
                os.startfile(output_file)
            except:
                try:
                    os.system(f'open "{output_file}"')
                except:
                    os.system(f'xdg-open "{output_file}"')
        
        root.destroy()
        
    except Exception as e:
        print(f"❌ Error during processing: {e}")
        messagebox.showerror("Error", f"An error occurred:\n{e}")


# STEP 3 FUNCTIONS
def search_files_and_rename(target_folder, df):
    """Search for files using Base_Col3 and prepare rename mapping"""
    matches = []
    
    valid_rows = df[(df['Base_Col3'].notna()) & (df['Mapped Value'].notna()) & (df['Mapped Value'] != '')]
    
    print(f"\n🔍 Searching for {len(valid_rows)} files to rename...")
    
    rename_map = {}
    for idx, row in valid_rows.iterrows():
        wrong_name = str(row['Base_Col3']).lower().strip()
        correct_name = str(row['Mapped Value']).strip()
        rename_map[wrong_name] = correct_name
    
    found_values = set()
    
    for root, dirs, files in os.walk(target_folder):
        for file in files:
            file_lower = file.lower()
            file_name_without_ext = os.path.splitext(file)[0].lower()
            file_ext = os.path.splitext(file)[1]
            
            for wrong_name, correct_name in rename_map.items():
                if (wrong_name == file_lower or 
                    wrong_name == file_name_without_ext or
                    file_name_without_ext.startswith(wrong_name) or
                    wrong_name in file_name_without_ext):
                    
                    if wrong_name not in found_values:
                        full_path = os.path.join(root, file)
                        if '.' in correct_name:
                            new_name = correct_name
                        else:
                            new_name = correct_name + file_ext
                        
                        matches.append({
                            'wrong_name': wrong_name,
                            'file_name': file,
                            'full_path': full_path,
                            'new_name': new_name,
                            'correct_name_base': correct_name
                        })
                        found_values.add(wrong_name)
                        print(f"  ✓ Found: {file} → will rename to: {new_name}")
                        break
    
    not_found = set(rename_map.keys()) - found_values
    if not_found:
        print(f"\n⚠ {len(not_found)} files were not found:")
        for value in list(not_found)[:10]:
            print(f"  - {value} (should become: {rename_map[value]})")
        if len(not_found) > 10:
            print(f"  ... and {len(not_found) - 10} more")
    
    return matches


def copy_and_rename_files(excel_file_path, matches, output_folder):
    """Copy matched files to output folder with renamed filenames"""
    output_folder_path = Path(excel_file_path).parent / output_folder
    output_folder_path.mkdir(exist_ok=True)
    
    print(f"\n📁 Creating/using output folder: {output_folder_path}")
    
    seen_names = {}
    copied_count = 0
    skipped_duplicates = []
    
    for match in matches:
        source_file = Path(match['full_path'])
        new_name = match['new_name']
        
        if new_name.lower() in seen_names:
            skipped_duplicates.append(f"{match['file_name']} → {new_name} (duplicate)")
            print(f"  ⚠ Skipping duplicate: {match['file_name']} → {new_name}")
            continue
        
        dest_file = output_folder_path / new_name
        
        try:
            shutil.copy2(source_file, dest_file)
            copied_count += 1
            seen_names[new_name.lower()] = match['file_name']
            print(f"  📋 Copied and renamed: {match['file_name']} → {new_name}")
        except Exception as e:
            print(f"  ⚠ Error copying {match['file_name']}: {e}")
    
    if skipped_duplicates:
        print(f"\n⚠ Skipped {len(skipped_duplicates)} duplicate target names:")
        for dup in skipped_duplicates[:5]:
            print(f"  - {dup}")
        if len(skipped_duplicates) > 5:
            print(f"  ... and {len(skipped_duplicates) - 5} more")
    
    print(f"\n✓ Copied and renamed {copied_count} audio files to {output_folder}")
    
    return copied_count


def third_step_process():
    """STEP 3: Audio File Extraction and Renaming Process"""
    print("\n" + "=" * 60)
    print("STEP 3: Audio File Extraction and Renaming Process")
    print("=" * 60)
    
    print("\n📁 Please select the Excel file with mapping (from Step 1 or 2)...")
    excel_file = select_file("Select Excel File with Mapping", "Excel")
    
    if not excel_file:
        print("❌ No Excel file selected. Exiting.")
        return
    
    print(f"✓ Excel file selected: {os.path.basename(excel_file)}")
    
    try:
        df = pd.read_excel(excel_file)
        
        required_columns = ['Base_Col3', 'Mapped Value']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            messagebox.showerror("Error", f"The selected Excel file is missing required columns: {', '.join(missing_columns)}")
            return
        
        mapped_values = df['Mapped Value'].dropna()
        mapped_values = mapped_values[mapped_values != '']
        
        base_names = mapped_values.apply(lambda x: os.path.splitext(str(x))[0].lower())
        duplicates = base_names[base_names.duplicated()].unique()
        
        if len(duplicates) > 0:
            warning_msg = "Warning: Duplicate target filenames found:\n\n"
            for i, dup in enumerate(duplicates[:10]):
                warning_msg += f"• {dup}\n"
            if len(duplicates) > 10:
                warning_msg += f"... and {len(duplicates) - 10} more\n"
            warning_msg += "\nDuplicate files will be skipped. Continue anyway?"
            
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            
            if not messagebox.askyesno("Duplicate Names Warning", warning_msg):
                root.destroy()
                return
            
            root.destroy()
            
            print(f"⚠ Warning: Found {len(duplicates)} duplicate target names")
        
        print(f"✓ Found {len(mapped_values)} files to rename")
        
        print("\n📁 Please select the TARGET FOLDER to search for audio files...")
        target_folder = select_folder("Select Target Folder with Audio Files")
        
        if not target_folder:
            print("❌ No folder selected. Exiting.")
            return
        
        print(f"✓ Target folder selected: {target_folder}")
        
        matches = search_files_and_rename(target_folder, df)
        
        if not matches:
            messagebox.showwarning("No Matches", "No matching audio files were found in the selected folder.")
            return
        
        print(f"\n✓ Found {len(matches)} matching files to copy and rename")
        
        copied_count = copy_and_rename_files(excel_file, matches, "renamed_audio")
        
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        
        message = f"Step 3 Processing complete!\n\n"
        message += f"Files copied and renamed: {copied_count}\n"
        message += f"Output folder: renamed_audio\n\n"
        message += f"Files have been renamed from Base_Col3 (wrong) to Mapped Value (correct)."
        
        messagebox.showinfo("Audio Renaming Complete", message)
        
        if messagebox.askyesno("Open Folder?", "Would you like to open the output folder?"):
            output_folder_path = Path(excel_file).parent / "renamed_audio"
            try:
                os.startfile(output_folder_path)
            except:
                try:
                    os.system(f'open "{output_folder_path}"')
                except:
                    os.system(f'xdg-open "{output_folder_path}"')
        
        root.destroy()
        
    except Exception as e:
        print(f"❌ Error during processing: {e}")
        messagebox.showerror("Error", f"An error occurred:\n{e}")


def gui_main():
    """Enhanced main function with three-step process GUI"""
    root = tk.Tk()
    root.title("Excel Mapping Tool - Three Step Process")
    root.geometry("700x850")
    root.resizable(False, False)
    
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (700 // 2)
    y = (root.winfo_screenheight() // 2) - (850 // 2)
    root.geometry(f'+{x}+{y}')
    
    bg_color = "#f0f0f0"
    root.configure(bg=bg_color)
    
    title_label = tk.Label(
        root, 
        text="Excel Mapping Tool - Three Step Process", 
        font=("Arial", 16, "bold"),
        bg=bg_color
    )
    title_label.pack(pady=20)
    
    info_text = """ADVANCED MATCHING SYSTEM:
- Smart N-gram indexing for fast fuzzy matching
- Dictionary-based candidate selection
- Best match selection from top candidates
- No multiprocessing = More stable!"""
    
    info_label = tk.Label(
        root,
        text=info_text,
        font=("Arial", 10, "italic"),
        bg=bg_color,
        fg="#666666",
        justify="left"
    )
    info_label.pack(pady=10, padx=20)
    
    # Step 1 Frame
    step1_frame = tk.LabelFrame(
        root,
        text="STEP 1: Text Mapping with Smart Indexing",
        font=("Arial", 12, "bold"),
        bg=bg_color,
        padx=20,
        pady=15
    )
    step1_frame.pack(pady=10, padx=20, fill="x")
    
    step1_desc = tk.Label(
        step1_frame,
        text="Advanced fuzzy matching with n-gram indexing\nNo multiprocessing = More reliable!",
        font=("Arial", 10),
        bg=bg_color,
        justify="center"
    )
    step1_desc.pack(pady=5)
    
    def start_step1():
        root.destroy()
        main()
    
    step1_button = tk.Button(
        step1_frame,
        text="Start Step 1 Process",
        command=start_step1,
        font=("Arial", 11),
        bg="#4CAF50",
        fg="white",
        padx=20,
        pady=8,
        cursor="hand2"
    )
    step1_button.pack(pady=10)
    
    # Separator 1
    separator1 = tk.Frame(root, height=2, bg="#cccccc")
    separator1.pack(fill="x", padx=20, pady=10)
    
    # Step 2 Frame
    step2_frame = tk.LabelFrame(
        root,
        text="STEP 2: Audio File Mapping",
        font=("Arial", 12, "bold"),
        bg=bg_color,
        padx=20,
        pady=15
    )
    step2_frame.pack(pady=10, padx=20, fill="x")
    
    step2_desc = tk.Label(
        step2_frame,
        text="Use Base_Col3 (wrong filenames) to find audio files,\ncopy them, and add hyperlinks to Excel.",
        font=("Arial", 10),
        bg=bg_color,
        justify="center"
    )
    step2_desc.pack(pady=5)
    
    def start_step2():
        root.destroy()
        second_step_process()
    
    step2_button = tk.Button(
        step2_frame,
        text="Start Step 2 Process",
        command=start_step2,
        font=("Arial", 11),
        bg="#2196F3",
        fg="white",
        padx=20,
        pady=8,
        cursor="hand2"
    )
    step2_button.pack(pady=10)
    
    # Separator 2
    separator2 = tk.Frame(root, height=2, bg="#cccccc")
    separator2.pack(fill="x", padx=20, pady=10)
    
    # Step 3 Frame
    step3_frame = tk.LabelFrame(
        root,
        text="STEP 3: Audio File Renaming",
        font=("Arial", 12, "bold"),
        bg=bg_color,
        padx=20,
        pady=15
    )
    step3_frame.pack(pady=10, padx=20, fill="x")
    
    step3_desc = tk.Label(
        step3_frame,
        text="Find files using Base_Col3 (wrong names) and\nrename them to Mapped Value (correct names).",
        font=("Arial", 10),
        bg=bg_color,
        justify="center"
    )
    step3_desc.pack(pady=5)
    
    def start_step3():
        root.destroy()
        third_step_process()
    
    step3_button = tk.Button(
        step3_frame,
        text="Start Step 3 Process",
        command=start_step3,
        font=("Arial", 11),
        bg="#FF9800",
        fg="white",
        padx=20,
        pady=8,
        cursor="hand2"
    )
    step3_button.pack(pady=10)
    
    inst_label = tk.Label(
        root,
        text="Complete each step in order: Step 1 → Step 2 → Step 3\n\nStep 1: Map Excel data\nStep 2: Find and copy audio files\nStep 3: Rename to correct filenames",
        font=("Arial", 9, "italic"),
        bg=bg_color,
        fg="#666666",
        justify="center"
    )
    inst_label.pack(pady=15)
    
    root.mainloop()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        print("Command line mode not supported with new matching logic.")
        print("Please run without arguments to use GUI mode.")
    else:
        gui_main()