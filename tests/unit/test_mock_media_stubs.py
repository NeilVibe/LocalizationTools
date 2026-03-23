"""Test mock universe media stubs and language data (MOCK-09 through MOCK-12)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from lxml import etree

MOCK_DIR = Path(__file__).parent.parent / "fixtures" / "mock_gamedata"
STATIC_DIR = MOCK_DIR / "StaticInfo"

# Correct Perforce-mapped paths (matching PerforcePathService.configure_for_mock_gamedata)
DDS_DIR = MOCK_DIR / "texture" / "image"
AUDIO_DIR_EN = MOCK_DIR / "sound" / "windows" / "English(US)"
AUDIO_DIR_KR = MOCK_DIR / "sound" / "windows" / "Korean"
AUDIO_DIR_ZH = MOCK_DIR / "sound" / "windows" / "Chinese(PRC)"
LOC_DIR = MOCK_DIR / "loc"

# Legacy PNG fallback directory (used by thumbnail endpoint)
TEXTURES_DIR = MOCK_DIR / "textures"


class TestDdsFiles:
    """Verify DDS texture stubs at correct Perforce-mapped path."""

    def test_dds_file_count(self) -> None:
        dds_files = list(DDS_DIR.glob("*.dds"))
        assert len(dds_files) >= 20, f"Only {len(dds_files)} DDS files (need 20+)"

    def test_dds_files_have_valid_headers(self) -> None:
        dds_files = list(DDS_DIR.glob("*.dds"))
        invalid = []
        for dds in dds_files:
            data = dds.read_bytes()
            if not data.startswith(b"DDS "):
                invalid.append(dds.name)
        assert not invalid, f"Invalid DDS headers: {invalid}"

    def test_dds_files_openable_by_pillow(self) -> None:
        """Each DDS file should be openable by Pillow as 64x64 RGBA."""
        try:
            from PIL import Image
        except ImportError:
            pytest.skip("Pillow not installed")

        dds_files = list(DDS_DIR.glob("*.dds"))
        assert len(dds_files) > 0, "No DDS files found"

        errors = []
        for dds in dds_files:
            try:
                img = Image.open(dds)
                if img.size != (64, 64):
                    errors.append(f"{dds.name}: size={img.size}, expected (64, 64)")
                if img.mode != "RGBA":
                    errors.append(f"{dds.name}: mode={img.mode}, expected RGBA")
            except Exception as e:
                errors.append(f"{dds.name}: {e}")
        assert not errors, f"DDS open errors: {errors}"


class TestWemFiles:
    """Verify WEM audio stubs at correct Perforce-mapped paths."""

    def test_wem_file_count(self) -> None:
        wem_files = list(AUDIO_DIR_EN.glob("*.wem"))
        assert len(wem_files) >= 10, f"Only {len(wem_files)} WEM files (need 10+)"

    def test_wem_files_have_valid_headers(self) -> None:
        wem_files = list(AUDIO_DIR_EN.glob("*.wem"))
        invalid = []
        for wem in wem_files:
            data = wem.read_bytes()
            if not data.startswith(b"RIFF"):
                invalid.append(wem.name)
        assert not invalid, f"Invalid WEM headers: {invalid}"

    def test_korean_audio_folder_exists(self) -> None:
        assert AUDIO_DIR_KR.exists(), f"Korean audio folder missing: {AUDIO_DIR_KR}"
        wem_files = list(AUDIO_DIR_KR.glob("*.wem"))
        assert len(wem_files) >= 10, f"Only {len(wem_files)} Korean WEM files (need 10+)"

    def test_chinese_audio_folder_exists(self) -> None:
        assert AUDIO_DIR_ZH.exists(), f"Chinese audio folder missing: {AUDIO_DIR_ZH}"
        wem_files = list(AUDIO_DIR_ZH.glob("*.wem"))
        assert len(wem_files) >= 10, f"Only {len(wem_files)} Chinese WEM files (need 10+)"

    def test_all_languages_have_same_filenames(self) -> None:
        en_stems = {f.stem for f in AUDIO_DIR_EN.glob("*.wem")}
        kr_stems = {f.stem for f in AUDIO_DIR_KR.glob("*.wem")}
        zh_stems = {f.stem for f in AUDIO_DIR_ZH.glob("*.wem")}

        assert en_stems, "No English WEM files found"
        assert en_stems == kr_stems, f"EN/KR mismatch: EN-only={en_stems - kr_stems}, KR-only={kr_stems - en_stems}"
        assert en_stems == zh_stems, f"EN/ZH mismatch: EN-only={en_stems - zh_stems}, ZH-only={zh_stems - en_stems}"


class TestTextureReferences:
    """Verify KnowledgeInfo UITextureName -> DDS file mapping."""

    def test_knowledge_texture_refs_have_dds(self) -> None:
        """Every UITextureName in KnowledgeInfo has a matching .dds file."""
        knowledge_dir = STATIC_DIR / "knowledgeinfo"
        if not knowledge_dir.exists():
            pytest.skip("knowledgeinfo directory not found")

        # Collect all UITextureNames
        texture_names: list[str] = []
        for xml_path in knowledge_dir.glob("*.xml"):
            tree = etree.parse(str(xml_path))
            for el in tree.getroot().findall(".//KnowledgeInfo"):
                tex = el.get("UITextureName")
                if tex:
                    texture_names.append(tex)

        assert len(texture_names) > 0, "No UITextureName attributes found"

        # Check DDS at Perforce path AND PNG at fallback path
        dds_stems = {f.stem.lower() for f in DDS_DIR.glob("*.dds")}
        png_stems = {f.stem.lower() for f in TEXTURES_DIR.glob("*.png")} if TEXTURES_DIR.exists() else set()
        all_stems = dds_stems | png_stems
        missing = [t for t in texture_names if t.lower() not in all_stems]
        assert not missing, f"Missing DDS/PNG for textures: {missing[:10]}"


class TestLanguageData:
    """Verify language data XML files for EN, KR, JP."""

    def test_eng_kor_jpn_exist(self) -> None:
        assert (LOC_DIR / "languagedata_ENG.xml").exists(), "ENG language data missing"
        assert (LOC_DIR / "languagedata_KOR.xml").exists(), "KOR language data missing"
        assert (LOC_DIR / "languagedata_JPN.xml").exists(), "JPN language data missing"

    def test_jpn_has_all_stringids(self) -> None:
        """JPN file must have the same StringIds as KOR file."""
        jpn_tree = etree.parse(str(LOC_DIR / "languagedata_JPN.xml"))
        kor_tree = etree.parse(str(LOC_DIR / "languagedata_KOR.xml"))

        jpn_ids = {e.get("StringId") for e in jpn_tree.getroot().findall(".//LocStr")}
        kor_ids = {e.get("StringId") for e in kor_tree.getroot().findall(".//LocStr")}

        missing = kor_ids - jpn_ids
        assert not missing, f"Missing StringIds in JPN: {missing}"
        assert len(jpn_ids) == len(kor_ids), f"Count mismatch: JPN={len(jpn_ids)}, KOR={len(kor_ids)}"

    def test_br_tags_properly_encoded(self) -> None:
        """All XML files must use &lt;br/&gt; not raw <br/> in attributes."""
        for lang in ("ENG", "KOR", "JPN"):
            xml_path = LOC_DIR / f"languagedata_{lang}.xml"
            if not xml_path.exists():
                continue

            # Parse the XML — if raw <br/> existed in attributes, lxml would parse
            # them as child elements. The fact it parses cleanly means encoding is correct.
            tree = etree.parse(str(xml_path))
            root = tree.getroot()

            # Double-check: read raw content and verify no unescaped <br/> inside attributes
            content = xml_path.read_text(encoding="utf-8")
            # Split by lines and check each LocStr line
            for line in content.split("\n"):
                if "LocStr" in line and "<br/>" in line:
                    # If <br/> appears in a LocStr line, it should only be as &lt;br/&gt;
                    # The raw text will show &lt;br/&gt; since we read the file as text
                    # A raw <br/> would be an XML child element, not in the attribute
                    assert False, f"Raw <br/> found in {lang}: {line[:100]}"


class TestPerforcePathResolution:
    """Verify all 11 PerforcePathService template directories exist."""

    def test_all_11_template_dirs_exist(self) -> None:
        """configure_for_mock_gamedata maps 11 keys to subdirectories of MOCK_DIR."""
        # Add server to path so we can import PerforcePathService
        server_dir = Path(__file__).parent.parent.parent / "server"
        if str(server_dir) not in sys.path:
            sys.path.insert(0, str(server_dir))

        try:
            from tools.ldm.services.perforce_path_service import PerforcePathService
        except ImportError:
            pytest.skip("PerforcePathService not importable")

        svc = PerforcePathService()
        svc.configure_for_mock_gamedata(MOCK_DIR)

        resolved = svc.get_all_resolved()
        assert len(resolved) == 11, f"Expected 11 paths, got {len(resolved)}: {list(resolved.keys())}"

        missing_dirs = []
        for key, path in resolved.items():
            if not path.exists():
                missing_dirs.append(f"{key} -> {path}")
            elif not path.is_dir():
                missing_dirs.append(f"{key} -> {path} (not a directory)")

        assert not missing_dirs, f"Missing template directories: {missing_dirs}"
