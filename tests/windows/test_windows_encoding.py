"""
Windows File Encoding Tests

Tests for file encoding, BOM handling, and Korean text on Windows.
Critical for localization tools.
"""

import os
import platform
import tempfile
from pathlib import Path

import pytest


pytestmark = pytest.mark.skipif(
    platform.system() != "Windows",
    reason="Windows-only tests"
)


class TestUTF8Encoding:
    """Test UTF-8 encoding on Windows."""

    def test_utf8_file_write_read(self):
        """UTF-8 files should write and read correctly."""
        test_content = "Hello World - 안녕하세요 - こんにちは - 你好"

        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                                          delete=False, suffix='.txt') as f:
            f.write(test_content)
            temp_path = f.name

        try:
            with open(temp_path, 'r', encoding='utf-8') as f:
                read_content = f.read()
            assert read_content == test_content
        finally:
            os.unlink(temp_path)

    def test_utf8_with_bom_read(self):
        """UTF-8 with BOM should be readable."""
        test_content = "한글 테스트"
        bom = b'\xef\xbb\xbf'

        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.txt') as f:
            f.write(bom + test_content.encode('utf-8'))
            temp_path = f.name

        try:
            with open(temp_path, 'r', encoding='utf-8-sig') as f:
                read_content = f.read()
            assert read_content == test_content
        finally:
            os.unlink(temp_path)

    def test_utf8_without_bom_write(self):
        """UTF-8 without BOM should write correctly."""
        test_content = "테스트 콘텐츠"

        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                                          delete=False, suffix='.txt') as f:
            f.write(test_content)
            temp_path = f.name

        try:
            with open(temp_path, 'rb') as f:
                raw_bytes = f.read()
            # Should NOT have BOM
            assert not raw_bytes.startswith(b'\xef\xbb\xbf')
            assert raw_bytes == test_content.encode('utf-8')
        finally:
            os.unlink(temp_path)


class TestKoreanText:
    """Test Korean text handling on Windows."""

    def test_korean_filename(self):
        """Korean filenames should work."""
        appdata = os.environ.get("APPDATA")
        test_dir = Path(appdata) / "LocaNext" / "test_encoding"
        test_dir.mkdir(parents=True, exist_ok=True)

        korean_file = test_dir / "한글파일명.txt"
        korean_file.write_text("한글 내용", encoding='utf-8')

        assert korean_file.exists()
        content = korean_file.read_text(encoding='utf-8')
        assert content == "한글 내용"

        # Cleanup
        korean_file.unlink()
        test_dir.rmdir()

    def test_korean_path_components(self):
        """Korean path components should work."""
        appdata = os.environ.get("APPDATA")
        test_path = Path(appdata) / "LocaNext" / "테스트" / "하위폴더"
        test_path.mkdir(parents=True, exist_ok=True)

        assert test_path.exists()
        assert test_path.is_dir()

        # Cleanup
        test_path.rmdir()
        test_path.parent.rmdir()

    def test_korean_content_roundtrip(self):
        """Korean content should survive write/read cycle."""
        test_strings = [
            "안녕하세요",
            "게임 로컬라이제이션",
            "번역 메모리 검색",
            "StringID: STR_001_대화_인사",
            "{0}님, 환영합니다!",
            "레벨 {level}에 도달했습니다.",
        ]

        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                                          delete=False, suffix='.txt') as f:
            for s in test_strings:
                f.write(s + "\n")
            temp_path = f.name

        try:
            with open(temp_path, 'r', encoding='utf-8') as f:
                read_lines = f.read().strip().split("\n")

            assert read_lines == test_strings
        finally:
            os.unlink(temp_path)


class TestSpecialCharacters:
    """Test special characters in file content."""

    def test_code_placeholders(self):
        """Code placeholders like {0}, {name} should work."""
        test_content = "Hello {0}, you have {count} messages."

        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                                          delete=False, suffix='.txt') as f:
            f.write(test_content)
            temp_path = f.name

        try:
            with open(temp_path, 'r', encoding='utf-8') as f:
                read_content = f.read()
            assert read_content == test_content
        finally:
            os.unlink(temp_path)

    def test_xml_special_chars(self):
        """XML special characters should be preserved."""
        test_content = '<text id="1">Hello &amp; Welcome</text>'

        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                                          delete=False, suffix='.xml') as f:
            f.write(test_content)
            temp_path = f.name

        try:
            with open(temp_path, 'r', encoding='utf-8') as f:
                read_content = f.read()
            assert read_content == test_content
        finally:
            os.unlink(temp_path)

    def test_mixed_language_content(self):
        """Mixed language content should work."""
        test_content = """English text here
한국어 텍스트
日本語テキスト
中文文本
Emoji: 🎮 🎯 ✅"""

        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                                          delete=False, suffix='.txt') as f:
            f.write(test_content)
            temp_path = f.name

        try:
            with open(temp_path, 'r', encoding='utf-8') as f:
                read_content = f.read()
            assert read_content == test_content
        finally:
            os.unlink(temp_path)


class TestJSONEncoding:
    """Test JSON file encoding."""

    def test_json_with_korean(self):
        """JSON with Korean content should work."""
        import json

        test_data = {
            "string_id": "STR_001",
            "source": "Hello",
            "target": "안녕하세요",
            "notes": "인사말 번역"
        }

        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                                          delete=False, suffix='.json') as f:
            json.dump(test_data, f, ensure_ascii=False, indent=2)
            temp_path = f.name

        try:
            with open(temp_path, 'r', encoding='utf-8') as f:
                read_data = json.load(f)
            assert read_data == test_data
        finally:
            os.unlink(temp_path)

    def test_json_ensure_ascii_false(self):
        """JSON should preserve non-ASCII when ensure_ascii=False."""
        import json

        test_data = {"text": "한글"}

        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                                          delete=False, suffix='.json') as f:
            json.dump(test_data, f, ensure_ascii=False)
            temp_path = f.name

        try:
            with open(temp_path, 'rb') as f:
                raw_bytes = f.read()
            # Should contain actual Korean bytes, not \uXXXX escapes
            assert "한글".encode('utf-8') in raw_bytes
        finally:
            os.unlink(temp_path)
