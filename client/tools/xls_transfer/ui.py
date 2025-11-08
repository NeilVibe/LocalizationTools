"""
XLSTransfer Gradio UI

Clean, professional Gradio interface for all XLSTransfer functions.
Integrates with refactored modules and logging system.
"""

import gradio as gr
from pathlib import Path
from typing import List, Optional, Tuple
import time
from loguru import logger

from client.tools.xls_transfer import config
from client.tools.xls_transfer.embeddings import (
    process_excel_for_dictionary,
    save_dictionary,
    load_dictionary,
    check_dictionary_exists
)
from client.tools.xls_transfer.translation import (
    translate_text_multi_mode,
    TranslationProgress
)
from client.tools.xls_transfer.excel_utils import (
    get_sheet_names,
    write_translations_to_excel,
    check_newline_mismatches,
    combine_excel_files,
    auto_adapt_newlines,
    simple_excel_transfer,
    read_excel_columns
)
from client.utils.logger import get_logger
from client.utils.progress import ProgressTracker


# ============================================
# Global State
# ============================================

# Dictionary storage
_split_dict = None
_whole_dict = None
_split_index = None
_whole_index = None
_split_sentences = None
_whole_sentences = None


# ============================================
# Function 1: Create Dictionary
# ============================================

def create_dictionary_ui(
    files: List[str],
    kr_columns: str,
    trans_columns: str,
    progress=gr.Progress()
) -> str:
    """
    Create translation dictionary from Excel files.

    Args:
        files: List of Excel file paths
        kr_columns: Comma-separated column letters for Korean
        trans_columns: Comma-separated column letters for translations
        progress: Gradio progress tracker

    Returns:
        Status message
    """
    usage_logger = get_logger()
    start_time = time.time()
    status = "success"
    error_msg = None

    try:
        logger.info(f"Creating dictionary from {len(files)} files")

        if not files:
            return "❌ No files selected"

        # Parse columns
        kr_cols = [c.strip().upper() for c in kr_columns.split(',')]
        trans_cols = [c.strip().upper() for c in trans_columns.split(',')]

        if len(kr_cols) != len(files) or len(trans_cols) != len(files):
            return "❌ Number of columns must match number of files"

        # Prepare file data
        excel_files = []
        for i, file_path in enumerate(files):
            sheets = get_sheet_names(file_path)
            # Use first sheet for now (can be enhanced later)
            excel_files.append((file_path, sheets[0], kr_cols[i], trans_cols[i]))

        # Create progress tracker
        with ProgressTracker(total=len(files) + 2, desc="Creating dictionary", gradio_progress=progress) as tracker:
            # Process Excel files
            tracker.update(0, status="Processing Excel files...")
            split_dict, whole_dict, split_emb, whole_emb = process_excel_for_dictionary(
                excel_files,
                progress_tracker=tracker
            )

            tracker.update(1, status="Saving dictionaries...")

            # Save dictionaries
            save_dictionary(split_emb, split_dict, "split")
            if whole_dict:
                save_dictionary(whole_emb, whole_dict, "whole")

            tracker.update(1, status="Complete!")

        result = f"""
✅ Dictionary created successfully!

📊 Statistics:
- Split mode: {len(split_dict)} unique translations
- Whole mode: {len(whole_dict)} unique translations
- Total files processed: {len(files)}

💾 Files saved:
- {config.SPLIT_EMBEDDINGS_FILE}
- {config.SPLIT_DICTIONARY_FILE}
- {config.WHOLE_EMBEDDINGS_FILE} (if applicable)
- {config.WHOLE_DICTIONARY_FILE} (if applicable)

✨ Ready to use! Click "Load Dictionary" to start translating.
"""

        return result

    except Exception as e:
        status = "error"
        error_msg = str(e)
        logger.error(f"Error creating dictionary: {e}")
        return f"❌ Error: {str(e)}"

    finally:
        duration = time.time() - start_time
        usage_logger.log_operation(
            user_id=None,
            username="local_user",  # TODO: Get from session
            tool_name="XLSTransfer",
            function_name="create_dictionary",
            duration_seconds=duration,
            status=status,
            rows_processed=len(_split_dict) if _split_dict else 0,
            error_message=error_msg
        )


