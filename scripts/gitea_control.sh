#!/bin/bash
# gitea_control.sh - Unified Gitea + Linux Runner + Windows Runner management
# Usage: ./gitea_control.sh {status|stop|kill|start|restart|monitor}
#
# Manages:
#   1. Gitea Server (WSL - systemd)
#   2. Linux Runner (WSL - act_runner daemon)
#   3. Windows Runner (Windows - GiteaActRunner service via NSSM)
#
# WARNING: This is CRITICAL INFRASTRUCTURE. Read GITEA_CLEAN_KILL_PROTOCOL.md first!

GITEA_DIR="/home/neil1988/gitea"
GITEA_DB="$GITEA_DIR/data/gitea.db"
WIN_RUNNER_SERVICE="GiteaActRunner"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if we can run PowerShell commands
can_manage_windows() {
    command -v powershell.exe &> /dev/null
}

print_status() {
    echo -e "${GREEN}[OK]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

status() {
    echo "=== Gitea Status (Full Architecture) ==="
    echo ""

    # --- GITEA SERVER ---
    echo -e "${BLUE}[SERVER]${NC}"
    if systemctl is-active --quiet gitea; then
        GITEA_PID=$(pgrep -f "gitea web" | head -1)
        if [ -n "$GITEA_PID" ]; then
            CPU=$(ps -p $GITEA_PID -o %cpu --no-headers | tr -d ' ')
            MEM=$(ps -p $GITEA_PID -o %mem --no-headers | tr -d ' ')
            print_status "Gitea Server: Running (PID: $GITEA_PID, CPU: ${CPU}%, MEM: ${MEM}%)"

            # Warn if CPU is high
            if (( $(echo "$CPU > 30" | bc -l) )); then
                print_warning "CPU is high! Consider restart"
            fi
        fi
    else
        print_error "Gitea Server: Not running"
    fi

    # --- LINUX RUNNER ---
    echo ""
    echo -e "${BLUE}[LINUX RUNNER]${NC}"
    RUNNER_PID=$(pgrep -f "act_runner daemon" | head -1)
    if [ -n "$RUNNER_PID" ]; then
        CPU=$(ps -p $RUNNER_PID -o %cpu --no-headers | tr -d ' ')
        print_status "Linux Runner: Running (PID: $RUNNER_PID, CPU: ${CPU}%)"
    else
        print_warning "Linux Runner: Not running"
    fi

    # --- WINDOWS RUNNER ---
    echo ""
    echo -e "${BLUE}[WINDOWS RUNNER]${NC}"
    if can_manage_windows; then
        WIN_STATUS=$(powershell.exe -Command "Get-Service $WIN_RUNNER_SERVICE -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Status" 2>/dev/null | tr -d '\r')
        if [ "$WIN_STATUS" = "Running" ]; then
            WIN_PID=$(powershell.exe -Command "(Get-Process act_runner* -ErrorAction SilentlyContinue | Select-Object -First 1).Id" 2>/dev/null | tr -d '\r')
            print_status "Windows Runner: Running (Service: $WIN_RUNNER_SERVICE, PID: $WIN_PID)"
        elif [ "$WIN_STATUS" = "Stopped" ]; then
            print_warning "Windows Runner: Stopped (Service exists but not running)"
        else
            print_error "Windows Runner: Service not found or error"
        fi
    else
        echo "  (Cannot check - PowerShell not available from WSL)"
    fi

    # --- LATEST BUILD ---
    echo ""
    echo "=== Latest Build ==="
    python3 -c "
import sqlite3, time
c = sqlite3.connect('$GITEA_DB').cursor()
c.execute('SELECT id, status, started FROM action_run ORDER BY id DESC LIMIT 1')
r = c.fetchone()
if r:
    status = {1: 'SUCCESS', 2: 'FAILURE', 6: 'RUNNING'}.get(r[1], f'UNKNOWN({r[1]})')
    elapsed = (int(time.time()) - r[2]) // 60 if r[2] else 0
    print(f'Build {r[0]}: {status} ({elapsed}m ago)')

    # Check for running stages
    c.execute('SELECT name, status FROM action_run_job WHERE run_id=? AND status=6', (r[0],))
    running = c.fetchall()
    if running:
        print('Running stages:')
        for s in running:
            print(f'  - {s[0]}')
"
}

stop_graceful() {
    echo "=== Graceful Stop (All Components) ==="

    # --- WINDOWS RUNNER (stop first - depends on Gitea) ---
    echo ""
    echo -e "${BLUE}[WINDOWS RUNNER]${NC}"
    if can_manage_windows; then
        WIN_STATUS=$(powershell.exe -Command "(Get-Service $WIN_RUNNER_SERVICE -ErrorAction SilentlyContinue).Status" 2>/dev/null | tr -d '\r')
        if [ "$WIN_STATUS" = "Running" ]; then
            echo "Stopping Windows Runner service..."
            powershell.exe -Command "Stop-Service $WIN_RUNNER_SERVICE -Force" 2>/dev/null
            sleep 3
            print_status "Windows Runner stopped"
        else
            echo "Windows Runner was not running"
        fi
    else
        echo "  (Skipping - PowerShell not available)"
    fi

    # --- LINUX RUNNER ---
    echo ""
    echo -e "${BLUE}[LINUX RUNNER]${NC}"
    if pgrep -f "act_runner daemon" > /dev/null; then
        echo "Stopping Linux Runner (graceful)..."
        pkill -SIGTERM -f "act_runner daemon"
        sleep 3

        if pgrep -f "act_runner daemon" > /dev/null; then
            print_warning "Linux Runner still running, forcing..."
            pkill -9 -f "act_runner daemon"
        fi
        print_status "Linux Runner stopped"
    else
        echo "Linux Runner was not running"
    fi

    # --- GITEA SERVER (stop last) ---
    echo ""
    echo -e "${BLUE}[GITEA SERVER]${NC}"
    if systemctl is-active --quiet gitea; then
        echo "Stopping Gitea Server (systemctl stop)..."
        sudo systemctl stop gitea
        sleep 3

        if systemctl is-active --quiet gitea; then
            print_warning "Gitea still running, will try kill..."
            sudo systemctl kill gitea
        fi
        print_status "Gitea Server stopped"
    else
        echo "Gitea Server was not running"
    fi
}

stop_force() {
    echo "=== Force Kill (All Components) ==="
    print_warning "This will forcefully kill all CI/CD components!"

    # --- WINDOWS RUNNER ---
    echo ""
    echo -e "${BLUE}[WINDOWS RUNNER]${NC}"
    if can_manage_windows; then
        echo "Force stopping Windows Runner..."
        powershell.exe -Command "Stop-Service $WIN_RUNNER_SERVICE -Force -ErrorAction SilentlyContinue" 2>/dev/null
        powershell.exe -Command "Get-Process act_runner* -ErrorAction SilentlyContinue | Stop-Process -Force" 2>/dev/null
        print_status "Windows Runner killed"
    fi

    # --- LINUX RUNNER ---
    echo ""
    echo -e "${BLUE}[LINUX RUNNER]${NC}"
    if pgrep -f "act_runner" > /dev/null; then
        echo "Force killing Linux Runner..."
        pkill -9 -f "act_runner"
        print_status "Linux Runner killed"
    fi

    # --- GITEA SERVER ---
    echo ""
    echo -e "${BLUE}[GITEA SERVER]${NC}"
    if pgrep -f "gitea" > /dev/null; then
        echo "Force killing Gitea Server..."
        sudo systemctl kill gitea 2>/dev/null
        pkill -9 -f "gitea" 2>/dev/null
        print_status "Gitea Server killed"
    fi

    # --- DOCKER CLEANUP ---
    echo ""
    echo -e "${BLUE}[DOCKER CLEANUP]${NC}"
    if command -v docker &> /dev/null; then
        CONTAINERS=$(docker ps -q 2>/dev/null)
        if [ -n "$CONTAINERS" ]; then
            echo "Stopping Docker containers..."
            docker stop $CONTAINERS 2>/dev/null
            docker rm $CONTAINERS 2>/dev/null
            print_status "Docker containers cleaned"
        else
            echo "No Docker containers running"
        fi
    fi
}

start() {
    echo "=== Starting Services (All Components) ==="

    # --- GITEA SERVER (start first - others depend on it) ---
    echo ""
    echo -e "${BLUE}[GITEA SERVER]${NC}"
    if ! systemctl is-active --quiet gitea; then
        echo "Starting Gitea Server..."
        sudo systemctl start gitea
        sleep 3

        if systemctl is-active --quiet gitea; then
            print_status "Gitea Server started"
        else
            print_error "Failed to start Gitea Server"
            return 1
        fi
    else
        echo "Gitea Server already running"
    fi

    # --- LINUX RUNNER ---
    echo ""
    echo -e "${BLUE}[LINUX RUNNER]${NC}"
    if ! pgrep -f "act_runner daemon" > /dev/null; then
        echo "Starting Linux Runner..."
        cd "$GITEA_DIR"
        nohup ./act_runner daemon --config runner_config.yaml > /tmp/act_runner.log 2>&1 &
        sleep 2

        if pgrep -f "act_runner daemon" > /dev/null; then
            print_status "Linux Runner started"
        else
            print_error "Failed to start Linux Runner"
            return 1
        fi
    else
        echo "Linux Runner already running"
    fi

    # --- WINDOWS RUNNER ---
    echo ""
    echo -e "${BLUE}[WINDOWS RUNNER]${NC}"
    if can_manage_windows; then
        WIN_STATUS=$(powershell.exe -Command "(Get-Service $WIN_RUNNER_SERVICE -ErrorAction SilentlyContinue).Status" 2>/dev/null | tr -d '\r')
        if [ "$WIN_STATUS" != "Running" ]; then
            echo "Starting Windows Runner service..."
            powershell.exe -Command "Start-Service $WIN_RUNNER_SERVICE -ErrorAction SilentlyContinue" 2>/dev/null
            sleep 3

            WIN_STATUS=$(powershell.exe -Command "(Get-Service $WIN_RUNNER_SERVICE -ErrorAction SilentlyContinue).Status" 2>/dev/null | tr -d '\r')
            if [ "$WIN_STATUS" = "Running" ]; then
                print_status "Windows Runner started"
            else
                print_warning "Failed to start Windows Runner (may need admin rights)"
            fi
        else
            echo "Windows Runner already running"
        fi
    else
        echo "  (Skipping - PowerShell not available)"
    fi

    echo ""
    status
}

restart() {
    echo "=== Restart ==="
    stop_graceful
    sleep 2
    start
}

monitor() {
    echo "=== Live Monitor (Ctrl+C to exit) ==="
    while true; do
        clear
        echo "=== Gitea Monitor - $(date) ==="
        echo ""

        # Process stats
        GITEA_PID=$(pgrep -f "gitea web" | head -1)
        RUNNER_PID=$(pgrep -f "act_runner daemon" | head -1)

        if [ -n "$GITEA_PID" ]; then
            ps -p $GITEA_PID -o pid,%cpu,%mem,etime --no-headers | awk '{printf "Gitea:      PID %-8s CPU %5s%%  MEM %5s%%  Uptime %s\n", $1, $2, $3, $4}'
        else
            echo "Gitea:      NOT RUNNING"
        fi

        if [ -n "$RUNNER_PID" ]; then
            ps -p $RUNNER_PID -o pid,%cpu,%mem,etime --no-headers | awk '{printf "act_runner: PID %-8s CPU %5s%%  MEM %5s%%  Uptime %s\n", $1, $2, $3, $4}'
        else
            echo "act_runner: NOT RUNNING"
        fi

        echo ""

        # Latest build
        python3 -c "
import sqlite3, time
c = sqlite3.connect('$GITEA_DB').cursor()
c.execute('SELECT id, status, started FROM action_run ORDER BY id DESC LIMIT 1')
r = c.fetchone()
if r:
    status = {1: '✅ SUCCESS', 2: '❌ FAILURE', 6: '🔄 RUNNING'}.get(r[1], f'UNKNOWN({r[1]})')
    elapsed = (int(time.time()) - r[2]) // 60 if r[2] else 0
    print(f'Latest: Build {r[0]} {status} ({elapsed}m ago)')

    if r[1] == 6 and elapsed > 15:
        print('⚠️  BUILD TIMEOUT WARNING: >15 minutes!')
"

        sleep 10
    done
}

# Main
case "$1" in
    status)
        status
        ;;
    stop)
        stop_graceful
        ;;
    kill)
        stop_force
        ;;
    start)
        start
        ;;
    restart)
        restart
        ;;
    monitor)
        monitor
        ;;
    *)
        echo "Usage: $0 {status|stop|kill|start|restart|monitor}"
        echo ""
        echo "Manages: Gitea Server + Linux Runner + Windows Runner"
        echo ""
        echo "Commands:"
        echo "  status   - Show status of ALL components (Gitea + both runners)"
        echo "  stop     - Graceful stop (SIGTERM → wait → SIGKILL if needed)"
        echo "  kill     - Force kill everything (use when stuck)"
        echo "  start    - Start all components in correct order"
        echo "  restart  - Stop then start (fixes high CPU issues)"
        echo "  monitor  - Live monitoring (refreshes every 10s)"
        echo ""
        echo "Components managed:"
        echo "  [SERVER]  Gitea Server    - WSL systemd (gitea.service)"
        echo "  [LINUX]   Linux Runner    - WSL daemon (act_runner)"
        echo "  [WINDOWS] Windows Runner  - Windows Service (GiteaActRunner)"
        echo ""
        echo "⚠️  Read docs/wip/GITEA_CLEAN_KILL_PROTOCOL.md before using!"
        exit 1
        ;;
esac
