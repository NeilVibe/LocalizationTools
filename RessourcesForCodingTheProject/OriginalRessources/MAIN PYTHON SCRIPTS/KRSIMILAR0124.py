print("- KR Similar - ver. 0124 (By Neil)")
print("- KR Similar - ver. 0124 (By Neil)")
print("- KR Similar - ver. 0124 (By Neil)")
import os
import sys
import pandas as pd
import numpy as np
print("Loading... Please wait...")
from sentence_transformers import SentenceTransformer
import pickle
import re
print("Loading... Please wait a little bit more...")
import faiss
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import torch
from concurrent.futures import ThreadPoolExecutor
import threading
print("All done !")

try:
    import pyi_splash
    splash_active = True
except ImportError:
    splash_active = False

def on_closing():
    root.destroy()
    sys.exit()

# Initialize the SentenceTransformer model
model = SentenceTransformer('snunlp/KR-SBERT-V40K-klueNLI-augSTS')

def normalize_text(text):
    if pd.isna(text) or not isinstance(text, str):
        return ''
    # Remove newlines unless they are right before a code block or triangle
    # Replace \n not followed by { or ▶ with space
    text = re.sub(r'\\n(?![\{▶])', ' ', text)
    # Proceed with other normalizations
    text = re.sub(r'▶', '', text)  # Remove triangles
    text = re.sub(r'<Scale[^>]*>|</Scale>', '', text)
    text = re.sub(r'<color[^>]*>|</color>', '', text)
    text = re.sub(r'<PAColor[^>]*>|<PAOldColor>', '', text)
    text = re.sub(r'\{[^}]*\}', '', text)  # Remove content in curly braces (code markers)
    text = re.sub(r'<Style:[^>]*>', '', text) # To handle Style tags
    # Remove any extra spaces
    text = re.sub(r'\s+', ' ', text)
    return text.strip()



def process_embeddings_thread():
    threading.Thread(target=process_embeddings).start()

