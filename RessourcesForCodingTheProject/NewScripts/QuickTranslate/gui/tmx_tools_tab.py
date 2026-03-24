"""
TMX Tools Tab — Tab 3 in QuickTranslate.

Section 1: MemoQ-TMX Conversion (auto language detection)
Section 2: TMX Cleaner -> Excel export
"""
from __future__ import annotations

import logging
import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

from core.tmx_tools import convert_to_memoq_tmx, clean_and_convert_to_excel, excel_to_memoq_tmx

logger = logging.getLogger(__name__)


class _TMXLogBridge(logging.Handler):
    """Bridges logger calls from TMX tools threads to the app's GUI log.

    Uses widget.after() for thread-safe delivery — no queue polling needed.
    Only active during TMX operations (attached/detached per operation).
    """

    _LEVEL_TO_TAG = {
        logging.DEBUG: 'info',
        logging.INFO: 'info',
        logging.WARNING: 'warning',
        logging.ERROR: 'error',
    }

    def __init__(self, widget: tk.Widget, log_fn):
        super().__init__()
        self._widget = widget
        self._log_fn = log_fn

    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
            tag = self._LEVEL_TO_TAG.get(record.levelno, 'info')
            for line in msg.split('\n'):
                if line.strip():
                    self._widget.after(0, lambda m=line, t=tag: self._log_fn(m, t))
        except Exception:
            self.handleError(record)


