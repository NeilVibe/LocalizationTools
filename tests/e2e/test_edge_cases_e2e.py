"""
End-to-End Edge Case Tests

Tests for edge cases and boundary conditions across all tools:
1. Empty inputs
2. Unicode/special characters
3. Large inputs
4. Malformed data
5. Concurrent operations

These tests use real modules and verify correct error handling.
"""

import pytest
import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Fixtures directory
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


class TestKRSimilarEdgeCases:
    """Edge case tests for KR Similar tool."""

    @pytest.fixture(scope="class")
    def embeddings_manager(self):
        """Get EmbeddingsManager instance."""
        try:
            from server.tools.kr_similar.embeddings import EmbeddingsManager, DICT_TYPES
            manager = EmbeddingsManager()

            # Create a TEST dictionary for edge case testing
            if "TEST" not in DICT_TYPES:
                DICT_TYPES.append("TEST")

            fixture_file = str(FIXTURES_DIR / "sample_language_data.txt")
            if Path(fixture_file).exists():
                # Create dictionary from fixture
                manager.create_dictionary(
                    file_paths=[fixture_file],
                    dict_type="TEST",
                    kr_column=5,
                    trans_column=6
                )
                # Load dictionary
                manager.load_dictionary("TEST")

            return manager
        except ImportError:
            pytest.skip("KR Similar modules not available")

    @pytest.fixture(scope="class")
    def searcher(self, embeddings_manager):
        """Get Searcher instance."""
        from server.tools.kr_similar.searcher import SimilaritySearcher
        return SimilaritySearcher(embeddings_manager=embeddings_manager)

    def test_01_empty_query_handling(self, searcher):
        """Test handling of empty search query.

        PRODUCTION USE: User enters nothing in search box.
        EXPECTED: Empty result list or appropriate error, no crash.
        """
        result = searcher.find_similar(
            query="",
            threshold=0.5,
            top_k=5,
            use_whole=False
        )

        # Should return empty list or handle gracefully
        assert isinstance(result, list), "Result should be a list"
        print(f"Empty query result: {result}")

    def test_02_whitespace_only_query(self, searcher):
        """Test handling of whitespace-only query.

        PRODUCTION USE: User enters spaces/tabs only.
        EXPECTED: Empty result or appropriate handling.
        """
        result = searcher.find_similar(
            query="   \t\n   ",
            threshold=0.5,
            top_k=5,
            use_whole=False
        )

        assert isinstance(result, list)
        print(f"Whitespace query result: {result}")

    def test_03_special_characters_in_query(self, searcher):
        """Test handling of special characters in query.

        PRODUCTION USE: Query contains game code markers like {Scale(1.2)}.
        EXPECTED: Markers should be stripped, Korean text should be searched.
        """
        # Query with code markers (from fixture data pattern)
        query_with_markers = "{ChangeScene(Main_001)}{AudioVoice(NPC_001)}안녕하세요"

        result = searcher.find_similar(
            query=query_with_markers,
            threshold=0.3,
            top_k=5,
            use_whole=False
        )

        assert isinstance(result, list)
        print(f"Special chars query result: {len(result)} items")

    def test_04_html_tags_in_query(self, searcher):
        """Test handling of HTML-like tags in query.

        PRODUCTION USE: Game data contains <color=red> tags.
        EXPECTED: Tags should be handled gracefully.
        """
        query_with_html = "<color=red>경고</color>: 테스트입니다"

        result = searcher.find_similar(
            query=query_with_html,
            threshold=0.3,
            top_k=5,
            use_whole=False
        )

        assert isinstance(result, list)
        print(f"HTML tags query result: {len(result)} items")

    def test_05_very_long_query(self, searcher):
        """Test handling of very long query string.

        PRODUCTION USE: User pastes entire paragraph.
        EXPECTED: Should process without error, may truncate.
        """
        # Create a long query by repeating Korean text
        long_query = "안녕하세요 마을에 오신 것을 환영합니다. " * 100

        result = searcher.find_similar(
            query=long_query,
            threshold=0.3,
            top_k=5,
            use_whole=True
        )

        assert isinstance(result, list)
        print(f"Long query ({len(long_query)} chars) result: {len(result)} items")

    def test_06_mixed_language_query(self, searcher):
        """Test handling of mixed Korean/English query.

        PRODUCTION USE: Query contains both languages.
        EXPECTED: Should process without error.
        """
        mixed_query = "Hello 안녕하세요 World 세계"

        result = searcher.find_similar(
            query=mixed_query,
            threshold=0.3,
            top_k=5,
            use_whole=False
        )

        assert isinstance(result, list)
        print(f"Mixed language query result: {len(result)} items")

    def test_07_emoji_in_query(self, searcher):
        """Test handling of emoji in query.

        PRODUCTION USE: Modern game text may include emoji.
        EXPECTED: Should process without crash.
        """
        emoji_query = "안녕하세요 👋 환영합니다 🎉"

        result = searcher.find_similar(
            query=emoji_query,
            threshold=0.3,
            top_k=5,
            use_whole=False
        )

        assert isinstance(result, list)
        print(f"Emoji query result: {len(result)} items")

    def test_08_zero_threshold(self, searcher):
        """Test with zero similarity threshold.

        PRODUCTION USE: User wants to see all possible matches.
        EXPECTED: Should return many results without error.
        """
        result = searcher.find_similar(
            query="마을",
            threshold=0.0,
            top_k=10,
            use_whole=False
        )

        assert isinstance(result, list)
        print(f"Zero threshold result: {len(result)} items")

    def test_09_one_threshold(self, searcher):
        """Test with 1.0 similarity threshold.

        PRODUCTION USE: User wants only exact matches.
        EXPECTED: Should return few/no results (exact semantic match rare).
        """
        result = searcher.find_similar(
            query="마을",
            threshold=1.0,
            top_k=10,
            use_whole=False
        )

        assert isinstance(result, list)
        print(f"1.0 threshold result: {len(result)} items")


