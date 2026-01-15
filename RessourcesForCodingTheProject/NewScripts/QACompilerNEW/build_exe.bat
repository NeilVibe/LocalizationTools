@echo off
REM ============================================================================
REM QA Compiler Suite - Build Executable
REM ============================================================================
REM This script creates a standalone Windows executable.
REM Requirements: Python 3.8+ with pip
REM ============================================================================

echo.
echo ========================================
echo   QA Compiler Suite - Build Executable
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.8+
    pause
    exit /b 1
)

echo [1/4] Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo [2/4] Installing PyInstaller...
pip install pyinstaller
if errorlevel 1 (
    echo ERROR: Failed to install PyInstaller
    pause
    exit /b 1
)

echo [3/4] Building executable...
pyinstaller QACompiler.spec --clean
if errorlevel 1 (
    echo ERROR: Build failed
    pause
    exit /b 1
)

echo [4/4] Copying required folders to dist...
REM Create empty folders that the app expects
if not exist "dist\QACompiler\QAfolder" mkdir "dist\QACompiler\QAfolder"
if not exist "dist\QACompiler\QAfolderOLD" mkdir "dist\QACompiler\QAfolderOLD"
if not exist "dist\QACompiler\QAfolderNEW" mkdir "dist\QACompiler\QAfolderNEW"
if not exist "dist\QACompiler\GeneratedDatasheets" mkdir "dist\QACompiler\GeneratedDatasheets"
if not exist "dist\QACompiler\Masterfolder_EN" mkdir "dist\QACompiler\Masterfolder_EN"
if not exist "dist\QACompiler\Masterfolder_EN\Images" mkdir "dist\QACompiler\Masterfolder_EN\Images"
if not exist "dist\QACompiler\Masterfolder_CN" mkdir "dist\QACompiler\Masterfolder_CN"
if not exist "dist\QACompiler\Masterfolder_CN\Images" mkdir "dist\QACompiler\Masterfolder_CN\Images"

REM Copy config and tester list
copy /Y "languageTOtester_list.txt" "dist\QACompiler\" >nul 2>&1
copy /Y "languageTOtester_list.example.txt" "dist\QACompiler\" >nul 2>&1

echo.
echo ========================================
echo   BUILD COMPLETE!
echo ========================================
echo.
echo Executable location: dist\QACompiler\QACompiler.exe
echo.
echo To distribute:
echo   1. Copy the entire "dist\QACompiler" folder
echo   2. Users double-click QACompiler.exe to run
echo.
pause
