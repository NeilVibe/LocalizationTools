# PowerShell wrapper to run QA comprehensive test
# This script sets the environment variables and runs the Node.js test

Write-Host "=== LocaNext QA Comprehensive Test ===" -ForegroundColor Cyan
Write-Host ""

# Set credentials from .env.local
$envFile = "\\wsl.localhost\Ubuntu2\home\neil1988\LocalizationTools\.env.local"
if (Test-Path $envFile) {
    Write-Host "Loading credentials from .env.local..." -ForegroundColor Yellow
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^CDP_TEST_USER=(.+)$') {
            $env:CDP_TEST_USER = $matches[1]
            Write-Host "CDP_TEST_USER set to: $($matches[1])" -ForegroundColor Green
        }
        if ($_ -match '^CDP_TEST_PASS=(.+)$') {
            $env:CDP_TEST_PASS = $matches[1]
            Write-Host "CDP_TEST_PASS set" -ForegroundColor Green
        }
    }
} else {
    Write-Host "WARNING: .env.local not found, using defaults" -ForegroundColor Yellow
    $env:CDP_TEST_USER = "neil"
    $env:CDP_TEST_PASS = "neil"
}

Write-Host ""
Write-Host "Running test..." -ForegroundColor Cyan
Write-Host ""

# Run the test
Push-Location '\\wsl.localhost\Ubuntu2\home\neil1988\LocalizationTools\testing_toolkit\cdp'
node test_qa_comprehensive.js
Pop-Location

Write-Host ""
Write-Host "Test complete!" -ForegroundColor Cyan
