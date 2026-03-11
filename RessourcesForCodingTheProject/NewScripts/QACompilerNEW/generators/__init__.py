"""
Generators Package
==================
Datasheet generators for LQA testing.

Each generator extracts data from game XML files and creates
Excel datasheets with translations for QA testers.
"""

import time
from typing import Dict, List, Set

# Import individual generators (lazy imports to avoid circular dependencies)


def generate_datasheets(categories: List[str], log_callback=None) -> Dict:
    """
    Generate datasheets for the specified categories.

    Args:
        categories: List of category names (e.g., ["Quest", "Knowledge"])
        log_callback: Optional callback(message, tag) for GUI logging

    Returns:
        Dict with results: {
            "success": True/False,
            "categories_processed": [...],
            "files_created": N,
            "errors": [...],
            "korean_strings": {category: Set[str]}
        }
    """
    def _log(msg, tag='info'):
        if log_callback:
            log_callback(msg, tag)
        print(msg)
    # CLI safety net: refuse to generate if Perforce paths don't exist
    from config import validate_paths
    ok, missing = validate_paths()
    if not ok:
        _log(f"Critical paths not found: {', '.join(missing)}. Check Branch and Drive settings.", 'error')
        return {
            "success": False,
            "categories_processed": [],
            "files_created": 0,
            "errors": [f"Critical paths not found: {', '.join(missing)}. Check Branch and Drive settings."],
            "korean_strings": {},
        }

    results = {
        "success": True,
        "categories_processed": [],
        "files_created": 0,
        "errors": [],
        "korean_strings": {},  # For coverage tracking
    }

    # Normalize category names
    categories = [c.lower() for c in categories]

    total_cats = len(categories)
    for cat_idx, category in enumerate(categories):
        _log(f"[{cat_idx + 1}/{total_cats}] Generating: {category.capitalize()}...")
        cat_start = time.time()
        try:
            korean_strings: Set[str] = set()

            if category == "help" or category == "gameadvice":
                from generators.help import generate_help_datasheets, get_collected_korean_strings
                result = generate_help_datasheets()
                korean_strings = get_collected_korean_strings()
                results["korean_strings"]["Help"] = korean_strings
            elif category == "gimmick":
                from generators.gimmick import generate_gimmick_datasheets, get_collected_korean_strings
                result = generate_gimmick_datasheets()
                korean_strings = get_collected_korean_strings()
                results["korean_strings"]["Gimmick"] = korean_strings
            elif category == "character":
                from generators.character import generate_character_datasheets, get_collected_korean_strings
                result = generate_character_datasheets()
                korean_strings = get_collected_korean_strings()
                results["korean_strings"]["Character"] = korean_strings
            elif category == "region":
                from generators.region import generate_region_datasheets, get_collected_korean_strings
                result = generate_region_datasheets()
                korean_strings = get_collected_korean_strings()
                results["korean_strings"]["Region"] = korean_strings
            elif category == "skill":
                from generators.skill import generate_skill_datasheets, get_collected_korean_strings
                result = generate_skill_datasheets()
                korean_strings = get_collected_korean_strings()
                results["korean_strings"]["Skill"] = korean_strings
                # NOTE: Skill is now standalone (row-per-text, UIPosition ordered).
                # It no longer merges into Master_System.xlsx.
            elif category == "knowledge":
                from generators.knowledge import generate_knowledge_datasheets, get_collected_korean_strings
                result = generate_knowledge_datasheets()
                korean_strings = get_collected_korean_strings()
                results["korean_strings"]["Knowledge"] = korean_strings
            elif category == "item":
                from generators.item import generate_item_datasheets, get_collected_korean_strings
                result = generate_item_datasheets()
                korean_strings = get_collected_korean_strings()
                results["korean_strings"]["Item"] = korean_strings
            elif category == "itemknowledgecluster":
                from generators.itemknowledgecluster import generate_itemknowledgecluster_datasheets, get_collected_korean_strings
                result = generate_itemknowledgecluster_datasheets()
                korean_strings = get_collected_korean_strings()
                results["korean_strings"]["ItemKnowledgeCluster"] = korean_strings
            elif category == "quest":
                from generators.quest import generate_quest_datasheets, get_collected_korean_strings
                result = generate_quest_datasheets()
                korean_strings = get_collected_korean_strings()
                results["korean_strings"]["Quest"] = korean_strings
            elif category == "system":
                # System = Help only (Skill is now standalone)
                from generators.help import generate_help_datasheets, get_collected_korean_strings as help_strings
                result_help = generate_help_datasheets()
                help_korean = help_strings()
                result = {
                    "category": "System",
                    "files_created": result_help.get("files_created", 0),
                    "errors": result_help.get("errors", []),
                }
                results["korean_strings"]["Help"] = help_korean
                korean_strings = help_korean
            elif category == "script":
                from generators.script import generate_script_datasheets, get_collected_korean_strings
                result = generate_script_datasheets()
                korean_strings = get_collected_korean_strings()
                results["korean_strings"]["Script"] = korean_strings
            else:
                results["errors"].append(f"Unknown category: {category}")
                continue

            cat_name = result.get("category", category)
            cat_files = result.get("files_created", 0)
            cat_elapsed = time.time() - cat_start
            results["categories_processed"].append(cat_name)
            results["files_created"] += cat_files
            kr_count = len(korean_strings) if korean_strings else 0
            _log(f"  {cat_name}: {cat_files} file(s) ({cat_elapsed:.1f}s, {kr_count:,} KR strings)", 'success')
            if result.get("errors"):
                results["errors"].extend(result["errors"])
                for err in result["errors"]:
                    _log(f"  Error: {err}", 'error')

        except ImportError as e:
            _log(f"  Generator not available for {category}: {e}", 'error')
            results["errors"].append(f"Generator not available for {category}: {e}")
            results["success"] = False
        except Exception as e:
            _log(f"  Error generating {category}: {e}", 'error')
            results["errors"].append(f"Error generating {category}: {e}")
            results["success"] = False

    if results["errors"]:
        results["success"] = False

    total_kr = sum(len(s) for s in results['korean_strings'].values())
    _log(f"Total: {total_kr:,} Korean strings collected")

    _log(f"Generation complete: {results['files_created']} file(s) for {len(results['categories_processed'])} categories",
         'success' if results["success"] else 'warning')

    return results


# Convenience exports
__all__ = [
    "generate_datasheets",
]