# ============================================
# Function 2: Load Dictionary
# ============================================

def load_dictionary_ui() -> str:
    """
    Load existing dictionary files.

    Returns:
        Status message
    """
    global _split_dict, _whole_dict, _split_index, _whole_index, _split_sentences, _whole_sentences

    usage_logger = get_logger()
    start_time = time.time()
    status = "success"
    error_msg = None

    try:
        logger.info("Loading dictionaries...")

        modes_loaded = []

        # Try to load split mode
        if check_dictionary_exists("split"):
            emb, trans_dict, index, sentences = load_dictionary("split")
            _split_dict = trans_dict
            _split_index = index
            _split_sentences = sentences
            modes_loaded.append(f"Split ({len(trans_dict)} translations)")
            logger.info(f"Split mode loaded: {len(trans_dict)} translations")

        # Try to load whole mode
        if check_dictionary_exists("whole"):
            emb, trans_dict, index, sentences = load_dictionary("whole")
            _whole_dict = trans_dict
            _whole_index = index
            _whole_sentences = sentences
            modes_loaded.append(f"Whole ({len(trans_dict)} translations)")
            logger.info(f"Whole mode loaded: {len(trans_dict)} translations")

        if not modes_loaded:
            return "❌ No dictionary files found. Please create a dictionary first."

        return f"""
✅ Dictionary loaded successfully!

📚 Modes available:
{chr(10).join(f'- {mode}' for mode in modes_loaded)}

🎯 Ready to translate!
Use "Transfer to Excel" or "Transfer to Close" functions.
"""

    except Exception as e:
        status = "error"
        error_msg = str(e)
        logger.error(f"Error loading dictionary: {e}")
        return f"❌ Error: {str(e)}"

    finally:
        duration = time.time() - start_time
        usage_logger.log_operation(
            user_id=None,
            username="local_user",
            tool_name="XLSTransfer",
            function_name="load_dictionary",
            duration_seconds=duration,
            status=status,
            error_message=error_msg
        )


# ============================================
# Function 3: Transfer to Excel
# ============================================

def transfer_to_excel_ui(
    file: str,
    kr_column: str,
    trans_column: str,
    threshold: float,
    progress=gr.Progress()
) -> Tuple[str, Optional[str]]:
    """
    Transfer translations to Excel file.

    Args:
        file: Excel file path
        kr_column: Korean column letter
        trans_column: Translation column letter to write to
        threshold: FAISS similarity threshold
        progress: Gradio progress tracker

    Returns:
        Tuple of (status_message, output_file_path)
    """
    usage_logger = get_logger()
    start_time = time.time()
    status = "success"
    error_msg = None
    rows_processed = 0

    try:
        if not file:
            return "❌ No file selected", None

        if not _split_dict and not _whole_dict:
            return "❌ Please load dictionary first", None

        logger.info(f"Translating {Path(file).name}")

        # Read Excel file
        sheets = get_sheet_names(file)
        sheet_name = sheets[0]  # Use first sheet

        kr_texts, _ = read_excel_columns(file, sheet_name, kr_column)
        rows_processed = len(kr_texts)

        # Translate with progress
        translations = {}
        with ProgressTracker(total=len(kr_texts), desc="Translating", gradio_progress=progress) as tracker:
            for idx, kr_text in enumerate(kr_texts, start=1):
                translation = translate_text_multi_mode(
                    kr_text,
                    _split_index,
                    _split_sentences,
                    _split_dict,
                    _whole_index,
                    _whole_sentences,
                    _whole_dict,
                    threshold=threshold
                )

                if translation:
                    translations[idx] = translation

                tracker.update(1, status=f"Translated {idx}/{len(kr_texts)}")

        # Write to file
        output_file = write_translations_to_excel(
            file,
            sheet_name,
            kr_column,
            trans_column,
            translations
        )

        match_rate = (len(translations) / len(kr_texts) * 100) if kr_texts else 0

        result = f"""
✅ Translation complete!

📊 Statistics:
- Total rows: {len(kr_texts)}
- Translated: {len(translations)} ({match_rate:.1f}%)
- Threshold: {threshold}

💾 Output saved to:
{output_file}
"""

        return result, output_file

    except Exception as e:
        status = "error"
        error_msg = str(e)
        logger.error(f"Error translating Excel: {e}")
        return f"❌ Error: {str(e)}", None

    finally:
        duration = time.time() - start_time
        usage_logger.log_operation(
            user_id=None,
            username="local_user",
            tool_name="XLSTransfer",
            function_name="transfer_to_excel",
            duration_seconds=duration,
            status=status,
            rows_processed=rows_processed,
            error_message=error_msg
        )


