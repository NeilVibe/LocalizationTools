==================================
QAfolderNEW - Place NEW Empty QA Files Here
==================================

This folder is for FRESH/EMPTY QA templates from the datasheet generator.

Expected structure:
  QAfolderNEW/
    {TesterName}_{Category}/
      {TesterName}_{Category}.xlsx

Example:
  QAfolderNEW/
    John_Quest/
      John_Quest.xlsx
    Mary_Item/
      Mary_Item.xlsx

These files contain:
  - Updated source strings (Korean)
  - Updated translations (English/Other)
  - Empty STATUS, COMMENT, SCREENSHOT columns

The Transfer function will:
  1. Match rows between OLD and NEW files
  2. Copy comments/status/screenshots from OLD to NEW
  3. Output merged files to QAfolder/

After placing files here, run "Transfer QA Files" in the GUI.
