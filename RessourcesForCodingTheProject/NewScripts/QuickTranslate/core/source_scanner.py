"""
Source Scanner - Auto-recursive language detection from folder/file structure.

Automatically detects language codes from source folder structure:
- Folders with suffix: Corrections_FRE/ -> all files inside mapped to FRE
- Files with suffix: hotfix_SPA.xml -> mapped to SPA

This eliminates manual language selection for batch operations.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

import config

logger = logging.getLogger(__name__)


@dataclass
class SourceScanResult:
    """Result of scanning a source folder for language-tagged items."""

    lang_files: Dict[str, List[Path]] = field(default_factory=dict)  # {lang_code: [files]}
    unrecognized: List[Path] = field(default_factory=list)  # Items without lang suffix
    warnings: List[str] = field(default_factory=list)
    stats: Dict[str, int] = field(default_factory=dict)

    @property
    def total_files(self) -> int:
        """Total number of files across all languages."""
        return sum(len(files) for files in self.lang_files.values())

    @property
    def language_count(self) -> int:
        """Number of unique languages detected."""
        return len(self.lang_files)

    def get_languages(self) -> List[str]:
        """Get sorted list of detected language codes."""
        return sorted(self.lang_files.keys())


def extract_language_suffix(name: str, valid_codes: Set[str]) -> Optional[str]:
    """
    Extract language code suffix from a folder or file name.

    Patterns supported:
    - name_ZHO-CN -> ZHO-CN (hyphenated codes first)
    - name_FRE -> FRE
    - languagedata_ger.xml -> GER (from stem, case-insensitive)

    Args:
        name: Folder name or file stem (without extension)
        valid_codes: Set of valid language codes (uppercase)

    Returns:
        Uppercase language code if found, None otherwise
    """
    if not name:
        return None

    # Remove extension if present (for file names)
    if "." in name:
        name = Path(name).stem

    # Split by underscore
    parts = name.split("_")
    if len(parts) < 2:
        return None

    # Check last part(s) for language code
    # First try hyphenated codes (ZHO-CN, ZHO-TW) - join last two parts with hyphen
    # Works for both: corrections_ZHO_CN (3 parts) AND ZHO_CN (2 parts)
    if len(parts) >= 2:
        hyphenated = f"{parts[-2]}-{parts[-1]}".upper()
        if hyphenated in valid_codes:
            return hyphenated

    # Then try single last part (for non-hyphenated codes like FRE, GER)
    suffix = parts[-1].upper()
    if suffix in valid_codes:
        return suffix

    return None


def _get_valid_language_codes() -> Set[str]:
    """Get set of valid language codes from config."""
    codes = set()

    # Add all keys from LANGUAGE_NAMES (uppercase)
    for code in config.LANGUAGE_NAMES.keys():
        codes.add(code.upper())

    # Also add values (they're already uppercase abbreviations)
    for abbrev in config.LANGUAGE_NAMES.values():
        codes.add(abbrev.upper())

    return codes


def scan_source_for_languages(source_path: Path) -> SourceScanResult:
    """
    Scan source folder for language-tagged files/folders.

    Detection rules:
    1. Folder with language suffix (e.g., Corrections_FRE/):
       - ALL files inside (recursive) are assigned to that language
    2. File with language suffix (e.g., patch_GER.xml):
       - Single file assigned to that language
    3. languagedata_XXX.xml pattern:
       - Standard language data file pattern

    Args:
        source_path: Path to source folder to scan

    Returns:
        SourceScanResult with detected languages and files
    """
    result = SourceScanResult()
    valid_codes = _get_valid_language_codes()

    if not source_path.exists():
        result.warnings.append(f"Source path does not exist: {source_path}")
        return result

    if not source_path.is_dir():
        # Single file mode - detect language from filename
        lang = extract_language_suffix(source_path.stem, valid_codes)
        if lang:
            result.lang_files[lang] = [source_path]
        else:
            result.unrecognized.append(source_path)
        return result

    # Scan immediate children of source folder
    try:
        children = list(source_path.iterdir())
    except OSError as e:
        result.warnings.append(f"Cannot read folder: {e}")
        return result

    for child in children:
        if child.is_dir():
            # Check folder name for language suffix
            lang = extract_language_suffix(child.name, valid_codes)
            if lang:
                # Collect ALL files inside (recursive) for this language
                lang_files = []
                for f in child.rglob("*"):
                    if f.is_file() and f.suffix.lower() in (".xml", ".xlsx", ".xls"):
                        lang_files.append(f)

                if lang_files:
                    if lang not in result.lang_files:
                        result.lang_files[lang] = []
                    result.lang_files[lang].extend(lang_files)
                    logger.debug(f"Folder {child.name}: {len(lang_files)} files -> {lang}")
                else:
                    result.warnings.append(f"Folder {child.name} has suffix {lang} but no source files")
            else:
                # No language suffix - mark as unrecognized
                result.unrecognized.append(child)

        elif child.is_file() and child.suffix.lower() in (".xml", ".xlsx", ".xls"):
            # Check file name for language suffix
            lang = extract_language_suffix(child.stem, valid_codes)

            # Also handle standard languagedata_XXX.xml pattern
            if not lang and child.stem.lower().startswith("languagedata_"):
                suffix_part = child.stem[13:]  # After "languagedata_"
                if suffix_part.upper() in valid_codes or suffix_part.lower() in [k.lower() for k in valid_codes]:
                    # Find the proper uppercase version
                    for code in valid_codes:
                        if code.lower() == suffix_part.lower():
                            lang = code
                            break

            if lang:
                if lang not in result.lang_files:
                    result.lang_files[lang] = []
                result.lang_files[lang].append(child)
                logger.debug(f"File {child.name}: -> {lang}")
            else:
                result.unrecognized.append(child)

    # Build stats
    result.stats = {
        "languages_detected": len(result.lang_files),
        "total_files": result.total_files,
        "unrecognized_items": len(result.unrecognized),
    }

    for lang, files in result.lang_files.items():
        result.stats[f"files_{lang}"] = len(files)

    return result


@dataclass
class ValidationResult:
    """Result of validating source scan against target folder."""

    matched_languages: List[str] = field(default_factory=list)  # Languages with target match
    source_only: List[str] = field(default_factory=list)  # Languages with no target
    target_only: List[str] = field(default_factory=list)  # Targets with no source
    is_valid: bool = True
    warnings: List[str] = field(default_factory=list)


def validate_source_structure(
    scan_result: SourceScanResult,
    target_folder: Path,
) -> ValidationResult:
    """
    Validate scanned source against target folder.

    Checks which source languages have matching targets.

    Args:
        scan_result: Result from scan_source_for_languages
        target_folder: Target folder with languagedata_*.xml files

    Returns:
        ValidationResult with match analysis
    """
    validation = ValidationResult()

    if not target_folder.exists():
        validation.is_valid = False
        validation.warnings.append(f"Target folder does not exist: {target_folder}")
        return validation

    # Find target language files
    target_langs = set()
    for f in target_folder.glob("*.xml"):
        if f.stem.lower().startswith("languagedata_"):
            lang_part = f.stem[13:]
            # Normalize to uppercase for comparison
            target_langs.add(lang_part.upper())

    source_langs = set(scan_result.lang_files.keys())

    # Compare
    validation.matched_languages = sorted(source_langs & target_langs)
    validation.source_only = sorted(source_langs - target_langs)
    validation.target_only = sorted(target_langs - source_langs)

    if validation.source_only:
        validation.warnings.append(
            f"Source languages without target: {', '.join(validation.source_only)}"
        )

    if not validation.matched_languages:
        validation.is_valid = False
        validation.warnings.append("No matching languages between source and target")

    return validation


def format_scan_result(
    scan_result: SourceScanResult,
    validation: Optional[ValidationResult] = None,
) -> str:
    """
    Format scan result as a human-readable report.

    Args:
        scan_result: Result from scan_source_for_languages
        validation: Optional validation result

    Returns:
        Formatted report string
    """
    lines = []
    H = "─"
    width = 60

    lines.append("")
    lines.append(H * width)
    lines.append("  SOURCE LANGUAGE SCAN RESULTS")
    lines.append(H * width)

    if scan_result.lang_files:
        lines.append(f"\n  DETECTED LANGUAGES ({scan_result.language_count}):")
        lines.append(f"  {'Language':<10} {'Files':<8} {'Source Items'}")
        lines.append(f"  {'-'*10} {'-'*8} {'-'*30}")

        for lang in scan_result.get_languages():
            files = scan_result.lang_files[lang]
            # Show first few file names
            if len(files) <= 2:
                items = ", ".join(f.name for f in files)
            else:
                items = f"{files[0].name}, ... ({len(files)} total)"
            lines.append(f"  {lang:<10} {len(files):<8} {items}")

        lines.append(f"\n  Total: {scan_result.total_files} files in {scan_result.language_count} languages")
    else:
        lines.append("\n  No language-tagged items found!")

    if scan_result.unrecognized:
        lines.append(f"\n  UNRECOGNIZED ITEMS ({len(scan_result.unrecognized)}):")
        for item in scan_result.unrecognized[:5]:
            item_type = "folder" if item.is_dir() else "file"
            lines.append(f"    - {item.name} ({item_type})")
        if len(scan_result.unrecognized) > 5:
            lines.append(f"    ... and {len(scan_result.unrecognized) - 5} more")

    if validation:
        lines.append(f"\n  VALIDATION:")
        if validation.matched_languages:
            lines.append(f"  [OK] Matched: {', '.join(validation.matched_languages)}")
        if validation.source_only:
            lines.append(f"  [!!] Source only: {', '.join(validation.source_only)}")
        if validation.target_only:
            lines.append(f"  [--] Target only: {', '.join(validation.target_only)}")

    if scan_result.warnings or (validation and validation.warnings):
        lines.append(f"\n  WARNINGS:")
        for w in scan_result.warnings:
            lines.append(f"    ! {w}")
        if validation:
            for w in validation.warnings:
                lines.append(f"    ! {w}")

    lines.append(H * width)
    lines.append("")

    return "\n".join(lines)


# =============================================================================
# Transfer Plan - Full Tree Table of Source → Target Mappings
# =============================================================================

@dataclass
class FileMapping:
    """Single source file → target file mapping."""
    source_file: Path
    target_file: Optional[Path]
    language: str
    status: str  # "OK", "NO_TARGET", "SKIPPED"
    source_type: str  # "folder_child" or "direct_file"
    source_origin: str  # Name of parent folder or direct file name
    file_size_kb: float = 0.0


@dataclass
class LanguageTransferPlan:
    """Transfer plan for a single language."""
    language: str
    source_files: List[Path]
    target_file: Optional[Path]
    status: str  # "READY", "NO_TARGET", "EMPTY"
    file_count: int = 0
    total_size_kb: float = 0.0


@dataclass
class TransferPlan:
    """Complete transfer plan with full file mappings."""

    source_folder: Path
    target_folder: Path
    language_plans: Dict[str, LanguageTransferPlan] = field(default_factory=dict)
    file_mappings: List[FileMapping] = field(default_factory=list)
    unrecognized: List[Path] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def total_source_files(self) -> int:
        return len(self.file_mappings)

    @property
    def total_ready(self) -> int:
        return sum(1 for m in self.file_mappings if m.status == "OK")

    @property
    def total_skipped(self) -> int:
        return sum(1 for m in self.file_mappings if m.status == "NO_TARGET")

    @property
    def languages_ready(self) -> List[str]:
        return sorted([lang for lang, plan in self.language_plans.items() if plan.status == "READY"])

    @property
    def languages_skipped(self) -> List[str]:
        return sorted([lang for lang, plan in self.language_plans.items() if plan.status == "NO_TARGET"])


def generate_transfer_plan(
    source_path: Path,
    target_folder: Path,
    scan_result: Optional[SourceScanResult] = None,
) -> TransferPlan:
    """
    Generate a complete transfer plan showing every source file → target mapping.

    This is the FULL TREE TABLE that shows exactly what will be transferred where.

    Args:
        source_path: Source folder or file
        target_folder: Target folder containing languagedata_*.xml files
        scan_result: Optional pre-computed scan result (will scan if not provided)

    Returns:
        TransferPlan with complete file mappings
    """
    plan = TransferPlan(source_folder=source_path, target_folder=target_folder)

    # Scan source if not provided
    if scan_result is None:
        scan_result = scan_source_for_languages(source_path)

    plan.unrecognized = scan_result.unrecognized.copy()
    plan.warnings = scan_result.warnings.copy()

    # Build target language → file lookup
    target_files: Dict[str, Path] = {}
    if target_folder.exists():
        for f in target_folder.glob("*.xml"):
            if f.stem.lower().startswith("languagedata_"):
                lang_code = f.stem[13:].upper()
                target_files[lang_code] = f
                # Also store lowercase version for case-insensitive matching
                target_files[lang_code.lower()] = f

    # Process each detected language
    for lang, source_files in scan_result.lang_files.items():
        # Find matching target file (case-insensitive)
        target_file = target_files.get(lang) or target_files.get(lang.lower())

        # Determine status
        if not source_files:
            status = "EMPTY"
        elif target_file is None:
            status = "NO_TARGET"
            plan.warnings.append(f"No target languagedata_{lang}.xml found - {len(source_files)} files will be SKIPPED")
        else:
            status = "READY"

        # Calculate total size
        total_size = 0.0
        for f in source_files:
            try:
                total_size += f.stat().st_size / 1024
            except OSError:
                pass

        # Create language plan
        lang_plan = LanguageTransferPlan(
            language=lang,
            source_files=source_files,
            target_file=target_file,
            status=status,
            file_count=len(source_files),
            total_size_kb=total_size,
        )
        plan.language_plans[lang] = lang_plan

        # Create individual file mappings
        for src_file in source_files:
            # Determine source origin (folder or direct file)
            rel_to_source = src_file.relative_to(source_path) if source_path.is_dir() else src_file.name
            parts = str(rel_to_source).split("/") if "/" in str(rel_to_source) else str(rel_to_source).split("\\")

            if len(parts) > 1:
                source_type = "folder_child"
                source_origin = parts[0]  # Parent folder name
            else:
                source_type = "direct_file"
                source_origin = src_file.name

            try:
                file_size = src_file.stat().st_size / 1024
            except OSError:
                file_size = 0.0

            mapping = FileMapping(
                source_file=src_file,
                target_file=target_file,
                language=lang,
                status="OK" if target_file else "NO_TARGET",
                source_type=source_type,
                source_origin=source_origin,
                file_size_kb=file_size,
            )
            plan.file_mappings.append(mapping)

    return plan


def format_transfer_plan(plan: TransferPlan, show_all_files: bool = True) -> str:
    """
    Format transfer plan as a FULL TREE TABLE.

    Shows every source file and its destination target.

    Args:
        plan: TransferPlan from generate_transfer_plan()
        show_all_files: If True, show every file. If False, show summary only.

    Returns:
        Formatted tree table string
    """
    lines = []
    H = "═"
    h = "─"
    V = "║"  # Double vertical to match other box characters
    TL, TR, BL, BR = "╔", "╗", "╚", "╝"
    LT, RT = "╠", "╣"

    width = 80

    # Header
    lines.append("")
    lines.append(TL + H * (width - 2) + TR)
    lines.append(V + "  FULL TRANSFER TREE".ljust(width - 2) + V)
    lines.append(V + f"  Source: {plan.source_folder}".ljust(width - 2)[:width-2] + V)
    lines.append(V + f"  Target: {plan.target_folder}".ljust(width - 2)[:width-2] + V)
    lines.append(LT + H * (width - 2) + RT)

    # Summary stats
    lines.append(V + f"  Languages: {len(plan.language_plans)} detected, {len(plan.languages_ready)} ready, {len(plan.languages_skipped)} skipped".ljust(width - 2) + V)
    lines.append(V + f"  Files: {plan.total_source_files} total, {plan.total_ready} will transfer, {plan.total_skipped} skipped".ljust(width - 2) + V)
    lines.append(LT + H * (width - 2) + RT)

    # Per-language breakdown with full file tree
    for lang in sorted(plan.language_plans.keys()):
        lang_plan = plan.language_plans[lang]

        # Language header
        status_icon = "[OK]" if lang_plan.status == "READY" else "[!!]" if lang_plan.status == "NO_TARGET" else "[--]"
        target_name = lang_plan.target_file.name if lang_plan.target_file else "(NO TARGET)"

        lines.append(V + "".ljust(width - 2) + V)
        lines.append(V + f"  {status_icon} {lang}: {lang_plan.file_count} files → {target_name}".ljust(width - 2) + V)

        if lang_plan.status == "NO_TARGET":
            lines.append(V + f"      ⚠ SKIPPED - no languagedata_{lang}.xml in target folder".ljust(width - 2) + V)

        if show_all_files and lang_plan.source_files:
            # Get mappings for this language
            lang_mappings = [m for m in plan.file_mappings if m.language == lang]

            # Group by source origin (folder or direct)
            by_origin: Dict[str, List[FileMapping]] = {}
            for m in lang_mappings:
                if m.source_origin not in by_origin:
                    by_origin[m.source_origin] = []
                by_origin[m.source_origin].append(m)

            lines.append(V + f"      {'SOURCE FILE':<40} {'SIZE':<10} {'STATUS'}".ljust(width - 2) + V)
            lines.append(V + f"      {h*40} {h*10} {h*10}".ljust(width - 2) + V)

            for origin, mappings in sorted(by_origin.items()):
                if mappings[0].source_type == "folder_child":
                    # Show folder header
                    lines.append(V + f"      {origin}/ ({len(mappings)} files)".ljust(width - 2) + V)
                    for m in mappings:
                        rel_path = m.source_file.name
                        size_str = f"{m.file_size_kb:.0f} KB" if m.file_size_kb < 1024 else f"{m.file_size_kb/1024:.1f} MB"
                        status_str = "→ OK" if m.status == "OK" else "→ SKIP"
                        lines.append(V + f"        ├─ {rel_path:<36} {size_str:<10} {status_str}".ljust(width - 2) + V)
                else:
                    # Direct file
                    m = mappings[0]
                    size_str = f"{m.file_size_kb:.0f} KB" if m.file_size_kb < 1024 else f"{m.file_size_kb/1024:.1f} MB"
                    status_str = "→ OK" if m.status == "OK" else "→ SKIP"
                    lines.append(V + f"      {m.source_file.name:<40} {size_str:<10} {status_str}".ljust(width - 2) + V)

    # Unrecognized items
    if plan.unrecognized:
        lines.append(LT + H * (width - 2) + RT)
        lines.append(V + f"  UNRECOGNIZED ({len(plan.unrecognized)} items - no language suffix detected)".ljust(width - 2) + V)
        for item in plan.unrecognized[:10]:
            item_type = "folder" if item.is_dir() else "file"
            lines.append(V + f"    - {item.name} ({item_type})".ljust(width - 2) + V)
        if len(plan.unrecognized) > 10:
            lines.append(V + f"    ... and {len(plan.unrecognized) - 10} more".ljust(width - 2) + V)

    # Warnings
    if plan.warnings:
        lines.append(LT + H * (width - 2) + RT)
        lines.append(V + "  WARNINGS:".ljust(width - 2) + V)
        for w in plan.warnings:
            lines.append(V + f"    ! {w}"[:width-2].ljust(width - 2) + V)

    # Footer
    lines.append(BL + H * (width - 2) + BR)

    # Legend
    lines.append("")
    lines.append("Legend: [OK] = Ready to transfer  [!!] = No target (skipped)  [--] = Empty")
    lines.append("")

    return "\n".join(lines)
