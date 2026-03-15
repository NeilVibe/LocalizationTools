#!/bin/bash
# ============================================================================
# LocaNext API Test Runner — Overnight Autonomous Execution
# ============================================================================
# Runs pytest-based API E2E tests by subsystem with result capture.
#
# Usage:
#   ./testing_toolkit/run_api_tests.sh              # Run all subsystems
#   ./testing_toolkit/run_api_tests.sh all           # Same as above
#   ./testing_toolkit/run_api_tests.sh auth files    # Run only auth + files
#   ./testing_toolkit/run_api_tests.sh --help        # Show this help
#
# Results are saved to:
#   testing_toolkit/api_test_results_YYYY-MM-DD_HHMMSS.log
# ============================================================================

set -uo pipefail

# --- Configuration -----------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TESTS_DIR="$PROJECT_ROOT/tests/api"
PYTEST_CONFIG="$SCRIPT_DIR/pytest_api_config.ini"
BASE_URL="http://localhost:8888"
PER_TEST_TIMEOUT=120

# Subsystem execution order (dependency-safe)
ALL_SUBSYSTEMS=(
    health
    auth
    projects
    folders
    files
    rows
    tm
    gamedata
    codex
    worldmap
    ai
    search
    qa
    merge
    export
    offline
    admin
    tools
    integration
)

# --- Colors ------------------------------------------------------------------

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# --- Counters ----------------------------------------------------------------

TOTAL_PASSED=0
TOTAL_FAILED=0
TOTAL_SKIPPED=0
TOTAL_ERRORS=0
SUBSYSTEM_RESULTS=()
RUN_DATE=$(date -u +"%Y-%m-%d_%H%M%S")
LOG_FILE="$SCRIPT_DIR/api_test_results_${RUN_DATE}.log"

# --- Functions ---------------------------------------------------------------

usage() {
    cat << 'EOF'
LocaNext API Test Runner — Overnight Autonomous Execution

Usage:
  ./testing_toolkit/run_api_tests.sh [OPTIONS] [SUBSYSTEMS...]

Options:
  --help, -h     Show this help message
  --list, -l     List available subsystems
  --dry-run      Show what would be run without executing

Subsystems:
  all            Run all subsystems (default)
  health         Health & status endpoints
  auth           Authentication & sessions
  projects       Project management
  folders        Folder operations
  files          File upload/download/convert
  rows           Row CRUD operations
  tm             Translation Memory
  gamedata       GameData browse/columns
  codex          Codex entity endpoints
  worldmap       World map data
  ai             AI intelligence (suggestions, naming, context)
  search         Search functionality
  qa             QA and grammar checks
  merge          Merge operations
  export         Export pipeline
  offline        Offline mode & sync
  admin          Admin & stats
  tools          External tools (QuickSearch, KR Similar, XLSTransfer)
  integration    Cross-subsystem integration tests

Examples:
  ./testing_toolkit/run_api_tests.sh                    # Run everything
  ./testing_toolkit/run_api_tests.sh auth files rows    # Run specific subsystems
  ./testing_toolkit/run_api_tests.sh --list             # Show available subsystems

Results saved to: testing_toolkit/api_test_results_YYYY-MM-DD_HHMMSS.log
EOF
}

list_subsystems() {
    echo "Available subsystems:"
    for sub in "${ALL_SUBSYSTEMS[@]}"; do
        local test_file="$TESTS_DIR/test_${sub}.py"
        if [ -f "$test_file" ]; then
            echo -e "  ${GREEN}*${NC} $sub  (test file exists)"
        else
            echo -e "  ${YELLOW}-${NC} $sub  (test file pending)"
        fi
    done
}

log() {
    local msg="$1"
    echo -e "$msg"
    # Strip ANSI codes for log file
    echo -e "$msg" | sed 's/\x1b\[[0-9;]*m//g' >> "$LOG_FILE"
}

