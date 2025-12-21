# Windows Runner Installation Script
# Installs patched act_runner as a Windows Service using NSSM
#
# Requirements:
# - Run as Administrator
# - Chocolatey installed (for NSSM)
# - act_runner_patched_v15.exe built and available
# - Runner already registered with Gitea

param(
    [string]$RunnerDir = "C:\NEIL_PROJECTS_WINDOWSBUILD\GiteaRunner",
    [string]$RunnerExe = "act_runner_patched_v15.exe",
    [string]$ServiceName = "GiteaActRunner"
)

Write-Host "=============================================="
Write-Host "  Windows Runner Installation (NSSM Service)"
Write-Host "=============================================="
Write-Host ""

# Check admin rights
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "ERROR: This script must be run as Administrator" -ForegroundColor Red
    exit 1
}

# Check runner exists
$runnerPath = Join-Path $RunnerDir $RunnerExe
if (-not (Test-Path $runnerPath)) {
    Write-Host "ERROR: Runner not found at $runnerPath" -ForegroundColor Red
    Write-Host "Build the patched runner first using build_patched_runner.sh"
    exit 1
}

# Install NSSM if needed
$nssm = "C:\ProgramData\chocolatey\lib\NSSM\tools\nssm.exe"
if (-not (Test-Path $nssm)) {
    Write-Host "[1/4] Installing NSSM via Chocolatey..."
    choco install nssm -y
}
else {
    Write-Host "[1/4] NSSM already installed"
}

# Stop and remove existing service
Write-Host "[2/4] Removing existing service if present..."
sc.exe stop $ServiceName 2>$null
sc.exe delete $ServiceName 2>$null
Start-Sleep -Seconds 2

# Create service
Write-Host "[3/4] Creating new service..."
& $nssm install $ServiceName "$runnerPath" "-c config.yaml daemon"
& $nssm set $ServiceName AppDirectory $RunnerDir
& $nssm set $ServiceName Start SERVICE_AUTO_START
& $nssm set $ServiceName DisplayName "Gitea Actions Runner (Patched v15)"
& $nssm set $ServiceName Description "Patched act_runner with NUL byte fix for Windows PowerShell compatibility"

# Start service
Write-Host "[4/4] Starting service..."
& $nssm start $ServiceName

Write-Host ""
Write-Host "=============================================="
Write-Host "  INSTALLATION COMPLETE!"
Write-Host "=============================================="
Write-Host ""
Write-Host "Service Status:" -ForegroundColor Green
Get-Service $ServiceName | Format-List Name, Status, StartType

Write-Host ""
Write-Host "Verify runner is working:"
Write-Host "  1. Check Gitea -> Settings -> Actions -> Runners"
Write-Host "  2. Runner should show as 'Idle' or 'Running'"
Write-Host ""
Write-Host "Management commands:"
Write-Host "  Stop:    Stop-Service $ServiceName"
Write-Host "  Start:   Start-Service $ServiceName"
Write-Host "  Restart: Restart-Service $ServiceName"
Write-Host "  Remove:  & `$nssm remove $ServiceName confirm"
Write-Host ""
