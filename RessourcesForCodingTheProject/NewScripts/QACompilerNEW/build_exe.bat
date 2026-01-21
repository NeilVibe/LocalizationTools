@echo off
REM ============================================================================
REM QA Compiler Suite - Build Executable
REM ============================================================================
REM This script creates a standalone Windows executable.
REM Requirements: Python 3.8+ with pip
REM
REM FEATURE: Drive Selection
REM   The default LOC path uses F: drive. If your Perforce is on a different
REM   drive (D:, E:, etc.), this script will create a settings.json file
REM   that configures the app to use your drive at runtime.
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

echo [4/4] Setting up dist folder...
REM Create empty folders that the app expects
if not exist "dist\QACompiler\QAfolder" mkdir "dist\QACompiler\QAfolder"
if not exist "dist\QACompiler\QAfolderOLD" mkdir "dist\QACompiler\QAfolderOLD"
if not exist "dist\QACompiler\QAfolderNEW" mkdir "dist\QACompiler\QAfolderNEW"
if not exist "dist\QACompiler\GeneratedDatasheets" mkdir "dist\QACompiler\GeneratedDatasheets"
if not exist "dist\QACompiler\Masterfolder_EN" mkdir "dist\QACompiler\Masterfolder_EN"
if not exist "dist\QACompiler\Masterfolder_EN\Images" mkdir "dist\QACompiler\Masterfolder_EN\Images"
if not exist "dist\QACompiler\Masterfolder_CN" mkdir "dist\QACompiler\Masterfolder_CN"
if not exist "dist\QACompiler\Masterfolder_CN\Images" mkdir "dist\QACompiler\Masterfolder_CN\Images"

REM Copy tester list
copy /Y "languageTOtester_list.txt" "dist\QACompiler\" >nul 2>&1
copy /Y "languageTOtester_list.example.txt" "dist\QACompiler\" >nul 2>&1

REM ============================================================================
REM CREATE SETTINGS.JSON (if not default F: drive)
REM ============================================================================
REM The app reads drive letter from settings.json at runtime.
REM This allows one exe to work with any drive - just change settings.json!
if /i not "%DRIVE_LETTER%"=="F" (
    echo.
    echo Creating settings.json with drive letter %DRIVE_LETTER%:
    python drive_replacer.py %DRIVE_LETTER% "dist\QACompiler\settings.json"
    if errorlevel 1 (
        echo WARNING: Failed to create settings.json
        echo          The app will default to F: drive.
    )
)

echo.
echo ========================================
echo   BUILD COMPLETE!
echo ========================================
echo.
echo Drive configured: %DRIVE_LETTER%:
echo LOC path:         %DRIVE_LETTER%:\perforce\cd\mainline\resource\GameData\stringtable\loc
echo.
echo Executable location: dist\QACompiler\QACompiler.exe
echo.
if /i not "%DRIVE_LETTER%"=="F" (
    echo NOTE: settings.json was created with drive %DRIVE_LETTER%:
    echo       To change the drive later, edit dist\QACompiler\settings.json
    echo.
)
echo To distribute:
echo   1. Copy the entire "dist\QACompiler" folder
echo   2. Users double-click QACompiler.exe to run
echo.
echo TIP: To change the drive on any installation:
echo      Edit settings.json in the app folder.
echo.
pause
