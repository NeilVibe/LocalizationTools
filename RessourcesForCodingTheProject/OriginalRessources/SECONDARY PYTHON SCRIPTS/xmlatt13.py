import re
import os
import time
import lxml.etree as ET
import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk, Checkbutton, IntVar
from collections import defaultdict
import threading
from datetime import datetime
import io
import sys
import json
from pathlib import Path
import traceback

# ------------------------------------------------------------
# XML reading + sanitizing
# ------------------------------------------------------------
def fix_bad_entities(xml_text):
    # Escape any bare & not part of a known entity
    return re.sub(r'&(?!lt;|gt;|amp;|apos;|quot;)', '&amp;', xml_text)

def parse_xml_file(file_path):
    """Read, wrap in a dummy <ROOT>, recover, then do a strict re‐parse."""
    try:
        txt = open(file_path, encoding='utf-8').read()
    except Exception as e:
        print(f"Error reading {file_path!r}: {e}")
        return None

    txt = fix_bad_entities(txt)
    wrapped = "<ROOT>\n" + txt + "\n</ROOT>"

    # first pass, recover mode
    rec_parser = ET.XMLParser(recover=True)
    try:
        recovered = ET.fromstring(wrapped.encode('utf-8'), parser=rec_parser)
    except ET.XMLSyntaxError as e:
        print(f"Fatal parse error (recover mode) on {file_path!r}: {e}")
        return None

    # serialize & re‐parse strictly
    strict_parser = ET.XMLParser(recover=False)
    blob = ET.tostring(recovered, encoding='utf-8')
    try:
        return ET.fromstring(blob, parser=strict_parser)
    except ET.XMLSyntaxError:
        # if strict still fails, return the recovered tree
        return recovered

# ------------------------------------------------------------
# Fast XML folder indexing with STRUCTURE STORAGE
# ------------------------------------------------------------
class XMLFolderIndex:
    """
    Indexes all XML files in a folder for fast lookup by tag, id, or strkey.
    NOW WITH FULL STRUCTURAL HIERARCHY STORAGE!
    """
    def __init__(self, folder_path, progress_callback=None):
        self.folder_path = folder_path
        # key → list of (element, filename)
        self.by_tag = defaultdict(list)
        self.by_id = defaultdict(list)
        self.by_strkey = defaultdict(list)
        self.by_attribute = defaultdict(lambda: defaultdict(list))  # attr_name -> attr_value -> list of (element, filename)
        self.by_parent_attribute = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))  # parent_tag -> attr_name -> attr_value -> list of (element, filename)
        self._file_trees = {}  # filename → parsed lxml root
        self.progress_callback = progress_callback
        
        # NEW STRUCTURE STORAGE
        self.parent_map = {}  # element_id -> parent_element_id
        self.children_map = defaultdict(list)  # element_id -> [child_element_ids]
        self.element_to_file = {}  # element_id -> filename
        self.id_to_element = {}  # element_id -> actual element reference
        
    def index_folder(self):
        """Index all XML files in the folder recursively"""
        print(f"Indexing XML files in {self.folder_path} ...")
        for dirpath, _, filenames in os.walk(self.folder_path):
            for fname in filenames:
                if not fname.lower().endswith(".xml"):
                    continue
                full = os.path.join(dirpath, fname)
                root = parse_xml_file(full)
                if root is None:
                    print(f"    Failed to parse {full}")
                    continue
                self._file_trees[full] = root
                
                # FIRST PASS: Store structure
                for el in root.iter():
                    if not isinstance(el.tag, str):
                        continue
                    
                    element_id = id(el)
                    self.id_to_element[element_id] = el
                    
                    # Store element ID as attribute for later reference
                    el.set("_element_id", str(element_id))
                    
                    # Skip the virtual ROOT wrapper
                    if el.tag == "ROOT":
                        continue
                    
                    # STORE PARENT-CHILD RELATIONSHIPS
                    parent = el.getparent()
                    if parent is not None and parent.tag != "ROOT":
                        parent_id = id(parent)
                        self.parent_map[element_id] = parent_id
                        self.children_map[parent_id].append(element_id)
                    
                    self.element_to_file[element_id] = full
                    
                    # Continue with normal indexing
                    self.by_tag[el.tag].append((el, full))
                    
                    for k, v in el.attrib.items():
                        if k.startswith("_"):  # Skip our internal attributes
                            continue
                        k_lower = k.lower()
                        if k_lower == "id":
                            self.by_id[v].append((el, full))
                        elif k_lower == "strkey":
                            self.by_strkey[v].append((el, full))
                        
                        # Index all attributes
                        self.by_attribute[k_lower][v].append((el, full))
                        
                        # Index attributes with parent context
                        self.by_parent_attribute[el.tag][k_lower][v].append((el, full))
                        
                if self.progress_callback:
                    self.progress_callback(f"Indexed: {full}")
                    
        print(f"Indexing complete: {len(self._file_trees)} files.")
        if self.progress_callback:
            self.progress_callback(f"Indexing complete: {len(self._file_trees)} files.")

    def find_elements_by_value(self, value):
        """
        Find all elements that match a specific value in any identifying attributes.
        Searches in tag, id, strkey, and name attributes.
        Returns a list of (element, filename) tuples.
        """
        results = []
        
        # Check tag matches
        results.extend(self.by_tag.get(value, []))
        
        # Check id matches
        results.extend(self.by_id.get(value, []))
        
        # Check strkey matches
        results.extend(self.by_strkey.get(value, []))
        
        # Also check name attribute
        if 'name' in self.by_attribute:
            results.extend(self.by_attribute['name'].get(value, []))
        
        return results
    
    def find_elements_with_attribute(self, attribute_name, attribute_value):
        """Find all elements with a specific attribute name and value"""
        return self.by_attribute.get(attribute_name.lower(), {}).get(attribute_value, [])
    
    def find_elements_with_parent_attribute(self, parent_tag, attribute_name, attribute_value):
        """Find all elements with a specific parent tag, attribute name, and attribute value"""
        return self.by_parent_attribute.get(parent_tag, {}).get(attribute_name.lower(), {}).get(attribute_value, [])
    
    def get_attribute_values(self, attribute_name):
        """Get all values for a specific attribute name"""
        return list(self.by_attribute.get(attribute_name.lower(), {}).keys())
    
    def get_attribute_values_by_parent(self, parent_tag, attribute_name):
        """Get all values for a specific attribute name under a specific parent tag"""
        return list(self.by_parent_attribute.get(parent_tag, {}).get(attribute_name.lower(), {}).keys())
    
    def get_unique_attribute_names(self):
        """Return a list of all unique attribute names in the indexed files"""
        return sorted(self.by_attribute.keys())
    
    def get_unique_parent_attribute_combinations(self):
        """Return a list of (parent_tag, attribute_name) tuples for unique combinations"""
        combinations = []
        for parent_tag, attrs in self.by_parent_attribute.items():
            for attr_name in attrs.keys():
                combinations.append((parent_tag, attr_name))
        return sorted(combinations)

    def get_all_attribute_names_from_elements(self, elements):
        """
        Extract all attribute names from a list of (element, filename) tuples,
        recursively through all descendants.
        """
        attr_names = set()
        for el, _ in elements:
            for descendant in el.iter():
                for k in descendant.attrib.keys():
                    if not k.startswith("_"):  # Skip internal attributes
                        attr_names.add(k.lower())
        return sorted(attr_names)
    
    def get_all_parent_attribute_combinations_from_elements(self, elements):
        """
        Extract all parent tag and attribute name combinations from a list of (element, filename) tuples,
        recursively through all descendants.
        """
        combinations = set()
        for el, _ in elements:
            for descendant in el.iter():
                if not isinstance(descendant.tag, str) or descendant.tag == "ROOT":
                    continue
                for k in descendant.attrib.keys():
                    if not k.startswith("_"):  # Skip internal attributes
                        combinations.add((descendant.tag, k.lower()))
        return sorted(combinations)
    
    def get_element_children(self, element):
        """Get all direct children of an element using stored structure"""
        element_id = element.get("_element_id")
        if element_id:
            element_id = int(element_id)
            child_ids = self.children_map.get(element_id, [])
            children = []
            for child_id in child_ids:
                if child_id in self.id_to_element:
                    children.append(self.id_to_element[child_id])
            return children
        return []
    
    def get_element_ancestors(self, element):
        """Get all ancestors of an element up to the root"""
        ancestors = []
        element_id = element.get("_element_id")
        if element_id:
            element_id = int(element_id)
            while element_id in self.parent_map:
                parent_id = self.parent_map[element_id]
                if parent_id in self.id_to_element:
                    parent = self.id_to_element[parent_id]
                    if parent.tag != "ROOT":
                        ancestors.append(parent)
                element_id = parent_id
        return list(reversed(ancestors))  # Return from root to immediate parent

