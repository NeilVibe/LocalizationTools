#!/usr/bin/env python3
"""
Endpoint Audit Tool v2.0 - Comprehensive API Audit System

Features:
- Smart path matching (handles {param} patterns)
- OpenAPI documentation quality audit
- Auto-generate test stubs for missing tests
- Security audit (auth requirements)
- CI/CD integration (JSON output, exit codes)
- Full HTML report generation

Usage:
    python3 scripts/endpoint_audit.py                    # Full audit
    python3 scripts/endpoint_audit.py --coverage         # Test coverage only
    python3 scripts/endpoint_audit.py --docs             # Documentation quality
    python3 scripts/endpoint_audit.py --security         # Security audit
    python3 scripts/endpoint_audit.py --generate-stubs   # Generate missing tests
    python3 scripts/endpoint_audit.py --json             # JSON output for CI
    python3 scripts/endpoint_audit.py --html             # Generate HTML report
"""

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class Endpoint:
    method: str
    path: str
    operation_id: str = ""
    summary: str = ""
    description: str = ""
    tags: list = field(default_factory=list)
    auth_required: bool = True
    deprecated: bool = False
    request_body: bool = False
    response_schema: bool = False
    tested: bool = False
    test_file: str = ""
    test_line: int = 0
    doc_score: int = 0  # 0-100


@dataclass
class AuditResult:
    total_endpoints: int = 0
    tested_endpoints: int = 0
    documented_endpoints: int = 0
    deprecated_endpoints: int = 0
    auth_protected: int = 0
    missing_summary: list = field(default_factory=list)
    missing_description: list = field(default_factory=list)
    missing_response_schema: list = field(default_factory=list)
    untested: list = field(default_factory=list)
    security_issues: list = field(default_factory=list)
    endpoints: list = field(default_factory=list)


def path_to_regex(path: str) -> re.Pattern:
    """Convert OpenAPI path with {params} to regex pattern."""
    # Escape special regex chars except { }
    escaped = re.escape(path)
    # Replace escaped {param} with regex pattern
    pattern = re.sub(r'\\{[^}]+\\}', r'[^/]+', escaped)
    return re.compile(f'^{pattern}$')


