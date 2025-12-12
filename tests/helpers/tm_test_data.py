"""
TM Test Data Generator

Generates mock Translation Memory data for testing:
- TEXT format (TSV with newlines as \\n)
- XML format (with <br/> and &lt;br/&gt; newlines)
- Various sizes: small (100), medium (1000), large (10000)

Usage:
    from tests.helpers.tm_test_data import TMTestDataGenerator

    gen = TMTestDataGenerator()
    entries = gen.generate_entries(count=1000)
    text_content = gen.to_text_format(entries)
    xml_content = gen.to_xml_format(entries)
"""

import random
import string
from typing import List, Dict, Tuple
from datetime import datetime


# Korean sample words for generating realistic source text
KOREAN_WORDS = [
    "저장", "취소", "확인", "삭제", "편집", "추가", "수정", "검색",
    "설정", "파일", "폴더", "문서", "이미지", "동영상", "음악",
    "사용자", "관리자", "시스템", "네트워크", "서버", "클라이언트",
    "버튼", "메뉴", "창", "대화상자", "알림", "경고", "오류",
    "성공", "실패", "진행", "완료", "대기", "처리", "로딩",
    "로그인", "로그아웃", "가입", "탈퇴", "비밀번호", "아이디",
    "이메일", "전화", "주소", "이름", "날짜", "시간", "숫자",
    "텍스트", "링크", "이동", "복사", "붙여넣기", "잘라내기",
    "실행", "중지", "시작", "종료", "재시작", "업데이트",
]

KOREAN_PHRASES = [
    "저장하시겠습니까?", "삭제하시겠습니까?", "확인을 눌러주세요.",
    "취소하면 변경사항이 손실됩니다.", "작업이 완료되었습니다.",
    "오류가 발생했습니다.", "다시 시도해 주세요.", "로딩 중입니다.",
    "파일을 선택해 주세요.", "입력값이 올바르지 않습니다.",
    "비밀번호가 일치하지 않습니다.", "로그인에 성공했습니다.",
    "네트워크 연결을 확인해 주세요.", "서버에 연결할 수 없습니다.",
    "권한이 없습니다.", "세션이 만료되었습니다.",
]

# English sample words for generating target text
ENGLISH_WORDS = [
    "Save", "Cancel", "Confirm", "Delete", "Edit", "Add", "Modify", "Search",
    "Settings", "File", "Folder", "Document", "Image", "Video", "Music",
    "User", "Admin", "System", "Network", "Server", "Client",
    "Button", "Menu", "Window", "Dialog", "Alert", "Warning", "Error",
    "Success", "Failure", "Progress", "Complete", "Waiting", "Processing", "Loading",
    "Login", "Logout", "Sign up", "Delete account", "Password", "Username",
    "Email", "Phone", "Address", "Name", "Date", "Time", "Number",
    "Text", "Link", "Move", "Copy", "Paste", "Cut",
    "Run", "Stop", "Start", "End", "Restart", "Update",
]

ENGLISH_PHRASES = [
    "Do you want to save?", "Do you want to delete?", "Please click confirm.",
    "Changes will be lost if you cancel.", "Operation completed successfully.",
    "An error occurred.", "Please try again.", "Loading...",
    "Please select a file.", "Invalid input value.",
    "Passwords do not match.", "Login successful.",
    "Please check your network connection.", "Cannot connect to server.",
    "Permission denied.", "Session expired.",
]


