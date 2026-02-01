import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk, simpledialog
import os
import xml.etree.ElementTree as ET
from collections import defaultdict
import hashlib
from datetime import datetime
import threading

class TranslationComparer:
    def __init__(self, root):
        self.root = root
        self.root.title("Translation Files Comparer - Multi-Folder Support")
        self.root.geometry("1000x800")

        self.source_folders = []
        self.target_folders = []

        # Create main frame
        main_frame = tk.Frame(root, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Source folders selection
        source_frame = tk.Frame(main_frame)
        source_frame.pack(fill=tk.X, pady=10)

        tk.Label(source_frame, text="Source Folders:", font=("Arial", 10, "bold")).pack(anchor=tk.W)

        # Source folders listbox with scrollbar
        source_list_frame = tk.Frame(source_frame)
        source_list_frame.pack(fill=tk.X, pady=5)

        source_scrollbar = tk.Scrollbar(source_list_frame)
        source_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.source_listbox = tk.Listbox(source_list_frame, height=4, yscrollcommand=source_scrollbar.set)
        self.source_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        source_scrollbar.config(command=self.source_listbox.yview)

        source_buttons_frame = tk.Frame(source_frame)
        source_buttons_frame.pack(fill=tk.X)
        tk.Button(source_buttons_frame, text="Select Source Folders",
                  command=self.select_source_folders, bg="#2196F3", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(source_buttons_frame, text="Clear All", command=self.clear_source_folders).pack(side=tk.LEFT, padx=5)

        # Target folders selection
        target_frame = tk.Frame(main_frame)
        target_frame.pack(fill=tk.X, pady=10)

        tk.Label(target_frame, text="Target Folders:", font=("Arial", 10, "bold")).pack(anchor=tk.W)

        # Target folders listbox with scrollbar
        target_list_frame = tk.Frame(target_frame)
        target_list_frame.pack(fill=tk.X, pady=5)

        target_scrollbar = tk.Scrollbar(target_list_frame)
        target_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.target_listbox = tk.Listbox(target_list_frame, height=4, yscrollcommand=target_scrollbar.set)
        self.target_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        target_scrollbar.config(command=self.target_listbox.yview)

        target_buttons_frame = tk.Frame(target_frame)
        target_buttons_frame.pack(fill=tk.X)
        tk.Button(target_buttons_frame, text="Select Target Folders",
                  command=self.select_target_folders, bg="#2196F3", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(target_buttons_frame, text="Clear All", command=self.clear_target_folders).pack(side=tk.LEFT, padx=5)

        # Compare button
        tk.Button(main_frame, text="Compare All Combinations", command=self.start_comparison,
                  bg="#4CAF50", fg="white", font=("Arial", 12), pady=10).pack(pady=(20, 5))

        # Export Differences as XML
        tk.Button(main_frame, text="Export Differences as XML", command=self.start_export_differences_xml,
                  bg="#FF9800", fg="white", font=("Arial", 12), pady=10).pack(pady=(0, 20))

        # Check Duplicates   
        tk.Button(main_frame, text="Check Duplicates Between Source and Target",
                  command=self.start_check_duplicates,
                  bg="#E91E63", fg="white", font=("Arial", 12), pady=10).pack(pady=(0, 20))                  
                  
        # Check Translation Changes   
        tk.Button(main_frame,
                  text="Check Translation Changes",
                  command=self.start_check_translation_changes,
                  bg="#9C27B0", fg="white", font=("Arial", 12), pady=10).pack(pady=(0, 20))


                  
        # Progress frame
        progress_frame = tk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=5)

        self.progress_label = tk.Label(progress_frame, text="Ready to compare")
        self.progress_label.pack(anchor=tk.W)

        self.progress = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress.pack(fill=tk.X, pady=5)

        # Output text area
        tk.Label(main_frame, text="Current Comparison:").pack(anchor=tk.W)
        self.output_text = scrolledtext.ScrolledText(main_frame, height=20, width=100)
        self.output_text.pack(fill=tk.BOTH, expand=True, pady=10)

    def select_source_folders(self):
        root = tk.Tk()
        root.withdraw()
        root.call('wm', 'attributes', '.', '-topmost', True)
        folders = filedialog.askdirectory(title="Select Source Folders (use Ctrl+Click for multiple)")
        root.destroy()

        if folders:
            parent_dir = folders
            self.source_folders = []
            self.source_listbox.delete(0, tk.END)
            self.show_folder_selection_dialog(parent_dir, is_source=True)

    def select_target_folders(self):
        root = tk.Tk()
        root.withdraw()
        root.call('wm', 'attributes', '.', '-topmost', True)
        folders = filedialog.askdirectory(title="Select Target Folders (use Ctrl+Click for multiple)")
        root.destroy()

        if folders:
            parent_dir = folders
            self.target_folders = []
            self.target_listbox.delete(0, tk.END)
            self.show_folder_selection_dialog(parent_dir, is_source=False)

    def show_folder_selection_dialog(self, parent_dir, is_source):
        subdirs = []
        for item in os.listdir(parent_dir):
            item_path = os.path.join(parent_dir, item)
            if os.path.isdir(item_path):
                subdirs.append((item, item_path))

        if not subdirs:
            messagebox.showwarning("No Folders", "No subdirectories found in the selected directory.")
            return

        selection_window = tk.Toplevel(self.root)
        selection_window.title("Select Folders (Ctrl+Click for multiple)")
        selection_window.geometry("500x600")

        tk.Label(selection_window, text="Select folders:", font=("Arial", 10, "bold")).pack(pady=10)

        list_frame = tk.Frame(selection_window)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED, yscrollcommand=scrollbar.set)
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=listbox.yview)

        folder_map = {}
        for name, path in sorted(subdirs):
            listbox.insert(tk.END, name)
            folder_map[listbox.size() - 1] = path

        def on_confirm():
            selections = listbox.curselection()
            if is_source:
                self.source_folders = []
                self.source_listbox.delete(0, tk.END)
                for idx in selections:
                    folder_path = folder_map[idx]
                    self.source_folders.append(folder_path)
                    folder_name = os.path.basename(folder_path)
                    self.source_listbox.insert(tk.END, f"{folder_name} - {folder_path}")
            else:
                self.target_folders = []
                self.target_listbox.delete(0, tk.END)
                for idx in selections:
                    folder_path = folder_map[idx]
                    self.target_folders.append(folder_path)
                    folder_name = os.path.basename(folder_path)
                    self.target_listbox.insert(tk.END, f"{folder_name} - {folder_path}")
            selection_window.destroy()

        def on_select_all():
            listbox.select_set(0, tk.END)

        button_frame = tk.Frame(selection_window)
        button_frame.pack(pady=10)

        tk.Button(button_frame, text="Select All", command=on_select_all).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Confirm", command=on_confirm,
                  bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Cancel", command=selection_window.destroy).pack(side=tk.LEFT, padx=5)

    def clear_source_folders(self):
        self.source_listbox.delete(0, tk.END)
        self.source_folders = []

    def clear_target_folders(self):
        self.target_listbox.delete(0, tk.END)
        self.target_folders = []

    def create_row_signature(self, element):
        str_origin = element.get('StrOrigin', '')
        string_id = element.get('StringId', '')
        signature = f"StrOrigin={str_origin}|StringId={string_id}"
        return hashlib.md5(signature.encode()).hexdigest()

    def get_file_display_path(self, file_identifier, file_paths_map):
        if file_identifier in file_paths_map:
            rel_path = file_paths_map[file_identifier]
            path_parts = rel_path.split(os.sep)
            if len(path_parts) > 2:
                grandparent = path_parts[-3]
                parent = path_parts[-2]
                filename = path_parts[-1]
                return f"{grandparent}/{parent}/{filename}"
            elif len(path_parts) > 1:
                parent = path_parts[-2]
                filename = path_parts[-1]
                return f"{parent}/{filename}"
            else:
                return path_parts[0]
        return file_identifier

    def find_subset_files(self, folder_path):
        file_signatures = {}
        file_paths = {}

        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith('.xml'):
                    full_path = os.path.join(root, file)
                    try:
                        tree = ET.parse(full_path)
                        xml_root = tree.getroot()
                        file_identifier = xml_root.get('FileName', os.path.relpath(full_path, folder_path))
                        relative_path = os.path.relpath(full_path, folder_path)
                        file_paths[file_identifier] = relative_path
                        signatures = set()
                        for element in xml_root.findall('.//LocStr'):
                            signature = self.create_row_signature(element)
                            signatures.add(signature)
                        if signatures:
                            file_signatures[file_identifier] = signatures
                    except Exception as e:
                        print(f"Error reading {full_path}: {str(e)}")

        subset_files = set()
        subset_relationships = []

        for file1, sigs1 in file_signatures.items():
            if file1 in subset_files:
                continue
            for file2, sigs2 in file_signatures.items():
                if file1 == file2 or file2 in subset_files:
                    continue
                if len(sigs1) < len(sigs2):
                    common_sigs = sigs1 & sigs2
                    if len(sigs1) > 0:
                        overlap_percentage = len(common_sigs) / len(sigs1) * 100
                        if overlap_percentage >= 20:
                            subset_files.add(file1)
                            subset_relationships.append({
                                'subset': self.get_file_display_path(file1, file_paths),
                                'superset': self.get_file_display_path(file2, file_paths),
                                'overlap': overlap_percentage,
                                'subset_size': len(sigs1),
                                'superset_size': len(sigs2)
                            })
                            break

        return subset_files, subset_relationships

    def build_mega_table(self, folder_path, excluded_files=None):
        if excluded_files is None:
            excluded_files = set()

        mega_table = {}
        file_signatures = defaultdict(set)
        file_row_count = defaultdict(int)
        file_paths = {}

        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith('.xml'):
                    full_path = os.path.join(root, file)
                    try:
                        tree = ET.parse(full_path)
                        xml_root = tree.getroot()
                        file_identifier = xml_root.get('FileName', os.path.relpath(full_path, folder_path))
                        relative_path = os.path.relpath(full_path, folder_path)
                        file_paths[file_identifier] = relative_path
                        if file_identifier in excluded_files:
                            continue
                        for idx, element in enumerate(xml_root.findall('.//LocStr')):
                            signature = self.create_row_signature(element)
                            if signature not in mega_table:
                                mega_table[signature] = []
                            mega_table[signature].append({
                                'file': file_identifier,
                                'element': element,
                                'index': idx
                            })
                            file_signatures[file_identifier].add(signature)
                            file_row_count[file_identifier] += 1
                    except Exception as e:
                        pass

        return mega_table, file_signatures, file_row_count, file_paths

    def compare_single_pair(self, source_folder, target_folder):
        report_lines = []

        source_name = os.path.basename(source_folder)
        target_name = os.path.basename(target_folder)

        source_subsets, source_relationships = self.find_subset_files(source_folder)
        target_subsets, target_relationships = self.find_subset_files(target_folder)

        if source_subsets or target_subsets:
            report_lines.append("SUBSET FILES DETECTED AND EXCLUDED:")
            report_lines.append("-" * 60)
            if source_relationships:
                report_lines.append(f"\nIn {source_name}:")
                for rel in source_relationships:
                    report_lines.append(
                        f"  - \"{rel['subset']}\" is a subset of \"{rel['superset']}\" "
                        f"({rel['overlap']:.1f}% overlap, {rel['subset_size']} vs {rel['superset_size']} rows)")
            if target_relationships:
                report_lines.append(f"\nIn {target_name}:")
                for rel in target_relationships:
                    report_lines.append(
                        f"  - \"{rel['subset']}\" is a subset of \"{rel['superset']}\" "
                        f"({rel['overlap']:.1f}% overlap, {rel['subset_size']} vs {rel['superset_size']} rows)")
            report_lines.append("")

        source_table, source_file_sigs, source_file_counts, source_file_paths = self.build_mega_table(
            source_folder, source_subsets)
        target_table, target_file_sigs, target_file_counts, target_file_paths = self.build_mega_table(
            target_folder, target_subsets)

        source_signatures = set(source_table.keys())
        target_signatures = set(target_table.keys())

        missing_signatures = source_signatures - target_signatures
        extra_signatures = target_signatures - source_signatures

        file_missing_details = defaultdict(list)
        file_extra_details = defaultdict(list)

        for sig in missing_signatures:
            for occurrence in source_table[sig]:
                element = occurrence['element']
                str_origin = element.get('StrOrigin', '')
                string_id = element.get('StringId', '')
                file_missing_details[occurrence['file']].append({
                    'StrOrigin': str_origin,
                    'StringId': string_id
                })

        for sig in extra_signatures:
            for occurrence in target_table[sig]:
                element = occurrence['element']
                str_origin = element.get('StrOrigin', '')
                string_id = element.get('StringId', '')
                file_extra_details[occurrence['file']].append({
                    'StrOrigin': str_origin,
                    'StringId': string_id
                })

        completely_missing_files = []
        partially_missing_files = {}

        for file, missing_details in file_missing_details.items():
            total_rows = source_file_counts.get(file, 0)
            if total_rows > 0 and len(missing_details) == total_rows:
                display_path = self.get_file_display_path(file, source_file_paths)
                completely_missing_files.append((display_path, total_rows))
            else:
                partially_missing_files[file] = {
                    'missing_details': missing_details,
                    'total': total_rows
                }

        completely_extra_files = []
        partially_extra_files = {}

        for file, extra_details in file_extra_details.items():
            if file not in source_file_sigs:
                display_path = self.get_file_display_path(file, target_file_paths)
                completely_extra_files.append((display_path, len(extra_details)))
            else:
                partially_extra_files[file] = extra_details

        report_lines.append(f"COMPARISON REPORT - {target_name} compared to {source_name}:")
        report_lines.append("=" * 80)
        report_lines.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"Source folder: {source_folder}")
        report_lines.append(f"Target folder: {target_folder}")
        report_lines.append(f"(Excluded {len(source_subsets)} subset files from source, "
                            f"{len(target_subsets)} from target)\n")

        differences_found = bool(completely_missing_files or completely_extra_files or
                                 partially_missing_files or partially_extra_files)

        if not differences_found:
            report_lines.append("✓ No differences found! The folders have identical structure.")
        else:
            if completely_missing_files:
                report_lines.append(f"COMPLETELY MISSING FILES IN TARGET ({len(completely_missing_files)}):")
                for file_path, row_count in sorted(completely_missing_files):
                    report_lines.append(f"  File : \"{file_path}\" is completely missing ({row_count} rows)")
                report_lines.append("")

            if completely_extra_files:
                report_lines.append(f"COMPLETELY EXTRA FILES IN TARGET ({len(completely_extra_files)}):")
                for file_path, row_count in sorted(completely_extra_files):
                    report_lines.append(f"  File : \"{file_path}\" exists only in target ({row_count} rows)")
                report_lines.append("")

            all_files_with_diffs = set(partially_missing_files.keys()) | set(partially_extra_files.keys())

            if all_files_with_diffs:
                report_lines.append(f"FILES WITH DIFFERENCES ({len(all_files_with_diffs)}):")
                report_lines.append("=" * 80)

                for file in sorted(all_files_with_diffs):
                    display_path = self.get_file_display_path(
                        file,
                        source_file_paths if file in source_file_paths else target_file_paths
                    )

                    report_lines.append(f"\nFile: \"{display_path}\"")
                    report_lines.append("-" * 60)

                    if file in partially_missing_files:
                        missing_details = partially_missing_files[file]['missing_details']
                        report_lines.append(f"  MISSING ROWS ({len(missing_details)} rows missing in target):")
                        for detail in missing_details[:10]:
                            report_lines.append(f"    - StrOrigin: \"{detail['StrOrigin']}\", StringId: \"{detail['StringId']}\"")
                        if len(missing_details) > 10:
                            report_lines.append(f"    ... and {len(missing_details) - 10} more missing rows")

                    if file in partially_extra_files:
                        extra_details = partially_extra_files[file]
                        report_lines.append(f"  EXTRA ROWS ({len(extra_details)} rows extra in target):")
                        for detail in extra_details[:10]:
                            report_lines.append(f"    - StrOrigin: \"{detail['StrOrigin']}\", StringId: \"{detail['StringId']}\"")
                        if len(extra_details) > 10:
                            report_lines.append(f"    ... and {len(extra_details) - 10} more extra rows")

            report_lines.append(f"\n\nTOTAL STATISTICS:")
            report_lines.append(f"  - Source total rows: {len(source_signatures)}")
            report_lines.append(f"  - Target total rows: {len(target_signatures)}")
            report_lines.append(f"  - Missing rows: {len(missing_signatures)}")
            report_lines.append(f"  - Extra rows: {len(extra_signatures)}")
            report_lines.append(f"  - Completely missing files: {len(completely_missing_files)}")
            report_lines.append(f"  - Completely extra files: {len(completely_extra_files)}")
            report_lines.append(f"  - Files with partial differences: {len(all_files_with_diffs)}")

        return "\n".join(report_lines), differences_found

    def start_comparison(self):
        if not self.source_folders or not self.target_folders:
            messagebox.showerror("Error", "Please select at least one source and one target folder")
            return

        thread = threading.Thread(target=self.run_comparisons)
        thread.start()

    def run_comparisons(self):
        total_comparisons = len(self.source_folders) * len(self.target_folders)
        comparison_count = 0

        script_dir = os.path.dirname(os.path.abspath(__file__))

        for source_folder in self.source_folders:
            source_name = os.path.basename(source_folder)
            report_folder = os.path.join(script_dir, f"Source_{source_name}_compare")

            if not os.path.exists(report_folder):
                os.makedirs(report_folder)

            for target_folder in self.target_folders:
                comparison_count += 1
                target_name = os.path.basename(target_folder)

                self.progress['value'] = (comparison_count / total_comparisons) * 100
                self.progress_label.config(text=f"Comparing {source_name} to {target_name} ({comparison_count}/{total_comparisons})")
                self.output_text.delete(1.0, tk.END)
                self.output_text.insert(tk.END, f"Processing: {source_name} → {target_name}\n")
                self.root.update()

                report_content, has_differences = self.compare_single_pair(source_folder, target_folder)

                self.output_text.insert(tk.END, "\n" + report_content)
                self.root.update()

                report_filename = f"{target_name}_report.txt"
                report_path = os.path.join(report_folder, report_filename)

                with open(report_path, 'w', encoding='utf-8') as f:
                    f.write(report_content)

                self.output_text.insert(tk.END, f"\n\nReport saved to: {report_path}\n")
                self.root.update()

        self.progress['value'] = 100
        self.progress_label.config(text="All comparisons completed!")
        messagebox.showinfo("Completed", f"All {total_comparisons} comparisons have been completed.\n"
                                         f"Reports saved in respective Source_*_compare folders.")

    # ------------------- NEW FUNCTIONALITY BELOW -------------------

    def start_export_differences_xml(self):
        if not self.source_folders or not self.target_folders:
            messagebox.showerror("Error", "Please select at least one source and one target folder")
            return

        # Only allow one-to-one for this operation for clarity
        if len(self.source_folders) != 1 or len(self.target_folders) != 1:
            messagebox.showerror("Error", "Please select exactly one source and one target folder for XML export.")
            return

        # Ask for output XML file name
        default_name = "EN_temp_translations"
        file_name = simpledialog.askstring("Output XML Name",
                                           "Enter the output XML file name (without .xml):",
                                           initialvalue=default_name,
                                           parent=self.root)
        if not file_name:
            return

        # Ask for save location
        save_path = filedialog.asksaveasfilename(
            title="Save XML File",
            defaultextension=".xml",
            filetypes=[("XML files", "*.xml")],
            initialfile=f"{file_name}.xml"
        )
        if not save_path:
            return

        # Run in thread to keep UI responsive
        thread = threading.Thread(target=self.export_differences_xml, args=(self.source_folders[0], self.target_folders[0], file_name, save_path))
        thread.start()

    def export_differences_xml(self, source_folder, target_folder, file_name, save_path):
        from lxml import etree

        self.progress_label.config(text="Exporting differences as XML...")
        self.progress['value'] = 0
        self.output_text.delete(1.0, tk.END)
        self.output_text.insert(tk.END, f"Exporting differences from:\nSource: {source_folder}\nTarget: {target_folder}\n\n")
        self.root.update()

        # Find subset files (exclude them)
        source_subsets, _ = self.find_subset_files(source_folder)
        target_subsets, _ = self.find_subset_files(target_folder)

        # Build mega tables
        source_table, _, _, _ = self.build_mega_table(source_folder, source_subsets)
        target_table, _, _, _ = self.build_mega_table(target_folder, target_subsets)

        source_signatures = set(source_table.keys())
        target_signatures = set(target_table.keys())
        missing_signatures = source_signatures - target_signatures

        # Gather all missing LocStr elements
        all_missing_locstrs = []
        for sig in missing_signatures:
            for occurrence in source_table[sig]:
                element = occurrence['element']
                all_missing_locstrs.append(element)

        # Build the output XML: all LocStrs directly under <root>
        output_root = etree.Element("root", FileName=f"{file_name}.xml")
        total_locstrs = len(all_missing_locstrs)

        for idx, loc in enumerate(all_missing_locstrs):
            # Deep copy LocStr using lxml
            loc_xml = ET.tostring(loc, encoding="utf-8")
            loc_elem = etree.fromstring(loc_xml)
            output_root.append(loc_elem)
            # Progress update
            if (idx + 1) % 100 == 0 or (idx + 1) == total_locstrs:
                self.progress['value'] = ((idx + 1) / total_locstrs) * 100
                self.root.update()

        # Write to file (NO XML declaration)
        try:
            xml_bytes = etree.tostring(output_root, pretty_print=True, encoding='UTF-8', xml_declaration=False)
            with open(save_path, "wb") as f:
                f.write(xml_bytes)
            self.output_text.insert(tk.END, f"Exported {total_locstrs} differing rows to:\n{save_path}\n")
            self.progress['value'] = 100
            self.progress_label.config(text="Export completed!")
            print(f"[Console] Exported {total_locstrs} differing rows to: {save_path}")
            messagebox.showinfo("Export Completed", f"Exported {total_locstrs} differing rows to:\n{save_path}")
        except Exception as e:
            self.output_text.insert(tk.END, f"Error writing XML: {e}\n")
            self.progress_label.config(text="Export failed!")
            print(f"[Console] Error writing XML: {e}")
            messagebox.showerror("Export Failed", f"Error writing XML: {e}")


    def start_check_duplicates(self):
        if not self.source_folders or not self.target_folders:
            messagebox.showerror("Error", "Please select at least one source and one target folder")
            return

        # Only allow one-to-one for this operation for clarity
        if len(self.source_folders) != 1 or len(self.target_folders) != 1:
            messagebox.showerror("Error", "Please select exactly one source and one target folder for duplicate check.")
            return

        thread = threading.Thread(target=self.check_duplicates_between_source_target)
        thread.start()

    def check_duplicates_between_source_target(self):
        self.progress_label.config(text="Checking for duplicates with differing Str values...")
        self.progress['value'] = 0
        self.output_text.delete(1.0, tk.END)
        self.root.update()

        source_folder = self.source_folders[0]
        target_folder = self.target_folders[0]

        def collect_entries(folder_path):
            # Map: (StrOrigin, StringId) -> list of dicts
            entries = defaultdict(list)
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file.lower().endswith('.xml'):
                        full_path = os.path.join(root, file)
                        try:
                            tree = ET.parse(full_path)
                            xml_root = tree.getroot()
                            file_identifier = xml_root.get('FileName', os.path.relpath(full_path, folder_path))
                            rel_path = os.path.relpath(full_path, folder_path)
                            for idx, element in enumerate(xml_root.findall('.//LocStr')):
                                str_origin = element.get('StrOrigin', '')
                                string_id = element.get('StringId', '')
                                str_val = element.get('Str', '')
                                # Skip if StrOrigin is empty or StrOrigin == Str
                                if not str_origin or str_origin == str_val:
                                    continue
                                key = (str_origin, string_id)
                                entries[key].append({
                                    'file': file_identifier,
                                    'rel_path': rel_path,
                                    'StringId': string_id,
                                    'StrOrigin': str_origin,
                                    'Str': str_val
                                })
                        except Exception as e:
                            pass
            return entries

        src_entries = collect_entries(source_folder)
        tgt_entries = collect_entries(target_folder)

        # Only consider keys present in both
        common_keys = set(src_entries.keys()) & set(tgt_entries.keys())

        report_lines = []
        report_lines.append("DUPLICATES WITH DIFFERENT Str VALUES (StrOrigin+StringId match, Str differs)")
        report_lines.append("=" * 80)
        report_lines.append(f"Source folder: {source_folder}")
        report_lines.append(f"Target folder: {target_folder}")
        report_lines.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        count = 0
        for key in sorted(common_keys):
            src_list = src_entries[key]
            tgt_list = tgt_entries[key]
            # Compare all source-target pairs for this key
            for src in src_list:
                for tgt in tgt_list:
                    if src['Str'] != tgt['Str']:
                        count += 1
                        report_lines.append(f"File : {src['rel_path']}")
                        report_lines.append(f"Source : StrOrigin=\"{src['StrOrigin']}\", StringId=\"{src['StringId']}\", Str=\"{src['Str']}\"")
                        report_lines.append(f"Target : StrOrigin=\"{tgt['StrOrigin']}\", StringId=\"{tgt['StringId']}\", Str=\"{tgt['Str']}\"")
                        report_lines.append("")  # Blank line between entries

        if count == 0:
            report_lines.append("✓ No duplicates found with different Str values for identical StrOrigin+StringId.")

        # Output to GUI
        self.output_text.delete(1.0, tk.END)
        self.output_text.insert(tk.END, "\n".join(report_lines))
        self.progress['value'] = 100
        self.progress_label.config(text="Duplicate check completed!")
        self.root.update()

        # Save to file
        script_dir = os.path.dirname(os.path.abspath(__file__))
        src_name = os.path.basename(source_folder)
        tgt_name = os.path.basename(target_folder)
        report_folder = os.path.join(script_dir, f"Source_{src_name}_compare")
        if not os.path.exists(report_folder):
            os.makedirs(report_folder)
        report_path = os.path.join(report_folder, f"{tgt_name}_str_diff_duplicates_report.txt")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))
        self.output_text.insert(tk.END, f"\n\nReport saved to: {report_path}\n")
        messagebox.showinfo("Duplicate Check Completed", f"Duplicate check completed.\nReport saved to:\n{report_path}")
            
    def start_check_translation_changes(self):
        """
        GUI-entry method. Ensures exactly ONE source and ONE target folder are selected,
        then spawns a thread that runs the heavy comparison.
        """
        if not self.source_folders or not self.target_folders:
            messagebox.showerror("Error", "Please select at least one source and one target folder")
            return

        if len(self.source_folders) != 1 or len(self.target_folders) != 1:
            messagebox.showerror("Error",
                                 "Please select exactly one source and one target folder for translation-change check.")
            return

        thread = threading.Thread(target=self.check_translation_changes_between_source_target)
        thread.start()

    def check_translation_changes_between_source_target(self):
        """
        Compare source vs target (1-to-1) and list every LocStr where
        StrOrigin & StringId are identical BUT Str value differs.
        This reveals actual translation changes between versions.
        """
        self.progress_label.config(text="Checking for translation (Str) changes...")
        self.progress['value'] = 0
        self.output_text.delete(1.0, tk.END)
        self.root.update()

        source_folder = self.source_folders[0]
        target_folder = self.target_folders[0]

        def collect_entries(folder_path):
            """
            Returns a mapping:
                file_identifier -> { (StrOrigin, StringId): Str }
            """
            file_map = {}
            for root_dir, dirs, files in os.walk(folder_path):
                for file in files:
                    if not file.lower().endswith(".xml"):
                        continue
                    full_path = os.path.join(root_dir, file)
                    try:
                        tree = ET.parse(full_path)
                        xml_root = tree.getroot()
                        file_identifier = xml_root.get('FileName', os.path.relpath(full_path, folder_path))
                        inner_map = {}
                        for element in xml_root.findall('.//LocStr'):
                            str_origin = element.get('StrOrigin', '')
                            string_id = element.get('StringId', '')
                            str_val = element.get('Str', '')
                            key = (str_origin, string_id)
                            inner_map[key] = str_val
                        file_map[file_identifier] = inner_map
                    except Exception:
                        continue
            return file_map

        src_files = collect_entries(source_folder)
        tgt_files = collect_entries(target_folder)

        # Determine common files (by FileName / identifier) to compare
        common_files = set(src_files.keys()) & set(tgt_files.keys())

        total_files = len(common_files)
        processed_files = 0

        report_lines = []
        report_lines.append("TRANSLATION (Str) CHANGES REPORT")
        report_lines.append("=" * 80)
        report_lines.append(f"Source folder: {source_folder}")
        report_lines.append(f"Target folder: {target_folder}")
        report_lines.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("Only entries where StrOrigin and StringId are identical but Str value differs are listed.\n")

        total_changes = 0

        for file_id in sorted(common_files):
            processed_files += 1
            # Progress bar update
            self.progress['value'] = (processed_files / total_files) * 100
            self.progress_label.config(text=f"Processing ({processed_files}/{total_files}) : {file_id}")
            self.root.update()

            src_dict = src_files[file_id]
            tgt_dict = tgt_files[file_id]

            common_keys = set(src_dict.keys()) & set(tgt_dict.keys())
            # Collect row differences
            diffs = []
            for key in common_keys:
                src_str = src_dict[key]
                tgt_str = tgt_dict[key]
                if src_str != tgt_str:
                    diffs.append({
                        'StrOrigin': key[0],
                        'StringId': key[1],
                        'SourceStr': src_str,
                        'TargetStr': tgt_str
                    })

            if diffs:
                total_changes += len(diffs)
                report_lines.append(f"File : \"{file_id}\"")
                report_lines.append(f"  Modified rows : {len(diffs)}")
                for d in diffs[:10]:  # show only first 10 per file for brevity
                    report_lines.append(f"    - StrOrigin=\"{d['StrOrigin']}\"  "
                                        f"StringId=\"{d['StringId']}\"")
                    report_lines.append(f"        Source Str : \"{d['SourceStr']}\"")
                    report_lines.append(f"        Target Str : \"{d['TargetStr']}\"")
                if len(diffs) > 10:
                    report_lines.append(f"    ... and {len(diffs)-10} more changes")
                report_lines.append("")

        if total_changes == 0:
            report_lines.append("✓ No translation (Str) changes detected between the two folders.")

        report_lines.append("\nSUMMARY")
        report_lines.append("-" * 80)
        report_lines.append(f"Total files compared : {total_files}")
        report_lines.append(f"Total Str changes    : {total_changes}")

        # Output to GUI
        self.output_text.delete(1.0, tk.END)
        self.output_text.insert(tk.END, "\n".join(report_lines))
        self.progress['value'] = 100
        self.progress_label.config(text="Translation change check completed!")
        self.root.update()

        # Save to disk
        script_dir = os.path.dirname(os.path.abspath(__file__))
        src_name = os.path.basename(source_folder)
        tgt_name = os.path.basename(target_folder)
        report_folder = os.path.join(script_dir, f"Source_{src_name}_compare")
        if not os.path.exists(report_folder):
            os.makedirs(report_folder)
        report_path = os.path.join(report_folder, f"{tgt_name}_translation_changes_report.txt")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))

        self.output_text.insert(tk.END, f"\n\nReport saved to: {report_path}\n")
        messagebox.showinfo("Translation Change Check",
                            f"Translation change check completed.\nReport saved to:\n{report_path}")            

def main():
    root = tk.Tk()
    app = TranslationComparer(root)
    root.mainloop()

if __name__ == "__main__":
    main()