preflight_check() {
    log "${CYAN}${BOLD}=== Pre-flight Checks ===${NC}"

    # Check Python
    if ! command -v python3 &> /dev/null; then
        log "${RED}FATAL: python3 not found${NC}"
        exit 1
    fi
    log "  ${GREEN}OK${NC} python3 found: $(python3 --version 2>&1)"

    # Check pytest
    if ! python3 -m pytest --version &> /dev/null 2>&1; then
        log "${RED}FATAL: pytest not found. Install: pip install pytest${NC}"
        exit 1
    fi
    log "  ${GREEN}OK${NC} pytest found: $(python3 -m pytest --version 2>&1 | head -1)"

    # Check server health
    local health_status
    health_status=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "$BASE_URL/api/health/ping" 2>/dev/null || echo "000")

    if [ "$health_status" = "000" ]; then
        log "${RED}FATAL: Server not reachable at $BASE_URL${NC}"
        log ""
        log "Start the server first:"
        log "  cd $PROJECT_ROOT && DEV_MODE=true python3 server/main.py"
        log ""
        log "Or use check_servers.sh:"
        log "  ./scripts/check_servers.sh"
        exit 1
    fi

    # Accept 2xx and 4xx as server-alive (4xx = auth-gated but server responds)
    if [[ "$health_status" =~ ^[245] ]]; then
        log "  ${GREEN}OK${NC} Server responding at $BASE_URL (HTTP $health_status)"
    else
        log "${RED}FATAL: Server returned HTTP $health_status${NC}"
        exit 1
    fi

    # Check pytest config
    if [ -f "$PYTEST_CONFIG" ]; then
        log "  ${GREEN}OK${NC} Using pytest config: $PYTEST_CONFIG"
    else
        log "  ${YELLOW}WARN${NC} No pytest config at $PYTEST_CONFIG, using defaults"
        PYTEST_CONFIG=""
    fi

    log ""
}

