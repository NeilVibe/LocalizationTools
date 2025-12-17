#!/usr/bin/env python3
"""
Translate .txt file (Transfer to Close)
Exact replica of translate_file from original XLSTransfer0225.py (lines 362-631)

Usage: python translate_file.py <file_path> <threshold>
"""

import sys
import json
import os
import pickle
import numpy as np
import pandas as pd
import re
from pathlib import Path
import faiss
from typing import TYPE_CHECKING

# Lazy import for SentenceTransformer (takes ~30s to load PyTorch)
if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))
from core import clean_text, simple_number_replace


def clean_audiovoice_tags(text):
    """Remove game code tags for embedding"""
    text = re.sub(r'\{[^}]*\}', '', text)  # Remove any code that starts with {
    text = re.sub(r'<PAColor[^>]*>', '', text)  # Remove color code tags
    text = re.sub(r'<PAOldColor>', '', text)  # Remove <PAOldColor> tag
    return text


def trim_columns(path_in):
    """Trim to first 9 columns"""
    columns_to_keep = list(range(9))
    trimmed_lines = []
    with open(path_in, 'r', encoding='utf-8') as f_in:
        for line in f_in:
            columns = line.rstrip('\n').split('\t')
            if len(columns) < 9:
                columns += [''] * (9 - len(columns))
            new_line = '\t'.join([columns[i] for i in columns_to_keep])
            trimmed_lines.append(new_line)
    return trimmed_lines


def convert_newlines(text):
    """Convert literal newlines to \\n"""
    return text.replace('\n', '\\n')


def main():
    try:
        if len(sys.argv) < 3:
            result = {
                "success": False,
                "error": "Usage: translate_file.py <file_path> <threshold>"
            }
            print(json.dumps(result))
            sys.exit(1)

        file_path = sys.argv[1]
        threshold = float(sys.argv[2])

        # Load model (lazy import to avoid slow startup)
        print("Loading model...", file=sys.stderr)
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('snunlp/KR-SBERT-V40K-klueNLI-augSTS')

        # Load dictionaries
        print("Loading dictionaries...", file=sys.stderr)

        # Load split mode
        if not os.path.exists('SplitExcelDictionary.pkl') or not os.path.exists('SplitExcelEmbeddings.npy'):
            return {"success": False, "error": "Dictionary not loaded. Please create and load dictionary first."}

        with open('SplitExcelDictionary.pkl', 'rb') as file:
            translation_dict_split = pickle.load(file)
        ref_kr_embeddings_split = np.load('SplitExcelEmbeddings.npy')
        ref_kr_sentences_split = pd.Series(list(translation_dict_split.keys()), dtype=str)
        faiss.normalize_L2(ref_kr_embeddings_split)
        index_split = faiss.IndexFlatIP(ref_kr_embeddings_split.shape[1])
        index_split.add(ref_kr_embeddings_split)

        # Load whole mode if available
        whole_mode_available = False
        translation_dict_whole = None
        ref_kr_sentences_whole = None
        index_whole = None

        if os.path.exists('WholeExcelDictionary.pkl') and os.path.exists('WholeExcelEmbeddings.npy'):
            with open('WholeExcelDictionary.pkl', 'rb') as file:
                translation_dict_whole = pickle.load(file)
            ref_kr_embeddings_whole = np.load('WholeExcelEmbeddings.npy')
            ref_kr_sentences_whole = pd.Series(list(translation_dict_whole.keys()), dtype=str)
            faiss.normalize_L2(ref_kr_embeddings_whole)
            index_whole = faiss.IndexFlatIP(ref_kr_embeddings_whole.shape[1])
            index_whole.add(ref_kr_embeddings_whole)
            whole_mode_available = True

        # Process file
        print("Processing file...", file=sys.stderr)
        trimmed_lines = trim_columns(file_path)
        total_sentences = len(trimmed_lines)
        updated_data_rows = []

        for idx, line in enumerate(trimmed_lines):
            row = line.split('\t')
            korean_text = row[5] if len(row) > 5 else ""

            if not korean_text.strip():
                continue

            lines = korean_text.split("\\n")
            final_reconstruction = []
            translation_inserted = False

            # Try whole mode first
            if whole_mode_available:
                clean_sentence = clean_audiovoice_tags(korean_text)
                sentence_embeddings = model.encode([clean_sentence])
                faiss.normalize_L2(sentence_embeddings)
                distances, indices = index_whole.search(sentence_embeddings, 1)
                best_match_index = indices[0][0]
                distance_score = distances[0][0]

                if distance_score >= threshold and best_match_index < len(ref_kr_sentences_whole):
                    best_match_korean = ref_kr_sentences_whole.iloc[best_match_index]
                    whole_translated_text = translation_dict_whole.get(best_match_korean, "")
                    if whole_translated_text:
                        whole_translated_text = convert_newlines(whole_translated_text)
                        final_reconstruction.append(whole_translated_text)
                        translation_inserted = True

            # Fallback to split mode
            if not translation_inserted:
                for line in lines:
                    if line.strip() == "":
                        final_reconstruction.append("")
                        continue

                    clean_sentence = clean_audiovoice_tags(line)
                    sentence_embeddings = model.encode([clean_sentence])
                    faiss.normalize_L2(sentence_embeddings)
                    distances, indices = index_split.search(sentence_embeddings, 1)
                    best_match_index = indices[0][0]
                    distance_score = distances[0][0]

                    if distance_score >= threshold and best_match_index < len(ref_kr_sentences_split):
                        best_match_korean = ref_kr_sentences_split.iloc[best_match_index]
                        translated_sentence = translation_dict_split.get(best_match_korean, "")
                        if translated_sentence:
                            final_translation = simple_number_replace(line, translated_sentence)
                            final_reconstruction.append(final_translation)
                            translation_inserted = True
                        else:
                            final_reconstruction.append(line)
                    else:
                        final_reconstruction.append(line)

            if translation_inserted:
                row[6] = "\\n".join(final_reconstruction)
                updated_data_rows.append(row)

            if (idx + 1) % 100 == 0:
                print(f"Processed {idx + 1}/{total_sentences} rows", file=sys.stderr)

        # Write output
        output_file_path = f"{os.path.splitext(file_path)[0]}_translated.txt"
        if updated_data_rows:
            with open(output_file_path, 'w', newline='', encoding='utf-8') as f:
                for row in updated_data_rows:
                    f.write('\t'.join(row) + '\n')

            return {
                "success": True,
                "output_file": output_file_path,
                "rows_translated": len(updated_data_rows),
                "message": f"Translation completed! {len(updated_data_rows)} rows modified."
            }
        else:
            return {
                "success": True,
                "rows_translated": 0,
                "message": "No translations inserted. Output file not created."
            }

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
