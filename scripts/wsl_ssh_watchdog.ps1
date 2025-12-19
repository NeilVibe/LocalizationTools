# ============================================================================
# WSL SSH Watchdog - Auto-restart WSL if SSH dies
# ============================================================================
# Purpose: Keep WSL SSH server alive for remote access
# Safety: Max 3 restarts per hour to prevent death loops
#
# INSTALL AS SCHEDULED TASK:
#   1. Open Task Scheduler
#   2. Create Basic Task: "WSL SSH Watchdog"
#   3. Trigger: At startup + Repeat every 5 minutes
#   4. Action: Start Program
#      - Program: powershell.exe
#      - Arguments: -ExecutionPolicy Bypass -File "D:\LocalizationTools\scripts\wsl_ssh_watchdog.ps1"
#   5. Run whether user is logged on or not
# ============================================================================

$LogFile = "$env:LOCALAPPDATA\wsl_ssh_watchdog.log"
$StateFile = "$env:LOCALAPPDATA\wsl_ssh_watchdog_state.json"
$SSHPort = 22
$MaxRestartsPerHour = 3
$CooldownMinutes = 20

function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp | $Message" | Out-File -Append -FilePath $LogFile
    Write-Host "$timestamp | $Message"
}

function Get-State {
    if (Test-Path $StateFile) {
        return Get-Content $StateFile | ConvertFrom-Json
    }
    return @{
        restarts = @()
    }
}

function Save-State {
    param($State)
    $State | ConvertTo-Json | Set-Content $StateFile
}

function Test-SSHAlive {
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $tcp.Connect("127.0.0.1", $SSHPort)
        $tcp.Close()
        return $true
    } catch {
        return $false
    }
}

function Get-RestartsLastHour {
    param($State)
    $oneHourAgo = (Get-Date).AddHours(-1)
    $recent = $State.restarts | Where-Object {
        [DateTime]::Parse($_) -gt $oneHourAgo
    }
    return @($recent).Count
}

# Main logic
Write-Log "Watchdog check started"

# Check if SSH is alive
if (Test-SSHAlive) {
    Write-Log "SSH alive on port $SSHPort - OK"
    exit 0
}

Write-Log "SSH not responding on port $SSHPort"

# Load state and check restart count
$state = Get-State
$restartsLastHour = Get-RestartsLastHour -State $state

if ($restartsLastHour -ge $MaxRestartsPerHour) {
    Write-Log "ERROR: Max restarts ($MaxRestartsPerHour) reached in last hour. NOT restarting to prevent death loop."
    Write-Log "Manual intervention required. Clear state file to reset: $StateFile"
    exit 1
}

Write-Log "Restarts in last hour: $restartsLastHour / $MaxRestartsPerHour"

# Check if WSL is running at all
$wslRunning = (wsl --list --running 2>$null) -match "Ubuntu|Debian|kali"

if ($wslRunning) {
    Write-Log "WSL is running but SSH not responding. May need manual check."
    # Don't restart if WSL is running - SSH might just be slow or misconfigured
    exit 0
}

# WSL not running - restart it
Write-Log "WSL not running. Starting WSL..."

# Record this restart
$state.restarts += (Get-Date).ToString("o")
# Keep only last 10 entries
$state.restarts = $state.restarts | Select-Object -Last 10
Save-State -State $state

# Start WSL (this launches the default distro and runs the init system)
wsl --exec /bin/bash -c "echo WSL started at $(date)"

# Wait for SSH to come up
Start-Sleep -Seconds 10

if (Test-SSHAlive) {
    Write-Log "SUCCESS: WSL restarted, SSH alive"
} else {
    Write-Log "WARNING: WSL started but SSH still not responding after 10s"
}

Write-Log "Watchdog check complete"