class TMTestDataGenerator:
    """Generate mock TM data for testing."""

    def __init__(self, seed: int = 42):
        """
        Initialize generator with optional seed for reproducibility.

        Args:
            seed: Random seed for reproducible data
        """
        self.random = random.Random(seed)

    def _random_korean_text(self, min_words: int = 1, max_words: int = 8) -> str:
        """Generate random Korean text."""
        # 30% chance of using a full phrase
        if self.random.random() < 0.3 and KOREAN_PHRASES:
            return self.random.choice(KOREAN_PHRASES)

        # Otherwise generate from words
        num_words = self.random.randint(min_words, max_words)
        words = [self.random.choice(KOREAN_WORDS) for _ in range(num_words)]
        return " ".join(words)

    def _random_english_text(self, min_words: int = 1, max_words: int = 8) -> str:
        """Generate random English text."""
        # 30% chance of using a full phrase
        if self.random.random() < 0.3 and ENGLISH_PHRASES:
            return self.random.choice(ENGLISH_PHRASES)

        # Otherwise generate from words
        num_words = self.random.randint(min_words, max_words)
        words = [self.random.choice(ENGLISH_WORDS) for _ in range(num_words)]
        return " ".join(words)

    def _random_multiline_korean(self, min_lines: int = 2, max_lines: int = 5) -> str:
        """Generate multi-line Korean text."""
        num_lines = self.random.randint(min_lines, max_lines)
        lines = [self._random_korean_text(2, 6) for _ in range(num_lines)]
        return "\n".join(lines)

    def _random_multiline_english(self, num_lines: int) -> str:
        """Generate multi-line English text matching line count."""
        lines = [self._random_english_text(2, 6) for _ in range(num_lines)]
        return "\n".join(lines)

    def generate_entry(self, include_string_id: bool = False, multiline_chance: float = 0.3) -> Dict:
        """
        Generate a single TM entry.

        Args:
            include_string_id: Whether to include string_id field
            multiline_chance: Probability of generating multi-line text

        Returns:
            Dict with source, target, and optional string_id
        """
        # Decide if multiline
        is_multiline = self.random.random() < multiline_chance

        if is_multiline:
            source = self._random_multiline_korean()
            num_lines = len(source.split("\n"))
            target = self._random_multiline_english(num_lines)
        else:
            source = self._random_korean_text()
            target = self._random_english_text()

        entry = {
            "source": source,
            "target": target,
        }

        if include_string_id:
            entry["string_id"] = f"STR_{self.random.randint(10000, 99999)}"

        return entry

    def generate_entries(
        self,
        count: int = 100,
        include_string_id: bool = False,
        multiline_chance: float = 0.3
    ) -> List[Dict]:
        """
        Generate multiple TM entries.

        Args:
            count: Number of entries to generate
            include_string_id: Include string_id field
            multiline_chance: Probability of multi-line entries

        Returns:
            List of TM entry dicts
        """
        return [
            self.generate_entry(include_string_id, multiline_chance)
            for _ in range(count)
        ]

    def to_text_format(self, entries: List[Dict], newline_style: str = "escaped") -> str:
        """
        Convert entries to TEXT format (TSV).

        Args:
            entries: List of TM entries
            newline_style: "escaped" (\\n), "literal" (actual newline in text)

        Returns:
            TSV formatted string
        """
        lines = []

        for i, entry in enumerate(entries):
            source = entry["source"]
            target = entry["target"]

            # Escape newlines for TEXT format
            if newline_style == "escaped":
                source = source.replace("\n", "\\n")
                target = target.replace("\n", "\\n")

            # Format: index\tsource\ttarget (or with string_id)
            if "string_id" in entry:
                line = f"{i}\t{entry['string_id']}\t{source}\t{target}"
            else:
                line = f"{i}\t{source}\t{target}"

            lines.append(line)

        return "\n".join(lines)

    def to_xml_format(
        self,
        entries: List[Dict],
        newline_style: str = "br",
        escape_html: bool = False
    ) -> str:
        """
        Convert entries to XML format.

        Args:
            entries: List of TM entries
            newline_style: "br" (<br/>), "escaped_br" (&lt;br/&gt;)
            escape_html: Whether to escape < > in content

        Returns:
            XML formatted string
        """
        xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>']
        xml_lines.append('<translation_memory>')

        for i, entry in enumerate(entries):
            source = entry["source"]
            target = entry["target"]

            # Convert newlines to XML format
            if newline_style == "br":
                source = source.replace("\n", "<br/>")
                target = target.replace("\n", "<br/>")
            elif newline_style == "escaped_br":
                source = source.replace("\n", "&lt;br/&gt;")
                target = target.replace("\n", "&lt;br/&gt;")

            # Escape HTML entities if needed
            if escape_html:
                source = source.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                target = target.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

            string_id = entry.get("string_id", f"entry_{i}")

            xml_lines.append(f'  <entry id="{i}" stringid="{string_id}">')
            xml_lines.append(f'    <source>{source}</source>')
            xml_lines.append(f'    <target>{target}</target>')
            xml_lines.append('  </entry>')

        xml_lines.append('</translation_memory>')
        return "\n".join(xml_lines)

    def generate_test_set(
        self,
        name: str = "default",
        count: int = 100,
        include_string_id: bool = False
    ) -> Dict:
        """
        Generate a complete test set with both TEXT and XML formats.

        Args:
            name: Name for the test set
            count: Number of entries
            include_string_id: Include string_id

        Returns:
            Dict with entries and formatted versions
        """
        entries = self.generate_entries(count, include_string_id)

        return {
            "name": name,
            "count": count,
            "entries": entries,
            "text_escaped": self.to_text_format(entries, "escaped"),
            "text_literal": self.to_text_format(entries, "literal"),
            "xml_br": self.to_xml_format(entries, "br"),
            "xml_escaped_br": self.to_xml_format(entries, "escaped_br"),
        }