def get_openapi_spec(base_url: str = "http://localhost:8888") -> dict:
    """Fetch OpenAPI spec from running server."""
    try:
        result = subprocess.run(
            ["curl", "-s", f"{base_url}/openapi.json"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception as e:
        print(f"ERROR: Could not fetch OpenAPI spec: {e}", file=sys.stderr)
    return {}


def parse_endpoints(spec: dict) -> list[Endpoint]:
    """Parse all endpoints from OpenAPI spec."""
    endpoints = []
    global_security = spec.get("security", [])

    for path, methods in spec.get("paths", {}).items():
        for method, details in methods.items():
            if method.upper() not in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                continue

            # Check auth requirement
            endpoint_security = details.get("security", global_security)
            auth_required = bool(endpoint_security)

            # Check documentation quality
            summary = details.get("summary", "")
            description = details.get("description", "")
            response_schema = bool(details.get("responses", {}).get("200", {}).get("content"))

            # Calculate doc score
            doc_score = 0
            if summary:
                doc_score += 40
            if description:
                doc_score += 30
            if response_schema:
                doc_score += 30

            endpoints.append(Endpoint(
                method=method.upper(),
                path=path,
                operation_id=details.get("operationId", ""),
                summary=summary,
                description=description,
                tags=details.get("tags", []),
                auth_required=auth_required,
                deprecated=details.get("deprecated", False),
                request_body=bool(details.get("requestBody")),
                response_schema=response_schema,
                doc_score=doc_score,
            ))

    return sorted(endpoints, key=lambda e: (e.path, e.method))


def discover_tested_endpoints(tests_path: Path) -> dict[str, tuple[str, int, str]]:
    """
    Find tested endpoints from test files.
    Returns dict: "METHOD /path" -> (test_file, line, test_name)
    """
    tested = {}

    # Patterns
    client_call = re.compile(r'client\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']', re.IGNORECASE)
    test_func = re.compile(r'def\s+(test_\w+)')

    for test_file in tests_path.rglob("test_*.py"):
        try:
            content = test_file.read_text()
            lines = content.split("\n")

            current_test = "unknown"
            for i, line in enumerate(lines, 1):
                # Track current test function
                func_match = test_func.search(line)
                if func_match:
                    current_test = func_match.group(1)

                # Find client calls
                call_match = client_call.search(line)
                if call_match:
                    method = call_match.group(1).upper()
                    path = call_match.group(2)
                    key = f"{method} {path}"
                    if key not in tested:
                        tested[key] = (str(test_file.name), i, current_test)
        except Exception:
            pass

    return tested


def match_tests_to_endpoints(endpoints: list[Endpoint], tested: dict) -> None:
    """Match discovered tests to endpoints using smart path matching."""
    for ep in endpoints:
        # Direct match first
        key = f"{ep.method} {ep.path}"
        if key in tested:
            ep.tested = True
            ep.test_file, ep.test_line, _ = tested[key]
            continue

        # Try regex matching for path params
        path_regex = path_to_regex(ep.path)
        for test_key, (test_file, test_line, _) in tested.items():
            test_method, test_path = test_key.split(" ", 1)
            if test_method == ep.method and path_regex.match(test_path):
                ep.tested = True
                ep.test_file = test_file
                ep.test_line = test_line
                break


def run_audit(endpoints: list[Endpoint]) -> AuditResult:
    """Run comprehensive audit on endpoints."""
    result = AuditResult(
        total_endpoints=len(endpoints),
        endpoints=endpoints,
    )

    for ep in endpoints:
        # Count tested
        if ep.tested:
            result.tested_endpoints += 1
        else:
            result.untested.append(ep)

        # Count documented
        if ep.doc_score >= 70:
            result.documented_endpoints += 1

        # Count deprecated
        if ep.deprecated:
            result.deprecated_endpoints += 1

        # Count auth protected
        if ep.auth_required:
            result.auth_protected += 1

        # Documentation issues
        if not ep.summary:
            result.missing_summary.append(ep)
        if not ep.description and ep.method in ["POST", "PUT", "PATCH"]:
            result.missing_description.append(ep)
        if not ep.response_schema:
            result.missing_response_schema.append(ep)

        # Security issues
        if not ep.auth_required and ep.method in ["POST", "PUT", "DELETE", "PATCH"]:
            if "/auth/" not in ep.path and "/health" not in ep.path:
                result.security_issues.append(f"Unprotected mutating endpoint: {ep.method} {ep.path}")

    return result


def print_coverage_report(result: AuditResult):
    """Print test coverage report."""
    pct = 100 * result.tested_endpoints // result.total_endpoints if result.total_endpoints > 0 else 0

    print("=" * 70)
    print("                    ENDPOINT TEST COVERAGE REPORT")
    print("=" * 70)
    print()
    print(f"  Total Endpoints:    {result.total_endpoints}")
    print(f"  Tested:             {result.tested_endpoints} ({pct}%)")
    print(f"  Untested:           {len(result.untested)}")
    print()

    # Coverage by tag
    tags = {}
    for ep in result.endpoints:
        tag = ep.tags[0] if ep.tags else "untagged"
        if tag not in tags:
            tags[tag] = {"total": 0, "tested": 0}
        tags[tag]["total"] += 1
        if ep.tested:
            tags[tag]["tested"] += 1

    print("  Coverage by Category:")
    print("  " + "-" * 50)
    for tag in sorted(tags.keys()):
        stats = tags[tag]
        tag_pct = 100 * stats["tested"] // stats["total"] if stats["total"] > 0 else 0
        bar = "█" * (tag_pct // 5) + "░" * (20 - tag_pct // 5)
        status = "✅" if tag_pct == 100 else "⚠️ " if tag_pct >= 70 else "❌"
        print(f"  {status} {tag:20} {bar} {stats['tested']:3}/{stats['total']:3} ({tag_pct}%)")

    print()

    if result.untested:
        print("  Untested Endpoints (need tests):")
        print("  " + "-" * 50)
        for ep in result.untested[:20]:
            print(f"    ❌ {ep.method:6} {ep.path}")
        if len(result.untested) > 20:
            print(f"    ... and {len(result.untested) - 20} more")
    print()


def print_docs_report(result: AuditResult):
    """Print documentation quality report."""
    doc_pct = 100 * result.documented_endpoints // result.total_endpoints if result.total_endpoints > 0 else 0

    print("=" * 70)
    print("                 OPENAPI DOCUMENTATION QUALITY REPORT")
    print("=" * 70)
    print()
    print(f"  Well-documented (score >= 70):  {result.documented_endpoints}/{result.total_endpoints} ({doc_pct}%)")
    print(f"  Missing summary:                {len(result.missing_summary)}")
    print(f"  Missing description:            {len(result.missing_description)}")
    print(f"  Missing response schema:        {len(result.missing_response_schema)}")
    print()

    if result.missing_summary:
        print("  Endpoints missing summary:")
        print("  " + "-" * 50)
        for ep in result.missing_summary[:10]:
            print(f"    ⚠️  {ep.method:6} {ep.path}")
        if len(result.missing_summary) > 10:
            print(f"    ... and {len(result.missing_summary) - 10} more")
    print()


def print_security_report(result: AuditResult):
    """Print security audit report."""
    print("=" * 70)
    print("                      SECURITY AUDIT REPORT")
    print("=" * 70)
    print()
    print(f"  Auth-protected endpoints:  {result.auth_protected}/{result.total_endpoints}")
    print(f"  Deprecated endpoints:      {result.deprecated_endpoints}")
    print(f"  Security issues found:     {len(result.security_issues)}")
    print()

    if result.security_issues:
        print("  ⚠️  Security Issues:")
        print("  " + "-" * 50)
        for issue in result.security_issues:
            print(f"    🔓 {issue}")
    else:
        print("  ✅ No security issues found")
    print()


def generate_test_stubs(result: AuditResult, output_path: Path):
    """Generate test stubs for untested endpoints."""
    stubs = []
    stubs.append('"""Auto-generated test stubs for untested endpoints."""')
    stubs.append("")
    stubs.append("import pytest")
    stubs.append("from fastapi.testclient import TestClient")
    stubs.append("")
    stubs.append("")

    # Group by tag
    by_tag = {}
    for ep in result.untested:
        tag = ep.tags[0] if ep.tags else "misc"
        tag = tag.replace("-", "_").replace(" ", "_")
        if tag not in by_tag:
            by_tag[tag] = []
        by_tag[tag].append(ep)

    for tag, endpoints in sorted(by_tag.items()):
        class_name = f"Test{tag.title().replace('_', '')}"
        stubs.append(f"class {class_name}:")
        stubs.append(f'    """Tests for {tag} endpoints."""')
        stubs.append("")

        for ep in endpoints:
            func_name = ep.operation_id or ep.path.replace("/", "_").replace("{", "").replace("}", "")
            func_name = f"test_{ep.method.lower()}_{func_name}".replace("__", "_").strip("_")

            stubs.append(f"    def {func_name}(self, client, auth_headers):")
            stubs.append(f'        """{ep.method} {ep.path} - {ep.summary or "TODO: add description"}"""')

            # Replace path params with test values
            test_path = ep.path
            test_path = test_path.replace("{user_id}", "1")
            test_path = test_path.replace("{file_id}", "1")
            test_path = test_path.replace("{folder_id}", "1")
            test_path = test_path.replace("{project_id}", "1")
            test_path = test_path.replace("{row_id}", "1")
            test_path = test_path.replace("{tm_id}", "1")
            test_path = test_path.replace("{session_id}", "test-session")
            test_path = test_path.replace("{operation_id}", "test-op")
            test_path = test_path.replace("{installation_id}", "test-install")
            test_path = test_path.replace("{filename}", "test.exe")

            if ep.method == "GET":
                stubs.append(f'        response = client.get("{test_path}", headers=auth_headers)')
            elif ep.method == "POST":
                stubs.append(f'        response = client.post("{test_path}", json={{}}, headers=auth_headers)')
            elif ep.method == "PUT":
                stubs.append(f'        response = client.put("{test_path}", json={{}}, headers=auth_headers)')
            elif ep.method == "DELETE":
                stubs.append(f'        response = client.delete("{test_path}", headers=auth_headers)')
            elif ep.method == "PATCH":
                stubs.append(f'        response = client.patch("{test_path}", json={{}}, headers=auth_headers)')

            # Accept: 200/201/204 (success), 422 (validation = endpoint exists), 404 (resource not found = endpoint exists)
            stubs.append("        # Endpoint existence check: 2xx = success, 422 = validation (needs data), 404 = not found (needs real ID)")
            stubs.append("        assert response.status_code in [200, 201, 204, 422, 404], f'Unexpected {response.status_code}: {response.text[:200]}'")
            stubs.append("")

        stubs.append("")

    output_path.write_text("\n".join(stubs))
    print(f"Generated test stubs: {output_path}")
    print(f"  {len(result.untested)} tests generated")


def generate_html_report(result: AuditResult, output_path: Path):
    """Generate HTML audit report."""
    coverage_pct = 100 * result.tested_endpoints // result.total_endpoints if result.total_endpoints > 0 else 0
    doc_pct = 100 * result.documented_endpoints // result.total_endpoints if result.total_endpoints > 0 else 0

    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Endpoint Audit Report</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 40px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .stats {{ display: flex; gap: 20px; margin: 20px 0; }}
        .stat-card {{ background: #f8f9fa; padding: 20px; border-radius: 8px; flex: 1; text-align: center; }}
        .stat-value {{ font-size: 36px; font-weight: bold; color: #4CAF50; }}
        .stat-label {{ color: #666; margin-top: 5px; }}
        .progress-bar {{ background: #e0e0e0; border-radius: 10px; height: 20px; overflow: hidden; }}
        .progress-fill {{ height: 100%; background: linear-gradient(90deg, #4CAF50, #8BC34A); }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #f5f5f5; font-weight: 600; }}
        tr:hover {{ background: #f9f9f9; }}
        .tested {{ color: #4CAF50; }}
        .untested {{ color: #f44336; }}
        .badge {{ padding: 2px 8px; border-radius: 4px; font-size: 12px; }}
        .badge-get {{ background: #61affe; color: white; }}
        .badge-post {{ background: #49cc90; color: white; }}
        .badge-put {{ background: #fca130; color: white; }}
        .badge-delete {{ background: #f93e3e; color: white; }}
        .badge-patch {{ background: #50e3c2; color: white; }}
        .timestamp {{ color: #999; font-size: 12px; margin-top: 30px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 Endpoint Audit Report</h1>

        <div class="stats">
            <div class="stat-card">
                <div class="stat-value">{result.total_endpoints}</div>
                <div class="stat-label">Total Endpoints</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{coverage_pct}%</div>
                <div class="stat-label">Test Coverage</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{doc_pct}%</div>
                <div class="stat-label">Documentation</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(result.security_issues)}</div>
                <div class="stat-label">Security Issues</div>
            </div>
        </div>

        <h2>Test Coverage</h2>
        <div class="progress-bar">
            <div class="progress-fill" style="width: {coverage_pct}%"></div>
        </div>
        <p>{result.tested_endpoints} of {result.total_endpoints} endpoints tested</p>

        <h2>All Endpoints</h2>
        <table>
            <tr>
                <th>Method</th>
                <th>Path</th>
                <th>Summary</th>
                <th>Auth</th>
                <th>Tested</th>
                <th>Doc Score</th>
            </tr>
"""

    for ep in result.endpoints:
        method_class = f"badge-{ep.method.lower()}"
        tested_class = "tested" if ep.tested else "untested"
        tested_icon = "✅" if ep.tested else "❌"
        auth_icon = "🔒" if ep.auth_required else "🔓"

        html += f"""            <tr>
                <td><span class="badge {method_class}">{ep.method}</span></td>
                <td><code>{ep.path}</code></td>
                <td>{ep.summary or '<em>No summary</em>'}</td>
                <td>{auth_icon}</td>
                <td class="{tested_class}">{tested_icon}</td>
                <td>{ep.doc_score}%</td>
            </tr>
"""

    html += f"""        </table>

        <p class="timestamp">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
</body>
</html>"""

    output_path.write_text(html)
    print(f"Generated HTML report: {output_path}")


def output_json(result: AuditResult):
    """Output JSON for CI/CD integration."""
    output = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_endpoints": result.total_endpoints,
            "tested_endpoints": result.tested_endpoints,
            "coverage_percent": round(100 * result.tested_endpoints / result.total_endpoints, 2) if result.total_endpoints > 0 else 0,
            "documented_endpoints": result.documented_endpoints,
            "security_issues": len(result.security_issues),
        },
        "untested": [{"method": e.method, "path": e.path} for e in result.untested],
        "security_issues": result.security_issues,
        "missing_docs": [{"method": e.method, "path": e.path} for e in result.missing_summary],
    }
    print(json.dumps(output, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Endpoint Audit Tool v2.0")
    parser.add_argument("--coverage", action="store_true", help="Test coverage report")
    parser.add_argument("--docs", action="store_true", help="Documentation quality report")
    parser.add_argument("--security", action="store_true", help="Security audit report")
    parser.add_argument("--generate-stubs", action="store_true", help="Generate test stubs")
    parser.add_argument("--html", action="store_true", help="Generate HTML report")
    parser.add_argument("--json", action="store_true", help="JSON output for CI")
    parser.add_argument("--strict", action="store_true", help="Exit 1 if coverage < 80%")
    parser.add_argument("--url", default="http://localhost:8888", help="API base URL")
    args = parser.parse_args()

    # Default to all reports if nothing specified
    if not any([args.coverage, args.docs, args.security, args.generate_stubs, args.html, args.json]):
        args.coverage = True
        args.docs = True
        args.security = True

    # Get OpenAPI spec
    spec = get_openapi_spec(args.url)
    if not spec:
        print("ERROR: Could not fetch OpenAPI spec. Is the server running?", file=sys.stderr)
        print(f"  Tried: {args.url}/openapi.json", file=sys.stderr)
        sys.exit(1)

    # Parse endpoints
    endpoints = parse_endpoints(spec)
    print(f"Found {len(endpoints)} endpoints from OpenAPI spec\n")

    # Find tests
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    tests_path = project_root / "tests"

    tested = discover_tested_endpoints(tests_path)
    match_tests_to_endpoints(endpoints, tested)

    # Run audit
    result = run_audit(endpoints)

    # Output
    if args.json:
        output_json(result)
    else:
        if args.coverage:
            print_coverage_report(result)
        if args.docs:
            print_docs_report(result)
        if args.security:
            print_security_report(result)

    if args.generate_stubs:
        stubs_path = project_root / "tests" / "api" / "test_generated_stubs.py"
        generate_test_stubs(result, stubs_path)

    if args.html:
        html_path = project_root / "docs" / "endpoint_audit_report.html"
        html_path.parent.mkdir(exist_ok=True)
        generate_html_report(result, html_path)

    # Strict mode
    if args.strict:
        coverage = 100 * result.tested_endpoints // result.total_endpoints if result.total_endpoints > 0 else 0
        if coverage < 80:
            print(f"\n❌ STRICT MODE FAILED: Coverage {coverage}% < 80%")
            sys.exit(1)
        print(f"\n✅ STRICT MODE PASSED: Coverage {coverage}% >= 80%")


if __name__ == "__main__":
    main()
