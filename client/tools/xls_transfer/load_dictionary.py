#!/usr/bin/env python3
"""
Load embeddings and create FAISS index
Matches original XLSTransfer0225.py load_embeddings_and_create_index function
"""

import sys
import json
import os
import pickle
import numpy as np
import faiss


def main():
    try:
        # Global variables to store loaded data
        global ref_kr_embeddings_split, translation_dict_split, index_split, ref_kr_sentences_split
        global ref_kr_embeddings_whole, translation_dict_whole, index_whole, ref_kr_sentences_whole
        global split_mode_available, whole_mode_available

        split_mode_available = False
        whole_mode_available = False

        # Try to load split mode
        if os.path.exists('SplitExcelDictionary.pkl') and os.path.exists('SplitExcelEmbeddings.npy'):
            with open('SplitExcelDictionary.pkl', 'rb') as file:
                translation_dict_split = pickle.load(file)
            ref_kr_embeddings_split = np.load('SplitExcelEmbeddings.npy')
            import pandas as pd
            ref_kr_sentences_split = pd.Series(list(translation_dict_split.keys()), dtype=str)
            faiss.normalize_L2(ref_kr_embeddings_split)
            index_split = faiss.IndexFlatIP(ref_kr_embeddings_split.shape[1])
            index_split.add(ref_kr_embeddings_split)
            split_mode_available = True
            print("Split mode loaded successfully.", file=sys.stderr)

        # Try to load whole mode
        if os.path.exists('WholeExcelDictionary.pkl') and os.path.exists('WholeExcelEmbeddings.npy'):
            with open('WholeExcelDictionary.pkl', 'rb') as file:
                translation_dict_whole = pickle.load(file)
            ref_kr_embeddings_whole = np.load('WholeExcelEmbeddings.npy')
            import pandas as pd
            ref_kr_sentences_whole = pd.Series(list(translation_dict_whole.keys()), dtype=str)
            faiss.normalize_L2(ref_kr_embeddings_whole)
            index_whole = faiss.IndexFlatIP(ref_kr_embeddings_whole.shape[1])
            index_whole.add(ref_kr_embeddings_whole)
            whole_mode_available = True
            print("Whole mode loaded successfully.", file=sys.stderr)

        if split_mode_available or whole_mode_available:
            modes_loaded = []
            if split_mode_available:
                modes_loaded.append('Split')
            if whole_mode_available:
                modes_loaded.append('Whole')

            result = {
                "success": True,
                "modes": modes_loaded,
                "message": f"Loaded modes: {', '.join(modes_loaded)}"
            }
            print(json.dumps(result))
        else:
            result = {
                "success": False,
                "error": "No embedding modes were loaded. Please create a dictionary first."
            }
            print(json.dumps(result))
            sys.exit(1)

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
