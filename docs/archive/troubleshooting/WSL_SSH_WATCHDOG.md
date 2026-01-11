# WSL SSH Watchdog

**Purpose:** Auto-restart WSL if SSH server dies, enabling reliable remote access.

---

## How It Works

```
Every 5 minutes:
  1. Check if port 22 responds
  2. If yes → do nothing
  3. If no → check if WSL running
  4. If WSL not running → restart it
  5. Safety: Max 3 restarts/hour (prevents death loops)
```

---

## Install

### Step 1: Copy Script to Windows

The script is at: `scripts/wsl_ssh_watchdog.ps1`

From WSL:
```bash
cp /home/neil1988/LocalizationTools/scripts/wsl_ssh_watchdog.ps1 /mnt/c/Scripts/
```

Or from Windows, copy from: `D:\LocalizationTools\scripts\wsl_ssh_watchdog.ps1`

### Step 2: Create Scheduled Task

**Option A: PowerShell (run as Admin)**
```powershell
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -WindowStyle Hidden -File C:\Scripts\wsl_ssh_watchdog.ps1"
$trigger1 = New-ScheduledTaskTrigger -AtStartup
$trigger2 = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 5)
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName "WSL SSH Watchdog" -Action $action -Trigger $trigger1,$trigger2 -Settings $settings -RunLevel Highest -User "SYSTEM"
```

**Option B: Task Scheduler GUI**
1. Open Task Scheduler
2. Create Basic Task → Name: "WSL SSH Watchdog"
3. Trigger: At startup
4. Action: Start a program
   - Program: `powershell.exe`
   - Arguments: `-ExecutionPolicy Bypass -WindowStyle Hidden -File C:\Scripts\wsl_ssh_watchdog.ps1`
5. Finish, then edit task:
   - Add second trigger: Repeat every 5 minutes
   - Run whether user logged in or not
   - Run with highest privileges

---

## Safety Features

| Feature | Value | Purpose |
|---------|-------|---------|
| Max restarts/hour | 3 | Prevents infinite restart loops |
| Cooldown | Automatic | After 3 restarts, waits for hour to pass |
| State file | `%LOCALAPPDATA%\wsl_ssh_watchdog_state.json` | Tracks restart history |
| Log file | `%LOCALAPPDATA%\wsl_ssh_watchdog.log` | Debugging |

---

## Logs

Check logs at:
```
%LOCALAPPDATA%\wsl_ssh_watchdog.log
```

Example:
```
2025-12-19 14:30:00 | Watchdog check started
2025-12-19 14:30:00 | SSH alive on port 22 - OK
```

---

## Reset After Death Loop

If watchdog hit max restarts and stopped:

```powershell
# Clear state file
Remove-Item "$env:LOCALAPPDATA\wsl_ssh_watchdog_state.json"

# Manually start WSL
wsl

# Verify SSH
Test-NetConnection -ComputerName 127.0.0.1 -Port 22
```

---

## Troubleshooting

### Watchdog not running
```powershell
# Check task status
Get-ScheduledTask -TaskName "WSL SSH Watchdog" | Select State, LastRunTime, LastTaskResult
```

### SSH still not starting
- Check if SSH server is enabled in WSL: `sudo systemctl status ssh`
- Check if SSH starts on boot: `sudo systemctl enable ssh`

### Manual test
```powershell
# Run watchdog manually
powershell -ExecutionPolicy Bypass -File C:\Scripts\wsl_ssh_watchdog.ps1
```

---

## Uninstall

```powershell
Unregister-ScheduledTask -TaskName "WSL SSH Watchdog" -Confirm:$false
Remove-Item "$env:LOCALAPPDATA\wsl_ssh_watchdog*"
```

---

*Created: 2025-12-19 | For reliable remote WSL access*
