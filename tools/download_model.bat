@echo off
REM ============================================
REM LocaNext - Korean BERT Model Downloader
REM ============================================
REM
REM Downloads AI model from Hugging Face
REM Uses embedded Python (no install required)
REM
REM IT-Friendly: You can inspect this .bat and
REM the download_model.py script to see exactly
REM what it does. Safe, transparent, trusted.
REM ============================================

echo.
echo ============================================
echo   LocaNext - AI Model Download
echo ============================================
echo.
echo   Model: Korean BERT (snunlp/KR-SBERT)
echo   Size:  ~447 MB
echo   Time:  5-10 minutes
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
    pause
    exit /b 1
)

echo.
echo ============================================
echo   Download complete!
echo ============================================
echo.
pause
