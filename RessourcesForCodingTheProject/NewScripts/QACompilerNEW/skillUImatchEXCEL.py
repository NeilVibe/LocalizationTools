
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GUI file picker + tolerant parser for the provided (XML-like) SkillTreeInfo/SkillNode/StatNode text.

It lists nodes sorted TOP-LEFT -> BOTTOM-RIGHT using UIPositionXY in the MAIN frame.

Sorting (main frame):
  1) y ascending (top to bottom)
  2) x ascending (left to right)

Notes:
- UIPositionXY is treated as the "actual position".
- UIPosition is treated as a "subframe/grid position" and is shown only as extra info.
- Input is NOT valid XML (has </> etc), so this uses a tolerant regex parser.

How to run:
  python list_skills_by_xy_gui.py

What you get:
- A file dialog to choose your text file
- Optional filters (Tree Key / Character / Page Name)
- Output shown in a scrollable text box
- "Save Output..." button to save the sorted list
"""

from __future__ import annotations

import re
import tkinter as tk
from dataclasses import dataclass
from tkinter import filedialog, messagebox, ttk
from typing import Dict, Iterable, List, Optional, Tuple


SKILLTREE_OPEN_RE = re.compile(r"<SkillTreeInfo\b([^>]*)>", re.IGNORECASE)
SKILLTREE_CLOSE_RE = re.compile(r"</SkillTreeInfo\s*>", re.IGNORECASE)

# Match self-closing nodes like:
#   <SkillNode .../>
#   <StatNode .../>
# Also match non-self-closing open tags like:
#   <SkillNode ...>
NODE_OPEN_RE = re.compile(r"<(SkillNode|StatNode)\b([^>/]*?)(/?)>", re.IGNORECASE)

ATTR_RE = re.compile(r'(\w+)\s*=\s*"([^"]*)"', re.IGNORECASE)

# UIPositionXY="640 270" (space-separated ints, may be negative)
UIXY_RE = re.compile(r"^\s*(-?\d+)\s+(-?\d+)\s*$")


@dataclass(frozen=True)
class Node:
    tree_key: str
    tree_strkey: str
    character_key: str
    page_name: str
    node_tag: str  # SkillNode or StatNode
    id: str
    best_key: str  # SkillKey / ResearchKey / KnowledgeKey / ItemKey / SubLevelKey
    ui_xy: Optional[Tuple[int, int]]
    ui_position: Optional[str]
    ui_node_type: Optional[str]
    raw_attrs: Dict[str, str]


@dataclass(frozen=True)
class SkillTree:
    key: str
    strkey: str
    character_key: str
    page_name: str
    raw_attrs: Dict[str, str]


def parse_attrs(attr_text: str) -> Dict[str, str]:
    return {m.group(1): m.group(2) for m in ATTR_RE.finditer(attr_text)}


def pick_best_key(attrs: Dict[str, str]) -> str:
    for k in ("SkillKey", "ResearchKey", "KnowledgeKey", "ItemKey", "SubLevelKey"):
        if k in attrs:
            return attrs[k]
    return ""


def parse_uixy(attrs: Dict[str, str]) -> Optional[Tuple[int, int]]:
    v = attrs.get("UIPositionXY")
    if not v:
        return None
    m = UIXY_RE.match(v)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def iter_trees_and_nodes(text: str) -> Tuple[List[SkillTree], List[Node]]:
    trees: List[SkillTree] = []
    nodes: List[Node] = []

    i = 0
    n = len(text)
    current_tree: Optional[SkillTree] = None

    while i < n:
        candidates = []

        m_open = SKILLTREE_OPEN_RE.search(text, i)
        if m_open:
            candidates.append(("tree_open", m_open.start(), m_open))

        m_close = SKILLTREE_CLOSE_RE.search(text, i)
        if m_close:
            candidates.append(("tree_close", m_close.start(), m_close))

        m_node = NODE_OPEN_RE.search(text, i)
        if m_node:
            candidates.append(("node", m_node.start(), m_node))

        if not candidates:
            break

        kind, _, m = min(candidates, key=lambda t: t[1])
        i = m.end()

        if kind == "tree_open":
            attrs = parse_attrs(m.group(1))
            current_tree = SkillTree(
                key=attrs.get("Key", ""),
                strkey=attrs.get("StrKey", ""),
                character_key=attrs.get("CharacterKey", ""),
                page_name=attrs.get("UIPageName", ""),
                raw_attrs=attrs,
            )
            trees.append(current_tree)

        elif kind == "tree_close":
            current_tree = None

        else:  # node
            if current_tree is None:
                continue

            tag = m.group(1)
            attrs = parse_attrs(m.group(2))
            nodes.append(
                Node(
                    tree_key=current_tree.key,
                    tree_strkey=current_tree.strkey,
                    character_key=current_tree.character_key,
                    page_name=current_tree.page_name,
                    node_tag=tag,
                    id=attrs.get("Id", ""),
                    best_key=pick_best_key(attrs),
                    ui_xy=parse_uixy(attrs),
                    ui_position=attrs.get("UIPosition"),
                    ui_node_type=attrs.get("UISkillTreeNodeType"),
                    raw_attrs=attrs,
                )
            )

    return trees, nodes


def sort_nodes_main_frame(nodes: Iterable[Node]) -> List[Node]:
    def keyfn(node: Node):
        assert node.ui_xy is not None
        x, y = node.ui_xy
        return (y, x)

    return sorted(nodes, key=keyfn)


def format_node_line(idx: int, node: Node) -> str:
    x, y = node.ui_xy if node.ui_xy else ("?", "?")
    extra = []
    if node.ui_node_type:
        extra.append(f"type={node.ui_node_type}")
    if node.ui_position:
        extra.append(f"grid={node.ui_position}")
    extra_s = (" | " + ", ".join(extra)) if extra else ""
    label = node.best_key or "(no key)"
    return f"{idx:03d}. ({x:>4}, {y:>4})  [{node.node_tag}] Id={node.id}  Key={label}{extra_s}"


def build_output(
    text: str,
    tree_key: str = "",
    character: str = "",
    page_name: str = "",
    skills_only: bool = False,
    include_stat: bool = True,
    include_missing_xy: bool = False,
) -> str:
    trees, nodes = iter_trees_and_nodes(text)

    # Filter
    filtered: List[Node] = []
    for node in nodes:
        if tree_key.strip() and node.tree_key != tree_key.strip():
            continue
        if character.strip() and node.character_key != character.strip():
            continue
        if page_name.strip() and node.page_name != page_name.strip():
            continue
        if skills_only and node.node_tag.lower() != "skillnode":
            continue
        if (not include_stat) and node.node_tag.lower() == "statnode":
            continue
        filtered.append(node)

    with_xy = [n for n in filtered if n.ui_xy is not None]
    without_xy = [n for n in filtered if n.ui_xy is None]
    ordered = sort_nodes_main_frame(with_xy)

    scope = []
    if tree_key.strip():
        scope.append(f"tree_key={tree_key.strip()}")
    if character.strip():
        scope.append(f"character={character.strip()}")
    if page_name.strip():
        scope.append(f"page_name={page_name.strip()}")
    scope_s = ", ".join(scope) if scope else "ALL"

    lines: List[str] = []
    lines.append(f"# Sorted by MAIN frame UIPositionXY (y asc, then x asc) | scope: {scope_s}")
    lines.append(f"# count(with XY)={len(ordered)}  count(missing XY)={len(without_xy)}")
    lines.append("")

    for idx, node in enumerate(ordered, 1):
        lines.append(format_node_line(idx, node))

    if include_missing_xy and without_xy:
        lines.append("")
        lines.append("# Nodes missing UIPositionXY (not sortable by main frame; listed after):")
        for node in without_xy:
            extra = []
            if node.ui_node_type:
                extra.append(f"type={node.ui_node_type}")
            if node.ui_position:
                extra.append(f"grid={node.ui_position}")
            extra_s = (" | " + ", ".join(extra)) if extra else ""
            label = node.best_key or "(no key)"
            lines.append(f"???. (   ?,    ?)  [{node.node_tag}] Id={node.id}  Key={label}{extra_s}")

    return "
".join(lines) + "
"


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("SkillTree UIPositionXY Sorter (Main Frame)")
        self.geometry("1100x750")

        self.file_path_var = tk.StringVar(value="")
        self.tree_key_var = tk.StringVar(value="")
        self.character_var = tk.StringVar(value="")
        self.page_name_var = tk.StringVar(value="")

        self.skills_only_var = tk.BooleanVar(value=False)
        self.include_stat_var = tk.BooleanVar(value=True)
        self.include_missing_xy_var = tk.BooleanVar(value=False)

        self._build_ui()

    def _build_ui(self) -> None:
        top = ttk.Frame(self, padding=10)
        top.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(top, text="Input file:").grid(row=0, column=0, sticky="w")
        entry = ttk.Entry(top, textvariable=self.file_path_var, width=80)
        entry.grid(row=0, column=1, sticky="we", padx=(8, 8))

        ttk.Button(top, text="Browse...", command=self.on_browse).grid(row=0, column=2, sticky="e")
        ttk.Button(top, text="Parse + Sort", command=self.on_parse).grid(row=0, column=3, sticky="e", padx=(8, 0))

        # Filters
        filters = ttk.LabelFrame(self, text="Filters (optional)", padding=10)
        filters.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(0, 10))

        ttk.Label(filters, text="Tree Key:").grid(row=0, column=0, sticky="w")
        ttk.Entry(filters, textvariable=self.tree_key_var, width=12).grid(row=0, column=1, sticky="w", padx=(6, 18))

        ttk.Label(filters, text="CharacterKey:").grid(row=0, column=2, sticky="w")
        ttk.Entry(filters, textvariable=self.character_var, width=16).grid(row=0, column=3, sticky="w", padx=(6, 18))

        ttk.Label(filters, text="UIPageName:").grid(row=0, column=4, sticky="w")
        ttk.Entry(filters, textvariable=self.page_name_var, width=28).grid(row=0, column=5, sticky="w", padx=(6, 0))

        opts = ttk.Frame(self, padding=(10, 0, 10, 10))
        opts.pack(side=tk.TOP, fill=tk.X)

        ttk.Checkbutton(opts, text="Skills only (exclude StatNode)", variable=self.skills_only_var).pack(
            side=tk.LEFT, padx=(0, 16)
        )
        ttk.Checkbutton(opts, text="Include StatNode", variable=self.include_stat_var).pack(side=tk.LEFT, padx=(0, 16))
        ttk.Checkbutton(opts, text="Include nodes missing UIPositionXY (at end)", variable=self.include_missing_xy_var).pack(
            side=tk.LEFT
        )

        # Output
        out_frame = ttk.Frame(self, padding=10)
        out_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.text = tk.Text(out_frame, wrap="none")
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        yscroll = ttk.Scrollbar(out_frame, orient="vertical", command=self.text.yview)
        yscroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.text.configure(yscrollcommand=yscroll.set)

        xscroll = ttk.Scrollbar(self, orient="horizontal", command=self.text.xview)
        xscroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.text.configure(xscrollcommand=xscroll.set)

        bottom = ttk.Frame(self, padding=10)
        bottom.pack(side=tk.BOTTOM, fill=tk.X)

        ttk.Button(bottom, text="Save Output...", command=self.on_save).pack(side=tk.RIGHT)
        ttk.Button(bottom, text="Clear", command=self.on_clear).pack(side=tk.RIGHT, padx=(0, 8))

    def on_browse(self) -> None:
        path = filedialog.askopenfilename(
            title="Select SkillTree text file",
            filetypes=[
                ("Text / XML-like files", "*.txt *.xml *.cfg *.dat *.ini *.log"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self.file_path_var.set(path)

    def on_parse(self) -> None:
        path = self.file_path_var.get().strip()
        if not path:
            messagebox.showerror("No file", "Please choose an input file first (Browse...).")
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception as e:
            messagebox.showerror("Read error", f"Failed to read file:
{e}")
            return

        try:
            output = build_output(
                text=text,
                tree_key=self.tree_key_var.get(),
                character=self.character_var.get(),
                page_name=self.page_name_var.get(),
                skills_only=self.skills_only_var.get(),
                include_stat=self.include_stat_var.get(),
                include_missing_xy=self.include_missing_xy_var.get(),
            )
        except Exception as e:
            messagebox.showerror("Parse error", f"Failed to parse/sort:
{e}")
            return

        self.text.delete("1.0", tk.END)
        self.text.insert(tk.END, output)

    def on_save(self) -> None:
        content = self.text.get("1.0", tk.END).strip("
")
        if not content.strip():
            messagebox.showerror("Nothing to save", "Output is empty. Click 'Parse + Sort' first.")
            return

        path = filedialog.asksaveasfilename(
            title="Save output",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content + "
")
        except Exception as e:
            messagebox.showerror("Save error", f"Failed to save:
{e}")
            return

        messagebox.showinfo("Saved", f"Saved to:
{path}")

    def on_clear(self) -> None:
        self.text.delete("1.0", tk.END)


def main() -> int:
    app = App()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())