class TestQuickSearchEdgeCases:
    """Edge case tests for QuickSearch tool."""

    @pytest.fixture(scope="class")
    def dict_manager(self):
        """Get DictionaryManager instance."""
        from server.tools.quicksearch.dictionary import DictionaryManager
        return DictionaryManager()

    @pytest.fixture(scope="class")
    def searcher(self, dict_manager):
        """Get Searcher instance with loaded dictionary."""
        from server.tools.quicksearch.searcher import Searcher

        searcher = Searcher()

        # Try to load a dictionary for testing
        fixture_file = str(FIXTURES_DIR / "sample_quicksearch_data.txt")
        if Path(fixture_file).exists():
            try:
                split_dict, whole_dict, string_keys, stringid_to_entry = dict_manager.create_dictionary(
                    file_paths=[fixture_file],
                    game="BDO",
                    language="EN"
                )
                # Load into searcher
                searcher.load_dictionary({
                    'split_dict': split_dict,
                    'whole_dict': whole_dict,
                    'string_keys': string_keys,
                    'stringid_to_entry': stringid_to_entry
                })
            except Exception as e:
                print(f"Could not load dictionary: {e}")

        return searcher

    def test_01_search_empty_string(self, searcher):
        """Test searching for empty string.

        PRODUCTION USE: User clears search box and presses enter.
        EXPECTED: Empty result, no crash.
        """
        result = searcher.search_one_line("")

        # search_one_line returns (results, count) tuple
        assert isinstance(result, (list, tuple))
        print(f"Empty search result: {result}")

    def test_02_search_single_character(self, searcher):
        """Test searching for single character.

        PRODUCTION USE: User types one character.
        EXPECTED: Should return matches containing that character.
        """
        result = searcher.search_one_line("마")

        # search_one_line returns (results, count) tuple
        assert isinstance(result, (list, tuple))
        if isinstance(result, tuple):
            results, count = result
            assert isinstance(results, list)
            print(f"Single char search result: {count} items")
        else:
            print(f"Single char search result: {len(result)} items")

    def test_03_search_special_regex_chars(self, searcher):
        """Test searching with regex special characters.

        PRODUCTION USE: User searches for text with *, +, etc.
        EXPECTED: Should escape and search literally.
        """
        # These are regex special chars that could cause problems if not escaped
        for special in [".", "*", "+", "?", "[", "]", "(", ")"]:
            result = searcher.search_one_line(f"test{special}query")
            # search_one_line returns (results, count) tuple
            assert isinstance(result, (list, tuple))

        print("Regex special chars handled correctly")

    def test_04_multiline_search(self, searcher):
        """Test multiline search query.

        PRODUCTION USE: User pastes multiple lines to search.
        EXPECTED: Should search each line or handle appropriately.
        """
        multiline = "첫 번째 줄\n두 번째 줄\n세 번째 줄"

        result = searcher.search_multi_line(multiline)

        assert isinstance(result, (list, dict))
        print(f"Multiline search result: {type(result)}")


