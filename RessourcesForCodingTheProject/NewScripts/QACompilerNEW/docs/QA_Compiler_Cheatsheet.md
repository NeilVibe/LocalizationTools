# QA Compiler Suite v2.0 - Quick Reference Cheatsheet

## Commands

| Action | Command |
|--------|---------|
| **Launch GUI** | `python main.py` |
| **Generate All** | `python main.py --generate all` |
| **Generate Specific** | `python main.py -g quest -g item` |
| **Transfer** | `python main.py --transfer` |
| **Build** | `python main.py --build` |
| **Full Pipeline** | `python main.py --all` |

## Folder Structure

```
QACompilerNEW/
├── QAfolder/{User}_{Category}/     ← Active QA files
├── QAfolderOLD/                    ← OLD files (for transfer)
├── QAfolderNEW/                    ← NEW files (for transfer)
├── Masterfolder_EN/                ← English output
├── Masterfolder_CN/                ← Chinese output
├── GeneratedDatasheets/            ← Generated datasheets
└── languageTOtester_list.txt       ← Tester mapping
```

## Folder Naming (CRITICAL!)

```
✅ John_Quest    ✅ Mary_Item    ✅ Chen_Knowledge
❌ John Quest    ❌ Mary-Item    ❌ john_quest
    (spaces!)        (hyphen!)       (case issues!)
```

## Categories (9 Total)

| Category | Description |
|----------|-------------|
| Quest | Main/Faction/Daily/Challenge/Minigame |
| Knowledge | Knowledge entries |
| Item | Items + Gimmick merged here |
| Region | Faction/Region data |
| System | Skill + Help merged here |
| Character | NPC/Monster info |
| Skill | Player skills |
| Help | GameAdvice |
| Gimmick | Gimmick objects |

## Status Values

| Tester | Manager |
|--------|---------|
| ISSUE | FIXED |
| NO ISSUE | REPORTED |
| BLOCKED | CHECKING |
| KOREAN | NON-ISSUE |

## Manager Status Preservation

Manager work is preserved via two-stage matching:
1. **QA -> Master:** Match by STRINGID + Translation (fallback: Translation only)
2. **Manager Lookup:** Match by MASTER stringid + Tester comment

*See `docs/TECHNICAL_MATCHING_SYSTEM.md` for details.*

## Tester Mapping (languageTOtester_list.txt)

```
ENG
John
Mary

ZHO-CN
Chen
Wei
```
*Unmapped testers default to EN*

## Workflows

**New Project:**
```
1. python main.py --generate all
2. Distribute datasheets to testers
3. Collect work in QAfolder/
4. python main.py --build
```

**Update Mid-Project:**
```
1. mv QAfolder/* QAfolderOLD/
2. python main.py --generate quest
3. Copy new files to QAfolderNEW/
4. python main.py --transfer
5. python main.py --build
```

**Daily Compilation:**
```
python main.py --all
```

## Outputs

| Output | Location |
|--------|----------|
| Datasheets | `GeneratedDatasheets/` |
| EN Masters | `Masterfolder_EN/Master_*.xlsx` |
| CN Masters | `Masterfolder_CN/Master_*.xlsx` |
| Images | `Masterfolder_*/Images/` |
| Tracker | `LQA_Tester_ProgressTracker.xlsx` |

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "No valid QA folders" | Check folder naming: `{User}_{Category}` |
| "Language folder not found" | Check paths in `config.py` |
| "No matching NEW folder" | Ensure OLD and NEW have same names |
| Low transfer rate | Normal if content changed significantly |
| Images missing | Check Images/ folder, avoid special chars |

## Quick Update (Don't Re-download Full Zip!)

| Change | Replace File |
|--------|--------------|
| Quest | `generators/quest.py` |
| Item | `generators/item.py` |
| Knowledge | `generators/knowledge.py` |
| Transfer | `core/transfer.py` |
| Build | `core/compiler.py` |
| Tracker | `tracker/*.py` |
| Config | `config.py` |

## Quest Command Column (Daily/Politics/Region Quest)

```
/complete mission Mission_A && Mission_B    ← Prerequisites first
/complete prevmission Mission_X             ← Progress command
/teleport 1234 567 89                       ← Teleport last
```

*Auto-generated from factioninfo Condition + Branch Execute*

## Ranking Formula

```
Score = 80% × Done + 20% × Actual Issues
```

---

*QA Compiler Suite v2.0 | Quick Reference | v1.1*
