# TMX Transfer Tool - User Guide

**Simple 3-Step Process for Translation Transfer**

---

## What This Tool Does

TMX Transfer helps you transfer translations from Excel files into XML game files by:
1. Generating unique StringIDs
2. Converting Excel data to TMX format
3. Matching and transferring translations to XML files

---

## Step 1: Generate StringID

**Purpose**: Create unique identifiers for each translation string

### How to Do It:

1. **Prepare your Excel file** with 2 columns:
   - **Column 1**: DialogVoice (the dialog identifier)
   - **Column 2**: EventName (the event identifier)

   Example:
   ```
   DialogVoice         EventName
   aidialog_npc       aidialog_npc_greeting_01
   aidialog_quest     aidialog_quest_start_02
   ```

2. **Run the tool**
   - Open `tmxtransfer8.py`
   - Click **"Generate StringID"** button

3. **Select your Excel file**
   - The tool will extract the unique part from EventName
   - Output: New Excel file with StringIDs (named `*_stridgenerated.xlsx`)

   Result:
   ```
   greeting_01
   start_02
   ```

---

## Step 2: Prepare Excel for TMX Conversion

**Purpose**: Create a properly formatted Excel file that can be converted to TMX

### Required Excel Format:

Your Excel must have **5 columns** in this exact order:

| Column | Name | Description | Example |
|--------|------|-------------|---------|
| **Col 1** | StrOrigin | Original Korean text | 안녕하세요 |
| **Col 2** | Str | English translation | Hello |
| **Col 3** | StringID | Unique identifier | greeting_01 |
| **Col 4** | DescOrigin | Original Korean description (optional) | 인사말입니다 |
| **Col 5** | Desc | English description (optional) | This is a greeting |

### Important Notes:

✅ **Columns 1-3 are required** for basic translation
✅ **Columns 4-5 are optional** but recommended for descriptions
✅ **StringID** must match the IDs in your XML files
✅ **Str** (Column 2) must be in English (no Korean characters)
✅ **Desc** (Column 5) must be in English (no Korean characters)

### Example Excel:

```
StrOrigin        Str              StringID        DescOrigin           Desc
안녕하세요       Hello            greeting_01     인사말입니다         This is a greeting
시작하기         Start            start_02        퀘스트 시작          Quest start
종료             End              end_03          퀘스트 종료          Quest end
```

---

## Step 3: Convert Excel to TMX

**Purpose**: Transform your Excel data into TMX format for translation transfer

### How to Do It:

1. **Run the tool**
   - Open `tmxtransfer8.py`

2. **Choose conversion type**:

   **Option A: Excel → TMX** (Standard format)
   - Click **"Excel → TMX"** button
   - Use this for most cases

   **Option B: Excel → MemoQ-TMX** (For MemoQ software)
   - Click **"Excel → MemoQ-TMX"** button
   - Use this if you're working with MemoQ translation software

3. **Select mode**:
   - **File mode**: Convert a single Excel file
   - **Folder mode**: Convert all Excel files in a folder

4. **Select your Excel file** (prepared in Step 2)

5. **Result**:
   - TMX file created with all your translations
   - File saved with `.tmx` extension
   - Both regular strings and descriptions are included

---

## Step 4: Simple Translate (Transfer Translations)

**Purpose**: Match translations from TMX to XML files and update them automatically

### How to Do It:

1. **Prepare your files**:
   - ✅ TMX file (from Step 3)
   - ✅ XML file(s) to update

2. **Run the tool**
   - Open `tmxtransfer8.py`

3. **Select mode**:
   - **File mode**: Update a single XML file
   - **Folder mode**: Update all XML files in a folder

4. **Upload XML**:
   - Click **"Upload XML Folder/File"**
   - Select your XML file or folder
   - Button turns **GREEN** when ready

5. **Upload TMX**:
   - Click **"Upload TMX File"**
   - Select your TMX file (from Step 3)
   - Button turns **GREEN** when ready

6. **Run Simple Translate**:
   - Click **"KR+ID SIMPLE TRANSLATE"** button
   - The tool will:
     - Match by StringID + Korean text (StrOrigin)
     - Match descriptions by StringID + Korean description (DescOrigin)
     - Update matching entries in XML files

7. **Check Results**:
   - A popup shows how many translations were updated
   - Example: "Updated Str: 150, Updated Desc: 45"
   - Your XML files are now updated!

---

## Matching Logic

**Simple Translate** matches translations using:

1. **StringID** + **StrOrigin** (Korean text)
   - Both must match exactly
   - Updates the `Str` attribute in XML

2. **StringID** + **DescOrigin** (Korean description)
   - Both must match exactly
   - Updates the `Desc` attribute in XML

**Why both?**
- StringID alone isn't unique enough
- Korean text confirms it's the correct string
- This prevents wrong translations from being applied

---

## Advanced: 2-Step Translate

**Alternative matching method with fallback**

If you want more matches, use **"2-STEP MATCH KR+ID → KR"**:

1. **First try**: Match by StringID + Korean text (like Simple Translate)
2. **Second try**: If no match, try Korean text only (ignores StringID)

**When to use**:
- When StringIDs might have changed
- When you want maximum translation coverage
- When you trust your Korean source text is unique

**Caution**: More matches = higher risk of incorrect matches

---

## Quick Reference

### Complete Workflow Summary:

```
1. Generate StringID
   ↓
2. Prepare Excel (5 columns: StrOrigin, Str, StringID, DescOrigin, Desc)
   ↓
3. Excel → TMX (convert Excel to TMX format)
   ↓
4. Simple Translate (upload XML + TMX, click translate)
   ↓
5. Done! (XML files updated with translations)
```

### File Requirements:

| Step | Input | Output |
|------|-------|--------|
| Generate StringID | Excel (2 cols: DialogVoice, EventName) | Excel with StringIDs |
| Excel → TMX | Excel (5 cols: StrOrigin, Str, StringID, DescOrigin, Desc) | TMX file |
| Simple Translate | XML files + TMX file | Updated XML files |

---

## Tips for Success

✅ **Always generate StringIDs first** - Don't skip this step
✅ **Check column order** - Excel columns must be in exact order
✅ **No Korean in Str/Desc** - English translations only
✅ **Match your XML StringIDs** - StringIDs must exist in your XML
✅ **Test with one file first** - Before processing a whole folder
✅ **Keep backups** - Original XML files are overwritten

---

## Troubleshooting

### Problem: "No matches found"
- ✓ Check StringIDs match between Excel and XML
- ✓ Check Korean text (StrOrigin) matches exactly
- ✓ Check for extra spaces or hidden characters

### Problem: "Button stays grey"
- ✓ Upload both XML and TMX files
- ✓ Both buttons must be green before translate

### Problem: "Few updates"
- ✓ Check StringID format matches XML
- ✓ Try 2-Step Translate for more matches
- ✓ Verify Korean text matches exactly

---

**Last Updated**: 2025-11-21
**Tool Version**: tmxtransfer8.py
**For**: Localization team members

---

*Need help? Check your StringIDs and column order first - these are the most common issues!*
