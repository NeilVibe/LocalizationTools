# Gradio Version Archive

**Date Archived**: 2025-11-08
**Reason**: Moving to Electron desktop app for professional UI

## What's Here

This folder contains the original Gradio-based UI files that were used during MVP development. They have been archived because:

1. **Gradio not suitable for professional presentation** - Tab-based UI doesn't scale well for many tools
2. **Moving to Electron + Svelte** - Professional desktop app with compact sidebar navigation
3. **Keeping as reference** - These files show the original implementation

## Archived Files

- `run_xlstransfer.py` - Standalone launcher for XLSTransfer Gradio UI
- `run_admin_dashboard.py` - Standalone launcher for Admin Dashboard Gradio UI
- `client_main_gradio.py` - Original Gradio-based client main file
- `xlstransfer_ui_gradio.py` - XLSTransfer Gradio interface (730+ lines, 7 tabs)
- `admin_dashboard/` - Gradio admin dashboard (5 tabs: Overview, Logs, Users, Errors, Settings)

## What's Still Used

The **core Python modules** are still active and will be integrated with Electron:
- `client/tools/xls_transfer/core.py` - Text processing functions
- `client/tools/xls_transfer/embeddings.py` - BERT embeddings & FAISS
- `client/tools/xls_transfer/translation.py` - Translation matching logic
- `client/tools/xls_transfer/excel_utils.py` - Excel file operations

These modules are **framework-agnostic** and work with any UI (Gradio, Electron, CLI, etc.)

## Can I Use These?

Yes! If you want to run the Gradio version for testing:

```bash
# XLSTransfer tool
python3 archive/gradio_version/run_xlstransfer.py

# Admin Dashboard
python3 archive/gradio_version/run_admin_dashboard.py
```

**Note**: These are functional but deprecated. The Electron version will be the primary interface going forward.
