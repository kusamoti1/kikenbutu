@echo off
chcp 65001
title Kikenbutsu Knowledge Graph AI

REM -------------------------------------------------------
REM  Check Python availability
REM -------------------------------------------------------
python --version
if %errorlevel% neq 0 (
    echo  [!] Python was not found.
    echo      Run the initial setup step first.
    pause
    exit /b 1
)

REM -------------------------------------------------------
REM  Check database file
REM -------------------------------------------------------
if not exist "%~dp0database\kikenbutsu.db" (
    echo  [!] Database has not been created yet.
    echo      Run the data import step first.
    pause
    exit /b 1
)

REM -------------------------------------------------------
REM  Launch app
REM -------------------------------------------------------
cd /d "%~dp0"
python -m streamlit run src/app_streamlit.py --server.headless false --browser.gatherUsageStats false
