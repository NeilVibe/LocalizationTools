@echo off
REM ============================================
REM LocaNext - Qwen Embedding Model Downloader
REM ============================================
REM
REM Downloads Embedding model from Hugging Face
REM Uses embedded Python (no install required)
REM
REM IT-Friendly: You can inspect this .bat and
REM the download_model.py script to see exactly
REM what it does. Safe, transparent, trusted.
REM
REM P20 Migration: Switched from KR-SBERT to Qwen
REM ============================================

echo.
echo ============================================
echo   LocaNext - Embedding Model Download
echo ============================================
echo.
echo   Model: Qwen/Qwen3-Embedding-0.6B
echo   Size:  ~1.21 GB
echo   Time:  5-15 minutes
echo.
echo   Using embedded Python (no install needed)
echo ============================================
echo.

REM Run Python script using embedded Python
"%~dp0python\python.exe" "%~dp0download_model.py"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Download failed. Check your internet connection.
    echo.
    exit /b 1
)

echo.
echo ============================================
echo   Download complete!
echo ============================================
echo.
