@echo off
chcp 65001
title Kikenbutsu Knowledge Graph AI - Data Import

echo.
echo  ============================================
echo    Kikenbutsu Knowledge Graph AI - Data Import
echo  ============================================
echo.

REM Ensure output folders exist
if not exist "%~dp0database"           mkdir "%~dp0database"
if not exist "%~dp0logs"               mkdir "%~dp0logs"
if not exist "%~dp0notebooklm_export"  mkdir "%~dp0notebooklm_export"

REM -------------------------------------------------------
REM  Check Python availability
REM -------------------------------------------------------
python --version
if %errorlevel% neq 0 (
    echo  [!] Python was not found.
    echo      Run the initial setup step first.
    echo.
    pause
    exit /b 1
)

REM -------------------------------------------------------
REM  Ensure input folder exists and contains PDF files
REM -------------------------------------------------------
if not exist "%~dp0input_pdf" mkdir "%~dp0input_pdf"

set "PDF_FOUND="
for %%F in ("%~dp0input_pdf\*.pdf") do (
    if exist "%%~fF" set "PDF_FOUND=1"
)

if not defined PDF_FOUND (
    echo  [!] No PDF files found in "input_pdf".
    echo.
    echo      The folder will be opened now.
    echo      Copy PDF files there, then run this file again.
    echo.
    explorer "%~dp0input_pdf"
    pause
    exit /b 0
)

echo  PDF files detected.
echo  Starting data import now.
echo.
echo  This may take several minutes depending on file count.
echo.

cd /d "%~dp0"
python run_pipeline.py

if %errorlevel% neq 0 (
    echo.
    echo  [!] Error occurred during data import.
    echo      Check logs\pipeline.log for details.
    echo.
    pause
    exit /b 1
)

echo.
echo  ============================================
echo    Data import completed
echo  ============================================
echo.
echo  Output files:
echo    - Database: database\kikenbutsu.db
echo    - Graph:    database\knowledge_graph.graphml
echo    - NotebookLM markdown: notebooklm_export\*.md
echo.
echo  Opening NotebookLM export folder...
explorer "%~dp0notebooklm_export"
echo.
echo  Next step:
echo    Run the Step-3 App Launch launcher.
echo.
pause
