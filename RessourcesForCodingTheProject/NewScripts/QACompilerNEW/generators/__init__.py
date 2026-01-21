"""
Generators Package
==================
Datasheet generators for LQA testing.

Each generator extracts data from game XML files and creates
Excel datasheets with translations for QA testers.
"""

from typing import Dict, List, Set

# Import individual generators (lazy imports to avoid circular dependencies)


def generate_datasheets(categories: List[str]) -> Dict:
    """
    Generate datasheets for the specified categories.

    Args:
        categories: List of category names (e.g., ["Quest", "Knowledge"])

    Returns:
        Dict with results: {
            "success": True/False,
            "categories_processed": [...],
            "files_created": N,
            "errors": [...],
            "korean_strings": {category: Set[str]}
        }
    """
    results = {
        "success": True,
        "categories_processed": [],
        "files_created": 0,
        "errors": [],
        "korean_strings": {},  # For coverage tracking
    }

    # Normalize category names
    categories = [c.lower() for c in categories]

    for category in categories:
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
            elif category == "quest":
                from generators.quest import generate_quest_datasheets, get_collected_korean_strings
                result = generate_quest_datasheets()
                korean_strings = get_collected_korean_strings()
                results["korean_strings"]["Quest"] = korean_strings
            elif category == "system":
                # System = Skill + Help combined
                from generators.skill import generate_skill_datasheets, get_collected_korean_strings as skill_strings
                from generators.help import generate_help_datasheets, get_collected_korean_strings as help_strings
                result_skill = generate_skill_datasheets()
                skill_korean = skill_strings()
                result_help = generate_help_datasheets()
                help_korean = help_strings()
                result = {
                    "category": "System",
                    "files_created": result_skill.get("files_created", 0) + result_help.get("files_created", 0),
                    "errors": result_skill.get("errors", []) + result_help.get("errors", []),
                }
                # Combine Skill and Help strings into System
                results["korean_strings"]["Skill"] = skill_korean
                results["korean_strings"]["Help"] = help_korean
            elif category == "script":
                from generators.script import generate_script_datasheets, get_collected_korean_strings
                result = generate_script_datasheets()
                korean_strings = get_collected_korean_strings()
                results["korean_strings"]["Script"] = korean_strings
            else:
                results["errors"].append(f"Unknown category: {category}")
                continue

            results["categories_processed"].append(result.get("category", category))
            results["files_created"] += result.get("files_created", 0)
            if result.get("errors"):
                results["errors"].extend(result["errors"])

        except ImportError as e:
            results["errors"].append(f"Generator not available for {category}: {e}")
            results["success"] = False
        except Exception as e:
            results["errors"].append(f"Error generating {category}: {e}")
            results["success"] = False

    if results["errors"]:
        results["success"] = False

    return results


# Convenience exports
__all__ = [
    "generate_datasheets",
]