# ============================================
# Function 5: Check Newlines
# ============================================

def check_newlines_ui(
    file: str,
    kr_column: str,
    trans_column: str
) -> str:
    """
    Check for newline mismatches.

    Args:
        file: Excel file path
        kr_column: Korean column letter
        trans_column: Translation column letter

    Returns:
        Status message with mismatch report
    """
    usage_logger = get_logger()
    start_time = time.time()
    status = "success"
    error_msg = None

    try:
        if not file:
            return "❌ No file selected"

        logger.info(f"Checking newlines in {Path(file).name}")

        sheets = get_sheet_names(file)
        sheet_name = sheets[0]

        mismatches = check_newline_mismatches(file, sheet_name, kr_column, trans_column)

        if not mismatches:
            return "✅ No newline mismatches found! All good!"

        # Build report
        report = f"""
⚠️ Found {len(mismatches)} newline mismatches:

Row | KR Newlines | Trans Newlines
----|-------------|---------------
"""

        for mismatch in mismatches[:20]:  # Show first 20
            report += f"{mismatch['row']} | {mismatch['kr_newlines']} | {mismatch['trans_newlines']}\n"

        if len(mismatches) > 20:
            report += f"\n... and {len(mismatches) - 20} more\n"

        report += f"\n💡 Use 'Newline Auto Adapt' to fix these automatically!"

        return report

    except Exception as e:
        status = "error"
        error_msg = str(e)
        logger.error(f"Error checking newlines: {e}")
        return f"❌ Error: {str(e)}"

    finally:
        duration = time.time() - start_time
        usage_logger.log_operation(
            user_id=None,
            username="local_user",
            tool_name="XLSTransfer",
            function_name="check_newlines",
            duration_seconds=duration,
            status=status,
            error_message=error_msg
        )


# ============================================
# Function 6: Combine Excel Files
# ============================================

def combine_excel_ui(files: List[str]) -> Tuple[str, Optional[str]]:
    """
    Combine multiple Excel files.

    Args:
        files: List of Excel file paths

    Returns:
        Tuple of (status_message, output_file_path)
    """
    usage_logger = get_logger()
    start_time = time.time()
    status = "success"
    error_msg = None

    try:
        if not files or len(files) < 2:
            return "❌ Please select at least 2 files to combine", None

        logger.info(f"Combining {len(files)} files")

        output_file = combine_excel_files(files)

        return f"""
✅ Files combined successfully!

📊 Combined {len(files)} files

💾 Output saved to:
{output_file}
""", output_file

    except Exception as e:
        status = "error"
        error_msg = str(e)
        logger.error(f"Error combining files: {e}")
        return f"❌ Error: {str(e)}", None

    finally:
        duration = time.time() - start_time
        usage_logger.log_operation(
            user_id=None,
            username="local_user",
            tool_name="XLSTransfer",
            function_name="combine_excel",
            duration_seconds=duration,
            status=status,
            error_message=error_msg
        )


