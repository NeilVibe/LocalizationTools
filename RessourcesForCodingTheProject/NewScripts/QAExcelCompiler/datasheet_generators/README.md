# Datasheet Generators

Scripts that generate QA Excel files from game StaticInfo XML data.

---

## Creating New Generators (Protocol)

When creating a new datasheet generator:

### 1. Analyze the XML Structure

User provides sample XML data. Identify:
- **Parent elements** (groups): What contains children? (e.g., `GameAdviceGroupInfo`)
- **Child elements** (items): What contains actual text? (e.g., `GameAdviceInfo`)
- **Key attributes**: `StrKey`, `Name`/`Title`, `Desc`, etc.
- **Nesting depth**: Simple parent-child or deep hierarchy?

### 2. Copy Patterns from Existing Generators

All generators share common patterns:

```python
# CONFIGURATION
RESOURCE_FOLDER = Path(r"F:\perforce\cd\mainline\resource\GameData\StaticInfo")  # Default
LANGUAGE_FOLDER = Path(r"F:\perforce\cd\mainline\resource\GameData\stringtable\loc")

# COMMON FUNCTIONS (copy from existing)
- normalize_placeholders()      # Whitespace/placeholder normalization
- is_good_translation()         # Korean detection for translation quality
- sanitize_xml()                # Fix malformed XML
- parse_xml_file()              # Safe XML parsing with recovery
- iter_xml_files()              # Recursive folder walking
- load_language_tables()        # Load translation tables

# DATA STRUCTURES
@dataclass
class YourItem:
    strkey: str
    name: str   # or title
    desc: str

# ROW GENERATION
def emit_rows() -> List[RowItem]:
    # (depth, text, needs_translation, ...)

# EXCEL WRITING
def write_workbook():
    # Headers: Original (KR) | English (ENG) | Translation (LOC) | STATUS | COMMENT | STRINGID | SCREENSHOT
```

### 3. Key Decisions

| Decision | Options |
|----------|---------|
| **Sheets** | One sheet (simple) vs Multiple sheets (by category/group) |
| **Indentation** | depth=0 for parents, depth+1 for children |
| **Subfolder** | Default `StaticInfo/` or specific subfolder |

### 4. Output Format

All generators produce consistent columns:
- `Original (KR)` - Korean source text
- `English (ENG)` - English translation (always included)
- `Translation (LOC)` - Target language (skipped for ENG workbook)
- `STATUS` - Dropdown: ISSUE / NO ISSUE / BLOCKED
- `COMMENT` - Tester feedback
- `STRINGID` - From StringId attribute in LanguageData
- `SCREENSHOT` - Hyperlink to image

---

## Scripts

| Script | Category | Description |
|--------|----------|-------------|
| `fullquest15.py` | Quest | Extracts quest text (dialogue, objectives, etc.) |
| `fullknowledge14.py` | Knowledge | Extracts knowledge/lore entries with hierarchy |
| `fullitem25.py` | Item | Extracts item names/descriptions with grouping |
| `fullregion7.py` | Region | Extracts faction/region location data |
| `fullcharacter1.py` | Character | Extracts NPC/monster character data |
| `fullgimmick1.py` | Gimmick | Extracts gimmick/interactable data |
| `fullgameadvice1.py` | GameAdvice | Extracts tutorial/help tip entries (Title/Desc) |
| `fullskill1.py` | Skill | Extracts skill data with linked KnowledgeInfo |

## Output Format

All scripts generate Excel files with consistent columns:

```
Original (KR) | English (ENG) | Translation (LOC) | STATUS | COMMENT | STRINGID | SCREENSHOT
```

**Key columns for QA workflow:**
- `STATUS` - Dropdown: ISSUE / NO ISSUE / BLOCKED
- `COMMENT` - Tester feedback
- `STRINGID` - Unique identifier for row matching
- `SCREENSHOT` - Hyperlink to image

## STRINGID Source

STRINGID comes from the `StringId` attribute in LanguageData XML files:
```xml
<LocStr StrOrigin="원본텍스트" Str="Translation" StringId="12345678" />
```

The scripts extract this directly - no transformation needed.

## Data Quality Features

### STRINGID Sanitization
All STRINGID cells are formatted as text (`number_format='@'`) to prevent:
- Excel converting large numbers to scientific notation (e.g., `1.23E+15`)
- Integer vs string type mismatches during matching

### Duplicate Row Filtering
Rows with identical **(Korean + Translation + STRINGID)** are automatically removed.
- Keeps first occurrence, removes duplicates
- Logs count of removed duplicates during generation
- Prevents testers from reviewing the same content twice

## Usage

1. Configure paths at top of script (RESOURCE_FOLDER, LANGUAGE_FOLDER)
2. Run: `python fullquest15.py`
3. Output goes to `{Category}_LQA_All/` folder

## Integration with QA Compiler

These scripts generate the **source QA files** that testers fill in.

Workflow:
```
1. Run datasheet generator → creates empty QA files (NEW structure)
2. Testers fill in STATUS/COMMENT/SCREENSHOT
3. QA Compiler → compiles tester files into master sheets
4. Manager reviews in master sheets
```

When structure changes:
```
1. Run datasheet generator → new QA files (NEW structure)
2. Use QA Compiler "Transfer QA Files" → OLD work → NEW structure
3. Testers continue with new structure
```

---

## Skill Generator Special Logic

The `fullskill1.py` generator has unique logic for linking Skills to Knowledge entries.

### Source File Restriction

Skills are extracted from **ONE file only**: `skillinfo/skillinfo_pc.staticinfo.xml`
- This restricts output to player character skills
- KnowledgeInfo is still scanned from ALL files for mapping

### XML Structure

```xml
<!-- SkillInfo with LearnKnowledgeKey -->
<SkillInfo Key="10280" StrKey="Skill_UnArmedMastery" SkillName="타격"
           MaxLevel="5" LearnKnowledgeKey="Knowledge_UnArmedMastery_I"
           SkillDesc="맨주먹으로 적과 싸우는 기술...">

<!-- Linked KnowledgeInfo with nested children -->
<KnowledgeInfo StrKey="Knowledge_UnArmedMastery_I" Name="타격" Desc="...">
    <KnowledgeInfo StrKey="Knowledge_LegSwing" Name="낚아 차기" Desc="..."/>
    <KnowledgeInfo StrKey="Knowledge_LowerKick" Name="쓸어 차기" Desc="..."/>
    ...
</KnowledgeInfo>
```

### Priority Rule (Duplicate LearnKnowledgeKey)

When multiple SkillInfo share the same `LearnKnowledgeKey`:
- **Winner**: Skill with highest `MaxLevel` gets the linked KnowledgeInfo
- **Loser**: Uses its own `SkillDesc` instead

Example:
```
Skill_UnArmedMastery (MaxLevel=5) → WINS → uses Knowledge_UnArmedMastery_I
Skill_PushKick (MaxLevel=1)       → LOSES → uses its own SkillDesc
```

### Output Structure (ONE sheet)

| Depth | Content | Color |
|-------|---------|-------|
| 0 | SkillName (parent skill) | Gold |
| 1 | KnowledgeInfo Name (or SkillDesc if no link) | Light Blue |
| 2 | KnowledgeInfo Desc | Light Green |
| 3+ | Nested KnowledgeInfo children (sub-skills) | Alternating colors |

---

*Copied from DATASHEET SCRIPTS 0108 on 2026-01-09*