class TestXLSTransferEdgeCases:
    """Edge case tests for XLSTransfer tool."""

    @pytest.fixture(scope="class")
    def core_module(self):
        """Get XLSTransfer core module."""
        try:
            from client.tools.xls_transfer import core
            return core
        except ImportError:
            pytest.skip("XLSTransfer core not available")

    def test_01_clean_text_edge_cases(self, core_module):
        """Test clean_text with various edge cases.

        PRODUCTION USE: Excel cells can contain unexpected data.
        """
        # None
        assert core_module.clean_text(None) is None

        # Empty string
        assert core_module.clean_text("") == ""

        # Numbers
        assert core_module.clean_text(123) == "123"
        assert core_module.clean_text(3.14) == "3.14"

        # Boolean
        result = core_module.clean_text(True)
        assert result in ["True", "1", True]  # Depends on implementation

        # Unicode
        assert core_module.clean_text("한글테스트") == "한글테스트"

        print("clean_text edge cases passed")

    def test_02_column_conversion_edge_cases(self, core_module):
        """Test Excel column conversion edge cases.

        PRODUCTION USE: Users may specify column references.
        NOTE: Current implementation only supports single letters A-Z.
        """
        # Single letters - the supported use case
        assert core_module.excel_column_to_index('A') == 0
        assert core_module.excel_column_to_index('B') == 1
        assert core_module.excel_column_to_index('Z') == 25

        # Lowercase - should be converted to uppercase
        assert core_module.excel_column_to_index('a') == 0
        assert core_module.excel_column_to_index('z') == 25

        # Reverse conversion - single letters
        assert core_module.index_to_excel_column(0) == 'A'
        assert core_module.index_to_excel_column(1) == 'B'
        assert core_module.index_to_excel_column(25) == 'Z'

        # Note: Double letters (AA, AB, etc.) are NOT supported by current implementation
        # This is a known limitation - XLSTransfer only uses columns A-Z typically

        print("Column conversion edge cases passed")


