"""Test mock universe media stubs (MOCK-03)."""
from __future__ import annotations

from pathlib import Path

import pytest
from lxml import etree

MOCK_DIR = Path(__file__).parent.parent / "fixtures" / "mock_gamedata"
STATIC_DIR = MOCK_DIR / "StaticInfo"
TEXTURES_DIR = MOCK_DIR / "textures"
AUDIO_DIR = MOCK_DIR / "audio"


class TestDdsFiles:
    """Verify DDS texture stubs."""

    def test_dds_file_count(self) -> None:
        dds_files = list(TEXTURES_DIR.glob("*.dds"))
        assert len(dds_files) >= 50, f"Only {len(dds_files)} DDS files (need 50+)"

    def test_dds_files_have_valid_headers(self) -> None:
        dds_files = list(TEXTURES_DIR.glob("*.dds"))
        invalid = []
        for dds in dds_files:
            data = dds.read_bytes()
            if not data.startswith(b"DDS "):
                invalid.append(dds.name)
        assert not invalid, f"Invalid DDS headers: {invalid}"


class TestWemFiles:
    """Verify WEM audio stubs."""

    def test_wem_file_count(self) -> None:
        wem_files = list(AUDIO_DIR.glob("*.wem"))
        assert len(wem_files) >= 15, f"Only {len(wem_files)} WEM files (need 15+)"

    def test_wem_files_have_valid_headers(self) -> None:
        wem_files = list(AUDIO_DIR.glob("*.wem"))
        invalid = []
        for wem in wem_files:
            data = wem.read_bytes()
            if not data.startswith(b"RIFF"):
                invalid.append(wem.name)
        assert not invalid, f"Invalid WEM headers: {invalid}"


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

        # Check each has a DDS file (case-insensitive)
        dds_stems = {f.stem.lower() for f in TEXTURES_DIR.glob("*.dds")}
        missing = [t for t in texture_names if t.lower() not in dds_stems]
        assert not missing, f"Missing DDS for textures: {missing[:10]}"
