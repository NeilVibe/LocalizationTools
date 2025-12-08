# LDM (LanguageData Manager) Demo Screenshots

**Last Updated:** 2025-12-08

## Folder Structure

```
ldm/
├── 01-navigation/          # Getting to LDM
│   ├── ldm_01_homepage.png
│   ├── ldm_02_apps.png
│   └── ldm_03_main.png
├── 02-project-management/  # Projects & folders
│   ├── ldm_04_new_project_modal.png
│   ├── ldm_05_project_name_filled.png
│   ├── ldm_06_project_created.png
│   └── ldm_07_project_selected.png
├── 03-grid-view/           # Data grid display
│   ├── ldm_08_grid_with_data.png
│   └── ldm_09_grid_full.png
├── 04-editing/             # Row editing
│   ├── ldm_10_row_selection.png
│   └── ldm_11_cell_interaction.png
├── 05-ui-interactions/     # Hover, selection effects (NEW)
│   └── (pending screenshots)
└── scripts/                # Capture automation
    └── capture_ldm.js
```

## Screenshot Index

### 01 - Navigation
| Screenshot | Description |
|------------|-------------|
| `ldm_01_homepage.png` | LocaNext main landing page |
| `ldm_02_apps.png` | Apps dropdown menu showing LDM option |
| `ldm_03_main.png` | LDM main view - empty state |

### 02 - Project Management
| Screenshot | Description |
|------------|-------------|
| `ldm_04_new_project_modal.png` | "New Project" modal dialog |
| `ldm_05_project_name_filled.png` | Project name entered |
| `ldm_06_project_created.png` | Project appears in sidebar |
| `ldm_07_project_selected.png` | Project selected, ready for file upload |

### 03 - Grid View
| Screenshot | Description |
|------------|-------------|
| `ldm_08_grid_with_data.png` | Grid showing uploaded TXT file data |
| `ldm_09_grid_full.png` | Full grid view with all columns |

### 04 - Editing
| Screenshot | Description |
|------------|-------------|
| `ldm_10_row_selection.png` | Row selected in grid |
| `ldm_11_cell_interaction.png` | Cell interaction/editing |

### 05 - UI Interactions (NEW - Implemented 2025-12-08)
**Features Implemented:**
- Smooth hover transitions (0.15s ease) on rows and cells
- Row hover highlight with subtle border (box-shadow)
- Selected row state - persists until another row clicked
- Edit icon fade-in on cell hover

| Screenshot | Description |
|------------|-------------|
| `ui_01_grid_normal.png` | Grid in normal state |
| (manual capture needed) | Row hover with smooth transition |
| (manual capture needed) | Row selected with border highlight |
| (manual capture needed) | Edit modal with TM suggestions |

**Note:** Automated screenshot capture pending - manual capture recommended.

## How to Capture New Screenshots

```bash
# Start servers
python3 server/main.py &
cd locaNext && npm run dev &

# Run capture script
cd docs/demos/ldm/scripts
node capture_ldm.js
```

Or use Playwright interactively for specific shots.
