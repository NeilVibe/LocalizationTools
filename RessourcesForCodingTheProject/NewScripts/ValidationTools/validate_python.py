#!/usr/bin/env python3
"""
Python Validation Tool
======================
A comprehensive validation script for Python files.

Checks:
- Syntax validation (py_compile)
- AST parsing
- Import availability
- Unused imports detection
- Static analysis (functions, classes, lines)
- Common issues (print statements, bare excepts, TODO/FIXME, missing type hints)

Usage:
    ./validate_python.py <path_to_python_file>
    python validate_python.py <path_to_python_file>

Exit codes:
    0 - All critical checks passed
    1 - Critical checks failed
"""

import argparse
import ast
import importlib.util
import os
import py_compile
import re
import sys
import tokenize
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Set, Tuple, Optional


# Symbols for output
PASS = "\u2705"  # Green checkmark
FAIL = "\u274C"  # Red X
WARN = "\u26A0\uFE0F"  # Warning sign


@dataclass
class ValidationResult:
    """Container for validation results."""
    passed: bool
    message: str
    details: List[str] = field(default_factory=list)


@dataclass
class FileStats:
    """Statistics about the analyzed file."""
    total_lines: int = 0
    code_lines: int = 0
    comment_lines: int = 0
    blank_lines: int = 0
    function_count: int = 0
    class_count: int = 0
    async_function_count: int = 0


