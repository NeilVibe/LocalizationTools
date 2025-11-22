"""
XLSTransfer Tool Configuration

Tool-specific settings for the XLSTransfer module.
"""

from pathlib import Path

# ============================================
# Model Settings
# ============================================

# Path to Korean BERT model (VRS-Manager pattern: models/kr-sbert/ at project root)
MODEL_NAME = "snunlp/KR-SBERT-V40K-klueNLI-augSTS"

# Get project root (3 levels up from this file: client/tools/xls_transfer/config.py)
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
MODEL_PATH = _PROJECT_ROOT / "models" / "kr-sbert"

# Model loading
LAZY_LOAD_MODEL = True  # Load only when needed
OFFLINE_MODE = True  # Use local model (downloaded and ready)

# ============================================
# FAISS Settings
# ============================================

# Similarity threshold (0.0 to 1.0)
# Higher = stricter matching, lower = more lenient
DEFAULT_FAISS_THRESHOLD = 0.99

# Threshold ranges for UI
MIN_FAISS_THRESHOLD = 0.80
MAX_FAISS_THRESHOLD = 1.00
FAISS_THRESHOLD_STEP = 0.01

# ============================================
# Processing Settings
# ============================================

# Batch sizes
EMBEDDING_BATCH_SIZE = 100  # Number of texts to embed at once
TRANSLATION_BATCH_SIZE = 50  # Number of translations to process at once

# File size limits
MAX_FILE_SIZE_MB = 100  # Maximum Excel file size

# Processing modes
MODES = ["split", "whole"]  # Available matching modes
DEFAULT_MODE = "whole"  # Try whole-text matching first

# ============================================
# Excel Settings
# ============================================

# Supported Excel formats
SUPPORTED_EXCEL_EXTENSIONS = [".xlsx", ".xls"]

# Default column settings
DEFAULT_KR_COLUMN = "A"
DEFAULT_TRANS_COLUMN = "B"

# Temp file suffix
TEMP_FILE_SUFFIX = "_temp"

# ============================================
# Dictionary Settings
# ============================================

# Dictionary file names (saved in same directory as Excel files or user data dir)
SPLIT_EMBEDDINGS_FILE = "SplitExcelEmbeddings.npy"
SPLIT_DICTIONARY_FILE = "SplitExcelDictionary.pkl"
WHOLE_EMBEDDINGS_FILE = "WholeExcelEmbeddings.npy"
WHOLE_DICTIONARY_FILE = "WholeExcelDictionary.pkl"

# Dictionary creation
MIN_UNIQUE_TEXTS = 10  # Minimum texts needed to create dictionary

# ============================================
# Text Processing
# ============================================

# Text cleaning
REMOVE_CARRIAGE_RETURN = True  # Remove _x000D_ characters
STRIP_WHITESPACE = True

# Code patterns (game localization codes)
CODE_PATTERNS = [
    r'\{[^}]+\}',           # {Code} format
    r'<PAColor[^>]*>',      # <PAColor> tags
    r'<PAOldColor>',        # End color tag
]

# Newline handling
NEWLINE_ESCAPE = r'\n'  # How newlines are represented in .txt files

# ============================================
# UI Settings
# ============================================

# Gradio interface
UI_TITLE = "XLS Transfer"
UI_DESCRIPTION = "AI-powered translation transfer using Korean BERT"

# Progress messages
PROGRESS_MESSAGES = {
    "loading_model": "Loading Korean BERT model...",
    "generating_embeddings": "Generating embeddings",
    "creating_index": "Creating FAISS index...",
    "translating": "Translating",
    "saving": "Saving results...",
}

# File upload
ALLOW_MULTIPLE_FILES = True
FILE_UPLOAD_LABEL = "Select Excel files"

# ============================================
# Logging Settings
# ============================================

# Enable detailed logging
ENABLE_FUNCTION_LOGGING = True

# Log file metadata (privacy setting)
LOG_FILE_NAMES = False  # Don't log actual file names

# Performance tracking
TRACK_PERFORMANCE_METRICS = True  # Log CPU/memory usage

# ============================================
# Output Settings
# ============================================

# Output file suffixes
OUTPUT_SUFFIXES = {
    "translate_excel": "_translated",
    "transfer_to_close": "_translated",
    "check_newlines": "_newline_report",
    "combine_excel": "_combined",
    "newline_adapt": "_adapted",
    "simple_transfer": "_transferred",
}

# Output formats
PRESERVE_FORMATTING = True  # Keep Excel cell formatting
PRESERVE_FORMULAS = False  # Convert formulas to values

# Organized output directory structure
from pathlib import Path as ConfigPath
import os

# Base output directory (user's home or project-specific)
OUTPUT_BASE_DIR = ConfigPath(os.path.expanduser("~")) / "LocalizationTools_Outputs"

# App-specific subdirectories
APP_OUTPUT_DIRS = {
    "xlstransfer": "XLSTransfer",
    "future_app": "FutureApp",  # Add more apps here
}

# Whether to organize outputs by date (YYYY-MM-DD folders)
ORGANIZE_BY_DATE = True  # Creates folders like "2025-11-09"

# ============================================
# Helper Functions
# ============================================

def get_model_path() -> Path:
    """Get the full path to the Korean BERT model."""
    return MODEL_PATH


def get_dictionary_files() -> dict:
    """Get dictionary file names."""
    return {
        "split_embeddings": SPLIT_EMBEDDINGS_FILE,
        "split_dictionary": SPLIT_DICTIONARY_FILE,
        "whole_embeddings": WHOLE_EMBEDDINGS_FILE,
        "whole_dictionary": WHOLE_DICTIONARY_FILE,
    }


def validate_faiss_threshold(threshold: float) -> float:
    """
    Validate and clamp FAISS threshold value.

    Args:
        threshold: Threshold value to validate

    Returns:
        Clamped threshold between MIN and MAX
    """
    return max(MIN_FAISS_THRESHOLD, min(MAX_FAISS_THRESHOLD, threshold))


def get_output_directory(app_name: str = "xlstransfer") -> ConfigPath:
    """
    Get organized output directory path for the given app.

    Creates structure:
    ~/LocalizationTools_Outputs/
      XLSTransfer/
        2025-11-09/  (if ORGANIZE_BY_DATE is True)

    Args:
        app_name: Name of the app (key in APP_OUTPUT_DIRS)

    Returns:
        Path object for the output directory
    """
    from datetime import datetime

    # Base directory
    output_dir = OUTPUT_BASE_DIR

    # App-specific subdirectory
    if app_name in APP_OUTPUT_DIRS:
        output_dir = output_dir / APP_OUTPUT_DIRS[app_name]

    # Date-based subdirectory (YYYY-MM-DD)
    if ORGANIZE_BY_DATE:
        today = datetime.now().strftime("%Y-%m-%d")
        output_dir = output_dir / today

    # Create directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    return output_dir


if __name__ == "__main__":
    # Print configuration summary
    print("XLSTransfer Configuration")
    print("=" * 50)
    print(f"Model Path: {get_model_path()}")
    print(f"Default FAISS Threshold: {DEFAULT_FAISS_THRESHOLD}")
    print(f"Batch Size (Embedding): {EMBEDDING_BATCH_SIZE}")
    print(f"Batch Size (Translation): {TRANSLATION_BATCH_SIZE}")
    print(f"Max File Size: {MAX_FILE_SIZE_MB}MB")
    print(f"Supported Formats: {SUPPORTED_EXCEL_EXTENSIONS}")
