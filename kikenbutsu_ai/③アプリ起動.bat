@echo off
chcp 65001 >nul 2>&1
title 危険物法令ナレッジAI - 起動中...

echo ============================================
echo   危険物法令ナレッジグラフAI  起動中
echo ============================================
echo.

REM --- Python の存在確認 ---
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [エラー] Python が見つかりません。
    echo 先に「①初期設定」を実行してください。
    pause
    exit /b 1
)

REM --- データベース確認 ---
if not exist "%~dp0database\kikenbutsu.db" (
    echo [注意] データベースがまだ作成されていません。
    echo 先に「②データ取込」を実行してください。
    pause
    exit /b 1
)

echo ブラウザでアプリを開きます...
echo.
echo ┌─────────────────────────────────────────┐
echo │  アプリが起動したら、ブラウザに          │
echo │  自動で画面が表示されます。              │
echo │                                          │
echo │  終了するには、この画面を閉じてください。│
echo └─────────────────────────────────────────┘
echo.

cd /d "%~dp0"
python -m streamlit run src/app_streamlit.py --server.headless false --browser.gatherUsageStats false
