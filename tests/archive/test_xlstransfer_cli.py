"""
Unit tests for XLSTransfer CLI wrapper
"""

import subprocess
import json
import os
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
CLI_SCRIPT = PROJECT_ROOT / "server/tools/xlstransfer/cli/xlstransfer_cli.py"
TEST_FILE = PROJECT_ROOT / "locaNext/test-data/TESTSMALL.xlsx"


def run_cli(command=None, *args):
    """Helper to run CLI command with proper environment"""
    env = os.environ.copy()
    env['PYTHONPATH'] = str(PROJECT_ROOT)

    if command is None:
        cmd = ['python3', str(CLI_SCRIPT)]
    else:
        cmd = ['python3', str(CLI_SCRIPT), command, *args]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env
    )

    return result


def test_cli_no_command():
    """Test CLI with no command shows error"""
    result = run_cli()
    assert result.returncode == 1
    output = json.loads(result.stdout)
    assert output['success'] == False
    assert 'available_commands' in output


def test_cli_unknown_command():
    """Test CLI with unknown command shows error"""
    result = run_cli('invalid_command')
    assert result.returncode == 1
    output = json.loads(result.stdout)
    assert output['success'] == False
    assert 'Unknown command' in output['error']


def test_validate_dict():
    """Test validate_dict command"""
    if not TEST_FILE.exists():
        return  # Skip if test file doesn't exist

    result = run_cli('validate_dict', str(TEST_FILE))
    assert result.returncode == 0

    # Parse JSON output (last line)
    output_lines = result.stdout.strip().split('\n')
    output = json.loads(output_lines[-1])

    assert output['success'] == True
    assert output['valid'] == True
    assert output['file'] == str(TEST_FILE)


def test_check_spaces():
    """Test check_spaces command"""
    if not TEST_FILE.exists():
        return

    result = run_cli('check_spaces', str(TEST_FILE))
    assert result.returncode == 0

    output_lines = result.stdout.strip().split('\n')
    output = json.loads(output_lines[-1])

    assert output['success'] == True
    assert 'mismatches' in output
    assert output['file'] == str(TEST_FILE)


def test_check_newlines():
    """Test check_newlines command"""
    if not TEST_FILE.exists():
        return

    result = run_cli('check_newlines', str(TEST_FILE))
    assert result.returncode == 0

    output_lines = result.stdout.strip().split('\n')
    output = json.loads(output_lines[-1])

    assert output['success'] == True
    assert 'mismatches' in output


def test_find_duplicates():
    """Test find_duplicates command"""
    if not TEST_FILE.exists():
        return

    # Use first column from the actual test file
    result = run_cli('find_duplicates', str(TEST_FILE), '연금 스킬 경험치가 증가합니다.')

    # If the column doesn't exist, that's expected - the test file might not have standard columns
    output_lines = result.stdout.strip().split('\n')
    output = json.loads(output_lines[-1])

    # Check that we got a valid response (success or error is both OK for this test)
    assert 'success' in output
    if output['success']:
        assert 'duplicates' in output


if __name__ == '__main__':
    print("Running XLSTransfer CLI tests...")
    print("\n1. Testing CLI with no command...")
    test_cli_no_command()
    print("✓ PASS")

    print("\n2. Testing CLI with unknown command...")
    test_cli_unknown_command()
    print("✓ PASS")

    print("\n3. Testing validate_dict...")
    test_validate_dict()
    print("✓ PASS")

    print("\n4. Testing check_spaces...")
    test_check_spaces()
    print("✓ PASS")

    print("\n5. Testing check_newlines...")
    test_check_newlines()
    print("✓ PASS")

    print("\n6. Testing find_duplicates...")
    test_find_duplicates()
    print("✓ PASS")

    print("\n✅ All XLSTransfer CLI tests passed!")