# ============================================
# Function 7: Newline Auto Adapt
# ============================================

def newline_adapt_ui(
    file: str,
    kr_column: str,
    trans_column: str
) -> Tuple[str, Optional[str]]:
    """
    Auto-adapt newlines in translations.

    Args:
        file: Excel file path
        kr_column: Korean column letter
        trans_column: Translation column letter

    Returns:
        Tuple of (status_message, output_file_path)
    """
    usage_logger = get_logger()
    start_time = time.time()
    status = "success"
    error_msg = None

    try:
        if not file:
            return "❌ No file selected", None

        logger.info(f"Auto-adapting newlines in {Path(file).name}")

        sheets = get_sheet_names(file)
        sheet_name = sheets[0]

        output_file, num_adapted = auto_adapt_newlines(
            file,
            sheet_name,
            kr_column,
            trans_column
        )

        return f"""
✅ Newline adaptation complete!

📊 Statistics:
- Rows adapted: {num_adapted}

💾 Output saved to:
{output_file}
""", output_file

    except Exception as e:
        status = "error"
        error_msg = str(e)
        logger.error(f"Error adapting newlines: {e}")
        return f"❌ Error: {str(e)}", None

    finally:
        duration = time.time() - start_time
        usage_logger.log_operation(
            user_id=None,
            username="local_user",
            tool_name="XLSTransfer",
            function_name="newline_auto_adapt",
            duration_seconds=duration,
            status=status,
            error_message=error_msg
        )


# ============================================
# Gradio Interface
# ============================================

