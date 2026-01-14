"""
Generators Package
==================
Datasheet generators for LQA testing.

Each generator extracts data from game XML files and creates
Excel datasheets with translations for QA testers.
"""

from typing import Dict, List

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
            "errors": [...]
        }
    """
    results = {
        "success": True,
        "categories_processed": [],
        "files_created": 0,
        "errors": [],
    }

    # Normalize category names
    categories = [c.lower() for c in categories]

    for category in categories:
        try:
            if category == "help" or category == "gameadvice":
                from generators.help import generate_help_datasheets
                result = generate_help_datasheets()
            elif category == "gimmick":
                from generators.gimmick import generate_gimmick_datasheets
                result = generate_gimmick_datasheets()
            elif category == "character":
                from generators.character import generate_character_datasheets
                result = generate_character_datasheets()
            elif category == "region":
                from generators.region import generate_region_datasheets
                result = generate_region_datasheets()
            elif category == "skill":
                from generators.skill import generate_skill_datasheets
                result = generate_skill_datasheets()
            elif category == "knowledge":
                from generators.knowledge import generate_knowledge_datasheets
                result = generate_knowledge_datasheets()
            elif category == "item":
                from generators.item import generate_item_datasheets
                result = generate_item_datasheets()
            elif category == "quest":
                from generators.quest import generate_quest_datasheets
                result = generate_quest_datasheets()
            elif category == "system":
                # System = Skill + Help combined
                from generators.skill import generate_skill_datasheets
                from generators.help import generate_help_datasheets
                result_skill = generate_skill_datasheets()
                result_help = generate_help_datasheets()
                result = {
                    "category": "System",
                    "files_created": result_skill.get("files_created", 0) + result_help.get("files_created", 0),
                    "errors": result_skill.get("errors", []) + result_help.get("errors", []),
                }
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
