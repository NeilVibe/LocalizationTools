@echo off
REM ============================================
REM LocaNext - Korean BERT Model Download (SILENT)
REM ============================================
REM
REM Silent version for Inno Setup wizard post-install
REM No pauses, no user interaction required
REM
REM Downloads snunlp/KR-SBERT-V40K-klueNLI-augSTS from Hugging Face
REM Model size: ~447MB
REM ============================================

REM Set working directory to script location
cd /d "%~dp0.."

REM Log file for debugging
set LOGFILE=%~dp0..\logs\model_download.log
if not exist "%~dp0..\logs" mkdir "%~dp0..\logs"

echo [%date% %time%] Starting model download... > "%LOGFILE%"

REM ============================================
REM Check if model already exists
REM ============================================
if exist "models\kr-sbert\model.safetensors" (
    echo [%date% %time%] Model already exists, skipping download >> "%LOGFILE%"
    exit /b 0
)

REM ============================================
REM Check Python Installation
REM ============================================
python --version >nul 2>&1
if errorlevel 1 (
    echo [%date% %time%] ERROR: Python not found >> "%LOGFILE%"
    exit /b 1
)

echo [%date% %time%] Python found >> "%LOGFILE%"

REM ============================================
REM Install sentence-transformers (quiet mode)
REM ============================================
echo [%date% %time%] Installing sentence-transformers... >> "%LOGFILE%"
pip install -q sentence-transformers >> "%LOGFILE%" 2>&1
if errorlevel 1 (
    echo [%date% %time%] ERROR: Failed to install sentence-transformers >> "%LOGFILE%"
    exit /b 1
)

echo [%date% %time%] sentence-transformers installed >> "%LOGFILE%"

REM ============================================
REM Download BERT Model
REM ============================================
echo [%date% %time%] Downloading Korean BERT model (447MB)... >> "%LOGFILE%"

python -c "from sentence_transformers import SentenceTransformer; model = SentenceTransformer('snunlp/KR-SBERT-V40K-klueNLI-augSTS'); model.save('./models/kr-sbert')" >> "%LOGFILE%" 2>&1

if errorlevel 1 (
    echo [%date% %time%] ERROR: Model download failed >> "%LOGFILE%"
    exit /b 1
)

REM ============================================
REM Verify Download
REM ============================================
if not exist "models\kr-sbert\config.json" (
    echo [%date% %time%] ERROR: config.json not found >> "%LOGFILE%"
    exit /b 1
)

if not exist "models\kr-sbert\model.safetensors" (
    echo [%date% %time%] ERROR: model.safetensors not found >> "%LOGFILE%"
    exit /b 1
)

echo [%date% %time%] SUCCESS: Model download complete >> "%LOGFILE%"
exit /b 0