run_subsystem() {
    local subsystem="$1"
    local test_file="$TESTS_DIR/test_${subsystem}.py"
    local sub_start sub_end sub_duration
    local passed=0 failed=0 skipped=0 errors=0 status_label

    sub_start=$(date +%s)
    local sub_start_time
    sub_start_time=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    log "${CYAN}${BOLD}--- [$subsystem] Start: $sub_start_time ---${NC}"

    # Skip if test file does not exist (Wave 2 creates them)
    if [ ! -f "$test_file" ]; then
        log "  ${YELLOW}SKIP${NC} $test_file does not exist yet"
        TOTAL_SKIPPED=$((TOTAL_SKIPPED + 1))
        SUBSYSTEM_RESULTS+=("$subsystem|SKIP|0|0|0|0|0s")
        log ""
        return 0
    fi

    # Build pytest command
    local pytest_cmd="python3 -m pytest $test_file -v --tb=short --timeout=$PER_TEST_TIMEOUT"
    if [ -n "$PYTEST_CONFIG" ]; then
        pytest_cmd="$pytest_cmd -c $PYTEST_CONFIG"
    fi

    # Execute and capture output
    local output_file="/tmp/api_test_${subsystem}_${RUN_DATE}.txt"
    local exit_code=0

    $pytest_cmd > "$output_file" 2>&1 || exit_code=$?

    # Append subsystem output to main log
    cat "$output_file" >> "$LOG_FILE"

    # Parse results from pytest output
    # Pytest summary line format: "X passed, Y failed, Z skipped, W error"
    local summary_line
    summary_line=$(tail -5 "$output_file" | grep -E "passed|failed|error|no tests" | tail -1)

    if echo "$summary_line" | grep -q "no tests ran"; then
        log "  ${YELLOW}SKIP${NC} No tests collected in $test_file"
        SUBSYSTEM_RESULTS+=("$subsystem|EMPTY|0|0|0|0|0s")
    elif [ $exit_code -eq 0 ]; then
        passed=$(echo "$summary_line" | grep -oP '\d+(?= passed)' || echo "0")
        skipped=$(echo "$summary_line" | grep -oP '\d+(?= skipped)' || echo "0")
        [ -z "$passed" ] && passed=0
        [ -z "$skipped" ] && skipped=0
        TOTAL_PASSED=$((TOTAL_PASSED + passed))
        TOTAL_SKIPPED=$((TOTAL_SKIPPED + skipped))
        status_label="${GREEN}PASS${NC}"
        SUBSYSTEM_RESULTS+=("$subsystem|PASS|$passed|0|$skipped|0|")
        log "  ${GREEN}PASS${NC} $passed passed, $skipped skipped"
    else
        passed=$(echo "$summary_line" | grep -oP '\d+(?= passed)' || echo "0")
        failed=$(echo "$summary_line" | grep -oP '\d+(?= failed)' || echo "0")
        skipped=$(echo "$summary_line" | grep -oP '\d+(?= skipped)' || echo "0")
        errors=$(echo "$summary_line" | grep -oP '\d+(?= error)' || echo "0")
        [ -z "$passed" ] && passed=0
        [ -z "$failed" ] && failed=0
        [ -z "$skipped" ] && skipped=0
        [ -z "$errors" ] && errors=0

        TOTAL_PASSED=$((TOTAL_PASSED + passed))
        TOTAL_FAILED=$((TOTAL_FAILED + failed))
        TOTAL_SKIPPED=$((TOTAL_SKIPPED + skipped))
        TOTAL_ERRORS=$((TOTAL_ERRORS + errors))

        if [ "$errors" -gt 0 ]; then
            status_label="${RED}ERROR${NC}"
            log "  ${RED}ERROR${NC} $passed passed, $failed failed, $errors errors"
            SUBSYSTEM_RESULTS+=("$subsystem|ERROR|$passed|$failed|$skipped|$errors|")
        else
            status_label="${RED}FAIL${NC}"
            log "  ${RED}FAIL${NC} $passed passed, $failed failed, $skipped skipped"
            SUBSYSTEM_RESULTS+=("$subsystem|FAIL|$passed|$failed|$skipped|$errors|")
        fi
    fi

    sub_end=$(date +%s)
    sub_duration=$((sub_end - sub_start))
    log "  Duration: ${sub_duration}s"
    log ""

    # Update last result with duration
    local last_idx=$((${#SUBSYSTEM_RESULTS[@]} - 1))
    SUBSYSTEM_RESULTS[$last_idx]="${SUBSYSTEM_RESULTS[$last_idx]}${sub_duration}s"

    # Clean up temp file
    rm -f "$output_file"

    return 0
}

print_summary() {
    local total=$((TOTAL_PASSED + TOTAL_FAILED + TOTAL_ERRORS))
    local run_end
    run_end=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    log ""
    log "${CYAN}${BOLD}================================================================${NC}"
    log "${CYAN}${BOLD}  API Test Results Summary${NC}"
    log "${CYAN}${BOLD}  Run: $RUN_DATE${NC}"
    log "${CYAN}${BOLD}================================================================${NC}"
    log ""
    log "  ${BOLD}Subsystem Results:${NC}"
    log "  %-15s %-8s %6s %6s %6s %6s %8s" "SUBSYSTEM" "STATUS" "PASS" "FAIL" "SKIP" "ERR" "TIME"
    log "  --------------- -------- ------ ------ ------ ------ --------"

    for result in "${SUBSYSTEM_RESULTS[@]}"; do
        IFS='|' read -r sub status p f s e dur <<< "$result"
        local color="$NC"
        case "$status" in
            PASS) color="$GREEN" ;;
            FAIL|ERROR) color="$RED" ;;
            SKIP|EMPTY) color="$YELLOW" ;;
        esac
        log "  $(printf '%-15s' "$sub") ${color}$(printf '%-8s' "$status")${NC} $(printf '%6s %6s %6s %6s %8s' "$p" "$f" "$s" "$e" "$dur")"
    done

    log ""
    log "  ${BOLD}Totals:${NC}"
    log "  ${GREEN}Passed:  $TOTAL_PASSED${NC}"
    log "  ${RED}Failed:  $TOTAL_FAILED${NC}"
    log "  ${YELLOW}Skipped: $TOTAL_SKIPPED${NC}"
    if [ "$TOTAL_ERRORS" -gt 0 ]; then
        log "  ${RED}Errors:  $TOTAL_ERRORS${NC}"
    fi
    log ""
    log "  Completed: $run_end"
    log "  Log file:  $LOG_FILE"
    log ""

    if [ "$TOTAL_FAILED" -gt 0 ] || [ "$TOTAL_ERRORS" -gt 0 ]; then
        log "${RED}${BOLD}RESULT: FAILED${NC} ($TOTAL_FAILED failures, $TOTAL_ERRORS errors)"
        return 1
    else
        log "${GREEN}${BOLD}RESULT: PASSED${NC} ($TOTAL_PASSED tests across ${#SUBSYSTEM_RESULTS[@]} subsystems)"
        return 0
    fi
}

