@echo off
REM ============================================
REM LocaNext - Korean BERT Model Download (Windows)
REM ============================================
REM
REM Downloads snunlp/KR-SBERT-V40K-klueNLI-augSTS from Hugging Face
REM Model size: ~447MB
REM Time: 5-10 minutes
REM
REM Based on VRS-Manager pattern
REM ============================================

echo.
echo ================================================================
echo LocaNext - Korean BERT Model Setup
echo ================================================================
echo.
echo This script will download the Korean BERT model (~447MB)
echo Required for AI-powered translation features
echo.
echo Estimated time: 5-10 minutes
echo Disk space needed: ~1GB (temporary + final)
echo.
pause

REM ============================================
REM 1. Check Python Installation
REM ============================================

echo.
echo [1/4] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: Python is not installed or not in PATH!
    echo.
    echo Please install Python 3.10 or later:
    echo   https://www.python.org/downloads/
    echo.
    echo IMPORTANT: During installation, check "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

python --version
echo Python found!

REM ============================================
REM 2. Check pip Installation
REM ============================================

echo.
echo [2/4] Checking pip installation...
pip --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: pip is not installed!
    echo.
    echo pip should come with Python. Try:
    echo   python -m ensurepip --upgrade
    echo.
    pause
    exit /b 1
)

pip --version
echo pip found!

REM ============================================
REM 3. Install sentence-transformers
REM ============================================

echo.
echo [3/4] Installing sentence-transformers library...
echo This may take a few minutes...
echo.

pip install sentence-transformers
if errorlevel 1 (
    echo.
    echo ERROR: Failed to install sentence-transformers!
    echo.
    echo Try manually:
    echo   pip install --upgrade sentence-transformers
    echo.
    pause
    exit /b 1
)

echo.
echo sentence-transformers installed successfully!

REM ============================================
REM 4. Download BERT Model
REM ============================================

echo.
echo [4/4] Downloading Korean BERT model...
echo.
echo Model: snunlp/KR-SBERT-V40K-klueNLI-augSTS
echo Size: ~447MB
echo.
echo This will take 5-10 minutes depending on your internet speed.
echo Please wait...
echo.

python -c "from sentence_transformers import SentenceTransformer; print('Downloading model...'); model = SentenceTransformer('snunlp/KR-SBERT-V40K-klueNLI-augSTS'); model.save('./models/kr-sbert'); print('\nModel download complete!')"

if errorlevel 1 (
    echo.
    echo ERROR: Model download failed!
    echo.
    echo Possible reasons:
    echo   1. No internet connection
    echo   2. Hugging Face Hub is down
    echo   3. Insufficient disk space
    echo.
    echo Please check your connection and try again.
    echo.
    pause
    exit /b 1
)

REM ============================================
REM Verify Download
REM ============================================

echo.
echo ================================================================
echo Verifying download...
echo ================================================================
echo.

if not exist "models\kr-sbert\config.json" (
    echo ERROR: config.json not found!
    echo Download may have failed. Please try again.
    pause
    exit /b 1
)

if not exist "models\kr-sbert\model.safetensors" (
    echo ERROR: model.safetensors not found!
    echo Download may have failed. Please try again.
    pause
    exit /b 1
)

echo Model files verified:
dir /b models\kr-sbert
echo.

REM ============================================
REM Success
REM ============================================

echo.
echo ================================================================
echo SUCCESS! Model download complete!
echo ================================================================
echo.
echo Location: models\kr-sbert\
echo Size: ~447MB
echo.
echo The model is now ready for:
echo   - Running LocaNext locally
echo   - Building FULL version executable (includes model)
echo   - Offline use (transfer models\ folder to other PCs)
echo.
echo For offline transfer:
echo   1. Copy the entire "models" folder
echo   2. Place it next to LocaNext.exe on the offline computer
echo   3. Model will load from local directory automatically
echo.
echo Next steps:
echo   - Run application: python server\main.py
echo   - Build executable: See docs\BUILD.md
echo.
pause