def create_ui() -> gr.Blocks:
    """
    Create the complete XLSTransfer Gradio UI.

    Returns:
        Gradio Blocks interface
    """

    with gr.Blocks(title="XLSTransfer - AI Translation Tool", theme=gr.themes.Soft()) as app:

        gr.Markdown("""
# 🔄 XLSTransfer - AI-Powered Translation Transfer

Transfer translations between Excel files using Korean BERT and FAISS similarity search.
        """)

        with gr.Tabs():

            # Tab 1: Create Dictionary
            with gr.Tab("📚 Create Dictionary"):
                gr.Markdown("""
### Create Translation Dictionary

Upload Excel files with Korean and translation columns to build a searchable dictionary.
                """)

                with gr.Row():
                    create_files = gr.File(
                        label="Select Excel Files",
                        file_count="multiple",
                        file_types=[".xlsx", ".xls"]
                    )

                with gr.Row():
                    create_kr_cols = gr.Textbox(
                        label="Korean Columns",
                        placeholder="A,A,B (one per file, comma-separated)",
                        value="A"
                    )
                    create_trans_cols = gr.Textbox(
                        label="Translation Columns",
                        placeholder="B,C,D (one per file, comma-separated)",
                        value="B"
                    )

                create_btn = gr.Button("🔨 Create Dictionary", variant="primary", size="lg")
                create_output = gr.Textbox(label="Status", lines=10)

                create_btn.click(
                    fn=create_dictionary_ui,
                    inputs=[create_files, create_kr_cols, create_trans_cols],
                    outputs=create_output
                )

            # Tab 2: Load Dictionary
            with gr.Tab("📂 Load Dictionary"):
                gr.Markdown("""
### Load Existing Dictionary

Load previously created dictionary files to start translating.
                """)

                load_btn = gr.Button("📥 Load Dictionary", variant="primary", size="lg")
                load_output = gr.Textbox(label="Status", lines=8)

                load_btn.click(
                    fn=load_dictionary_ui,
                    inputs=[],
                    outputs=load_output
                )

            # Tab 3: Transfer to Excel
            with gr.Tab("📝 Transfer to Excel"):
                gr.Markdown("""
### Transfer Translations to Excel

Translate Korean text in Excel using the loaded dictionary.
                """)

                transfer_file = gr.File(
                    label="Select Excel File",
                    file_types=[".xlsx", ".xls"]
                )

                with gr.Row():
                    transfer_kr_col = gr.Textbox(label="Korean Column", value="A")
                    transfer_trans_col = gr.Textbox(label="Translation Column (to write)", value="B")
                    transfer_threshold = gr.Slider(
                        minimum=config.MIN_FAISS_THRESHOLD,
                        maximum=config.MAX_FAISS_THRESHOLD,
                        value=config.DEFAULT_FAISS_THRESHOLD,
                        step=config.FAISS_THRESHOLD_STEP,
                        label="Similarity Threshold"
                    )

                transfer_btn = gr.Button("🔄 Translate", variant="primary", size="lg")
                transfer_output = gr.Textbox(label="Status", lines=8)
                transfer_download = gr.File(label="Download Result")

                transfer_btn.click(
                    fn=transfer_to_excel_ui,
                    inputs=[transfer_file, transfer_kr_col, transfer_trans_col, transfer_threshold],
                    outputs=[transfer_output, transfer_download]
                )

            # Tab 5: Check Newlines
            with gr.Tab("🔍 Check Newlines"):
                gr.Markdown("""
### Check Newline Mismatches

Find rows where Korean and translation have different newline counts.
                """)

                check_file = gr.File(label="Select Excel File", file_types=[".xlsx", ".xls"])

                with gr.Row():
                    check_kr_col = gr.Textbox(label="Korean Column", value="A")
                    check_trans_col = gr.Textbox(label="Translation Column", value="B")

                check_btn = gr.Button("🔍 Check Newlines", variant="primary", size="lg")
                check_output = gr.Textbox(label="Mismatch Report", lines=15)

                check_btn.click(
                    fn=check_newlines_ui,
                    inputs=[check_file, check_kr_col, check_trans_col],
                    outputs=check_output
                )

            # Tab 6: Combine Excel
            with gr.Tab("🔗 Combine Excel"):
                gr.Markdown("""
### Combine Multiple Excel Files

Merge multiple Excel files into one.
                """)

                combine_files = gr.File(
                    label="Select Excel Files to Combine",
                    file_count="multiple",
                    file_types=[".xlsx", ".xls"]
                )

                combine_btn = gr.Button("🔗 Combine Files", variant="primary", size="lg")
                combine_output = gr.Textbox(label="Status", lines=6)
                combine_download = gr.File(label="Download Result")

                combine_btn.click(
                    fn=combine_excel_ui,
                    inputs=[combine_files],
                    outputs=[combine_output, combine_download]
                )

            # Tab 7: Newline Auto Adapt
            with gr.Tab("🔧 Newline Auto Adapt"):
                gr.Markdown("""
### Auto-Fix Newline Mismatches

Automatically adapt translation newlines to match Korean text.
                """)

                adapt_file = gr.File(label="Select Excel File", file_types=[".xlsx", ".xls"])

                with gr.Row():
                    adapt_kr_col = gr.Textbox(label="Korean Column", value="A")
                    adapt_trans_col = gr.Textbox(label="Translation Column", value="B")

                adapt_btn = gr.Button("🔧 Auto Adapt", variant="primary", size="lg")
                adapt_output = gr.Textbox(label="Status", lines=6)
                adapt_download = gr.File(label="Download Result")

                adapt_btn.click(
                    fn=newline_adapt_ui,
                    inputs=[adapt_file, adapt_kr_col, adapt_trans_col],
                    outputs=[adapt_output, adapt_download]
                )

        gr.Markdown("""
---
**XLSTransfer** - AI-powered translation transfer using Korean BERT and FAISS similarity search.
        """)

    return app


# ============================================
# Main Entry Point
# ============================================

if __name__ == "__main__":
    logger.info("Starting XLSTransfer UI...")

    app = create_ui()

    app.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        show_error=True
    )