# --- Main --------------------------------------------------------------------

# Parse arguments
SUBSYSTEMS_TO_RUN=()
DRY_RUN=false

for arg in "$@"; do
    case "$arg" in
        --help|-h)
            usage
            exit 0
            ;;
        --list|-l)
            list_subsystems
            exit 0
            ;;
        --dry-run)
            DRY_RUN=true
            ;;
        all)
            SUBSYSTEMS_TO_RUN=("${ALL_SUBSYSTEMS[@]}")
            ;;
        *)
            # Validate subsystem name
            local_valid=false
            for valid_sub in "${ALL_SUBSYSTEMS[@]}"; do
                if [ "$arg" = "$valid_sub" ]; then
                    local_valid=true
                    break
                fi
            done
            if [ "$local_valid" = true ]; then
                SUBSYSTEMS_TO_RUN+=("$arg")
            else
                echo -e "${RED}Unknown subsystem: $arg${NC}"
                echo "Use --list to see available subsystems"
                exit 1
            fi
            ;;
    esac
done

# Default to all if no subsystems specified
if [ ${#SUBSYSTEMS_TO_RUN[@]} -eq 0 ]; then
    SUBSYSTEMS_TO_RUN=("${ALL_SUBSYSTEMS[@]}")
fi

# Dry run mode
if [ "$DRY_RUN" = true ]; then
    echo "Would run the following subsystems:"
    for sub in "${SUBSYSTEMS_TO_RUN[@]}"; do
        test_file="$TESTS_DIR/test_${sub}.py"
        if [ -f "$test_file" ]; then
            echo "  * $sub ($test_file)"
        else
            echo "  - $sub (SKIP — file not found)"
        fi
    done
    exit 0
fi

# Initialize log file
echo "LocaNext API Test Run — $RUN_DATE" > "$LOG_FILE"
echo "Subsystems: ${SUBSYSTEMS_TO_RUN[*]}" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

# Banner
log ""
log "${CYAN}${BOLD}================================================================${NC}"
log "${CYAN}${BOLD}  LocaNext API Test Runner — Overnight Autonomous Execution${NC}"
log "${CYAN}${BOLD}  ${#SUBSYSTEMS_TO_RUN[@]} subsystems queued${NC}"
log "${CYAN}${BOLD}================================================================${NC}"
log ""

# Pre-flight
preflight_check

# Execute subsystems
RUN_START=$(date +%s)

for subsystem in "${SUBSYSTEMS_TO_RUN[@]}"; do
    run_subsystem "$subsystem"
done

RUN_END=$(date +%s)
RUN_DURATION=$((RUN_END - RUN_START))

log "Total execution time: ${RUN_DURATION}s"

# Print summary and exit with appropriate code
print_summary
exit $?
