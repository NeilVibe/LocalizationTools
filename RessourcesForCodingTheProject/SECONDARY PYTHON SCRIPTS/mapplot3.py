
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

r"""
Crimson Desert – Faction / World-Node visualiser
────────────────────────────────────────────────
• Hover a town to see its name → all connected
  routes are shown automatically.
• SHORT left-click on a town → open the LQA panel
  (mark “LQA DONE” / “NEED CHECK”, see history).
• Keep the left button pressed and move the mouse
  anywhere to PAN the map.
• Right mouse button does absolutely nothing.
• “Save to JSON” dumps ONLY the decisions you made
  in this browser session into a new file
  `node_status_<yourname>_<timestamp>.json`.
  Nothing is written until you press that button.
• On start-up every existing `node_status_*.json`
  found in the working directory is merged and the
  last vote per node is used to colour the pins.
• The generated HTML is self-contained, works 100 %
  offline and remembers unsaved work via
  `localStorage` (auto-restore after reload).
────────────────────────────────────────────────
Python 3.8+          |     pip install lxml plotly
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

import plotly.graph_objects as go
import plotly.io as pio
from lxml import etree as ET

# ──────────────────────────────────────────────────────────────────────
# CONFIGURATION – adjust the three folders to match your checkout
# ──────────────────────────────────────────────────────────────────────
WAYPOINT_FOLDER = Path(
    r"F:\perforce\cd\mainline\resource\GameData\StaticInfo\factioninfo\NodeWaypointInfo"
)
FACTION_FOLDER = Path(
    r"F:\perforce\cd\mainline\resource\GameData\StaticInfo\factioninfo"
)
LOC_FOLDER = Path(r"F:\perforce\cd\mainline\resource\GameData\stringtable\loc")

OUT_HTML = Path(__file__).with_name("faction_world_map.html")
LOG_PATH = Path(__file__).with_name(
    f"faction_world_map_{datetime.now():%Y%m%d-%H%M%S}.log"
)

# ──────────────────────────────────────────────────────────────────────
# LOGGING (console + file; DEBUG verbosity)
# ──────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(LOG_PATH, "w", "utf-8")],
)
log = logging.getLogger("FactionMap")

# ──────────────────────────────────────────────────────────────────────
# XML SANITISER  –  battle-hardened against CD quirks
# ──────────────────────────────────────────────────────────────────────
_BAD_ENTITY_RE = re.compile(r"&(?!(?:lt|gt|amp|apos|quot);)")
_TAG_OPEN_RE = re.compile(r"<([A-Za-z0-9_]+)(\s[^>/]*)?>")
_TAG_CLOSE_RE = re.compile(r"</\s*([A-Za-z0-9_]+)\s*>")
_CTRL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _patch_bad_entities(txt: str) -> str:
    return _BAD_ENTITY_RE.sub("&amp;", txt)


def _patch_seg_breaks(txt: str) -> str:
    def repl(m: re.Match) -> str:
        inner = m.group(1).replace("\n", "&lt;br/&gt;").replace("\\n", "&lt;br/&gt;")
        return f"<seg>{inner}</seg>"

    return re.sub(r"<seg>(.*?)</seg>", repl, txt, flags=re.S)


def _patch_unterminated_attr(txt: str) -> str:
    return re.sub(
        r'="[^"\n<>]*?(?:<|&)|="[^"]*?$', lambda m: m.group(0).rstrip("<&") + '"', txt
    )


def sanitize_xml(raw: str) -> str:
    raw = _CTRL_CHAR_RE.sub("", raw)
    raw = _patch_bad_entities(raw)
    raw = _patch_seg_breaks(raw)
    raw = _patch_unterminated_attr(raw)

    tag_stack: List[str] = []
    fixed: List[str] = []

    for line in raw.splitlines():
        s = line.strip()
        m_open = _TAG_OPEN_RE.match(s)
        m_close = _TAG_CLOSE_RE.match(s)

        if m_open and not s.endswith("/>"):
            tag_stack.append(m_open.group(1))
            fixed.append(line)
            continue

        if s.startswith("</>"):
            if tag_stack:
                fixed.append(f"</{tag_stack.pop()}>")
            continue

        if m_close:
            want = m_close.group(1)
            while tag_stack and tag_stack[-1] != want:
                fixed.append(f"</{tag_stack.pop()}>")
            if tag_stack:
                tag_stack.pop()
            fixed.append(line)
            continue

        fixed.append(line)

    while tag_stack:
        fixed.append(f"</{tag_stack.pop()}>")

    return "\n".join(fixed)


def parse_xml(path: Path) -> Optional[ET._Element]:
    log.debug("Reading XML → %s", path)
    try:
        raw = path.read_text("utf-8", errors="ignore")
    except Exception:
        log.exception("Failed to read %s", path)
        return None

    for mode, text in (("strict", raw), ("sanitised", sanitize_xml(raw))):
        try:
            root = ET.fromstring(
                f"<ROOT>{text}</ROOT>",
                parser=ET.XMLParser(recover=(mode == "sanitised"), huge_tree=True),
            )
            log.debug("Parsed OK (%s) – %s", mode, path)
            return root
        except ET.XMLSyntaxError as e:
            log.debug("%s parse failed (%s): %s", mode.capitalize(), path, e)

    log.error("Completely failed to parse %s", path)
    return None


# ──────────────────────────────────────────────────────────────────────
# LANGUAGE TABLE
# ──────────────────────────────────────────────────────────────────────
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
        log.info("Loaded %d translations from %s", len(eng), p)
    if not eng:
        log.warning("No English translations found under %s", folder)
    return eng


# ──────────────────────────────────────────────────────────────────────
# FACTION NODES
# ──────────────────────────────────────────────────────────────────────
# (kr_name, en_name, en_description, (x, z))
NodeInfo = Tuple[str, str, str, Tuple[float, float]]


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
                log.debug(
                    "FactionNode %-38s (%8.1f, %8.1f)  %s / %s",
                    key,
                    x,
                    z,
                    kr_name,
                    en_name,
                )
    log.info("Collected %d explicit FactionNode positions", len(nodes))
    return nodes


# ──────────────────────────────────────────────────────────────────────
# ROUTES
# ──────────────────────────────────────────────────────────────────────
class Route:
    __slots__ = ("key", "fkey", "tkey", "pts")

    def __init__(
        self, key: str, fkey: str, tkey: str, pts: List[Tuple[float, float]]
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
                        log.debug("Bad waypoint '%s' in route %s", raw, key)
            if pts:
                routes.append(Route(key, fkey, tkey, pts))
                log.debug("Route %-8s  %s → %s   pts=%d", key, fkey, tkey, len(pts))
    log.info("Loaded %d routes", len(routes))
    return routes


# ──────────────────────────────────────────────────────────────────────
# ADJACENCY
# ──────────────────────────────────────────────────────────────────────
def build_adjacency(routes: List[Route]) -> Dict[str, set]:
    adj: Dict[str, set] = defaultdict(set)
    for r in routes:
        if r.fkey and r.tkey:
            adj[r.fkey].add(r.tkey)
            adj[r.tkey].add(r.fkey)
    log.info("Built adjacency for %d nodes", len(adj))
    return adj


# ──────────────────────────────────────────────────────────────────────
# MERGE EXISTING JSON FILES
# ──────────────────────────────────────────────────────────────────────
Decision = Dict[str, str]  # {'by': str, 'date': str, 'status': 'done'|'todo'}


def load_status_files(folder: Path) -> Dict[str, List[Decision]]:
    """
    Scan *folder* for every ``node_status_*.json`` file, merge
    the content into a single mapping: node-key → list[decision].
    Duplicates (same by/date/status triple) are discarded.
    Unknown formats are ignored but noted in the log.
    """
    merged: Dict[str, List[Decision]] = defaultdict(list)
    json_files = sorted(folder.glob("node_status_*.json"))
    if not json_files:
        log.info("No existing status JSON files found")
        return {}

    for p in json_files:
        try:
            payload = json.loads(p.read_text("utf-8"))
        except Exception as e:
            log.warning("Cannot read %s: %s", p, e)
            continue

        # Accept two possible structures (legacy or new):
        data_section = None
        if isinstance(payload, dict) and "data" in payload:
            data_section = payload["data"]
        elif isinstance(payload, dict):
            # assume direct mapping node→list OR node→str
            data_section = payload
        else:
            log.warning("Un-recognised JSON structure in %s", p)
            continue

        if not isinstance(data_section, dict):
            log.warning("Bad 'data' section in %s", p)
            continue

        for node_key, entries in data_section.items():
            if isinstance(entries, list):
                for ent in entries:
                    if not (
                        isinstance(ent, dict)
                        and {"by", "date", "status"}.issubset(ent.keys())
                    ):
                        continue
                    merged[node_key].append(ent)
            elif isinstance(entries, str):
                # legacy: single status string, fabricate minimal decision
                merged[node_key].append(
                    {
                        "by": payload.get("meta", {}).get("author", "unknown"),
                        "date": payload.get("meta", {}).get("saved", ""),
                        "status": entries,
                    }
                )
            else:
                continue

    # Deduplicate identical decisions
    for nk, lst in merged.items():
        seen = set()
        uniq: List[Decision] = []
        for d in lst:
            key = (d["by"], d["date"], d["status"])
            if key not in seen:
                seen.add(key)
                uniq.append(d)
        merged[nk] = uniq

    log.info(
        "Merged %d JSON files → %d nodes / %d total decisions",
        len(json_files),
        len(merged),
        sum(len(v) for v in merged.values()),
    )
    return merged


# ──────────────────────────────────────────────────────────────────────
# FIGURE
# ──────────────────────────────────────────────────────────────────────
def build_figure(
    nodes: Dict[str, Tuple[str, str, str, Tuple[float, float]]],
    routes: List[Route],
    adjacency: Dict[str, set],
) -> Tuple[go.Figure, Dict[str, List[int]]]:
    node_x: List[float] = []
    node_y: List[float] = []
    hover_text: List[str] = []
    node_keys: List[str] = []

    for key, (kr, en, desc, (x, z)) in nodes.items():
        node_x.append(x)
        node_y.append(z)
        node_keys.append(key)
        hover_text.append(
            f"<b>{en}</b><br>"
            f"KR: {kr}<br>"
            f"Key: {key}<br>"
            f"X: {x:.1f}   Z: {z:.1f}<br><br>"
            f"{desc}"
        )

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers",
        marker=dict(
            size=7,
            color=["crimson"] * len(node_x),  # will be updated via JS
            line=dict(color="black", width=1),
        ),
        hoverinfo="text",
        hovertext=hover_text,
        customdata=node_keys,  # the StrKey for JS
        name="Nodes",
    )

    fig = go.Figure(data=[node_trace])

    key2traces: Dict[str, List[int]] = defaultdict(list)

    for r in routes:
        xs = [p[0] for p in r.pts]
        ys = [p[1] for p in r.pts]
        trace = go.Scatter(
            x=xs,
            y=ys,
            mode="lines",
            line=dict(width=2, color="royalblue"),
            name=r.key,
            hoverinfo="skip",
            visible=False,
        )
        idx = len(fig.data)
        fig.add_trace(trace)
        if r.fkey:
            key2traces[r.fkey].append(idx)
        if r.tkey:
            key2traces[r.tkey].append(idx)

    xmin, xmax = min(node_x), max(node_x)
    ymin, ymax = min(node_y), max(node_y)
    dx = (xmax - xmin) * 0.02 or 1
    dy = (ymax - ymin) * 0.02 or 1

    fig.update_layout(
        title=(
            "Crimson Desert – World Nodes"
            "<br><span style='font-size:14px;'>hover = show routes &nbsp;&nbsp;|&nbsp;&nbsp;"
            "L-click (no move) = LQA panel &nbsp;&nbsp;|&nbsp;&nbsp;drag = pan</span>"
        ),
        xaxis=dict(
            title="World X",
            scaleanchor="y",
            scaleratio=1,
            range=[xmin - dx, xmax + dx],
            showgrid=True,
            zeroline=False,
        ),
        yaxis=dict(
            title="World Z",
            range=[ymin - dy, ymax + dy],
            showgrid=True,
            zeroline=False,
        ),
        template="plotly_white",
        width=2400,
        height=1500,
        margin=dict(l=50, r=50, t=110, b=40),
        hoverlabel=dict(bgcolor="white", font_size=12),
        showlegend=False,
        dragmode="pan",  # ← default to panning with left mouse button
    )

    return fig, key2traces


# ──────────────────────────────────────────────────────────────────────
# HTML WRITER  (self-contained, robust JS)
# ──────────────────────────────────────────────────────────────────────
def write_html(
    fig: go.Figure,
    mapping: Dict[str, List[int]],
    initial_status: Dict[str, List[Decision]],
    path: Path,
) -> None:
    html = pio.to_html(
        fig,
        full_html=True,
        include_plotlyjs="embed",
        auto_play=False,
        config={
            "scrollZoom": True,
            "displaylogo": False,
            "modeBarButtonsToRemove": ["select2d", "lasso2d", "zoom2d"],
        },
    )

    js = f"""
