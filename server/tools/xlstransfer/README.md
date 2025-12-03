# XLSTransfer Tool

AI-powered translation transfer between Excel files using Korean BERT embeddings and FAISS similarity search.

---

## 📋 Overview

XLSTransfer uses semantic similarity to match and transfer translations between Excel files. It's particularly effective for Korean ↔ translation pairs.

### Key Features
- **AI-Powered Matching**: Uses Korean BERT for semantic embeddings
- **FAISS Search**: Fast similarity search across thousands of translations
- **Multiple Modes**: Split-line and whole-text matching
- **Smart Code Handling**: Preserves game codes and formatting tags
- **Newline Adaptation**: Automatically adjusts line breaks between languages

---

## 🗂️ Module Structure (CLEAN Organization)

```
xls_transfer/
├── __init__.py           # Module exports
├── README.md             # This file
├── config.py             # Tool-specific settings
├── core.py               # Core logic and utilities
├── embeddings.py         # Embedding generation and FAISS
├── translation.py        # Translation matching engine
├── excel_utils.py        # Excel file operations
└── ui.py                 # Gradio interface
```

### Module Responsibilities

**config.py**:
- FAISS threshold settings
- Batch sizes
- Model configuration
- Default parameters

**core.py**:
- Text cleaning utilities
- Column index conversion
- Code pattern detection
- Number replacement logic

**embeddings.py**:
- Model loading (Korean BERT)
- Embedding generation
- FAISS index creation
- Dictionary management (save/load)

**translation.py**:
- Translation matching (whole & split modes)
- Batch processing
- Score filtering
- Result aggregation

**excel_utils.py**:
- Excel file reading/writing
- Sheet selection and validation
- Column operations
- Temp file management

**ui.py**:
- Gradio interface creation
- File upload/download
- Progress indicators
- User settings

---

## 🔄 Functions Available

### 1. Create Dictionary
**Purpose**: Build translation dictionary from reference Excel files
**Input**: Excel files with KR and translation columns
**Output**: Embeddings (.npy) and dictionary (.pkl) files
**Processing**: Generates FAISS index for fast similarity search

### 2. Load Dictionary
**Purpose**: Load existing embeddings and dictionary
**Input**: None (looks for local .npy and .pkl files)
**Output**: Ready-to-use translation index

### 3. Transfer to Excel
**Purpose**: Transfer translations from dictionary to new Excel file
**Input**: Excel file with Korean text
**Output**: Same file with translations filled in

### 4. Transfer to Close
**Purpose**: Transfer translations to .txt file (game localization format)
**Input**: Tab-separated .txt file
**Output**: File with translations inserted

### 5. Check Newlines
**Purpose**: Find mismatched line breaks between KR and translation
**Input**: Excel files
**Output**: Report of rows with different newline counts

### 6. Combine Excel Files
**Purpose**: Merge multiple Excel files into one
**Input**: Multiple Excel files
**Output**: Single combined Excel file

### 7. Newline Auto Adapt
**Purpose**: Automatically fix newline mismatches
**Input**: Excel file
**Output**: File with adjusted line breaks

### 8. Simple Excel Transfer
**Purpose**: Direct column-to-column transfer without AI
**Input**: Source and destination Excel files
**Output**: Destination file with transferred data

---

## 🚀 Usage Example

```python
from client.tools.xls_transfer import XLSTransferTool

# Initialize tool
tool = XLSTransferTool(username="john_doe")

# Create dictionary from reference files
tool.create_dictionary(
    files=["reference1.xlsx", "reference2.xlsx"],
    kr_columns=["A", "B"],
    trans_columns=["C", "D"]
)

# Load dictionary
tool.load_dictionary()

# Transfer translations
tool.transfer_to_excel(
    input_file="new_content.xlsx",
    kr_column="A",
    output_column="B"
)
```

---

## 🎛️ Configuration

Default settings in `config.py`:

```python
FAISS_THRESHOLD = 0.99        # Minimum similarity score (0-1)
BATCH_SIZE = 100              # Embeddings batch size
MAX_FILE_SIZE_MB = 100        # Maximum upload size
MODEL_PATH = "client/models/KRTransformer"  # Model location
```

---

## 📊 Performance

- **Model Loading**: ~5-10 seconds (first time)
- **Embedding Generation**: ~100 texts/second
- **Translation Matching**: ~200 texts/second
- **Memory Usage**: ~1-2GB (with model loaded)

---

## 🧹 Code Quality

All modules follow STRICT clean code standards:
- Type hints
- Comprehensive docstrings
- Error handling
- Progress tracking
- Logging integration
- No monolithic functions (everything modular)

---

## 🔧 Maintenance

To modify behavior:
1. **Adjust matching**: Edit `translation.py`
2. **Change UI**: Edit `ui.py`
3. **Add features**: Create new functions in appropriate module
4. **Update settings**: Modify `config.py`

Keep it CLEAN! Archive old code in `/ARCHIVE/xls_transfer/` when refactoring.

---

**Built with ❤️ for efficient localization workflows**
