# Korean Regex: Full Coverage

Korean detection MUST cover all three ranges:
```
[\uac00-\ud7af\u1100-\u11ff\u3130-\u318f]
```

- `AC00-D7AF` = Hangul Syllables (가-힣)
- `1100-11FF` = Hangul Jamo (ᄀ-ᇿ)
- `3130-318F` = Hangul Compatibility Jamo (ㄱ-ㅎ, ㅏ-ㅣ)

NEVER use syllables-only (`AC00-D7AF`). Single Jamo like ㅂ ㅎ ㄷ would be missed.

Canonical implementation: `QuickTranslate/core/korean_detection.py`