# ------------------------------------------------------------
# Main Application
# ------------------------------------------------------------
class XMLAttributeAnalyzer:
    def __init__(self, master):
        self.master = master
        self.master.title("XML Attribute Analyzer")
        self.master.geometry("900x700")
        
        # Data storage
        self.base_file = None
        self.folder = None
        self.xml_index = None
        self.matched_elements = []
        self.extracted_data = None  # Will store our hierarchical structure
        self.current_phase = 1
        self.attribute_values = {}  # To store values for each attribute
        self.phase1_search_keywords = {}  # To track Phase 1 search keywords and their values
        self.phase1_results = None  # To store Phase 1 results for Phase 2
        self.phase1_matched_values = []  # To store the list of matched values from Phase 1
        self.use_parent_context = False  # Default to off (broad search)
        
        # Create main frame
        self.main_frame = ttk.Frame(master)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Initialize setup screen
        self.show_setup_screen()
    
    def show_setup_screen(self):
        """Show the initial setup screen"""
        # Clear previous content
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        
        # Create header
        header = ttk.Label(self.main_frame, text="XML Attribute Analyzer - Setup", font=("Arial", 16))
        header.pack(pady=(0, 20))
        
        # File selection frame
        file_frame = ttk.LabelFrame(self.main_frame, text="Select Files and Folders")
        file_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Organize File selection
        ttk.Button(file_frame, text="Select Organize File", command=self.select_base_file)\
            .grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.lbl_base = ttk.Label(file_frame, text="No file selected")
        self.lbl_base.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        
        # Data Folder selection
        ttk.Button(file_frame, text="Select Data Folder", command=self.select_folder)\
            .grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.lbl_folder = ttk.Label(file_frame, text="No folder selected")
        self.lbl_folder.grid(row=1, column=1, sticky="w", padx=5, pady=5)
        
        # Progress frame
        progress_frame = ttk.LabelFrame(self.main_frame, text="Progress")
        progress_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.progress_label = ttk.Label(progress_frame, text="")
        self.progress_label.pack(fill=tk.X, padx=5, pady=5)
        
        self.progress_bar = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, length=100, mode='indeterminate')
        
        # Console output
        console_frame = ttk.LabelFrame(self.main_frame, text="Console Output")
        console_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.console = scrolledtext.ScrolledText(console_frame, wrap=tk.WORD)
        self.console.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Start button
        self.btn_start = ttk.Button(
            self.main_frame, 
            text="Start Analysis", 
            command=self.start_analysis,
            state=tk.DISABLED
        )
        self.btn_start.pack(pady=10)
    
    def show_search_screen(self):
        """Show the attribute search selection screen (PHASE 1 and PHASE 2)."""
        # Clear previous content
        for widget in self.main_frame.winfo_children():
            widget.destroy()

        header = ttk.Label(self.main_frame,
                          text=f"Phase {self.current_phase} - Select Attributes to Search",
                          font=("Arial", 16))
        header.pack(pady=(0, 20))

        # Parent‐context toggle
        toggle_frame = ttk.Frame(self.main_frame)
        toggle_frame.pack(fill=tk.X, padx=10, pady=5)
        self.parent_context_var = tk.BooleanVar(value=self.use_parent_context)
        parent_context_check = ttk.Checkbutton(
            toggle_frame,
            text="Differentiate attributes by parent node "
                 "(e.g., Mission.StrKey vs Stage.StrKey)",
            variable=self.parent_context_var,
            command=self.toggle_parent_context
        )
        parent_context_check.pack(side=tk.LEFT, padx=5)

        if self.current_phase == 1:
            # ----- Phase 1 UI (unchanged) -----
            instructions = ttk.Label(
                self.main_frame,
                text="Select attribute categories to search for in the data files:"
            )
            instructions.pack(pady=(0, 10))

            organize_root = parse_xml_file(self.base_file)
            self.attribute_values = {}
            self.search_items = []

            # Collect all possible attribute keys & values from organize file
            for el in organize_root.iter():
                if not isinstance(el.tag, str) or el.tag == "ROOT":
                    continue
                for k, v in el.attrib.items():
                    k_lower = k.lower()
                    if self.use_parent_context:
                        key = f"{el.tag}.{k_lower}"
                    else:
                        key = k_lower
                    if key not in self.search_items:
                        self.search_items.append(key)
                    self.attribute_values.setdefault(key, set()).add(v)

            self.search_items.sort()

            # Build scrollable checkbox list
            checkbox_frame = ttk.Frame(self.main_frame)
            checkbox_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            canvas = tk.Canvas(checkbox_frame)
            scrollbar = ttk.Scrollbar(
                checkbox_frame, orient="vertical", command=canvas.yview
            )
            scrollable_frame = ttk.Frame(canvas)
            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

            self.search_vars = {}
            for i, search_key in enumerate(self.search_items):
                var = tk.IntVar()
                count = len(self.attribute_values.get(search_key, []))
                cb = ttk.Checkbutton(
                    scrollable_frame,
                    text=f"{search_key} ({count} values)",
                    variable=var
                )
                cb.grid(row=i//2, column=i%2, sticky="w", padx=10, pady=5)
                self.search_vars[search_key] = var

            ttk.Button(
                self.main_frame,
                text="Search",
                command=self.execute_search,
                width=20
            ).pack(pady=20)

        else:
            # ----- Phase 2 UI (FIXED) -----
            instructions = ttk.Label(
                self.main_frame,
                text="Select attribute categories to search for in Phase 2 "
                     "(from Phase 1 extracted results):"
            )
            instructions.pack(pady=(0, 10))

            # 1) Recursively collect **only** true attribute‐lists from Phase1 results
            all_attrs = set()

            def collect_all_attrs(d):
                if not isinstance(d, dict):
                    return
                for k, v in d.items():
                    # Handle 'children' branch first
                    if k == "children" and isinstance(v, dict):
                        for child_list in v.values():
                            for child_data in child_list:
                                collect_all_attrs(child_data)

                    # Handle 'phase2' branch second
                    elif k == "phase2" and isinstance(v, dict):
                        for el_dict in v.values():
                            for attrs_dict in el_dict.values():
                                collect_all_attrs(attrs_dict)

                    # Now any pure list must be a real attribute bucket
                    elif isinstance(v, list) and not k.startswith("_"):
                        all_attrs.add(k)

                    # Otherwise dive into nested dicts
                    elif isinstance(v, dict):
                        collect_all_attrs(v)

            collect_all_attrs(self.phase1_results)
            self.phase2_search_items = sorted(all_attrs)

            # 2) Gather their values from the Phase1 tree
            self.phase2_attribute_values = self.collect_phase2_attribute_values(
                self.phase1_results, self.phase2_search_items
            )

            # Debug print (optional)
            print(f"[DEBUG] Phase 2 search items: {self.phase2_search_items}")
            for attr, vals in self.phase2_attribute_values.items():
                print(f"[DEBUG]   {attr}: {sorted(vals)}")

            # 3) Build the checkbox UI – default all ON
            checkbox_frame = ttk.Frame(self.main_frame)
            checkbox_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            canvas = tk.Canvas(checkbox_frame)
            scrollbar = ttk.Scrollbar(
                checkbox_frame, orient="vertical", command=canvas.yview
            )
            scrollable_frame = ttk.Frame(canvas)
            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

            self.search_vars = {}
            for i, search_key in enumerate(self.phase2_search_items):
                # default = 1 (checked)
                var = tk.IntVar(value=1)
                count = len(self.phase2_attribute_values.get(search_key, []))
                cb = ttk.Checkbutton(
                    scrollable_frame,
                    text=f"{search_key} ({count} values)",
                    variable=var
                )
                cb.grid(row=i//2, column=i%2, sticky="w", padx=10, pady=5)
                self.search_vars[search_key] = var

            ttk.Button(
                self.main_frame,
                text="Search Phase 2",
                command=self.execute_phase2_search,
                width=20
            ).pack(pady=20)
    
    def toggle_parent_context(self):
        """Toggle between using parent context or not and refresh the UI"""
        self.use_parent_context = self.parent_context_var.get()
        # Refresh the search screen to show updated options
        self.show_search_screen()
    
    def show_extract_screen(self):
        """Show the attribute extraction selection screen with double search/filter and select all."""
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        header = ttk.Label(self.main_frame, 
                          text=f"Phase {self.current_phase} - Select Attributes to Extract", 
                          font=("Arial", 16))
        header.pack(pady=(0, 20))
        result_text = f"Found {len(self.matched_elements)} matching elements."
        result_label = ttk.Label(self.main_frame, text=result_text)
        result_label.pack(pady=(0, 10))
        instructions = ttk.Label(self.main_frame, 
                               text="Select attribute categories to extract from matched elements:")
        instructions.pack(pady=(0, 10))
        
        # Add toggle for parent context
        toggle_frame = ttk.Frame(self.main_frame)
        toggle_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.extract_context_var = tk.BooleanVar(value=self.use_parent_context)
        extract_context_check = ttk.Checkbutton(
            toggle_frame, 
            text="Differentiate attributes by parent node (e.g., Mission.StrKey vs Stage.StrKey)", 
            variable=self.extract_context_var,
            command=self.toggle_extract_context
        )
        extract_context_check.pack(side=tk.LEFT, padx=5)
        
        # --- DOUBLE SEARCH/FILTER BAR ---
        search_frame = ttk.Frame(self.main_frame)
        search_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(search_frame, text="Filter 1:").pack(side=tk.LEFT, padx=(0,5))
        self.extract_search_var1 = tk.StringVar()
        search_entry1 = ttk.Entry(search_frame, textvariable=self.extract_search_var1, width=20)
        search_entry1.pack(side=tk.LEFT, padx=(0,5))
        search_entry1.bind("<KeyRelease>", lambda e: self._update_extract_filter())
        search_entry1.bind("<Return>", lambda e: self._update_extract_filter())
        ttk.Label(search_frame, text="Filter 2:").pack(side=tk.LEFT, padx=(10,5))
        self.extract_search_var2 = tk.StringVar()
        search_entry2 = ttk.Entry(search_frame, textvariable=self.extract_search_var2, width=20)
        search_entry2.pack(side=tk.LEFT, padx=(0,5))
        search_entry2.bind("<KeyRelease>", lambda e: self._update_extract_filter())
        search_entry2.bind("<Return>", lambda e: self._update_extract_filter())
        search_entry1.focus_set()
        # Select All / Deselect All buttons
        ttk.Button(search_frame, text="Select All", command=self._extract_select_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(search_frame, text="Deselect All", command=self._extract_deselect_all).pack(side=tk.LEFT, padx=5)
        
        # --- ATTRIBUTE CHECKBOXES ---
        if self.use_parent_context:
            combinations = self.xml_index.get_all_parent_attribute_combinations_from_elements(self.matched_elements)
            combinations = [(parent, attr) for parent, attr in combinations if not attr.startswith('_')]
            self.extract_items = [f"{parent}.{attr}" for parent, attr in combinations]
        else:
            self.extract_items = self.xml_index.get_all_attribute_names_from_elements(self.matched_elements)
            self.extract_items = [attr for attr in self.extract_items if not attr.startswith('_')]
        self.extract_items.sort()
        
        # Store original list for filtering
        self._extract_items_full = list(self.extract_items)
        
        checkbox_frame = ttk.Frame(self.main_frame)
        checkbox_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self._extract_canvas = tk.Canvas(checkbox_frame)
        self._extract_scrollbar = ttk.Scrollbar(checkbox_frame, orient="vertical", command=self._extract_canvas.yview)
        self._extract_scrollable_frame = ttk.Frame(self._extract_canvas)
        self._extract_scrollable_frame.bind(
            "<Configure>",
            lambda e: self._extract_canvas.configure(scrollregion=self._extract_canvas.bbox("all"))
        )
        self._extract_canvas.create_window((0, 0), window=self._extract_scrollable_frame, anchor="nw")
        self._extract_canvas.configure(yscrollcommand=self._extract_scrollbar.set)
        self._extract_canvas.pack(side="left", fill="both", expand=True)
        self._extract_scrollbar.pack(side="right", fill="y")
        
        # Dict: attribute name → IntVar
        self.extract_vars = {}
        self._extract_checkbox_widgets = {}  # attr → Checkbutton widget
        self._extract_visible_items = set()  # currently visible
        
        # Build all checkboxes (but show/hide with filter)
        for i, extract_key in enumerate(self.extract_items):
            var = tk.IntVar()
            cb = ttk.Checkbutton(self._extract_scrollable_frame, text=extract_key, variable=var)
            cb.grid(row=i//2, column=i%2, sticky="w", padx=10, pady=5)
            self.extract_vars[extract_key] = var
            self._extract_checkbox_widgets[extract_key] = cb
        
        # Initial filter (show all)
        self._update_extract_filter()
        
        button_frame = ttk.Frame(self.main_frame)
        button_frame.pack(fill=tk.X, pady=20)
        ttk.Button(button_frame, text="Extract and Export", command=self.extract_and_export, width=20)\
            .pack(side=tk.LEFT, padx=10)
        if self.current_phase == 1:
            ttk.Button(button_frame, text="Continue to Phase 2", command=self.start_phase2, width=20)\
                .pack(side=tk.RIGHT, padx=10)

    def _update_extract_filter(self):
        """Update the attribute extraction checkbox list based on two filter texts."""
        filter_text1 = self.extract_search_var1.get().strip().lower()
        filter_text2 = self.extract_search_var2.get().strip().lower()
        terms1 = [t for t in filter_text1.split() if t]
        terms2 = [t for t in filter_text2.split() if t]
        # Show only checkboxes that match ALL terms from BOTH bars (case-insensitive, anywhere in text)
        self._extract_visible_items = set()
        for attr, cb in self._extract_checkbox_widgets.items():
            match1 = all(term in attr.lower() for term in terms1)
            match2 = all(term in attr.lower() for term in terms2)
            if match1 and match2:
                cb.grid()  # Show
                self._extract_visible_items.add(attr)
            else:
                cb.grid_remove()  # Hide

    def _extract_select_all(self):
        """Select all currently visible attribute checkboxes."""
        for attr in self._extract_visible_items:
            self.extract_vars[attr].set(1)

    def _extract_deselect_all(self):
        """Deselect all currently visible attribute checkboxes."""
        for attr in self._extract_visible_items:
            self.extract_vars[attr].set(0)
    
    def toggle_extract_context(self):
        """Toggle between using parent context for extraction or not and refresh the UI"""
        self.use_parent_context = self.extract_context_var.get()
        # Refresh the extract screen to show updated options
        self.show_extract_screen()
    
    def show_export_screen(self):
        """Show the export options screen"""
        # Clear previous content
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        
        # Create header
        header = ttk.Label(self.main_frame, 
                          text="Export Results", 
                          font=("Arial", 16))
        header.pack(pady=(0, 20))
        
        # Export format selection - Only text format now
        format_frame = ttk.LabelFrame(self.main_frame, text="Export Format")
        format_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(format_frame, text="Text File Format")\
            .pack(padx=20, pady=10)
        
        # Export button
        ttk.Button(self.main_frame, text="Export", command=self.export_results, width=20)\
            .pack(pady=20)
        
        # Back button
        ttk.Button(self.main_frame, text="Back to Setup", command=self.show_setup_screen, width=20)\
            .pack(pady=10)
    
    def update_progress(self, message):
        """Update the progress label and console safely."""
        print(f"[PROGRESS] {message}")  # Always print to console
        # Check if progress_label exists and is still a valid widget
        if hasattr(self, 'progress_label'):
            try:
                if self.progress_label.winfo_exists():
                    self.progress_label.config(text=message)
            except tk.TclError:
                pass  # Widget was destroyed, ignore
        if hasattr(self, 'console'):
            try:
                if self.console.winfo_exists():
                    self.console.insert(tk.END, message + "\n")
                    self.console.see(tk.END)
            except tk.TclError:
                pass  # Widget was destroyed, ignore
    
    def select_base_file(self):
        """Select the organize XML file"""
        fp = filedialog.askopenfilename(
            title="Select Organize XML file",
            filetypes=[("XML Files","*.xml"),("All Files","*.*")])
        if not fp:
            return
        self.base_file = fp
        self.lbl_base.config(text=os.path.basename(fp))
        self._check_ready()
    
    def select_folder(self):
        """Select the data folder with XML files"""
        fld = filedialog.askdirectory(title="Select folder with data XML files")
        if not fld:
            return
        self.folder = fld
        self.lbl_folder.config(text=fld)
        # Start indexing in a separate thread
        self.start_indexing()
    
    def start_indexing(self):
        """Start indexing the XML files in the selected folder"""
        self.update_progress("Indexing files, please wait...")
        self.btn_start.config(state=tk.DISABLED)
        self.progress_bar.pack(fill=tk.X, padx=5, pady=5)
        self.progress_bar.start(10)
        
        # Create and start the indexing thread
        self.xml_index = XMLFolderIndex(self.folder, self.update_progress)
        indexing_thread = threading.Thread(target=self._do_indexing)
        indexing_thread.daemon = True
        indexing_thread.start()
    
    def _do_indexing(self):
        """Perform the indexing in a separate thread"""
        try:
            self.xml_index.index_folder()
            # Schedule UI update in the main thread
            self.master.after(100, self._indexing_complete)
        except Exception as e:
            # Schedule error display in the main thread
            error_msg = f"Indexing error: {str(e)}\n{traceback.format_exc()}"
            self.master.after(100, lambda: self._show_error(error_msg))
    
    def _indexing_complete(self):
        """Called when indexing is complete"""
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.update_progress("Indexing complete!")
        self._check_ready()
    
    def _check_ready(self):
        """Check if we're ready to proceed to analysis"""
        if self.base_file and self.folder and self.xml_index:
            self.btn_start.config(state=tk.NORMAL)
    
    def _show_error(self, message):
        """Display an error message in console only"""
        print(f"[ERROR] {message}")
        self.update_progress(f"Error: {message}")
    
    def start_analysis(self):
        """Start the analysis process"""
        # Reset phase data
        self.current_phase = 1
        self.phase1_search_keywords = {}
        self.phase1_results = None
        self.phase1_matched_values = []
        self.show_search_screen()
    
    def execute_search(self):
        """Execute the search with selected attributes"""
        if self.current_phase == 1:
            selected_attrs = [attr for attr, var in self.search_vars.items() if var.get() == 1]
            if not selected_attrs:
                self._show_error("Please select at least one attribute to search for.")
                return
            self.update_progress(f"Searching for elements with selected attributes (Phase 1)...")
            threading.Thread(target=self._do_search, args=(selected_attrs,), daemon=True).start()
        else:
            # Phase 2 search is now handled by execute_phase2_search
            self.execute_phase2_search()

    def execute_phase2_search(self):
        """Trigger the threaded Phase 2 search using the selected Phase 2 attributes."""
        # Collect selected attribute‐categories
        selected_attrs = [
            attr for attr, var in self.search_vars.items() if var.get() == 1
        ]
        if not selected_attrs:
            self._show_error("Please select at least one attribute to search for Phase 2.")
            return

        self.update_progress(f"Starting Phase 2 search for attributes: {selected_attrs}")
        thread = threading.Thread(
            target=self._do_phase2_search,
            args=(selected_attrs,),
            daemon=True
        )
        thread.start()

    def _do_search(self, selected_attrs):
        try:
            self.matched_elements = []
            # Phase 1: collect search keywords
            self.phase1_search_keywords = {}
            organize_root = parse_xml_file(self.base_file)
            
            # Collect values from organize file
            for search_key in selected_attrs:
                self.phase1_search_keywords[search_key] = []
                
                if self.use_parent_context and '.' in search_key:
                    parent_tag, attr_name = search_key.split(".", 1)
                    attr_name_lower = attr_name.lower()
                    
                    for el in organize_root.iter():
                        if not isinstance(el.tag, str) or el.tag == "ROOT":
                            continue
                        
                        if el.tag == parent_tag:
                            for k, v in el.attrib.items():
                                if k.lower() == attr_name_lower and v:
                                    if v not in self.phase1_search_keywords[search_key]:
                                        self.phase1_search_keywords[search_key].append(v)
                else:
                    attr_name_lower = search_key.lower()
                    
                    for el in organize_root.iter():
                        if not isinstance(el.tag, str) or el.tag == "ROOT":
                            continue
                        
                        for k, v in el.attrib.items():
                            if k.lower() == attr_name_lower and v:
                                if v not in self.phase1_search_keywords[search_key]:
                                    self.phase1_search_keywords[search_key].append(v)
                
                self.update_progress(f"Found {len(self.phase1_search_keywords[search_key])} values for {search_key}")

            # Now search for these values in data files using original broad search
            for search_key, values in self.phase1_search_keywords.items():
                for value in values:
                    self.update_progress(f"Searching for '{search_key}={value}'")
                    
                    # Use original broad search to find all matches
                    matches = self.xml_index.find_elements_by_value(value)
                    
                    if matches:
                        # Apply parent context filtering if enabled
                        if self.use_parent_context and '.' in search_key:
                            parent_tag, attr_name = search_key.split(".", 1)
                            self.update_progress(f"  Found {len(matches)} elements matching value '{value}', filtering for parent '{parent_tag}'")
                            
                            filtered_matches = []
                            for el, filename in matches:
                                if el.tag == parent_tag:
                                    el.set("_search_parent", parent_tag)
                                    el.set("_search_attr", attr_name)
                                    el.set("_search_value", value)
                                    el.set("_search_key", search_key)
                                    filtered_matches.append((el, filename))
                            
                            self.matched_elements.extend(filtered_matches)
                            self.update_progress(f"    Kept {len(filtered_matches)} elements with parent '{parent_tag}'")
                        else:
                            # No filtering - keep all matches
                            self.update_progress(f"  Found {len(matches)} elements matching '{search_key}={value}'")
                            for el, filename in matches:
                                el.set("_search_attr", search_key)
                                el.set("_search_value", value)
                                el.set("_search_key", search_key)
                                self.matched_elements.append((el, filename))
                        
                        # Add to phase1_matched_values
                        if value not in self.phase1_matched_values:
                            self.phase1_matched_values.append(value)
            
            self.update_progress(f"Found a total of {len(self.matched_elements)} matching elements.")
            self.master.after(100, self.show_extract_screen)
        except Exception as e:
            error_msg = f"Search error: {str(e)}\n{traceback.format_exc()}"
            self.master.after(100, lambda: self._show_error(error_msg))
    
    def _do_phase2_search(self, selected_attrs):
        """
        Perform Phase 2 search using selected_attrs, searching for every VALUE found in Phase 1 results.
        """
        try:
            self.update_progress(">> Phase 2: Gathering all values from Phase 1 results...")

            # 1) For each selected Phase 2 attribute, gather all values found in Phase 1 results
            attr_to_values = self._collect_phase2_values_from_phase1(self.phase1_results, selected_attrs)
            self.phase2_attribute_values = attr_to_values  # for the UI & debug

            # 2) Now search the indexed folder for each (attr, value)
            self.matched_elements = []
            for attr_name, values in attr_to_values.items():
                for value in values:
                    if not value:
                        continue
                    self.update_progress(f"Searching for '{attr_name}={value}'")

                    # Parent‐context ON: match parent tag + attribute name
                    if self.use_parent_context and "." in attr_name:
                        parent_tag, attr = attr_name.split(".", 1)
                        attr = attr.lower()
                        matches = self.xml_index.find_elements_with_parent_attribute(
                            parent_tag, attr, value
                        )
                    else:
                        # strip any accidental "Parent.Attr" into just attr
                        attr = attr_name.split(".", 1)[-1].lower()
                        matches = self.xml_index.find_elements_with_attribute(attr, value)

                    if not matches:
                        continue

                    self.update_progress(
                        f"  Found {len(matches)} matches for '{attr_name}={value}'"
                    )

                    # 3) Annotate and collect
                    for el, filename in matches:
                        el.set("_p2_search_attr", attr_name)
                        el.set("_p2_search_value", value)
                        self.matched_elements.append((el, filename))

            self.update_progress(
                f"Phase 2 search complete, total elements = {len(self.matched_elements)}"
            )
            # Hand back to GUI thread for extraction screen
            self.master.after(100, self.show_extract_screen)

        except Exception as e:
            err = f"Phase 2 search error: {e}\n{traceback.format_exc()}"
            self.master.after(100, lambda: self._show_error(err))


    def _collect_phase2_values_from_phase1(self, data, phase2_attrs):
        """
        Recursively collect all values for the given phase2_attrs in the Phase 1 result tree.
        Returns: dict attr_name → set of values
        """
        out = {attr: set() for attr in phase2_attrs}

        def _recurse(d):
            if isinstance(d, dict):
                for k, v in d.items():
                    # If this key is one of our target attrs and it's a flat list, grab it
                    if k in phase2_attrs and isinstance(v, list):
                        out[k].update(v)
                    # Dive into any nested dict
                    elif isinstance(v, dict):
                        _recurse(v)
                    # Special-case the 'children' node
                    elif k == "children" and isinstance(v, dict):
                        for child_tag, child_list in v.items():
                            for child_data in child_list:
                                _recurse(child_data)
                    # Special-case the 'phase2' node under Phase-1 results
                    elif k == "phase2" and isinstance(v, dict):
                        for el_tag, el_dict in v.items():
                            for el_key, attrs_dict in el_dict.items():
                                _recurse(attrs_dict)
        _recurse(data)
        # Convert sets to sorted lists for UI/debug
        return {k: sorted(list(v)) for k, v in out.items()}
    
    def _build_hierarchical_output(self, temp_extracted, selected_attrs):
        """Build hierarchical output using stored XML structure from indexing - GENERALIZED VERSION"""
        self.update_progress("Building hierarchical output using XML structure...")
        hierarchical_data = {}
        
        # Process each parent group
        for parent_key, search_values in temp_extracted.items():
            hierarchical_data[parent_key] = {}
            
            for search_value, attrs in search_values.items():
                # Find all elements that matched this search_value
                matched_value_elements = []
                for el, _ in self.matched_elements:
                    if el.get("_search_value") == search_value:
                        matched_value_elements.append(el)
                
                if not matched_value_elements:
                    # Fallback: just use the flat structure
                    hierarchical_data[parent_key][search_value] = attrs
                    continue
                
                # For each matched element, build the hierarchy
                hierarchical_data[parent_key][search_value] = {}
                
                for matched_el in matched_value_elements:
                    # Find the top-most ancestor that contains our search value
                    ancestors = self.xml_index.get_element_ancestors(matched_el)
                    
                    # Find the highest-level ancestor that still contains our matched element
                    top_ancestor = None
                    for ancestor in ancestors:
                        # Check if this ancestor contains any of the search values we're looking for
                        contains_search_value = False
                        for desc in ancestor.iter():
                            for k, v in desc.attrib.items():
                                if v == search_value:
                                    contains_search_value = True
                                    break
                            if contains_search_value:
                                break
                        if contains_search_value:
                            top_ancestor = ancestor
                            break
                    
                    # If no ancestor found, use the matched element itself
                    if not top_ancestor:
                        top_ancestor = matched_el
                    
                    # Now build the hierarchy from this top element
                    self._extract_hierarchy(top_ancestor, hierarchical_data[parent_key][search_value], 
                                           selected_attrs, search_value)
        
        self.update_progress("Hierarchical structure built successfully!")
        return hierarchical_data
    
    def _extract_hierarchy(self, element, output_dict, selected_attrs, search_value, level=0):
        """
        Recursively extract hierarchy, but only keep a node if:
          - it has one of the selected_attrs on itself, OR
          - at least one of its children has data
        Everything else is skipped, so you never see empty 'Stage' or similar.
        """
        # 1) Collect matching attributes on THIS element
        elem_data = {}
        has_values = False

        for attr_name in selected_attrs:
            if self.use_parent_context and "." in attr_name:
                parent_tag, attr = attr_name.split(".", 1)
                if element.tag == parent_tag:
                    for k, v in element.attrib.items():
                        if k.lower() == attr.lower() and not k.startswith("_"):
                            elem_data.setdefault(attr_name, [])
                            if v not in elem_data[attr_name]:
                                elem_data[attr_name].append(v)
                                has_values = True
            else:
                for k, v in element.attrib.items():
                    if k.lower() == attr_name.lower() and not k.startswith("_"):
                        elem_data.setdefault(attr_name, [])
                        if v not in elem_data[attr_name]:
                            elem_data[attr_name].append(v)
                            has_values = True

        # 2) Recurse into children and gather those that produce data
        children = self.xml_index.get_element_children(element)
        children_data = {}

        for child in children:
            child_output = {}
            self._extract_hierarchy(child, child_output, selected_attrs, search_value, level + 1)
            if child_output:
                # Only keep children that actually returned something
                children_data.setdefault(child.tag, []).append(child_output)

        # 3) If neither this node nor any of its children has data, SKIP it
        if not has_values and not children_data:
            return

        # 4) Otherwise, fold this node into the output:
        if level == 0:
            # Top‐level: merge attributes directly, then attach children under "children"
            if has_values:
                output_dict.update(elem_data)
            if children_data:
                output_dict.setdefault("children", {})
                for ctag, clist in children_data.items():
                    output_dict["children"].setdefault(ctag, []).extend(clist)
        else:
            # Nested level: create a sub‐dict keyed by element.tag
            result = {}
            if has_values:
                result.update(elem_data)
            if children_data:
                result["children"] = children_data
            output_dict[element.tag] = result
    
    def extract_and_export(self):
        """Extract selected attributes and go to export screen, with hierarchy and filtering."""
        selected_attrs = [attr for attr, var in self.extract_vars.items() if var.get() == 1]
        if not selected_attrs:
            self._show_error("Please select at least one attribute to extract.")
            return
        self.update_progress(f"Extracting {len(selected_attrs)} attribute types from {len(self.matched_elements)} elements...")
        
        try:
            if self.current_phase == 1:
                # Phase 1: Use original extraction logic
                self.extracted_data = {}
                organize_root = parse_xml_file(self.base_file)
                value_to_parent = {}
                
                # Original mapping logic
                for el in organize_root.iter():
                    if not isinstance(el.tag, str) or el.tag == "ROOT":  # Skip ROOT element
                        continue
                        
                    for k, v in el.attrib.items():
                        # Check against search keywords
                        for search_key in self.phase1_search_keywords.keys():
                            attr_name = search_key.split('.', 1)[1] if self.use_parent_context and '.' in search_key else search_key
                            if k.lower() == attr_name.lower():
                                parent = el.getparent() if el.getparent() is not None and el.getparent().tag != "ROOT" else el
                                parent_tag = parent.tag
                                parent_attrs = tuple(sorted(parent.attrib.items()))
                                value_to_parent[v] = (parent_tag, parent_attrs)
                
                # Extract data
                temp_extracted = {}
                for el, filename in self.matched_elements:
                    search_attr = el.get("_search_attr")
                    search_value = el.get("_search_value")
                    if not search_attr or not search_value:
                        continue
                        
                    parent_tag, parent_attrs = value_to_parent.get(search_value, ("<Unknown>", ()))
                    parent_key = (parent_tag, parent_attrs)
                    
                    if parent_key not in temp_extracted:
                        temp_extracted[parent_key] = {}
                    if search_value not in temp_extracted[parent_key]:
                        temp_extracted[parent_key][search_value] = {}
                        
                    # Extract attributes
                    for attr_name in selected_attrs:
                        if self.use_parent_context and '.' in attr_name:
                            extract_parent, extract_attr = attr_name.split(".", 1)
                            
                            if attr_name not in temp_extracted[parent_key][search_value]:
                                temp_extracted[parent_key][search_value][attr_name] = []
                            
                            for desc in el.iter():
                                if desc.tag == extract_parent:
                                    attr_value = None
                                    for key, value in desc.attrib.items():
                                        if key.lower() == extract_attr.lower() and not key.startswith("_"):
                                            attr_value = value
                                            break
                                    if attr_value is not None and attr_value not in temp_extracted[parent_key][search_value][attr_name]:
                                        temp_extracted[parent_key][search_value][attr_name].append(attr_value)
                        else:
                            attr_key = attr_name
                            if attr_key not in temp_extracted[parent_key][search_value]:
                                temp_extracted[parent_key][search_value][attr_key] = []
                            
                            for desc in el.iter():
                                attr_value = None
                                for key, value in desc.attrib.items():
                                    if key.lower() == attr_key.lower() and not key.startswith("_"):
                                        attr_value = value
                                        break
                                if attr_value is not None and attr_value not in temp_extracted[parent_key][search_value][attr_key]:
                                    temp_extracted[parent_key][search_value][attr_key].append(attr_value)
                
                # Filter out empty results
                for parent_key in list(temp_extracted.keys()):
                    for search_value in list(temp_extracted[parent_key].keys()):
                        total = sum(len(vals) for vals in temp_extracted[parent_key][search_value].values())
                        if total == 0:
                            del temp_extracted[parent_key][search_value]
                    if not temp_extracted[parent_key]:
                        del temp_extracted[parent_key]
                
                # NEW: Use stored XML structure with generalized hierarchy
                self.extracted_data = self._build_hierarchical_output(temp_extracted, selected_attrs)
                self.phase1_results = self.extracted_data
                
            else:  # Phase 2
                # Phase 2 extraction with proper nesting under Phase 1 results
                self.extracted_data = {}
                
                # Process Phase 2 matches
                phase2_by_parent = {}  # Group by Phase 1 parent
                
                for el, filename in self.matched_elements:
                    p2_search_value = el.get("_p2_search_value")
                    p1_parent_str = el.get("_p2_phase1_parent")
                    p1_value = el.get("_p2_phase1_value")
                    
                    if not p2_search_value or not p1_parent_str or not p1_value:
                        print(f"[DEBUG] Skipping element with missing metadata")
                        continue
                    
                    # Convert parent string back to tuple
                    try:
                        p1_parent_key = eval(p1_parent_str)
                    except:
                        print(f"[DEBUG] Failed to parse parent key: {p1_parent_str}")
                        continue
                    
                    key = (p1_parent_key, p1_value)
                    if key not in phase2_by_parent:
                        phase2_by_parent[key] = []
                    phase2_by_parent[key].append((el, filename, p2_search_value))
                
                print(f"[DEBUG] Phase 2 grouped into {len(phase2_by_parent)} parent groups")
                
                # Build the final structure with Phase 1 as base
                self.extracted_data = {}
                
                # First, copy Phase 1 structure
                for parent_key, values_dict in self.phase1_results.items():
                    self.extracted_data[parent_key] = {}
                    for search_value, data in values_dict.items():
                        self._copy_phase1_structure(self.extracted_data[parent_key], search_value, data)
                
                # Then add Phase 2 results
                for (p1_parent_key, p1_value), p2_elements in phase2_by_parent.items():
                    print(f"[DEBUG] Processing {len(p2_elements)} Phase 2 elements for {p1_value}")
                    
                    # Find where to add Phase 2 results in the hierarchy
                    if p1_parent_key in self.extracted_data:
                        self._add_phase2_to_hierarchy(self.extracted_data[p1_parent_key], p1_value, 
                                                    p2_elements, selected_attrs)
                
                print(f"[DEBUG] Phase 2 extraction complete")
            
            # Count total values extracted
            total_values = self._count_extracted_values(self.extracted_data)
            self.update_progress(f"Extracted a total of {total_values} attribute values.")
            self.show_export_screen()
            
        except Exception as e:
            error_msg = f"Extraction error: {str(e)}\n{traceback.format_exc()}"
            self._show_error(error_msg)
    
    def _copy_phase1_structure(self, dest, search_value, data):
        """Recursively copy Phase 1 structure"""
        if isinstance(data, dict):
            dest[search_value] = {}
            for k, v in data.items():
                if k == 'children' and isinstance(v, dict):
                    dest[search_value]['children'] = {}
                    for child_key, child_data in v.items():
                        dest[search_value]['children'][child_key] = child_data
                else:
                    dest[search_value][k] = v
        else:
            dest[search_value] = data
    
    def _add_phase2_to_hierarchy(self, parent_dict, search_value, p2_elements, selected_attrs):
        """Add Phase 2 results to the hierarchy under the correct Phase 1 value"""
        # Find the search_value in the hierarchy
        if search_value in parent_dict:
            node = parent_dict[search_value]
        else:
            # Search in children
            for value, data in parent_dict.items():
                if 'children' in data and search_value in data['children']:
                    node = data['children'][search_value]
                    break
            else:
                print(f"[DEBUG] Could not find {search_value} in hierarchy")
                return
        
        # Add phase2 results
        if 'phase2' not in node:
            node['phase2'] = {}
        
        # Extract attributes from Phase 2 elements
        for el, filename, p2_value in p2_elements:
            el_tag = el.tag
            
            if el_tag not in node['phase2']:
                node['phase2'][el_tag] = {}
            
            # Create unique key for this element
            el_key = f"{el_tag}_{p2_value}"
            
            if el_key not in node['phase2'][el_tag]:
                node['phase2'][el_tag][el_key] = {}
            
            # Extract selected attributes
            for attr_name in selected_attrs:
                if attr_name not in node['phase2'][el_tag][el_key]:
                    node['phase2'][el_tag][el_key][attr_name] = []
                
                if self.use_parent_context and '.' in attr_name:
                    extract_parent, extract_attr = attr_name.split(".", 1)
                    
                    for desc in el.iter():
                        if desc.tag == extract_parent:
                            attr_value = None
                            for key, value in desc.attrib.items():
                                if key.lower() == extract_attr.lower() and not key.startswith("_"):
                                    attr_value = value
                                    break
                            if attr_value is not None and attr_value not in node['phase2'][el_tag][el_key][attr_name]:
                                node['phase2'][el_tag][el_key][attr_name].append(attr_value)
                else:
                    for desc in el.iter():
                        attr_value = None
                        for key, value in desc.attrib.items():
                            if key.lower() == attr_name.lower() and not key.startswith("_"):
                                attr_value = value
                                break
                        if attr_value is not None and attr_value not in node['phase2'][el_tag][el_key][attr_name]:
                            node['phase2'][el_tag][el_key][attr_name].append(attr_value)
    
    def _count_extracted_values(self, data, level=0):
        """Recursively count all extracted values"""
        total = 0
        
        for key, value in data.items():
            if isinstance(value, dict):
                # Skip 'children' and 'phase2' keys, count their contents separately
                if key == 'children':
                    for child_type, child_list in value.items():
                        for child_data in child_list:
                            total += self._count_extracted_values(child_data, level + 1)
                elif key == 'phase2':
                    total += self._count_phase2_values(value)
                else:
                    # Regular dict traversal
                    total += self._count_extracted_values(value, level + 1)
            elif isinstance(value, list):
                total += len(value)
        
        return total
    
    def _count_phase2_values(self, phase2_data):
        """Count values in Phase 2 data"""
        total = 0
        for el_tag, el_dict in phase2_data.items():
            for el_key, attrs_dict in el_dict.items():
                for attr_name, attr_values in attrs_dict.items():
                    if isinstance(attr_values, list):
                        total += len(attr_values)
        return total
    
    def _prepare_phase1_results(self, selected_attrs):
        """
        Build self.phase1_results exactly as extract_and_export’s Phase 1 branch,
        but without popping to export.  Added debug so you can watch every step.
        """
        print("\n===== DEBUG _prepare_phase1_results() CALLED =====")
        self.update_progress(">> DEBUG: _prepare_phase1_results() called")
        print(f">> DEBUG: selected_attrs = {selected_attrs}")

        # 1) Build mapping from value → parent_key using the organize file
        organize_root = parse_xml_file(self.base_file)
        value_to_parent = {}
        print(">> DEBUG: Walking organize file to map each value → parent")
        self.update_progress(">> DEBUG: Mapping organize-file values to parents")

        for el in organize_root.iter():
            if not isinstance(el.tag, str) or el.tag == "ROOT":
                continue
            for k, v in el.attrib.items():
                if not v:
                    continue
                # does this attribute name match any selected Phase1 attr?
                for search_key in self.phase1_search_keywords.keys():
                    attr_name = (
                        search_key.split(".", 1)[1]
                        if self.use_parent_context and "." in search_key
                        else search_key
                    )
                    if k.lower() == attr_name.lower():
                        parent = el.getparent()
                        if parent is None or parent.tag == "ROOT":
                            parent = el
                        parent_key = (parent.tag, tuple(sorted(parent.attrib.items())))
                        value_to_parent[v] = parent_key
                        print(f">> DEBUG: value_to_parent['{v}'] = {parent_key}")
                        self.update_progress(f">> DEBUG: value_to_parent['{v}'] = {parent_key}")

        print(f">> DEBUG: Completed mapping. Total entries = {len(value_to_parent)}")
        self.update_progress(f">> DEBUG: Completed mapping. Total = {len(value_to_parent)}")

        # 2) Walk matched_elements to pick out the attributes you ticked
        temp_extracted = {}
        print(f">> DEBUG: Iterating {len(self.matched_elements)} matched_elements")
        self.update_progress(f">> DEBUG: Extracting from matched_elements")

        for idx, (el, _fn) in enumerate(self.matched_elements, 1):
            search_attr  = el.get("_search_attr")
            search_value = el.get("_search_value")
            print(f">> DEBUG ({idx}): el.tag={el.tag}, search_attr={search_attr}, search_value={search_value}")
            if not search_attr or not search_value:
                print(">> DEBUG: Missing metadata, skipping element")
                continue

            parent_key = value_to_parent.get(search_value, ("<Unknown>", ()))
            print(f">> DEBUG: Found parent_key = {parent_key} for value '{search_value}'")
            self.update_progress(f">> DEBUG: parent_key for '{search_value}' = {parent_key}")

            bucket = temp_extracted.setdefault(parent_key, {}).setdefault(search_value, {})

            # Now extract each selected attribute under this element
            for attr_name in selected_attrs:
                target = bucket.setdefault(attr_name, [])
                print(f">> DEBUG: extracting '{attr_name}' from element")
                if self.use_parent_context and "." in attr_name:
                    extract_parent, extract_attr = attr_name.split(".", 1)
                    for desc in el.iter():
                        if desc.tag == extract_parent:
                            val = desc.attrib.get(extract_attr)
                            if val and val not in target:
                                target.append(val)
                                print(f"   -> got '{val}'")
                else:
                    for desc in el.iter():
                        val = desc.attrib.get(attr_name)
                        if val and val not in target:
                            target.append(val)
                            print(f"   -> got '{val}'")

        # 3) Prune empty buckets
        print(">> DEBUG: Pruning empty buckets from temp_extracted")
        for pk in list(temp_extracted.keys()):
            for sv in list(temp_extracted[pk].keys()):
                if not any(temp_extracted[pk][sv].values()):
                    print(f"   -> removing empty search_value '{sv}' under {pk}")
                    del temp_extracted[pk][sv]
            if not temp_extracted[pk]:
                print(f"   -> removing empty parent_key {pk}")
                del temp_extracted[pk]

        # 4) Build the hierarchical form
        print(">> DEBUG: Building hierarchical output for Phase 1")
        self.phase1_results = self._build_hierarchical_output(temp_extracted, selected_attrs)
        self.extracted_data   = self.phase1_results
        print(f">> DEBUG: phase1_results STRUCTURE = {json.dumps(self.phase1_results, default=str, indent=2)}")
        self.update_progress(">> DEBUG: Phase 1 results prepared – ready for Phase 2")

        
    def collect_phase2_attribute_values(self, data, phase2_attrs, out=None, path="ROOT"):
        """
        Recursively collect all values for the given phase2_attrs in the Phase 1 result tree.
        Returns: dict attr_name → set of values
        """
        # Initialize our output map once at the top level
        if out is None:
            out = {attr: set() for attr in phase2_attrs}

        if isinstance(data, dict):
            for key, val in data.items():
                # If this key is one of our target attrs and it's a flat list, grab it
                if key in phase2_attrs and isinstance(val, list):
                    out[key].update(val)

                # Dive into any nested dict
                elif isinstance(val, dict):
                    self.collect_phase2_attribute_values(val, phase2_attrs, out,
                                                         path=f"{path}/{key}")

                # Special‐case the 'children' node
                elif key == "children" and isinstance(val, dict):
                    for child_tag, child_list in val.items():
                        for idx, child_data in enumerate(child_list):
                            self.collect_phase2_attribute_values(
                                child_data, phase2_attrs, out,
                                path=f"{path}/children/{child_tag}[{idx}]"
                            )

                # Special‐case the 'phase2' node under Phase-1 results
                elif key == "phase2" and isinstance(val, dict):
                    for el_tag, el_dict in val.items():
                        for el_key, attrs_dict in el_dict.items():
                            self.collect_phase2_attribute_values(
                                attrs_dict, phase2_attrs, out,
                                path=f"{path}/phase2/{el_tag}/{el_key}"
                            )

        return out      
        

    def start_phase2(self):
        """
        Replacement for the old start_phase2.
        If phase1_results is missing, automatically runs extraction with the currently selected attributes.
        Then flips to Phase 2 UI.
        """
        print("\n===== DEBUG start_phase2() CALLED =====")
        self.update_progress(">> DEBUG: start_phase2() called")
        # 1) Collect the attributes you checked on the Extract screen
        selected_attrs = [
            attr for attr, var in getattr(self, "extract_vars", {}).items()
            if var.get()
        ]
        print(f">> DEBUG: selected_attrs for Phase2 = {selected_attrs}")
        self.update_progress(f">> DEBUG: selected_attrs for Phase2 = {selected_attrs}")

        if not selected_attrs:
            msg = "Please select at least one attribute to extract before continuing to Phase 2."
            print(">> DEBUG: No attributes selected! aborting start_phase2.")
            return self._show_error(msg)

        # 2) Ensure Phase 1 results exist; if not, auto-extract them
        if not self.phase1_results:
            print(">> DEBUG: phase1_results empty—auto-extracting now")
            self.update_progress(">> DEBUG: phase1_results empty—auto-extracting now")
            # Run extraction in the main thread (since we're already in the UI thread)
            # This will set self.phase1_results and self.extracted_data
            try:
                # Save current extracted_data in case user returns
                prev_extracted_data = self.extracted_data
                self.extract_and_export()
                # extract_and_export() will call show_export_screen, so we need to force back to Phase 2 UI
                self.current_phase = 2
                self.extracted_data = prev_extracted_data  # Restore if needed
            except Exception as e:
                self._show_error(f"Error during auto-extraction for Phase 2: {e}")
                return

        print(f">> DEBUG: Now have phase1_results keys = {list(self.phase1_results.keys())}")
        self.update_progress(f">> DEBUG: phase1_results groups = {len(self.phase1_results)}")

        # 3) Flip to Phase 2 UI
        self.current_phase = 2
        print(">> DEBUG: Switching to Phase 2 search screen")
        self.update_progress(">> DEBUG: Switching to Phase 2 search screen")
        self.show_search_screen()


    def export_results(self):
        """Export the search results to text format"""
        if not self.extracted_data:
            self._show_error("No data to export.")
            return
        
        # Generate filename with datetime
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        phase_suffix = f"_Phase{self.current_phase}" if self.current_phase > 1 else ""
        default_file = f"XMLAnalysis_Results{phase_suffix}_{now}.txt"
        
        output_file = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt")],
            initialfile=default_file
        )
        
        if output_file:
            try:
                self.generate_text_output(output_file)
                self.update_progress(f"Results exported to {output_file}")
                # Return to the setup screen
                self.current_phase = 1
                self.show_setup_screen()
            except Exception as e:
                error_msg = f"Error exporting to text file: {str(e)}\n{traceback.format_exc()}"
                self._show_error(error_msg)

    def generate_text_output(self, output_file):
        """Generate a hierarchical text output file with proper nesting - CLEAN VERSION"""
        def format_parent_tag(parent_tag, parent_attrs):
            if parent_attrs:
                attrs_str = " ".join(f'{k}="{v}"' for k, v in parent_attrs)
                return f"<{parent_tag} {attrs_str}>"
            else:
                return f"<{parent_tag}>"

        def write_hierarchical_data(f, data, indent=0):
            """Write hierarchical data focusing on clean value display"""
            indent_str = "  " * indent
            
            for value, content in data.items():
                if isinstance(content, dict):
                    # Write the main value
                    f.write(f"{indent_str}{value}\n")
                    
                    # Write direct attributes (non-children, non-phase2)
                    for k, v in content.items():
                        if k not in ['children', 'phase2'] and isinstance(v, list):
                            for item in v:
                                f.write(f"{indent_str}  - {item}\n")
                    
                    # Write children if present
                    if 'children' in content:
                        for child_type, child_list in content['children'].items():
                            for child_data in child_list:
                                write_hierarchical_data(f, child_data, indent + 1)
                    
                    # Write phase2 if present
                    if 'phase2' in content:
                        f.write(f"{indent_str}  Phase 2:\n")
                        for el_tag, el_dict in content['phase2'].items():
                            for el_key, attrs_dict in el_dict.items():
                                has_values = False
                                for attr_name, attr_values in attrs_dict.items():
                                    if attr_values:
                                        has_values = True
                                        break
                                if has_values:
                                    f.write(f"{indent_str}    {el_key}:\n")
                                    for attr_name, attr_values in attrs_dict.items():
                                        for attr_value in attr_values:
                                            f.write(f"{indent_str}      - {attr_value}\n")

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"XML Attribute Analysis Results\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write(f"Phase: {self.current_phase}\n")
            f.write(f"Parent Context: {'Enabled' if self.use_parent_context else 'Disabled'}\n")
            f.write("=" * 80 + "\n\n")

            for parent_key, values_dict in self.extracted_data.items():
                parent_tag, parent_attrs = parent_key
                parent_line = format_parent_tag(parent_tag, parent_attrs)
                f.write(f"{parent_line}\n")
                f.write("-" * 80 + "\n\n")
                
                write_hierarchical_data(f, values_dict)
                f.write("\n")

# ------------------------------------------------------------
# Main entry point
# ------------------------------------------------------------
if __name__ == "__main__":
    # Create the Tk root
    root = tk.Tk()
    root.title("XML Attribute Analyzer")
    root.geometry("1000x800")  # Set a reasonable default size
    
    # Create the app
    app = XMLAttributeAnalyzer(root)
    
    # Start the main loop
    root.mainloop()