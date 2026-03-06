@echo off
chcp 65001
title Kikenbutsu Knowledge Graph AI - Initial Setup

echo.
echo  ============================================
echo    Kikenbutsu Knowledge Graph AI - Setup
echo  ============================================
echo.

REM -------------------------------------------------------
REM  Create required folders first (always)
REM -------------------------------------------------------
echo  Preparing folders...
if not exist "%~dp0input_pdf"          mkdir "%~dp0input_pdf"
if not exist "%~dp0database"           mkdir "%~dp0database"
if not exist "%~dp0logs"               mkdir "%~dp0logs"
if not exist "%~dp0ocr_text"           mkdir "%~dp0ocr_text"
if not exist "%~dp0notebooklm_export"  mkdir "%~dp0notebooklm_export"
echo  [OK] Folder setup completed.
echo.

REM -------------------------------------------------------
REM  Check Python availability
REM -------------------------------------------------------
python --version
if %errorlevel% neq 0 (
    echo  [!] Python was not found.
    echo.
    echo      Install Python first.
    echo      See README.md for details.
    echo.
    pause
    exit /b 1
)

echo  [OK] Python is available.
echo.

REM -------------------------------------------------------
REM  Install required libraries only when missing
REM -------------------------------------------------------
echo  Checking required libraries...
echo.
python -c "import importlib.util,sys; sys.exit(0 if importlib.util.find_spec('streamlit') and importlib.util.find_spec('networkx') else 1)"
if %errorlevel% equ 0 (
    echo  [OK] Required libraries are already installed.
    echo       Skipping install.
) else (
    echo  Installing required libraries...
    echo  Internet connection is required. This may take a few minutes.
    echo.
    python -m pip install --upgrade pip
    if %errorlevel% neq 0 (
        echo  [WARN] pip upgrade failed. Continuing with current pip.
        echo         If install fails later, run:
        echo           python -m pip install --upgrade pip
        echo.
    )

    python -m pip --version
    if %errorlevel% neq 0 (
        echo  pip is not available. Trying to enable pip (ensurepip)...
        python -m ensurepip --upgrade
        if %errorlevel% neq 0 (
            echo.
            echo  [!] pip is not available and could not be enabled.
            echo      Reinstall Python with pip included.
            echo.
            pause
            exit /b 1
        )
    )

    python -m pip install -r "%~dp0requirements.txt"
    if %errorlevel% neq 0 (
        echo  Standard install failed. Retrying with --user...
        python -m pip install --user -r "%~dp0requirements.txt"
    )
    if %errorlevel% neq 0 (
        echo.
        echo  [!] Error occurred during package installation.
        echo      Check internet connection and Python permissions.
        echo.
        pause
        exit /b 1
    )
    echo.
    echo  [OK] Library installation completed.
)
echo.
echo  ============================================
echo    Initial setup completed
echo  ============================================
echo.
echo  Next steps:
echo    1. Put PDF files into the "input_pdf" folder.
echo    2. Then run the Step-2 Data Import launcher.
echo.

explorer "%~dp0input_pdf"

pause