def process_embeddings():
    def select_dict_type():
        dict_type = None
        def on_select(type):
            nonlocal dict_type
            dict_type = type
            type_window.destroy()

        type_window = tk.Toplevel(root)
        type_window.title("Select Dictionary Type")
        type_window.geometry("300x150")
        type_window.resizable(False, False)

        # Calculate position
        root.update_idletasks()  # Ensure root's size is updated
        x = root.winfo_x() + (root.winfo_width() // 2) - (300 // 2)
        y = root.winfo_y() + (root.winfo_height() // 2) - (150 // 2)
        type_window.geometry(f"+{x}+{y}")

        tk.Button(type_window, text="BDO", command=lambda: on_select("BDO")).pack(pady=10)
        tk.Button(type_window, text="BDM", command=lambda: on_select("BDM")).pack(pady=10)

        type_window.transient(root)  # Set to be on top of the main window
        type_window.grab_set()  # Modal
        root.wait_window(type_window)
        return dict_type

    dict_type = select_dict_type()
    if not dict_type:
        print("No dictionary type selected.")
        return

    reference_file = filedialog.askopenfilename(title=f"Choose {dict_type} Language Data File")
    if not reference_file:
        print("No file selected.")
        return

    # Create directory for the selected dictionary type if it doesn't exist
    os.makedirs(dict_type, exist_ok=True)

    print(f"Starting the embeddings generation/update process for {dict_type}...")
    reference_data = pd.read_csv(reference_file, delimiter="\t", header=None, usecols=[5, 6])
    reference_data.columns = ['Korean', 'French']
    total_rows = len(reference_data)

    # Normalize the data
    print("Normalizing Korean and Translation text...")
    tokenized_count = 0

    def update_and_normalize(row):
        nonlocal tokenized_count
        tokenized_count += 1
        if tokenized_count % 1000 == 0:
            print(f"Normalized {tokenized_count}/{total_rows} rows")
        return pd.Series({
            'Korean': normalize_text(row['Korean']) if pd.notna(row['Korean']) else '',
            'French': normalize_text(row['French']) if pd.notna(row['French']) else ''
        })

    with ThreadPoolExecutor() as executor:
        reference_data[['Korean', 'French']] = reference_data.apply(update_and_normalize, axis=1)

    print("Normalization completed.")

    # Process Split Embeddings
    process_embeddings_type('split', reference_data, dict_type)

    # Process Whole Embeddings
    process_embeddings_type('whole', reference_data, dict_type)

def process_embeddings_type(embedding_type, reference_data, dict_type):
    print(f"Processing {embedding_type.capitalize()} Embeddings for {dict_type}...")
    
    if embedding_type == 'split':
        data = process_split_data(reference_data)
    else:
        data = reference_data.copy()
    
    # Group by Korean text and select the most frequent French translation
    data = data.groupby('Korean')['French'].agg(lambda x: x.value_counts().index[0]).reset_index()
    
    total_texts = len(data)
    print(f"Total unique {embedding_type} pairs after grouping: {total_texts}")

    embeddings_file = os.path.join(dict_type, f'{embedding_type}_embeddings.npy')
    dict_file = os.path.join(dict_type, f'{embedding_type}_translation_dict.pkl')

    # Check if existing embeddings and dictionary exist
    if os.path.exists(embeddings_file) and os.path.exists(dict_file):
        print(f"Existing {embedding_type} embeddings and dictionary found for {dict_type}. Updating...")
        existing_embeddings = np.load(embeddings_file)
        with open(dict_file, 'rb') as file:
            existing_dict = pickle.load(file)

        # Identify new or changed strings
        existing_data = pd.DataFrame(list(existing_dict.items()), columns=['Korean', 'French'])
        merged_data = pd.merge(data, existing_data, on='Korean', how='outer', suffixes=('_new', '_old'))
        new_or_changed = merged_data[merged_data['French_new'] != merged_data['French_old']].dropna(subset=['French_new'])

        print(f"Identified {len(new_or_changed)} new or changed strings.")

        # Update embeddings and dictionary
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model.to(device)

        total_updates = len(new_or_changed)
        for update_count, (_, row) in enumerate(new_or_changed.iterrows(), 1):
            korean, french = row['Korean'], row['French_new']
            embedding = model.encode([korean], device=device)[0]

            if korean in existing_dict:
                existing_index = list(existing_dict.keys()).index(korean)
                existing_embeddings[existing_index] = embedding
            else:
                existing_embeddings = np.vstack([existing_embeddings, embedding])

            existing_dict[korean] = french

            print(f"Updated {update_count}/{total_updates} entries")

        embeddings = existing_embeddings
        translation_dict = existing_dict

    else:
        print(f"No existing {embedding_type} embeddings found for {dict_type}. Creating new...")
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model.to(device)

        embeddings = []
        batch_size = 1000
        for i in range(0, total_texts, batch_size):
            batch_texts = data['Korean'].iloc[i:i+batch_size].tolist()
            batch_embeddings = model.encode(batch_texts, device=device)
            embeddings.extend(batch_embeddings)
            print(f"Processed {i + len(batch_embeddings)}/{total_texts} {embedding_type} texts")

        embeddings = np.array(embeddings)
        translation_dict = dict(zip(data['Korean'], data['French']))

    # Save updated embeddings and dictionary
    np.save(embeddings_file, embeddings)
    with open(dict_file, 'wb') as file:
        pickle.dump(translation_dict, file)

    print(f"{embedding_type.capitalize()} Embedding processing completed for {dict_type}.")
    print(f"Number of {embedding_type} embeddings: {embeddings.shape[0]}")

def process_split_data(reference_data):
    split_data = []
    for idx, row in reference_data.iterrows():
        kr_lines = row['Korean'].split('\\n')
        fr_lines = row['French'].split('\\n')
        if len(kr_lines) == len(fr_lines):
            for kr_line, fr_line in zip(kr_lines, fr_lines):
                if kr_line.strip() != '':
                    split_data.append({'Korean': kr_line.strip(), 'French': fr_line.strip()})
        if (idx + 1) % 1000 == 0:
            print(f"Processed {idx + 1}/{len(reference_data)} rows for split embeddings")

    return pd.DataFrame(split_data)


def kr_similar_extraction_thread():
    threading.Thread(target=kr_similar_extraction).start()

def kr_similar_extraction():
    input_file = filedialog.askopenfilename(title="Select Translation File to Analyze")
    if not input_file:
        print("No input file selected.")
        return

    # Generate output file name based on input file
    input_filename = os.path.splitext(os.path.basename(input_file))[0]
    output_file = f"{input_filename}_similarstrings.txt"
    output_path = os.path.join(os.path.dirname(input_file), output_file)

    filter_same_category = filter_var.get()
    min_char_length = int(min_char_entry.get())
    similarity_threshold = float(similarity_threshold_entry.get())

    print("Loading model...")
    model = SentenceTransformer('snunlp/KR-SBERT-V40K-klueNLI-augSTS')

    print(f"Processing input file: {input_file}")
    data = pd.read_csv(input_file, delimiter="\t", header=None, usecols=range(9))
    total_sentences = len(data)
    print(f"Total sentences before filtering: {total_sentences}")

    data['normalized_text'] = data.iloc[:, 5].apply(normalize_text)
    data = data[data['normalized_text'].str.len() >= min_char_length].reset_index(drop=True)
    filtered_sentences = len(data)
    print(f"\nSentences after length filtering: {filtered_sentences}")

    print("Generating embeddings...")
    embeddings = model.encode(data['normalized_text'].tolist(), show_progress_bar=True)

    print("Preparing FAISS index...")
    faiss.normalize_L2(embeddings)
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)
    print("FAISS index prepared.")

    def custom_search(index, query_vector, k, skip_id):
        distances, indices = index.search(query_vector, k+1)
        mask = indices[0] != skip_id
        return distances[0][mask][:k], indices[0][mask][:k]

    similar_groups = []
    processed_count = 0

    for idx, row in data.iterrows():
        normalized_text = row['normalized_text']
        embedding = embeddings[idx].reshape(1, -1)

        k = 10
        distances, indices = custom_search(index, embedding, k, idx)
        
        for dist, ind in zip(distances, indices):
            if similarity_threshold <= dist < 1.0:
                similar_text = data.iloc[ind]['normalized_text']
                if similar_text != normalized_text:
                    group = sorted([normalized_text, similar_text])
                    if group not in similar_groups:
                        similar_groups.append(group)
                    break
            elif dist >= 1.0:
                continue
            else:
                break

        processed_count += 1
        if processed_count % 10 == 0:
            print(f"Processed {processed_count}/{filtered_sentences} rows")

    print(f"\nTotal groups found before deduplication: {len(similar_groups)}")

    # Deduplication
    unique_groups = []
    for group in similar_groups:
        if group not in unique_groups:
            unique_groups.append(group)

    print(f"Groups after deduplication: {len(unique_groups)}")

    # Category filtering
    if filter_same_category:
        original_group_count = len(unique_groups)
        filtered_groups = []
        for group in unique_groups:
            rows = []
            for text in group:
                matching_rows = data[data['normalized_text'] == text]
                if not matching_rows.empty:
                    rows.append(matching_rows.iloc[0])
            if len(rows) == 2 and rows[0][0] != rows[1][0]:  # Compare categories (first column)
                filtered_groups.append(group)
        unique_groups = filtered_groups
        print(f"Groups after filtering same categories: {len(unique_groups)} (Removed {original_group_count - len(unique_groups)} groups)")

    print(f"\nWriting output file: {output_path}")
    output_rows = []
    for group in unique_groups:
        for text in group:
            matching_rows = data[data['normalized_text'] == text]
            if not matching_rows.empty:
                row = matching_rows.iloc[0]
                output_rows.append('\t'.join(str(x) if pd.notna(x) else '' for x in row.iloc[:9]))

    # Final deduplication based on the first 5 columns
    seen_keys = set()
    deduplicated_rows = []
    for row in output_rows:
        fields = row.split('\t')
        key = '\t'.join(fields[:5])  # Use the first 5 fields as the key
        if key not in seen_keys:
            seen_keys.add(key)
            deduplicated_rows.append(row)

    print(f"Rows after final deduplication: {len(deduplicated_rows)} (Removed {len(output_rows) - len(deduplicated_rows)} duplicate rows)")

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        for row in deduplicated_rows:
            f.write(row + '\n')

    print("Similar string extraction completed.")
    messagebox.showinfo("Extraction Completed", f"Similar string extraction completed successfully!\nExtracted {len(deduplicated_rows)} unique rows.\nSaved to: {output_path}")






def adapt_structure(kr_text, fr_text):
    kr_lines = kr_text.split('\\n')
    total_lines = len(kr_lines)
    non_empty_lines = sum(1 for line in kr_lines if line.strip())
    
    if not fr_text.strip():
        return '\\n'.join([''] * total_lines)
    
    ideal_length = len(fr_text) / non_empty_lines
    threshold = int(ideal_length * 1.5)  # 50% over ideal length
    
    end_punct_pattern = r'[.!?]|\.\.\.'
    all_punct_pattern = r'[.!?,;:]|\.\.\.'
    
    adapted_lines = []
    start = 0
    
    for line in kr_lines:
        if line.strip():
            if start >= len(fr_text):
                adapted_lines.append('')
                continue
            
            # Find all phrase-ending punctuations within the threshold
            matches = list(re.finditer(end_punct_pattern, fr_text[start:start + threshold]))
            
            if matches:
                # Find the punctuation closest to the ideal length
                closest_match = min(matches, key=lambda m: abs(m.end() - ideal_length))
                end = start + closest_match.end()
            else:
                # If no phrase-ending punctuation, fall back to any punctuation
                matches = list(re.finditer(all_punct_pattern, fr_text[start:start + threshold]))
                if matches:
                    closest_match = min(matches, key=lambda m: abs(m.end() - ideal_length))
                    end = start + closest_match.end()
                else:
                    # If no punctuation, break at the closest word to ideal length
                    last_space = fr_text.rfind(' ', start + int(ideal_length) - 10, start + int(ideal_length) + 10)
                    if last_space != -1:
                        end = last_space + 1
                    else:
                        end = start + int(ideal_length)
            
            # Ensure we're not breaking in the middle of an ellipsis
            if fr_text[end-3:end] == '...':
                end += 1  # include the space after the ellipsis
            
            adapted_lines.append(fr_text[start:end].strip())
            start = end
        else:
            adapted_lines.append('')
    
    # Add any remaining text to the last non-empty line
    if start < len(fr_text):
        for i in range(len(adapted_lines) - 1, -1, -1):
            if adapted_lines[i]:
                adapted_lines[i] += ' ' + fr_text[start:].strip()
                break
    
    return '\\n'.join(adapted_lines)


def replace_similar_content_thread():
    threading.Thread(target=replace_similar_content).start()

def replace_similar_content():
    def select_dict_type():
        dict_type = None
        def on_select(type):
            nonlocal dict_type
            dict_type = type
            type_window.destroy()

        type_window = tk.Toplevel(root)
        type_window.title("Select Dictionary Type")
        type_window.geometry("300x150")
        type_window.resizable(False, False)

        # Calculate position to center within main window
        root.update_idletasks()
        x = root.winfo_x() + (root.winfo_width() // 2) - (150)
        y = root.winfo_y() + (root.winfo_height() // 2) - (75)
        type_window.geometry(f"+{x}+{y}")

        tk.Button(type_window, text="BDO", command=lambda: on_select("BDO")).pack(pady=10)
        tk.Button(type_window, text="BDM", command=lambda: on_select("BDM")).pack(pady=10)

        type_window.transient(root)
        type_window.grab_set()
        root.wait_window(type_window)
        return dict_type

    dict_type = select_dict_type()
    if not dict_type:
        print("No dictionary type selected.")
        return

    input_file = filedialog.askopenfilename(title=f"Choose Input File to Replace Content ({dict_type})")
    if not input_file:
        print("No input file selected.")
        return

    input_filename = os.path.splitext(os.path.basename(input_file))[0]
    output_file = f"{input_filename}_translated.txt"
    output_path = os.path.join(os.path.dirname(input_file), output_file)

    similarity_threshold = float(replace_similarity_threshold_entry.get())

    print(f"Checking embeddings and translation dictionaries for {dict_type}...")
    
    split_embeddings_path = os.path.join(dict_type, 'split_embeddings.npy')
    split_dict_path = os.path.join(dict_type, 'split_translation_dict.pkl')
    whole_embeddings_path = os.path.join(dict_type, 'whole_embeddings.npy')
    whole_dict_path = os.path.join(dict_type, 'whole_translation_dict.pkl')

    if not all(os.path.exists(f) for f in [split_embeddings_path, split_dict_path, whole_embeddings_path, whole_dict_path]):
        message = f"No embeddings available for {dict_type}.\nPlease create dictionary for {dict_type} first."
        messagebox.showwarning("Embeddings Not Found", message)
        return

    try:
        split_embeddings = np.load(split_embeddings_path)
        with open(split_dict_path, 'rb') as file:
            split_translation_dict = pickle.load(file)
        
        whole_embeddings = np.load(whole_embeddings_path)
        with open(whole_dict_path, 'rb') as file:
            whole_translation_dict = pickle.load(file)
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred while loading files for {dict_type}: {str(e)}")
        return

    print(f"Loaded {len(split_embeddings)} split embeddings and {len(split_translation_dict)} split translations")
    print(f"Loaded {len(whole_embeddings)} whole embeddings and {len(whole_translation_dict)} whole translations")

    print("Preparing FAISS indexes...")
    faiss.normalize_L2(split_embeddings)
    split_index = faiss.IndexFlatIP(split_embeddings.shape[1])
    split_index.add(split_embeddings)
    faiss.normalize_L2(whole_embeddings)
    whole_index = faiss.IndexFlatIP(whole_embeddings.shape[1])
    whole_index.add(whole_embeddings)
    print("FAISS indexes prepared.")

    print(f"Processing input file: {input_file}")
    data = pd.read_csv(input_file, delimiter="\t", header=None, usecols=range(9))
    total_rows = len(data)
    print(f"Total rows: {total_rows}")

    replaced_count = 0
    changed_rows = []

    for idx, row in data.iterrows():
        original_text = row[5]
        normalized_text = normalize_text(original_text)
        original_lines = original_text.split('\\n')
        normalized_lines = normalized_text.split('\\n')

        # First attempt: Direct line-by-line matching (0930 style)
        if '▶' in original_text:
            translated_lines = []
            line_changed = False
            for line in normalized_lines:
                if not line.strip():
                    translated_lines.append('')
                    continue

                embedding = model.encode([line])
                faiss.normalize_L2(embedding)
                distances, indices = split_index.search(embedding, 1)
                best_match_index = indices[0][0]
                distance_score = distances[0][0]

                if distance_score >= similarity_threshold:
                    best_match_korean = list(split_translation_dict.keys())[best_match_index]
                    best_match_translation = split_translation_dict[best_match_korean]
                    translated_lines.append(best_match_translation.strip())
                    line_changed = True
                else:
                    translated_lines.append(line.strip())

            if line_changed:
                reconstructed_text = '\\n'.join('▶' + line if line else '' for line in translated_lines)
                new_row = row.copy()
                new_row[6] = reconstructed_text
                changed_rows.append(new_row)
                replaced_count += 1
            else:
                # Fallback: Try normalized structure approach
                normalized_structure = []
                current_line = ""
                for line in original_lines:
                    if line.strip().startswith('▶'):
                        if current_line:
                            normalized_structure.append(current_line)
                        current_line = line.strip()
                    else:
                        if line.strip():
                            current_line += " " + line.strip()
                if current_line:
                    normalized_structure.append(current_line)

                fully_normalized_text = ' '.join(line.replace('▶', '').strip() for line in normalized_structure)
                embedding = model.encode([fully_normalized_text])
                faiss.normalize_L2(embedding)
                distances, indices = whole_index.search(embedding, 1)
                best_match_index = indices[0][0]
                distance_score = distances[0][0]

                if distance_score >= similarity_threshold:
                    best_match_korean = list(whole_translation_dict.keys())[best_match_index]
                    best_match_translation = whole_translation_dict[best_match_korean]
                    
                    words = best_match_translation.split()
                    words_per_line = max(1, len(words) // len(normalized_structure))
                    translated_lines = []
                    
                    for i in range(len(normalized_structure)):
                        start_idx = i * words_per_line
                        end_idx = start_idx + words_per_line if i < len(normalized_structure) - 1 else len(words)
                        line_translation = ' '.join(words[start_idx:end_idx])
                        translated_lines.append(line_translation)
                    
                    reconstructed_text = '\\n'.join('▶' + line if line else '' for line in translated_lines)
                    new_row = row.copy()
                    new_row[6] = reconstructed_text
                    changed_rows.append(new_row)
                    replaced_count += 1

        else:  # Non-triangle text
            embedding = model.encode([normalized_text])
            faiss.normalize_L2(embedding)
            distances, indices = whole_index.search(embedding, 1)
            best_match_index = indices[0][0]
            distance_score = distances[0][0]
            if distance_score >= similarity_threshold:
                best_match_korean = list(whole_translation_dict.keys())[best_match_index]
                best_match_translation = whole_translation_dict[best_match_korean]
                adapted_translation = adapt_structure(original_text, best_match_translation)
                new_row = row.copy()
                new_row[6] = adapted_translation
                changed_rows.append(new_row)
                replaced_count += 1

        if (idx + 1) % 100 == 0:
            print(f"Processed {idx + 1}/{total_rows} rows")

    print(f"\nWriting output file: {output_path}")
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        for row in changed_rows:
            f.write('\t'.join(str(x) if pd.notna(x) else '' for x in row) + '\n')

    print("Content replacement completed.")
    print(f"Replaced and wrote {replaced_count} out of {total_rows} rows.")
    messagebox.showinfo("Replacement Completed", f"Content replacement completed successfully!\nReplaced and wrote {replaced_count} out of {total_rows} rows.\nSaved to: {output_path}")

    

# GUI setup
root = tk.Tk()
root.title("KR Similar ver. 0124 (by Neil)")

# Center the window on the screen
window_width = 500  # Adjust this value as needed
window_height = 350  # Adjust this value as needed

# Get the screen dimensions
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

# Calculate the x and y coordinates for the Tk root window
x = (screen_width / 2) - (window_width / 2)
y = (screen_height / 2) - (window_height / 2)

# Set the dimensions of the window and where it is placed
root.geometry('%dx%d+%d+%d' % (window_width, window_height, x, y))

embed_button = tk.Button(root, text="Create Dictionary", command=process_embeddings_thread)
embed_button.pack(pady=10)

# Frame for KR Similar Extraction options
kr_frame = ttk.LabelFrame(root, text="설정")
kr_frame.pack(pady=10, padx=10, fill="x")

filter_var = tk.BooleanVar(value=True)
filter_check = ttk.Checkbutton(kr_frame, text="동일 카테고리 무시", variable=filter_var)
filter_check.grid(row=0, column=0, sticky="w", padx=5, pady=5)

ttk.Label(kr_frame, text="스트링 최소 글자수:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
min_char_entry = ttk.Entry(kr_frame)
min_char_entry.insert(0, "50")
min_char_entry.grid(row=1, column=1, padx=5, pady=5)

ttk.Label(kr_frame, text="최소 일치율:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
similarity_threshold_entry = ttk.Entry(kr_frame)
similarity_threshold_entry.insert(0, "0.85")
similarity_threshold_entry.grid(row=2, column=1, padx=5, pady=5)

extract_button = tk.Button(kr_frame, text="서로 유사한 스트링 추출", command=kr_similar_extraction_thread)
extract_button.grid(row=3, column=0, columnspan=2, pady=10)

# Frame for Replace Similar Content options
replace_frame = ttk.LabelFrame(root, text="설정")
replace_frame.pack(pady=10, padx=10, fill="x")

ttk.Label(replace_frame, text="최소 일치율:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
replace_similarity_threshold_entry = ttk.Entry(replace_frame)
replace_similarity_threshold_entry.insert(0, "0.85")
replace_similarity_threshold_entry.grid(row=0, column=1, padx=5, pady=5)

replace_button = tk.Button(replace_frame, text="자동 번역 전환", command=replace_similar_content_thread)
replace_button.grid(row=1, column=0, columnspan=2, pady=10)

print("실행 완료 !")
root.protocol("WM_DELETE_WINDOW", on_closing)
if splash_active:
    pyi_splash.close()  # Close the splash screen

root.mainloop()