class PythonValidator:
    """Validates Python files for syntax, imports, and common issues."""

    # Standard library modules that don't need to be installed
    STDLIB_MODULES = {
        'abc', 'argparse', 'ast', 'asyncio', 'base64', 'bisect', 'calendar',
        'collections', 'contextlib', 'copy', 'csv', 'dataclasses', 'datetime',
        'decimal', 'difflib', 'email', 'enum', 'errno', 'functools', 'glob',
        'gzip', 'hashlib', 'heapq', 'hmac', 'html', 'http', 'importlib', 'inspect',
        'io', 'itertools', 'json', 'logging', 'math', 'mimetypes', 'multiprocessing',
        'numbers', 'operator', 'os', 'pathlib', 'pickle', 'platform', 'pprint',
        'queue', 'random', 're', 'secrets', 'shlex', 'shutil', 'signal', 'socket',
        'sqlite3', 'ssl', 'stat', 'statistics', 'string', 'struct', 'subprocess',
        'sys', 'tempfile', 'textwrap', 'threading', 'time', 'timeit', 'traceback',
        'types', 'typing', 'unittest', 'urllib', 'uuid', 'warnings', 'weakref',
        'xml', 'zipfile', 'zlib', 'py_compile', 'token', 'tokenize', 'codecs',
        'locale', 'gettext', 'configparser', 'typing_extensions', 'contextvars',
        '_thread', 'builtins', '__future__', 'pkgutil', 'runpy', 'compileall',
        'dis', 'code', 'codeop', 'pdb', 'profile', 'pstats', 'trace', 'tracemalloc',
        'gc', 'array', 'ctypes', 'mmap', 'struct', 'codecs', 'unicodedata', 'stringprep',
        'readline', 'rlcompleter', 'graphlib', 'fcntl', 'grp', 'pwd', 'select',
        'selectors', 'termios', 'tty', 'pty', 'fnmatch', 'linecache', 'fileinput',
        'filecmp', 'netrc', 'xdrlib', 'aifc', 'sunau', 'wave', 'chunk', 'colorsys',
        'imghdr', 'sndhdr', 'ossaudiodev', 'posix', 'posixpath', 'ntpath', 'genericpath',
        'sre_compile', 'sre_constants', 'sre_parse', 'keyword', 'symtable', 'tabnanny',
        'pyclbr', 'py_compile', 'pickletools', 'reprlib', 'atexit', 'faulthandler',
        'modulefinder', 'fractions', 'cmath', 'concurrent', 'venv', 'zipimport',
        'zipapp', 'bdb', 'cmd', 'curses', 'distutils', 'doctest', 'ensurepip',
        'idlelib', 'lib2to3', 'test', 'tkinter', 'turtle', 'turtledemo', 'webbrowser',
        'winsound', 'winreg', 'msvcrt', 'msilib', '_winapi'
    }

    def __init__(self, filepath: str) -> None:
        self.filepath = Path(filepath).resolve()
        self.source: Optional[str] = None
        self.tree: Optional[ast.AST] = None
        self.stats = FileStats()
        self.results: List[Tuple[str, ValidationResult]] = []
        self.critical_failed = False

    def load_file(self) -> bool:
        """Load the Python file content."""
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                self.source = f.read()
            return True
        except FileNotFoundError:
            self.results.append(("File Load", ValidationResult(
                False, "File not found", [str(self.filepath)]
            )))
            self.critical_failed = True
            return False
        except UnicodeDecodeError as e:
            self.results.append(("File Load", ValidationResult(
                False, "Unicode decode error", [str(e)]
            )))
            self.critical_failed = True
            return False
        except Exception as e:
            self.results.append(("File Load", ValidationResult(
                False, f"Error loading file: {e}", []
            )))
            self.critical_failed = True
            return False

    def check_syntax(self) -> ValidationResult:
        """Check Python syntax using py_compile."""
        try:
            py_compile.compile(str(self.filepath), doraise=True)
            return ValidationResult(True, "Syntax is valid")
        except py_compile.PyCompileError as e:
            self.critical_failed = True
            return ValidationResult(False, "Syntax error", [str(e)])

    def check_ast_parse(self) -> ValidationResult:
        """Parse the file as AST."""
        try:
            self.tree = ast.parse(self.source)
            return ValidationResult(True, "AST parsing successful")
        except SyntaxError as e:
            self.critical_failed = True
            return ValidationResult(
                False, "AST parse failed",
                [f"Line {e.lineno}: {e.msg}"]
            )

    def get_imports(self) -> Tuple[Set[str], Set[Tuple[str, int]]]:
        """Extract all imports from the AST.

        Returns:
            Tuple of (module_names, imports_with_lines)
        """
        if not self.tree:
            return set(), set()

        modules = set()
        imports_with_lines = set()

        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name.split('.')[0]
                    modules.add(name)
                    imports_with_lines.add((alias.asname or alias.name, node.lineno))
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    modules.add(node.module.split('.')[0])
                for alias in node.names:
                    imports_with_lines.add((alias.asname or alias.name, node.lineno))

        return modules, imports_with_lines

    def check_imports_available(self) -> ValidationResult:
        """Check if all imported modules are available."""
        modules, _ = self.get_imports()
        unavailable = []
        available = []

        for module in modules:
            # Skip relative imports and known stdlib
            if module in self.STDLIB_MODULES:
                available.append(module)
                continue

            # Try to find the module
            try:
                spec = importlib.util.find_spec(module)
                if spec is not None:
                    available.append(module)
                else:
                    unavailable.append(module)
            except (ModuleNotFoundError, ImportError, ValueError):
                unavailable.append(module)

        if unavailable:
            return ValidationResult(
                False, f"{len(unavailable)} unavailable module(s)",
                [f"  - {m}" for m in sorted(unavailable)]
            )
        return ValidationResult(
            True, f"All {len(available)} imports available"
        )

    def check_unused_imports(self) -> ValidationResult:
        """Detect potentially unused imports."""
        if not self.tree or not self.source:
            return ValidationResult(True, "Skipped (no AST)")

        _, imports_with_lines = self.get_imports()
        unused = []

        # Get all names used in the code
        used_names = set()
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Name):
                used_names.add(node.id)
            elif isinstance(node, ast.Attribute):
                # Handle attribute access like module.function
                if isinstance(node.value, ast.Name):
                    used_names.add(node.value.id)

        # Also check string references (for type hints as strings)
        string_pattern = re.compile(r'["\'](\w+)["\']')
        for match in string_pattern.finditer(self.source):
            used_names.add(match.group(1))

        for name, lineno in imports_with_lines:
            # Get the base name (first part before .)
            base_name = name.split('.')[0]
            if base_name not in used_names:
                unused.append(f"Line {lineno}: '{name}'")

        if unused:
            return ValidationResult(
                True, f"{len(unused)} potentially unused import(s)",
                unused
            )
        return ValidationResult(True, "No unused imports detected")

    def analyze_statistics(self) -> FileStats:
        """Analyze file statistics."""
        if not self.source or not self.tree:
            return self.stats

        lines = self.source.split('\n')
        self.stats.total_lines = len(lines)

        for line in lines:
            stripped = line.strip()
            if not stripped:
                self.stats.blank_lines += 1
            elif stripped.startswith('#'):
                self.stats.comment_lines += 1
            else:
                self.stats.code_lines += 1

        for node in ast.walk(self.tree):
            if isinstance(node, ast.FunctionDef):
                self.stats.function_count += 1
            elif isinstance(node, ast.AsyncFunctionDef):
                self.stats.async_function_count += 1
            elif isinstance(node, ast.ClassDef):
                self.stats.class_count += 1

        return self.stats

    def check_print_statements(self) -> ValidationResult:
        """Check for print() statements (should use logger)."""
        if not self.tree:
            return ValidationResult(True, "Skipped (no AST)")

        prints = []
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == 'print':
                    prints.append(f"Line {node.lineno}")

        if prints:
            return ValidationResult(
                True, f"{len(prints)} print() statement(s) found",
                [f"  - {p}" for p in prints]
            )
        return ValidationResult(True, "No print() statements")

    def check_bare_excepts(self) -> ValidationResult:
        """Check for bare except clauses."""
        if not self.tree:
            return ValidationResult(True, "Skipped (no AST)")

        bare_excepts = []
        for node in ast.walk(self.tree):
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    bare_excepts.append(f"Line {node.lineno}")

        if bare_excepts:
            return ValidationResult(
                True, f"{len(bare_excepts)} bare except clause(s)",
                [f"  - {b}" for b in bare_excepts]
            )
        return ValidationResult(True, "No bare except clauses")

    def check_todo_comments(self) -> ValidationResult:
        """Check for TODO/FIXME comments."""
        if not self.source:
            return ValidationResult(True, "Skipped (no source)")

        todos = []
        # Match TODO/FIXME etc in comments, but not in string literals
        # This pattern ensures we only match after a # that starts a comment
        keywords = ['TODO', 'FIXME', 'XXX', 'HACK']

        for i, line in enumerate(self.source.split('\n'), 1):
            # Find the comment portion of the line (after #, but not inside strings)
            # Simple heuristic: find # not preceded by quotes on same line
            comment_start = -1
            in_string = None
            for j, char in enumerate(line):
                if char in ('"', "'") and (j == 0 or line[j-1] != '\\'):
                    if in_string is None:
                        in_string = char
                    elif in_string == char:
                        in_string = None
                elif char == '#' and in_string is None:
                    comment_start = j
                    break

            if comment_start >= 0:
                comment = line[comment_start:]
                for kw in keywords:
                    if re.search(rf'\b{kw}\b', comment, re.IGNORECASE):
                        todos.append(f"Line {i}: {kw}")

        if todos:
            return ValidationResult(
                True, f"{len(todos)} TODO/FIXME comment(s)",
                [f"  - {t}" for t in todos]
            )
        return ValidationResult(True, "No TODO/FIXME comments")

    def check_type_hints(self) -> ValidationResult:
        """Check for missing type hints on functions."""
        if not self.tree:
            return ValidationResult(True, "Skipped (no AST)")

        missing = []

        for node in ast.walk(self.tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Skip private methods and dunder methods
                if node.name.startswith('_') and not node.name.startswith('__'):
                    continue

                issues = []

                # Check return type hint
                if node.returns is None:
                    issues.append("missing return type")

                # Check argument type hints (skip self, cls)
                for arg in node.args.args:
                    if arg.arg in ('self', 'cls'):
                        continue
                    if arg.annotation is None:
                        issues.append(f"missing type for '{arg.arg}'")

                if issues:
                    missing.append(f"Line {node.lineno}: {node.name}() - {', '.join(issues)}")

        if missing:
            return ValidationResult(
                True, f"{len(missing)} function(s) with missing type hints",
                missing[:10] + (['...and more'] if len(missing) > 10 else [])
            )
        return ValidationResult(True, "All functions have type hints")

    def validate(self) -> bool:
        """Run all validation checks.

        Returns:
            True if all critical checks passed, False otherwise.
        """
        # Load file
        if not self.load_file():
            return False

        # Critical checks
        self.results.append(("Syntax Check", self.check_syntax()))
        self.results.append(("AST Parse", self.check_ast_parse()))
        self.results.append(("Import Availability", self.check_imports_available()))

        # Analysis (non-critical)
        self.results.append(("Unused Imports", self.check_unused_imports()))
        self.results.append(("Print Statements", self.check_print_statements()))
        self.results.append(("Bare Excepts", self.check_bare_excepts()))
        self.results.append(("TODO/FIXME Comments", self.check_todo_comments()))
        self.results.append(("Type Hints", self.check_type_hints()))

        # Gather statistics
        self.analyze_statistics()

        return not self.critical_failed

    def print_report(self) -> None:
        """Print formatted validation report."""
        print("\n" + "=" * 60)
        print(f"Python Validation Report")
        print("=" * 60)
        print(f"File: {self.filepath}")
        print("-" * 60)

        # Critical checks
        print("\n[Critical Checks]")
        for name, result in self.results[:3]:  # First 3 are critical
            symbol = PASS if result.passed else FAIL
            print(f"  {symbol} {name}: {result.message}")
            for detail in result.details:
                print(f"       {detail}")

        # Analysis checks
        print("\n[Code Quality Analysis]")
        for name, result in self.results[3:]:  # Rest are analysis
            # Determine symbol based on content
            if not result.passed:
                symbol = FAIL
            elif result.details:
                symbol = WARN
            else:
                symbol = PASS
            print(f"  {symbol} {name}: {result.message}")
            for detail in result.details[:5]:  # Limit details shown
                print(f"       {detail}")
            if len(result.details) > 5:
                print(f"       ...and {len(result.details) - 5} more")

        # Statistics
        print("\n[File Statistics]")
        print(f"  Total lines:      {self.stats.total_lines}")
        print(f"  Code lines:       {self.stats.code_lines}")
        print(f"  Comment lines:    {self.stats.comment_lines}")
        print(f"  Blank lines:      {self.stats.blank_lines}")
        print(f"  Classes:          {self.stats.class_count}")
        print(f"  Functions:        {self.stats.function_count}")
        print(f"  Async functions:  {self.stats.async_function_count}")

        # Summary
        print("\n" + "-" * 60)
        if self.critical_failed:
            print(f"{FAIL} VALIDATION FAILED - Critical issues found")
        else:
            warnings = sum(1 for _, r in self.results if r.passed and r.details)
            if warnings:
                print(f"{WARN} VALIDATION PASSED with {warnings} warning(s)")
            else:
                print(f"{PASS} VALIDATION PASSED - All checks OK")
        print("=" * 60 + "\n")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Validate Python files for syntax, imports, and common issues.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s script.py
    %(prog)s /path/to/module.py
    %(prog)s ../relative/path/file.py
        """
    )
    parser.add_argument(
        'filepath',
        help='Path to the Python file to validate'
    )
    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Only show summary (no details)'
    )

    args = parser.parse_args()

    # Resolve path
    filepath = Path(args.filepath)
    if not filepath.is_absolute():
        filepath = Path.cwd() / filepath

    # Validate
    validator = PythonValidator(str(filepath))
    success = validator.validate()

    # Print report
    if not args.quiet:
        validator.print_report()
    else:
        if success:
            print(f"{PASS} {filepath.name}: Validation passed")
        else:
            print(f"{FAIL} {filepath.name}: Validation failed")

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
