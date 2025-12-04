@echo off
REM ============================================
REM LocaNext - Python Dependencies Installer
REM ============================================
REM
REM Installs required Python packages for backend
REM Uses embedded Python (no install required)
REM
REM IT-Friendly: You can inspect this .bat and
REM the install_deps.py script to see exactly
REM what it installs. Safe, transparent, trusted.
REM ============================================

echo.
echo ============================================
echo   LocaNext - Installing Dependencies
echo ============================================
echo.
echo   This will install:
echo   - FastAPI (web server)
echo   - torch (AI framework ~2GB)
echo   - transformers (NLP models)
echo   - sentence-transformers
echo   - Other required packages
echo.
echo   Total download: ~2GB
echo   Time: 15-20 minutes
echo.
echo   Using embedded Python (no install needed)
echo ============================================
echo.

REM Run Python script using embedded Python
"%~dp0python\python.exe" "%~dp0install_deps.py"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Installation failed. Check your internet connection.
    echo.
    exit /b 1
)

echo.
echo ============================================
echo   Dependencies installed successfully!
echo ============================================
echo.