# Pre-built test sets for convenience
def get_small_test_set(seed: int = 42) -> Dict:
    """Get small test set (100 entries)."""
    gen = TMTestDataGenerator(seed)
    return gen.generate_test_set("small", 100)


def get_medium_test_set(seed: int = 42) -> Dict:
    """Get medium test set (1000 entries)."""
    gen = TMTestDataGenerator(seed)
    return gen.generate_test_set("medium", 1000)


def get_large_test_set(seed: int = 42) -> Dict:
    """Get large test set (10000 entries)."""
    gen = TMTestDataGenerator(seed)
    return gen.generate_test_set("large", 10000)


def get_stress_test_set(seed: int = 42) -> Dict:
    """Get stress test set (50000 entries)."""
    gen = TMTestDataGenerator(seed)
    return gen.generate_test_set("stress", 50000)


# For quick testing
if __name__ == "__main__":
    import time

    gen = TMTestDataGenerator()

    print("=== TM Test Data Generator ===\n")

    # Generate sample
    print("Sample entry:")
    entry = gen.generate_entry(include_string_id=True)
    print(f"  Source: {entry['source']}")
    print(f"  Target: {entry['target']}")
    print(f"  StringID: {entry['string_id']}")

    print("\n--- Generation Speed Test ---")

    for size in [100, 1000, 10000]:
        start = time.time()
        entries = gen.generate_entries(size)
        elapsed = time.time() - start
        print(f"  {size:,} entries: {elapsed:.3f}s")

    print("\n--- Format Conversion Test ---")

    entries = gen.generate_entries(100, include_string_id=True, multiline_chance=0.5)

    text_content = gen.to_text_format(entries)
    print(f"  TEXT format: {len(text_content):,} chars")

    xml_content = gen.to_xml_format(entries, "br")
    print(f"  XML (br) format: {len(xml_content):,} chars")

    xml_escaped = gen.to_xml_format(entries, "escaped_br")
    print(f"  XML (escaped br) format: {len(xml_escaped):,} chars")

    print("\n--- Sample Output ---")
    print("\nTEXT format (first 3 lines):")
    for line in text_content.split("\n")[:3]:
        print(f"  {line[:80]}...")

    print("\nXML format (first entry):")
    for line in xml_content.split("\n")[2:7]:
        print(f"  {line}")