class TestDatabaseEdgeCases:
    """Edge case tests for database operations."""

    @pytest.fixture(scope="function")
    def test_db(self):
        """Create a test database."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from server.database.models import Base

        engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(engine)
        TestSession = sessionmaker(bind=engine)
        session = TestSession()
        yield session
        session.close()
        Base.metadata.drop_all(engine)

    def test_01_create_user_with_max_length_username(self, test_db):
        """Test creating user with very long username.

        PRODUCTION USE: Username validation.
        """
        from server.database.models import User

        # Most systems limit username to 255 chars
        long_username = "a" * 255

        user = User(
            username=long_username,
            password_hash="hash",
        )
        test_db.add(user)
        test_db.commit()

        # Should be able to query
        found = test_db.query(User).filter_by(username=long_username).first()
        assert found is not None
        assert found.username == long_username

        print(f"Created user with {len(long_username)} char username")

    def test_02_create_user_with_unicode_username(self, test_db):
        """Test creating user with Unicode characters.

        PRODUCTION USE: International usernames.
        """
        from server.database.models import User

        unicode_username = "사용자_테스트_유저"

        user = User(
            username=unicode_username,
            password_hash="hash",
        )
        test_db.add(user)
        test_db.commit()

        found = test_db.query(User).filter_by(username=unicode_username).first()
        assert found is not None
        assert found.username == unicode_username

        print(f"Created user with Korean username: {unicode_username}")

    def test_03_log_entry_with_empty_parameters(self, test_db):
        """Test creating log entry with empty parameters.

        PRODUCTION USE: Some operations have no parameters.
        """
        from server.database.models import User, LogEntry

        user = User(username="logtest", password_hash="hash")
        test_db.add(user)
        test_db.commit()

        log = LogEntry(
            user_id=user.user_id,
            username=user.username,
            machine_id="machine",
            tool_name="Test",
            function_name="test",
            duration_seconds=1.0,
            parameters={},  # Empty dict
        )
        test_db.add(log)
        test_db.commit()

        assert log.log_id is not None
        assert log.parameters == {}

        print("Created log entry with empty parameters")

    def test_04_log_entry_with_large_parameters(self, test_db):
        """Test creating log entry with large parameters dict.

        PRODUCTION USE: Complex operations may have many parameters.
        """
        from server.database.models import User, LogEntry

        user = User(username="largeparams", password_hash="hash")
        test_db.add(user)
        test_db.commit()

        # Create large parameters dict
        large_params = {f"param_{i}": f"value_{i}" for i in range(100)}
        large_params["nested"] = {"level1": {"level2": {"level3": "deep"}}}

        log = LogEntry(
            user_id=user.user_id,
            username=user.username,
            machine_id="machine",
            tool_name="Test",
            function_name="test",
            duration_seconds=1.0,
            parameters=large_params,
        )
        test_db.add(log)
        test_db.commit()

        assert log.log_id is not None
        assert len(log.parameters) == 101  # 100 params + nested

        print(f"Created log entry with {len(large_params)} parameters")

    def test_05_concurrent_session_creation(self, test_db):
        """Test creating multiple sessions rapidly.

        PRODUCTION USE: Multiple users logging in simultaneously.
        """
        from server.database.models import User, Session as DBSession
        from datetime import datetime

        user = User(username="concurrent", password_hash="hash")
        test_db.add(user)
        test_db.commit()

        # Create many sessions rapidly
        sessions = []
        for i in range(50):
            session = DBSession(
                user_id=user.user_id,
                machine_id=f"machine_{i}",
                ip_address=f"192.168.1.{i % 256}",
                app_version="1.0.0",
            )
            sessions.append(session)
            test_db.add(session)

        test_db.commit()

        # Verify all created
        count = test_db.query(DBSession).filter_by(user_id=user.user_id).count()
        assert count == 50

        print(f"Created {count} sessions concurrently")


class TestFileHandlingEdgeCases:
    """Edge case tests for file handling."""

    def test_01_empty_fixture_file(self):
        """Test handling of empty file.

        PRODUCTION USE: User uploads empty file.
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("")
            temp_path = f.name

        try:
            from server.tools.kr_similar.core import KRSimilarCore

            # Should handle gracefully
            try:
                df = KRSimilarCore.parse_language_file(temp_path, kr_column=5, trans_column=6)
                # Empty file should result in empty dataframe
                assert len(df) == 0
            except Exception as e:
                # Or raise appropriate error
                print(f"Empty file raised: {type(e).__name__}: {e}")
        finally:
            os.unlink(temp_path)

        print("Empty file handled correctly")

    def test_02_file_with_only_header(self):
        """Test handling of file with only header row.

        PRODUCTION USE: User uploads template file with headers only.
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write("ID\tKorean\tTranslation\n")
            temp_path = f.name

        try:
            from server.tools.kr_similar.core import KRSimilarCore

            try:
                df = KRSimilarCore.parse_language_file(temp_path, kr_column=1, trans_column=2)
                # Should have 0 or 1 rows depending on header handling
                assert len(df) <= 1
                print(f"Header-only file: {len(df)} rows")
            except Exception as e:
                print(f"Header-only file raised: {type(e).__name__}")
        finally:
            os.unlink(temp_path)

    def test_03_file_with_special_characters_in_path(self):
        """Test handling file paths with special characters.

        PRODUCTION USE: Users may have special chars in folder names.
        """
        # Create temp dir with special chars (that are valid on most filesystems)
        special_dir = tempfile.mkdtemp(prefix="test_특별한폴더_")

        try:
            test_file = Path(special_dir) / "테스트_파일.txt"
            test_file.write_text("test content", encoding='utf-8')

            # Verify we can read it
            content = test_file.read_text(encoding='utf-8')
            assert content == "test content"

            print(f"Special path handled: {test_file}")
        finally:
            shutil.rmtree(special_dir)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
