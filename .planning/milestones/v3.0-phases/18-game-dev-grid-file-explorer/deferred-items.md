# Deferred Items - Phase 18

## Pre-existing Test Failures

- `tests/unit/ldm/test_glossary_service.py::TestExtractGlossaryFromXML::test_extract_character_glossary` - expects 5 entries but gets 43. Likely caused by Phase 15 mock data generation expanding the character count. Not related to Phase 18 changes.
