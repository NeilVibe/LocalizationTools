@echo off
REM ============================================================================
REM QA Compiler Suite - Build Executable
REM ============================================================================
REM This script creates a standalone Windows executable.
REM Requirements: Python 3.8+ with pip
REM
REM FEATURE: Drive Selection
REM   The default LOC path uses F: drive. If your Perforce is on a different
REM   drive (D:, E:, etc.), this script will automatically update all paths
REM   before building.
REM ============================================================================

echo.
echo ========================================
echo   QA Compiler Suite - Build Executable
echo ========================================
echo.

REM ============================================================================
REM STEP 0: DRIVE SELECTION
REM ============================================================================
echo Current default LOC path uses F: drive
echo (F:\perforce\cd\mainline\resource\GameData\stringtable\loc)
echo.
echo If your Perforce is on a different drive, enter the drive letter.
echo Otherwise, just press Enter to keep F: drive.
echo.
set /p DRIVE_LETTER="Enter drive letter (F/D/E/etc.) [F]: "

REM Default to F if empty
if "%DRIVE_LETTER%"=="" set DRIVE_LETTER=F

REM Convert to uppercase
for %%i in (A B C D E F G H I J K L M N O P Q R S T U V W X Y Z) do (
    if /i "%DRIVE_LETTER%"=="%%i" set DRIVE_LETTER=%%i
)

echo.
echo Selected drive: %DRIVE_LETTER%:
echo.

REM ============================================================================
REM STEP 0.5: UPDATE PATHS IF NOT F DRIVE
REM ============================================================================
if /i not "%DRIVE_LETTER%"=="F" (
    echo [0/4] Updating paths from F: to %DRIVE_LETTER%: ...

    REM Backup original files
    copy /Y "config.py" "config.py.bak" >nul 2>&1
    copy /Y "system_localizer.py" "system_localizer.py.bak" >nul 2>&1

    REM Update config.py - replace F:\ with selected drive
    powershell -Command "(Get-Content 'config.py') -replace 'F:\\', '%DRIVE_LETTER%:\' | Set-Content 'config.py'"

    REM Update system_localizer.py - replace F:\ with selected drive
    powershell -Command "(Get-Content 'system_localizer.py') -replace 'F:\\', '%DRIVE_LETTER%:\' | Set-Content 'system_localizer.py'"

    echo      Paths updated to use %DRIVE_LETTER%: drive
    echo.
)

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
    REM Restore backups if build failed
    if exist "config.py.bak" (
        copy /Y "config.py.bak" "config.py" >nul 2>&1
        del "config.py.bak" >nul 2>&1
    )
    if exist "system_localizer.py.bak" (
        copy /Y "system_localizer.py.bak" "system_localizer.py" >nul 2>&1
        del "system_localizer.py.bak" >nul 2>&1
    )
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

REM ============================================================================
REM CLEANUP: Restore original files (keep source unchanged)
REM ============================================================================
if exist "config.py.bak" (
    copy /Y "config.py.bak" "config.py" >nul 2>&1
    del "config.py.bak" >nul 2>&1
)
if exist "system_localizer.py.bak" (
    copy /Y "system_localizer.py.bak" "system_localizer.py" >nul 2>&1
    del "system_localizer.py.bak" >nul 2>&1
)

echo.
echo ========================================
echo   BUILD COMPLETE!
echo ========================================
echo.
echo Drive used: %DRIVE_LETTER%:
echo LOC path:   %DRIVE_LETTER%:\perforce\cd\mainline\resource\GameData\stringtable\loc
echo.
echo Executable location: dist\QACompiler\QACompiler.exe
echo.
echo To distribute:
echo   1. Copy the entire "dist\QACompiler" folder
echo   2. Users double-click QACompiler.exe to run
echo.
pause