class TMXToolsTab(tk.Frame):
    """TMX Tools tab with conversion and cleaning sections."""

    def __init__(self, parent: tk.Widget, log_fn=None):
        super().__init__(parent, bg='#f0f0f0')
        self._mode = tk.StringVar(value="folder")
        self._path_var = tk.StringVar()
        self._status_var = tk.StringVar(value="No path selected")
        self._log_fn = log_fn
        # Log bridge: pipes logger output from TMX threads to GUI log
        self._log_bridge = None
        if log_fn:
            self._log_bridge = _TMXLogBridge(self, log_fn)
            self._log_bridge.setFormatter(logging.Formatter('%(message)s'))
        self._build_ui()

    def _build_ui(self):
        # ============================================================
        # Section 1: MemoQ-TMX Conversion
        # ============================================================
        conv_frame = tk.LabelFrame(
            self, text="MemoQ-TMX Conversion",
            font=('Segoe UI', 10, 'bold'),
            bg='#f0f0f0', fg='#555', padx=15, pady=8,
        )
        conv_frame.pack(fill=tk.X, pady=(0, 12), padx=5)

        # Mode toggle (ExtractAnything pattern)
        mode_row = tk.Frame(conv_frame, bg='#f0f0f0')
        mode_row.pack(fill=tk.X, pady=(0, 6))
        tk.Radiobutton(mode_row, text="Folder", variable=self._mode,
                        value="folder", bg='#f0f0f0',
                        font=('Segoe UI', 9)).pack(side=tk.LEFT, padx=(0, 10))
        tk.Radiobutton(mode_row, text="Single File", variable=self._mode,
                        value="file", bg='#f0f0f0',
                        font=('Segoe UI', 9)).pack(side=tk.LEFT)

        # Path row
        path_row = tk.Frame(conv_frame, bg='#f0f0f0')
        path_row.pack(fill=tk.X, pady=(0, 6))
        tk.Label(path_row, text="Path:", font=('Segoe UI', 9),
                 bg='#f0f0f0').pack(side=tk.LEFT)
        tk.Entry(path_row, textvariable=self._path_var,
                 font=('Segoe UI', 9),
                 width=50).pack(side=tk.LEFT, padx=(6, 6),
                                fill=tk.X, expand=True)
        tk.Button(path_row, text="Browse...", command=self._browse_path,
                  font=('Segoe UI', 9), cursor='hand2').pack(side=tk.LEFT)

        # Status label (detected languages)
        self._status_label = tk.Label(
            conv_frame, textvariable=self._status_var,
            font=('Segoe UI', 9), bg='#f0f0f0', fg='#666',
            anchor='w', wraplength=500,
        )
        self._status_label.pack(fill=tk.X, pady=(0, 8))

        # Convert button
        tk.Button(conv_frame, text="Convert to MemoQ-TMX",
                  command=self._on_convert,
                  font=('Segoe UI', 9, 'bold'), bg='#4472C4', fg='white',
                  relief='flat', padx=14, pady=4,
                  cursor='hand2').pack(anchor='w')

        # ============================================================
        # Section 2: TMX Cleaner -> Excel
        # ============================================================
        clean_frame = tk.LabelFrame(
            self, text="TMX Cleaner -> Excel",
            font=('Segoe UI', 10, 'bold'),
            bg='#f0f0f0', fg='#555', padx=15, pady=8,
        )
        clean_frame.pack(fill=tk.X, pady=(0, 8), padx=5)

        desc = tk.Label(
            clean_frame,
            text="Select a TMX file to clean all CAT tool markup and export "
                 "to Excel (5 columns: StrOrigin, Correction, StringID, DescOrigin, Desc).",
            font=('Segoe UI', 9), bg='#f0f0f0', fg='#666',
            wraplength=500, justify='left',
        )
        desc.pack(fill=tk.X, pady=(0, 8))

        tk.Button(clean_frame, text="Select TMX -> Clean & Export to Excel",
                  command=self._on_clean_to_excel,
                  font=('Segoe UI', 9, 'bold'), bg='#5cb85c', fg='white',
                  relief='flat', padx=14, pady=4,
                  cursor='hand2').pack(anchor='w')

        # ============================================================
        # Section 3: Excel -> MemoQ-TMX
        # ============================================================
        excel_frame = tk.LabelFrame(
            self, text="Excel -> MemoQ-TMX",
            font=('Segoe UI', 10, 'bold'),
            bg='#f0f0f0', fg='#555', padx=15, pady=8,
        )
        excel_frame.pack(fill=tk.X, pady=(0, 8), padx=5)

        desc3 = tk.Label(
            excel_frame,
            text="Select an Excel file (5-col: StrOrigin, Correction, StringID, "
                 "DescOrigin, DescText) or 3-col format to create MemoQ-compatible TMX.",
            font=('Segoe UI', 9), bg='#f0f0f0', fg='#666',
            wraplength=500, justify='left',
        )
        desc3.pack(fill=tk.X, pady=(0, 8))

        tk.Button(excel_frame, text="Select Excel -> Create MemoQ-TMX",
                  command=self._on_excel_to_tmx,
                  font=('Segoe UI', 9, 'bold'), bg='#e67e22', fg='white',
                  relief='flat', padx=14, pady=4,
                  cursor='hand2').pack(anchor='w')

    # ------------------------------------------------------------------
    # Log bridge: attach/detach around TMX operations
    # ------------------------------------------------------------------
    def _attach_log_bridge(self):
        """Attach log bridge so logger output appears in GUI during operation."""
        if self._log_bridge:
            logging.getLogger().addHandler(self._log_bridge)

    def _detach_log_bridge(self):
        """Detach log bridge after operation completes."""
        if self._log_bridge:
            logging.getLogger().removeHandler(self._log_bridge)

    # ------------------------------------------------------------------
    # Section 1: Browse + Convert
    # ------------------------------------------------------------------
    def _browse_path(self):
        if self._mode.get() == "folder":
            path = filedialog.askdirectory(
                title="Select folder with XML/Excel files")
        else:
            path = filedialog.askopenfilename(
                title="Select XML or Excel file",
                filetypes=[("XML files", "*.xml"),
                           ("Excel files", "*.xlsx;*.xls"),
                           ("All files", "*.*")])
        if path:
            self._path_var.set(path)
            self._scan_and_update_status(path)

    def _scan_and_update_status(self, path: str):
        """Scan path for languages, validate files, and log results to GUI."""
        try:
            from pathlib import Path as P
            from core.source_scanner import scan_source_for_languages
            scan = scan_source_for_languages(P(path))
            if scan.lang_files:
                parts = [
                    f"{k.upper()} ({len(v)} files)"
                    for k, v in sorted(scan.lang_files.items())
                ]
                self._status_var.set(f"Detected: {', '.join(parts)}")
                self._status_label.config(fg='#2d7d2d')
            else:
                msg = "No languages detected"
                if scan.unrecognized:
                    msg += f" ({len(scan.unrecognized)} unrecognized items)"
                self._status_var.set(msg)
                self._status_label.config(fg='#cc3333')

            # Launch validation in background thread (like Tab 1)
            self._validate_source_async(P(path), scan)

        except Exception as exc:
            self._status_var.set(f"Scan error: {exc}")
            self._status_label.config(fg='#cc3333')

    def _validate_source_async(self, path, scan):
        """Validate all source files — same checks as Tab 1's _validate_source_files_async."""
        def _validate():
            self._attach_log_bridge()
            try:
                from core.xml_parser import parse_xml_file, validate_xml_load
                from core.xml_io import parse_corrections_from_xml
                from core.excel_io import read_corrections_from_excel
                from core.checker import check_broken_xml_in_file

                # Collect all files (same as Tab 1)
                files = []
                for lang, flist in scan.lang_files.items():
                    for f in flist:
                        files.append((f, lang.upper()))
                for item in scan.unrecognized:
                    if item.is_file() and item.suffix.lower() in ('.xml', '.xlsx', '.xls'):
                        files.append((item, '???'))

                if not files:
                    logger.info("[TMX Validate] No files to validate.")
                    return

                logger.info("=" * 50)
                logger.info(f"[TMX Validate] Checking {len(files)} file(s)...")

                total_ok = 0
                total_fail = 0
                total_entries = 0
                all_formula_warnings = []
                all_integrity_warnings = []

                for filepath, lang in files:
                    suffix = filepath.suffix.lower() if hasattr(filepath, 'suffix') else os.path.splitext(str(filepath))[1].lower()
                    fname = filepath.name if hasattr(filepath, 'name') else os.path.basename(str(filepath))

                    if suffix == '.xml':
                        # ── XML validation (same as Tab 1) ──
                        # Step 1: XML load test
                        load_result = validate_xml_load(filepath)
                        if not load_result["ok"]:
                            logger.error(f"  FAIL [{lang}] {fname} — XML LOAD FAILED: {load_result['error']}")
                            total_fail += 1
                            continue

                        if load_result.get("recovery_parse_ok") and not load_result.get("strict_parse_ok"):
                            logger.warning(f"  WARN [{lang}] {fname} — loaded with recovery mode")

                        # Step 2: Parse corrections with full reports
                        xml_formula_report = []
                        xml_integrity_report = []
                        xml_no_translation_report = []
                        try:
                            entries = parse_corrections_from_xml(
                                filepath,
                                formula_report=xml_formula_report,
                                integrity_report=xml_integrity_report,
                                no_translation_report=xml_no_translation_report,
                            )
                            count = len(entries) if entries else 0
                        except Exception as e:
                            logger.error(f"  FAIL [{lang}] {fname} — parse error: {e}")
                            total_fail += 1
                            continue

                        # Step 3: Broken XML check
                        broken = check_broken_xml_in_file(filepath)
                        if broken:
                            logger.warning(f"  WARN [{lang}] {fname} — {len(broken)} broken LocStr node(s)")
                            for sid, _frag, _fn in broken[:3]:
                                logger.warning(f"    Broken: StringID={sid}")

                        # Step 4: Report issues with StringID + reason (same as Tab 1)
                        issues = []
                        if xml_formula_report:
                            logger.warning(f"  WARNING: {len(xml_formula_report)} formula-like entry(ies) in {fname}")
                            for r in xml_formula_report[:10]:
                                sid = r.get('string_id') or '(empty)'
                                logger.warning(f"    [{r.get('column', '?')}] StringID={sid}: {r.get('reason', '?')}")
                            if len(xml_formula_report) > 10:
                                logger.warning(f"    ...and {len(xml_formula_report) - 10} more")
                            issues.append(f"{len(xml_formula_report)} formula")
                            all_formula_warnings.extend(xml_formula_report)

                        if xml_integrity_report:
                            # Split: critical (real) vs non-impactful (source matches translation)
                            critical = [r for r in xml_integrity_report if not r.get('reason', '').startswith('Warning:')]
                            non_impact = [r for r in xml_integrity_report if r.get('reason', '').startswith('Warning:')]
                            if critical:
                                logger.warning(f"  WARNING: {len(critical)} integrity issue(s) in {fname}")
                                for r in critical[:10]:
                                    sid = r.get('string_id') or '(empty)'
                                    logger.warning(f"    [{r.get('column', '?')}] StringID={sid}: {r.get('reason', '?')}")
                                if len(critical) > 10:
                                    logger.warning(f"    ...and {len(critical) - 10} more")
                                issues.append(f"{len(critical)} integrity")
                            # non-impact: tracked but not logged per-file (source=translation, not real issue)
                            all_integrity_warnings.extend(xml_integrity_report)

                        if xml_no_translation_report:
                            issues.append(f"{len(xml_no_translation_report)} no-translation")

                        status = f"{count} entries"
                        if issues:
                            status += f" ({', '.join(issues)})"

                        logger.info(f"  OK   [{lang}] {fname} — {status}")
                        total_ok += 1
                        total_entries += count

                    elif suffix in ('.xlsx', '.xls'):
                        # ── Excel validation (same as Tab 1) ──
                        try:
                            formula_report = []
                            integrity_report = []
                            no_translation_report = []
                            entries = read_corrections_from_excel(
                                filepath,
                                formula_report=formula_report,
                                integrity_report=integrity_report,
                                no_translation_report=no_translation_report,
                            )
                            count = len(entries) if entries else 0

                            issues = []
                            if formula_report:
                                logger.warning(f"  WARNING: {len(formula_report)} formula cell(s) in {fname}")
                                for r in formula_report[:10]:
                                    sid = r.get('string_id') or '(empty)'
                                    logger.warning(f"    Row {r.get('row', '?')} [{r.get('column', '?')}] StringID={sid}: {r.get('reason', '?')}")
                                if len(formula_report) > 10:
                                    logger.warning(f"    ...and {len(formula_report) - 10} more")
                                issues.append(f"{len(formula_report)} formula")
                                all_formula_warnings.extend(formula_report)
                            if integrity_report:
                                critical = [r for r in integrity_report if not r.get('reason', '').startswith('Warning:')]
                                if critical:
                                    logger.warning(f"  WARNING: {len(critical)} integrity issue(s) in {fname}")
                                    for r in critical[:10]:
                                        sid = r.get('string_id') or '(empty)'
                                        logger.warning(f"    Row {r.get('row', '?')} [{r.get('column', '?')}] StringID={sid}: {r.get('reason', '?')}")
                                    if len(critical) > 10:
                                        logger.warning(f"    ...and {len(critical) - 10} more")
                                    issues.append(f"{len(critical)} integrity")
                                all_integrity_warnings.extend(integrity_report)
                            if no_translation_report:
                                issues.append(f"{len(no_translation_report)} no-translation")

                            # EventName detection
                            has_eventname = any(e.get('_source_eventname') for e in entries) if entries else False
                            has_stringid = any(e.get('string_id') for e in entries) if entries else False
                            if has_eventname and not has_stringid:
                                issues.append("EventName only — resolution needed")
                            elif has_eventname:
                                issues.append("EventName+StringID")

                            status = f"{count} entries"
                            if issues:
                                status += f" ({', '.join(issues)})"

                            logger.info(f"  OK   [{lang}] {fname} — {status}")
                            total_ok += 1
                            total_entries += count

                        except ValueError as e:
                            logger.error(f"  FAIL [{lang}] {fname} — {e}")
                            total_fail += 1
                        except Exception as e:
                            logger.error(f"  FAIL [{lang}] {fname} — {e}")
                            total_fail += 1

                # Summary
                logger.info("-" * 50)
                logger.info(f"[TMX Validate] {total_ok} OK, {total_fail} FAILED, {total_entries} total entries")
                if all_formula_warnings:
                    logger.warning(f"  Total formula warnings: {len(all_formula_warnings)}")
                if all_integrity_warnings:
                    critical_total = sum(1 for r in all_integrity_warnings if not r.get('reason', '').startswith('Warning:'))
                    if critical_total:
                        logger.warning(f"  Total integrity issues: {critical_total}")
                logger.info("=" * 50)
            finally:
                self._detach_log_bridge()

        threading.Thread(target=_validate, daemon=True).start()

    def _on_convert(self):
        path = self._path_var.get()
        if not path:
            messagebox.showwarning("No Path",
                                   "Please select a file or folder first.")
            return

        def _run():
            self._attach_log_bridge()
            try:
                results = convert_to_memoq_tmx(path)
                if not results:
                    msg = (
                        "No languages detected -- nothing to convert.\n"
                        "Make sure files/folders have language suffixes "
                        "(e.g. FRE/, corrections_GER.xml)"
                    )
                    self.after(0, lambda: messagebox.showwarning(
                        "No Languages", msg))
                    return
                summary = []
                for lang, out, ok in results:
                    status = "OK" if ok else "FAILED"
                    summary.append(f"{lang}: {status}")
                msg = ("MemoQ-TMX conversion complete:\n\n"
                       + "\n".join(summary))
                created = [out for _, out, ok in results if ok]
                if created:
                    msg += (f"\n\nFiles created in:\n"
                            f"{os.path.dirname(created[0])}")
                self.after(0, lambda: messagebox.showinfo(
                    "MemoQ-TMX Complete", msg))
            except Exception as exc:
                err_msg = str(exc)
                logger.error("[TMX] Conversion failed: %s", err_msg,
                             exc_info=True)
                self.after(0, lambda em=err_msg: messagebox.showerror(
                    "TMX Error", f"Failed: {em}"))
            finally:
                self._detach_log_bridge()

        threading.Thread(target=_run, daemon=True).start()

    # ------------------------------------------------------------------
    # Section 2: TMX Cleaner -> Excel
    # ------------------------------------------------------------------
    def _on_clean_to_excel(self):
        fpath = filedialog.askopenfilename(
            title="Select TMX file to clean and convert to Excel",
            filetypes=[("TMX files", "*.tmx"), ("All files", "*.*")]
        )
        if not fpath:
            return

        def _run():
            self._attach_log_bridge()
            try:
                out = clean_and_convert_to_excel(fpath)
                self.after(0, lambda: messagebox.showinfo(
                    "TMX Cleaner", f"Excel exported:\n{out}"))
            except Exception as exc:
                err_msg = str(exc)
                logger.error("[TMX Cleaner] Failed: %s", err_msg,
                             exc_info=True)
                self.after(0, lambda em=err_msg: messagebox.showerror(
                    "TMX Cleaner Error", f"Failed: {em}"))
            finally:
                self._detach_log_bridge()

        threading.Thread(target=_run, daemon=True).start()

    # ------------------------------------------------------------------
    # Section 3: Excel -> MemoQ-TMX
    # ------------------------------------------------------------------
    def _on_excel_to_tmx(self):
        fpath = filedialog.askopenfilename(
            title="Select Excel file to convert to MemoQ-TMX",
            filetypes=[("Excel files", "*.xlsx;*.xls"), ("All files", "*.*")]
        )
        if not fpath:
            return

        def _run():
            self._attach_log_bridge()
            try:
                out = excel_to_memoq_tmx(fpath)
                self.after(0, lambda: messagebox.showinfo(
                    "Excel to TMX", f"MemoQ-TMX created:\n{out}"))
            except Exception as exc:
                err_msg = str(exc)
                logger.error("[Excel to TMX] Failed: %s", err_msg,
                             exc_info=True)
                self.after(0, lambda em=err_msg: messagebox.showerror(
                    "Excel to TMX Error", f"Failed: {em}"))
            finally:
                self._detach_log_bridge()

        threading.Thread(target=_run, daemon=True).start()
