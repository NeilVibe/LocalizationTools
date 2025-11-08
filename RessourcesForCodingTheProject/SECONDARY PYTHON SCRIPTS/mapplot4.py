
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

r"""
Crimson Desert – Faction / World-Node visualiser  (Tkinter edition)
────────────────────────────────────────────────────────────────────
 • Hover a town → name(s) + description shown, connected routes light up
 • Short left-click → LQA panel (DONE / TODO / UNCHECK)
 • Drag with the mouse or use the toolbar for pan / zoom
 • “Save to JSON”           → dumps ONLY the decisions of this GUI session
 • “Reload status JSON”     → re-merge every node_status_*.json on disk
 • “Reset unsaved changes”  → wipe the current session (not the files)
The program is completely self-contained – no browser, no localStorage.
Python ≥ 3.8      |      pip install lxml matplotlib
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from lxml import etree as ET
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

# ───────────────────────────────────────────────────────────────────
# CONFIGURATION  – adjust these three folders to match your checkout
# ───────────────────────────────────────────────────────────────────
WAYPOINT_FOLDER = Path(
    r"F:\perforce\cd\mainline\resource\GameData\StaticInfo\factioninfo\NodeWaypointInfo"
)
FACTION_FOLDER = Path(
    r"F:\perforce\cd\mainline\resource\GameData\StaticInfo\factioninfo"
)
LOC_FOLDER = Path(r"F:\perforce\cd\mainline\resource\GameData\stringtable\loc")

LOG_PATH = Path(__file__).with_name(
    f"faction_world_map_gui_{datetime.now():%Y%m%d-%H%M%S}.log"
)

# ───────────────────────────────────────────────────────────────────
# LOGGING
# ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(LOG_PATH, "w", "utf-8")],
)
log = logging.getLogger("FactionMapGUI")

# ───────────────────────────────────────────────────────────────────
# XML sanitiser – battle-hardened
# ───────────────────────────────────────────────────────────────────
_BAD_ENTITY_RE = re.compile(r"&(?!(?:lt|gt|amp|apos|quot);)")
_TAG_OPEN_RE = re.compile(r"<([A-Za-z0-9_]+)(\s[^>/]*)?>")
_TAG_CLOSE_RE = re.compile(r"</\s*([A-Za-z0-9_]+)\s*>")
_CTRL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _patch_bad_entities(txt: str) -> str:
    return _BAD_ENTITY_RE.sub("&amp;", txt)


def _patch_seg_breaks(txt: str) -> str:
    # Replace literal line breaks inside <seg> ... </seg>
    def repl(m: re.Match) -> str:
        inner = m.group(1).replace("\n", "&lt;br/&gt;").replace("\\n", "&lt;br/&gt;")
        return f"<seg>{inner}</seg>"

    return re.sub(r"<seg>(.*?)</seg>", repl, txt, flags=re.S)


def _patch_unterminated_attr(txt: str) -> str:
    # Close un-terminated attribute values
    return re.sub(
        r'="[^"\n<>]*?(?:<|&)|="[^"]*?$',
        lambda m: m.group(0).rstrip("<&") + '"',
        txt,
    )


def sanitize_xml(raw: str) -> str:
    raw = _CTRL_CHAR_RE.sub("", raw)
    raw = _patch_bad_entities(raw)
    raw = _patch_seg_breaks(raw)
    raw = _patch_unterminated_attr(raw)

    tag_stack: List[str] = []
    fixed_lines: List[str] = []

    for line in raw.splitlines():
        s = line.strip()
        m_open = _TAG_OPEN_RE.match(s)
        m_close = _TAG_CLOSE_RE.match(s)

        if m_open and not s.endswith("/>"):
            tag_stack.append(m_open.group(1))
            fixed_lines.append(line)
            continue

        if s.startswith("</>"):
            if tag_stack:
                fixed_lines.append(f"</{tag_stack.pop()}>")
            continue

        if m_close:
            want = m_close.group(1)
            # close any still-open tags that shouldn’t be open
            while tag_stack and tag_stack[-1] != want:
                fixed_lines.append(f"</{tag_stack.pop()}>")
            if tag_stack:
                tag_stack.pop()
            fixed_lines.append(line)
            continue

        fixed_lines.append(line)

    while tag_stack:
        fixed_lines.append(f"</{tag_stack.pop()}>")

    return "\n".join(fixed_lines)


def parse_xml(path: Path) -> Optional[ET._Element]:
    try:
        raw = path.read_text("utf-8", errors="ignore")
    except Exception:
        log.exception("Failed to read %s", path)
        return None

    for mode, txt in (("strict", raw), ("sanitised", sanitize_xml(raw))):
        try:
            return ET.fromstring(
                f"<ROOT>{txt}</ROOT>",
                parser=ET.XMLParser(recover=(mode == "sanitised"), huge_tree=True),
            )
        except ET.XMLSyntaxError:
            continue

    log.warning("XML parse error → %s", path)
    return None


# ───────────────────────────────────────────────────────────────────
# FONT HANDLING  (Tk + Matplotlib) –––––––––––––––––––––────────────
# ───────────────────────────────────────────────────────────────────
def install_korean_font(root: tk.Tk) -> None:
    """
    Force Tk(8.6+) and Matplotlib to use a Hangul-capable font.
    The function is intentionally silent if the font is not available.
    """
    import tkinter.font as tkfont
    from matplotlib import font_manager, rcParams

    # order matters – the first match wins on any given platform
    font_candidates = [
        "Malgun Gothic",          # Windows Vista+
        "맑은 고딕",                # same, Korean name
        "NanumGothic",            # common on Linux distros
        "Noto Sans CJK KR",       # Google/Noto on Linux
        "AppleGothic",            # macOS
    ]

    available_tk = set(tkfont.families(root))
    chosen_font: Optional[str] = None
    for f in font_candidates:
        if f in available_tk:
            chosen_font = f
            break

    if not chosen_font:
        log.warning(
            "No Hangul-capable font from %s found in your system fonts.\n"
            "Korean glyphs may be missing. Install e.g. 'Malgun Gothic' or 'Noto Sans CJK KR'.",
            font_candidates,
        )
        return

    log.info("Using '%s' for all Tk widgets and Matplotlib.", chosen_font)

    # 1) Tkinter – overwrite default named fonts
    for name in (
        "TkDefaultFont",
        "TkTextFont",
        "TkMenuFont",
        "TkHeadingFont",
        "TkFixedFont",
    ):
        try:
            tkfont.nametofont(name).configure(family=chosen_font)
        except tk.TclError:
            pass  # just in case the named style does not exist (very old Tk)

    # 2) Matplotlib – pick first candidate that Matplotlib also knows
    for f in font_candidates:
        if any(f in fm.name for fm in font_manager.fontManager.ttflist):
            rcParams["font.family"] = f
            break

    # Make sure the minus glyph also comes from that font
    rcParams["axes.unicode_minus"] = False


# ───────────────────────────────────────────────────────────────────
# LANGUAGE TABLE
# ───────────────────────────────────────────────────────────────────
def load_eng_table(folder: Path) -> Dict[str, str]:
    eng: Dict[str, str] = {}
    for p in folder.rglob("LanguageData_eng.xml"):
        root = parse_xml(p)
        if root is None:
            continue
        for loc in root.iter("LocStr"):
            kr = loc.get("StrOrigin") or ""
            en = loc.get("Str") or ""
            if kr:
                eng[kr] = en
    log.info("Loaded %d translations", len(eng))
    return eng


# ───────────────────────────────────────────────────────────────────
# FACTION NODES
# ───────────────────────────────────────────────────────────────────
NodeInfo = Tuple[str, str, str, Tuple[float, float]]  # (kr, en, desc, (x, z))


def load_faction_nodes(folder: Path, tr: Dict[str, str]) -> Dict[str, NodeInfo]:
    nodes: Dict[str, NodeInfo] = {}
    for p in folder.rglob("*.xml"):
        root = parse_xml(p)
        if root is None:
            continue
        for fn in root.iter("FactionNode"):
            key = fn.get("StrKey")
            if not key:
                continue

            kr_name = (fn.get("Name") or "").strip()
            if not kr_name:
                continue
            en_name = tr.get(kr_name, kr_name)

            kr_desc = (fn.get("Desc") or "").replace("<br/>", "\n").strip()
            en_desc = tr.get(kr_desc, kr_desc)

            pos = fn.get("WorldPosition") or ""
            parts = re.split(r"[,\s]+", pos.strip())
            if len(parts) >= 3:
                try:
                    x, z = float(parts[0]), float(parts[2])
                except ValueError:
                    continue
                nodes[key] = (kr_name, en_name, en_desc, (x, z))
    log.info("Collected %d explicit FactionNode positions", len(nodes))
    return nodes


# ───────────────────────────────────────────────────────────────────
# ROUTES
# ───────────────────────────────────────────────────────────────────
class Route:
    __slots__ = ("key", "fkey", "tkey", "pts")

    def __init__(
        self,
        key: str,
        fkey: str,
        tkey: str,
        pts: List[Tuple[float, float]],
    ) -> None:
        self.key = key
        self.fkey = fkey
        self.tkey = tkey
        self.pts = pts


def load_routes(folder: Path) -> List[Route]:
    routes: List[Route] = []
    for p in folder.rglob("*.xml"):
        root = parse_xml(p)
        if root is None:
            continue
        for wp in root.iter("NodeWayPointInfo"):
            key = wp.get("Key") or p.stem
            fkey = (wp.get("FromNodeKey") or "").strip()
            tkey = (wp.get("ToNodeKey") or "").strip()
            pts: List[Tuple[float, float]] = []
            for wpos in wp.iter("WorldPosition"):
                raw = wpos.get("Position") or ""
                parts = re.split(r"[,\s]+", raw.strip())
                if len(parts) >= 3:
                    try:
                        x, z = float(parts[0]), float(parts[2])
                        pts.append((x, z))
                    except ValueError:
                        pass
            if pts:
                routes.append(Route(key, fkey, tkey, pts))
    log.info("Loaded %d routes", len(routes))
    return routes


# ───────────────────────────────────────────────────────────────────
# ADJACENCY
# ───────────────────────────────────────────────────────────────────
def build_adjacency(routes: List[Route]) -> Dict[str, set]:
    adj: Dict[str, set] = defaultdict(set)
    for r in routes:
        if r.fkey and r.tkey:
            adj[r.fkey].add(r.tkey)
            adj[r.tkey].add(r.fkey)
    return adj


# ───────────────────────────────────────────────────────────────────
# MERGE node_status_*.json
# ───────────────────────────────────────────────────────────────────
Decision = Dict[str, str]  # {'by': str, 'date': str, 'status': str}


def load_status_files(folder: Path) -> Dict[str, List[Decision]]:
    merged: Dict[str, List[Decision]] = defaultdict(list)
    for p in folder.glob("node_status_*.json"):
        try:
            payload = json.loads(p.read_text("utf-8"))
        except Exception as e:
            log.warning("Cannot read %s: %s", p, e)
            continue

        data_section = payload.get("data") if isinstance(payload, dict) else None
        if data_section is None and isinstance(payload, dict):
            data_section = payload  # legacy structure

        if not isinstance(data_section, dict):
            continue

        for nk, entries in data_section.items():
            if isinstance(entries, list):
                merged[nk].extend(
                    e
                    for e in entries
                    if isinstance(e, dict)
                    and {"by", "date", "status"}.issubset(e.keys())
                )
            elif isinstance(entries, str):
                merged[nk].append(
                    {
                        "by": payload.get("meta", {}).get("author", "unknown"),
                        "date": payload.get("meta", {}).get("saved", ""),
                        "status": entries,
                    }
                )

    # deduplicate
    for k in list(merged):
        uniq: List[Decision] = []
        seen = set()
        for d in merged[k]:
            key = (d["by"], d["date"], d["status"])
            if key not in seen:
                seen.add(key)
                uniq.append(d)
        merged[k] = sorted(uniq, key=lambda e: e["date"])
    log.info("Merged %d status files, %d nodes affected", len(list(folder.glob('node_status_*.json'))), len(merged))
    return merged


def colour_for_status(st: str) -> str:
    return {"done": "green", "todo": "red"}.get(st, "crimson")


# ───────────────────────────────────────────────────────────────────
# GUI (Tkinter + Matplotlib)
# ───────────────────────────────────────────────────────────────────
class App:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Crimson Desert – World nodes")

        # Ensure Korean glyphs are available everywhere
        install_korean_font(self.root)

        self.username: Optional[str] = None

        # ---------------- data ----------------
        self.eng = load_eng_table(LOC_FOLDER)
        self.routes = load_routes(WAYPOINT_FOLDER)
        self.adj = build_adjacency(self.routes)
        self.nodes = load_faction_nodes(FACTION_FOLDER, self.eng)

        # synthesise nodes referenced only in routes
        for r in self.routes:
            if r.fkey and r.fkey not in self.nodes:
                self.nodes[r.fkey] = (r.fkey, self.eng.get(r.fkey, r.fkey), "", r.pts[0])
            if r.tkey and r.tkey not in self.nodes:
                self.nodes[r.tkey] = (r.tkey, self.eng.get(r.tkey, r.tkey), "", r.pts[-1])

        self.history: Dict[str, List[Decision]] = load_status_files(Path.cwd())
        self.session_changes: Dict[str, List[Decision]] = {}

        self.node_keys: List[str] = []
        self.node_positions: List[Tuple[float, float]] = []
        for k, (_, _, _, (x, z)) in self.nodes.items():
            self.node_keys.append(k)
            self.node_positions.append((x, z))

        # ---------------- figure ----------------
        self.fig: Figure = Figure(figsize=(13, 8), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_title("Crimson Desert – World Nodes  (hover = routes | click = LQA panel)")
        self.ax.set_xlabel("World X")
        self.ax.set_ylabel("World Z")

        xs, ys = zip(*self.node_positions)
        dx = (max(xs) - min(xs)) * 0.02 or 1
        dy = (max(ys) - min(ys)) * 0.02 or 1
        self.ax.set_xlim(min(xs) - dx, max(xs) + dx)
        self.ax.set_ylim(min(ys) - dy, max(ys) + dy)
        self.ax.set_aspect("equal", adjustable="box")

        self.scatter = self.ax.scatter(
            xs,
            ys,
            s=30,
            c=[self.initial_colour(k) for k in self.node_keys],
            picker=True,
            zorder=3,
            edgecolor="k",
            linewidths=0.5,
        )

        # routes (Line2D), initially invisible (alpha = 0)
        self.route_lines: List[matplotlib.lines.Line2D] = []
        self.key2lines: Dict[str, List[int]] = defaultdict(list)
        for r in self.routes:
            x_r = [p[0] for p in r.pts]
            y_r = [p[1] for p in r.pts]
            ln, = self.ax.plot(
                x_r, y_r, color="royalblue", linewidth=1.5, alpha=0.0, zorder=1
            )
            idx = len(self.route_lines)
            self.route_lines.append(ln)
            if r.fkey:
                self.key2lines[r.fkey].append(idx)
            if r.tkey:
                self.key2lines[r.tkey].append(idx)

        # annotation for hover
        self.annot = self.ax.annotate(
            "",
            xy=(0, 0),
            xytext=(15, 15),
            textcoords="offset points",
            bbox=dict(boxstyle="round", fc="w"),
            arrowprops=dict(arrowstyle="->"),
        )
        self.annot.set_visible(False)

        # ---------------- Tk canvas ----------------
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # ---------------- toolbar ----------------
        toolbar = matplotlib.backends.backend_tkagg.NavigationToolbar2Tk(
            self.canvas, self.root
        )
        toolbar.update()

        # ---------------- buttons ----------------
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(fill=tk.X, padx=4, pady=4)

        tk.Button(btn_frame, text="Save to JSON", command=self.save_json).pack(side=tk.LEFT, padx=4)
        tk.Button(btn_frame, text="Reload status JSON", command=self.reload_status).pack(side=tk.LEFT, padx=4)
        tk.Button(btn_frame, text="Reset unsaved changes", command=self.reset_session).pack(side=tk.LEFT, padx=4)
        tk.Button(btn_frame, text="Quit", command=self.root.destroy).pack(side=tk.RIGHT)

        # ---------------- mpl events ----------------
        self.fig.canvas.mpl_connect("motion_notify_event", self.on_move)
        self.fig.canvas.mpl_connect("pick_event", self.on_pick)
        self.fig.canvas.mpl_connect("figure_leave_event", self.on_leave)
        self.fig.tight_layout()

        # LQA panel (hidden by default)
        self.panel: Optional[tk.Toplevel] = None
        self.current_pick: Optional[Tuple[int, str]] = None  # (index, node_key)

    # ───────────────────────── helpers ─────────────────────────
    def initial_colour(self, node_key: str) -> str:
        hist = self.history.get(node_key)
        return colour_for_status(hist[-1]["status"]) if hist else "crimson"

    def refresh_node_colours(self) -> None:
        self.scatter.set_color([self.initial_colour(k) for k in self.node_keys])
        self.fig.canvas.draw_idle()

    # ───────────────────────── events ─────────────────────────
    def hide_all_routes(self) -> None:
        for ln in self.route_lines:
            ln.set_alpha(0.0)

    def on_move(self, event):
        if not event.inaxes:
            self.annot.set_visible(False)
            self.hide_all_routes()
            self.fig.canvas.draw_idle()
            return

        cont, ind = self.scatter.contains(event)
        if cont:
            idx = ind["ind"][0]
            x, y = self.node_positions[idx]
            node_key = self.node_keys[idx]
            kr_name, en_name, desc, _ = self.nodes[node_key]

            # build annotation text
            if en_name == kr_name:
                label = en_name
            else:
                label = f"{en_name}\nKR: {kr_name}"
            if desc:
                # trim excessively long descriptions
                desc_short = (desc[:117] + "...") if len(desc) > 120 else desc
                label += f"\n\n{desc_short}"

            # update annotation
            self.annot.xy = (x, y)
            self.annot.set_text(label)
            self.annot.set_visible(True)

            # show connected routes
            self.hide_all_routes()
            for line_idx in self.key2lines.get(node_key, []):
                self.route_lines[line_idx].set_alpha(1.0)
            self.fig.canvas.draw_idle()
        else:
            self.annot.set_visible(False)
            self.hide_all_routes()
            self.fig.canvas.draw_idle()

    def on_leave(self, _event):
        self.annot.set_visible(False)
        self.hide_all_routes()
        self.fig.canvas.draw_idle()

    def on_pick(self, event):
        if event.mouseevent.button != 1:  # left mouse only
            return
        idx = event.ind[0]
        node_key = self.node_keys[idx]
        self.open_panel(idx, node_key)

    # ───────────────────────── LQA panel ─────────────────────────
    def open_panel(self, idx: int, node_key: str):
        # close previous panel
        if self.panel is not None:
            self.panel.destroy()

        self.current_pick = (idx, node_key)

        self.panel = tk.Toplevel(self.root)
        self.panel.transient(self.root)
        self.panel.title(f"{self.nodes[node_key][1]}  ({node_key})")

        # position near current mouse pointer
        x_root = self.root.winfo_pointerx()
        y_root = self.root.winfo_pointery()
        self.panel.geometry(f"+{x_root + 20}+{y_root + 20}")
        self.panel.resizable(False, False)

        # history list
        tk.Label(self.panel, text="History:", font=("Arial", 9, "bold")).pack(anchor="w", padx=6, pady=(6, 0))
        hist_box = tk.Text(self.panel, width=38, height=6, state="normal")
        hist_box.pack(padx=6, pady=4)
        hist_box.tag_configure("done", foreground="green")
        hist_box.tag_configure("todo", foreground="red")

        for rec in self.history.get(node_key, []):
            tag = rec["status"]
            hist_box.insert(
                "end",
                f"{rec['date'][:19]}  {rec['by']:<12}  {rec['status'].upper()}\n",
                tag,
            )
        hist_box.config(state="disabled")

        # buttons
        btn_frame = tk.Frame(self.panel)
        btn_frame.pack(pady=6)

        tk.Button(
            btn_frame, text="LQA DONE", width=10, command=lambda: self.add_decision("done")
        ).pack(side=tk.LEFT, padx=4)
        tk.Button(
            btn_frame, text="NEED CHECK", width=10, command=lambda: self.add_decision("todo")
        ).pack(side=tk.LEFT, padx=4)
        tk.Button(
            btn_frame, text="UNCHECK", width=10, command=self.undo_last_decision
        ).pack(side=tk.LEFT, padx=4)

    def add_decision(self, status_value: str):
        if self.current_pick is None:
            return
        idx, node_key = self.current_pick
        now_iso = datetime.utcnow().isoformat(timespec="seconds")

        if not self.username:
            self.username = (
                simpledialog.askstring("Your name", "Enter your name:", parent=self.root)
                or "unknown"
            )

        entry: Decision = {"by": self.username, "date": now_iso, "status": status_value}

        self.history.setdefault(node_key, []).append(entry)
        self.session_changes.setdefault(node_key, []).append(entry)

        # set colour
        rgba = matplotlib.colors.to_rgba(colour_for_status(status_value))
        self.scatter._facecolors[idx] = rgba
        self.scatter._edgecolors[idx] = matplotlib.colors.to_rgba("black")
        self.fig.canvas.draw_idle()

        if self.panel is not None:
            self.panel.destroy()
            self.panel = None
        self.current_pick = None

    def undo_last_decision(self):
        if self.current_pick is None:
            return
        idx, node_key = self.current_pick
        changed = False

        # remove from session_changes first
        if node_key in self.session_changes and self.session_changes[node_key]:
            self.session_changes[node_key].pop()
            if not self.session_changes[node_key]:
                del self.session_changes[node_key]
            changed = True

        # remove from history
        if self.history.get(node_key):
            self.history[node_key].pop()
            if not self.history[node_key]:
                del self.history[node_key]
            changed = True

        if changed:
            new_col = self.initial_colour(node_key)
            rgba = matplotlib.colors.to_rgba(new_col)
            self.scatter._facecolors[idx] = rgba
            self.fig.canvas.draw_idle()

        if self.panel is not None:
            self.panel.destroy()
            self.panel = None
        self.current_pick = None

    # ───────────────────────── save / reload / reset ─────────────────────────
    def save_json(self):
        if not self.session_changes:
            messagebox.showinfo("Save to JSON", "No new decisions to save.")
            return

        if not self.username:
            self.username = (
                simpledialog.askstring("Your name", "Enter your name:", parent=self.root)
                or "unknown"
            )

        stamp = datetime.utcnow().isoformat(timespec="seconds").replace(":", "-")
        safe_user = re.sub(r"\W+", "_", self.username)  # sanitise for filenames
        fname = f"node_status_{safe_user}_{stamp}.json"

        payload = {
            "meta": {"author": self.username, "saved": datetime.utcnow().isoformat()},
            "data": self.session_changes,
        }

        try:
            with open(fname, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2)
            messagebox.showinfo("Save to JSON", f"Wrote {fname}")
            # clear session changes but leave colours as they are
            self.session_changes.clear()
        except Exception as e:
            messagebox.showerror("Save to JSON", f"Cannot write file:\n{e}")

    def reload_status(self):
        self.history = load_status_files(Path.cwd())
        # keep unsaved changes visible
        for k, lst in self.session_changes.items():
            self.history.setdefault(k, []).extend(lst)
        self.refresh_node_colours()
        messagebox.showinfo("Reload", "Status JSON reloaded and colours refreshed.")

    def reset_session(self):
        if not self.session_changes:
            return
        if not messagebox.askyesno("Reset", "Discard ALL unsaved decisions?"):
            return
        self.session_changes.clear()
        self.history = load_status_files(Path.cwd())
        self.refresh_node_colours()

    # ───────────────────────── run ─────────────────────────
    def run(self):
        self.root.mainloop()


# ───────────────────────────────────────────────────────────────────
# main
# ───────────────────────────────────────────────────────────────────
def main():
    # sanity-check folders
    for p in (WAYPOINT_FOLDER, FACTION_FOLDER, LOC_FOLDER):
        if not p.is_dir():
            log.error("Folder not found: %s", p)
            sys.exit(1)

    App().run()


if __name__ == "__main__":
    main()
