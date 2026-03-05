@echo off
chcp 65001 >nul 2>&1
title 危険物法令ナレッジAI

REM -------------------------------------------------------
REM  Python の存在確認
REM -------------------------------------------------------
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo  [!] Python が見つかりません。
    echo      先に「①初期設定」を実行してください。
    pause
    exit /b 1
)

REM -------------------------------------------------------
REM  データベースの確認
REM -------------------------------------------------------
if not exist "%~dp0database\kikenbutsu.db" (
    echo  [!] データベースがまだ作成されていません。
    echo      先に「②データ取込」を実行してください。
    pause
    exit /b 1
)

REM -------------------------------------------------------
REM  アプリ起動
REM -------------------------------------------------------
cd /d "%~dp0"
python -m streamlit run src/app_streamlit.py --server.headless false --browser.gatherUsageStats false
