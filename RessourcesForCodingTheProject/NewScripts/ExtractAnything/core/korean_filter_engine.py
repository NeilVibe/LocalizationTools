"""Filter LocStr entries by Korean character presence in Str attribute."""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# Full Korean detection: syllables + Jamo + Compat Jamo
_KR_RE = re.compile(r"[\uac00-\ud7af\u1100-\u11ff\u3130-\u318f]")


def has_korean(text: str) -> bool:
    """Return True if *text* contains at least one Korean character."""
    return bool(_KR_RE.search(text))


def filter_by_korean(
    entries: list[dict],
    *,
    mode: str = "translated",
) -> list[dict]:
    """Filter entries based on Korean presence in Str.

    Parameters
    ----------
    mode : ``"translated"`` or ``"untranslated"``
        * ``"translated"``   — keep entries where Str contains Korean
        * ``"untranslated"`` — keep entries where Str does NOT contain Korean
    """
    want_kr = mode == "translated"
    result = []
    for e in entries:
        str_val = e.get("str_value", "")
        kr_present = has_korean(str_val)
        if kr_present == want_kr:
            result.append(e)
    return result