<script>
(function() {{
    const gd        = document.querySelector('.plotly-graph-div');
    const link      = {json.dumps(mapping, separators=(",", ":"))};
    const history   = {json.dumps(initial_status, separators=(",", ":"))}; // nodeKey → [{{by,date,status}}]
    const colours   = gd.data[0].marker.color.slice();   // copy existing colours
    const keys      = gd.data[0].customdata;
    const LS_KEY    = 'cd_node_lqa_session_v1';
    const DRAG_EPS  = 3;   // px – movement threshold to detect pan vs. click
    let   sessionChanges = Object.create(null);          // decisions in this session
    let   userName  = null;
    let   mouseDown = null;
    let   currentPt = null;

    /* ---------- bootstrap from localStorage ---------- */
    try {{
        const saved = JSON.parse(localStorage.getItem(LS_KEY) || 'null');
        if (saved && typeof saved === 'object') {{
            sessionChanges = saved.sessionChanges || {{}};
            userName       = saved.userName || null;
            // merge into history
            for (const k in sessionChanges) {{
                if (!history[k]) history[k] = [];
                history[k] = history[k].concat(sessionChanges[k]);
            }}
        }}
    }} catch(_) {{}}

    /* ---------- helpers ---------- */
    function colourForStatus(st) {{
        return st === 'done' ? 'green' : (st === 'todo' ? 'red' : 'crimson');
    }}

    function refreshColours() {{
        for (let i = 0; i < keys.length; ++i) {{
            const k = keys[i];
            const h = history[k];
            colours[i] = (h && h.length) ? colourForStatus(h[h.length-1].status) : 'crimson';
        }}
        Plotly.restyle(gd, {{'marker.color': [colours]}}, [0]);
    }}

    refreshColours();

    /* ---------- show / hide routes when hovering ---------- */
    function makeVisibilityMask(indices) {{
        const vis = new Array(gd.data.length).fill(false);
        vis[0] = true;          // always show nodes
        indices.forEach(i => vis[i] = true);
        return [vis];
    }}

    function hideAllRoutes() {{
        Plotly.restyle(gd, {{visible: makeVisibilityMask([])[0]}});
    }}

    gd.on('plotly_hover', ev => {{
        if (!ev.points || !ev.points.length) return;
        const pt = ev.points[0];
        if (pt.data.name !== 'Nodes') return;
        const traces = link[pt.customdata] || [];
        Plotly.restyle(gd, {{visible: makeVisibilityMask(traces)[0]}});
    }});
    gd.on('plotly_unhover', hideAllRoutes);
    hideAllRoutes();

    /* ---------- track mouse movement to detect real clicks ---------- */
    gd.addEventListener('mousedown', e => {{
        if (e.button !== 0) return;     // only L-MB
        mouseDown = {{x: e.clientX, y: e.clientY}};
    }});
    gd.addEventListener('mouseup', () => {{ mouseDown = null; }});

    function isTrueClick(ev) {{
        if (!mouseDown) return false;
        const dx = ev.event.clientX - mouseDown.x;
        const dy = ev.event.clientY - mouseDown.y;
        return Math.hypot(dx, dy) < DRAG_EPS;
    }}

    /* ---------- LQA pop-up panel ---------- */
    const panel = document.createElement('div');
    panel.style.position   = 'fixed';
    panel.style.background = '#fff';
    panel.style.border     = '1px solid #666';
    panel.style.padding    = '8px';
    panel.style.boxShadow  = '2px 2px 6px rgba(0,0,0,.4)';
    panel.style.zIndex     = '999';
    panel.style.display    = 'none';
    panel.style.width      = '260px';
    panel.style.maxHeight  = '60vh';
    panel.style.overflowY  = 'auto';
    document.body.appendChild(panel);

    const title = document.createElement('div');
    title.style.fontWeight   = 'bold';
    title.style.marginBottom = '6px';
    panel.appendChild(title);

    const historyBox = document.createElement('div');
    historyBox.style.fontSize   = '12px';
    historyBox.style.margin     = '6px 0';
    historyBox.style.whiteSpace = 'normal';
    panel.appendChild(historyBox);

    const btnDone = document.createElement('button');
    btnDone.textContent  = 'LQA DONE';
    btnDone.style.marginRight = '8px';
    panel.appendChild(btnDone);

    const btnTodo = document.createElement('button');
    btnTodo.textContent = 'NEED CHECK';
    panel.appendChild(btnTodo);

    function showPanel(clientX, clientY, label, nodeKey) {{
        panel.style.left = (clientX + 12) + 'px';
        panel.style.top  = (clientY + 12) + 'px';
        title.textContent = label;

        historyBox.innerHTML = '';
        const list = history[nodeKey] || [];
        if (list.length) {{
            const ul = document.createElement('ul');
            ul.style.margin = '0';
            ul.style.padding = '0 0 0 14px';
            list.forEach(rec => {{
                const li = document.createElement('li');
                li.textContent = `${{rec.status.toUpperCase()}} by ${{rec.by || '(unsaved)'}} @ ${{rec.date}}`;
                li.style.color = colourForStatus(rec.status);
                ul.appendChild(li);
            }});
            historyBox.appendChild(ul);
        }} else {{
            historyBox.textContent = '(no votes yet)';
        }}
        panel.style.display = 'block';
    }}

    function hidePanel() {{
        panel.style.display = 'none';
        currentPt = null;
    }}

    function addDecision(statusValue) {{
        if (!currentPt) return;
        const idx = currentPt.pointNumber;
        const key = currentPt.customdata;
        const now = new Date().toISOString();
        const entry = {{by: userName || '', date: now, status: statusValue}};

        if (!history[key]) history[key] = [];
        history[key].push(entry);

        if (!sessionChanges[key]) sessionChanges[key] = [];
        sessionChanges[key].push(entry);

        // persist to localStorage
        localStorage.setItem(LS_KEY, JSON.stringify({{sessionChanges, userName}}));

        colours[idx] = colourForStatus(statusValue);
        Plotly.restyle(gd, {{'marker.color': [colours]}}, [0]);
        hidePanel();
    }}

    btnDone.onclick = () => addDecision('done');
    btnTodo.onclick = () => addDecision('todo');

    gd.on('plotly_click', ev => {{
        if (!ev.points || !ev.points.length) return;
        if (ev.event && ev.event.button !== 0) return;      // ignore RMB/MMB
        if (!isTrueClick(ev)) return;                       // ignore pans

        const pt = ev.points[0];
        if (pt.data.name !== 'Nodes') return;

        currentPt = pt;
        const nodeKey = pt.customdata;
        const label = pt.hovertext.split('<br>')[0].replace(/<[^>]+>/g, '');
        showPanel(ev.event.clientX, ev.event.clientY, label, nodeKey);
    }});

    // close panel on Escape or click outside
    document.addEventListener('keydown', e => {{ if (e.key === 'Escape') hidePanel(); }});
    document.addEventListener('mousedown', e => {{
        if (!panel.contains(e.target)) hidePanel();
    }});

    /* ---------- SAVE to JSON ---------- */
    const exportBtn = document.createElement('button');
    exportBtn.textContent = 'Save to JSON';
    exportBtn.style.position = 'fixed';
    exportBtn.style.right = '20px';
    exportBtn.style.bottom = '20px';
    exportBtn.style.padding = '8px 12px';
    exportBtn.style.border = '1px solid #666';
    exportBtn.style.background = '#fafafa';
    exportBtn.style.cursor = 'pointer';
    document.body.appendChild(exportBtn);

    exportBtn.onclick = () => {{
        if (Object.keys(sessionChanges).length === 0) {{
            alert('No new decisions to save.');
            return;
        }}
        if (!userName) {{
            userName = prompt('Your name (will be stored in the JSON):', '') || 'unknown';
        }}
        // inject username into all session entries that are still empty
        for (const k in sessionChanges) {{
            sessionChanges[k].forEach(e => {{ if (!e.by) e.by = userName; }});
        }}
        localStorage.setItem(LS_KEY, JSON.stringify({{sessionChanges, userName}}));

        const stamp = new Date().toISOString().replace(/[:.]/g,'-');
        const payload = {{
            meta: {{author: userName, saved: new Date().toISOString()}},
            data: sessionChanges
        }};
        const blob = new Blob([JSON.stringify(payload, null, 2)], {{type: 'application/json'}});
        const url  = URL.createObjectURL(blob);
        const a    = document.createElement('a');
        a.href = url;
        a.download = `node_status_${{userName.replace(/\\W+/g,'_')}}_${{stamp}}.json`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
    }};
}})();
</script>
"""
    html = html.replace("</body>", js + "\n</body>")
    path.write_text(html, "utf-8")
    log.info("HTML map written to %s", path)

    try:
        import webbrowser

        webbrowser.open(path.as_uri())
    except Exception:
        pass


# ──────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────
def main() -> None:
    if not WAYPOINT_FOLDER.is_dir():
        log.error("Waypoint folder not found: %s", WAYPOINT_FOLDER)
        sys.exit(1)

    eng        = load_eng_table(LOC_FOLDER)
    routes     = load_routes(WAYPOINT_FOLDER)
    adjacency  = build_adjacency(routes)
    nodes      = load_faction_nodes(FACTION_FOLDER, eng)

    # synthesise positions for nodes only referenced via routes
    for r in routes:
        if r.fkey and r.fkey not in nodes:
            nodes[r.fkey] = (r.fkey, eng.get(r.fkey, r.fkey), "", r.pts[0])
        if r.tkey and r.tkey not in nodes:
            nodes[r.tkey] = (r.tkey, eng.get(r.tkey, r.tkey), "", r.pts[-1])

    log.info("Total nodes (explicit + synthetic): %d", len(nodes))

    merged_status = load_status_files(Path.cwd())

    fig, map_idx = build_figure(nodes, routes, adjacency)
    write_html(fig, map_idx, merged_status, OUT_HTML)

    log.info("Done – full log saved to %s", LOG_PATH)


if __name__ == "__main__":
    main()