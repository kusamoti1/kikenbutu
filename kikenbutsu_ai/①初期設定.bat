@echo off
chcp 65001 >nul 2>&1
title 危険物法令ナレッジAI - 初期設定

echo ============================================
echo   危険物法令ナレッジグラフAI  初期設定
echo ============================================
echo.

REM --- Python の存在確認 ---
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [エラー] Python が見つかりません。
    echo.
    echo Python のインストールが必要です。
    echo 以下の手順に従ってください:
    echo.
    echo   1. https://www.python.org/downloads/ を開く
    echo   2. 「Download Python」ボタンをクリック
    echo   3. インストール時に「Add Python to PATH」に必ずチェック
    echo   4. インストール完了後、もう一度このファイルを実行
    echo.
    pause
    exit /b 1
)

echo [1/3] Python が見つかりました。
for /f "tokens=*" %%i in ('python --version 2^>^&1') do echo       %%i
echo.

echo [2/3] 必要なライブラリをインストールしています...
echo       （初回は数分かかることがあります）
echo.
python -m pip install --upgrade pip >nul 2>&1
python -m pip install -r "%~dp0requirements.txt"
if %errorlevel% neq 0 (
    echo.
    echo [エラー] ライブラリのインストールに失敗しました。
    echo インターネット接続を確認してください。
    pause
    exit /b 1
)
echo.

echo [3/3] フォルダを準備しています...
if not exist "%~dp0input_pdf" mkdir "%~dp0input_pdf"
if not exist "%~dp0database" mkdir "%~dp0database"
if not exist "%~dp0logs" mkdir "%~dp0logs"
if not exist "%~dp0ocr_text" mkdir "%~dp0ocr_text"
if not exist "%~dp0notebooklm_export" mkdir "%~dp0notebooklm_export"

echo.
echo ============================================
echo   初期設定が完了しました！
echo ============================================
echo.
echo 次の手順:
echo   1. 「input_pdf」フォルダにPDFファイルを入れる
echo   2. 「②データ取込」をダブルクリック
echo   3. 「③アプリ起動」をダブルクリック
echo.
pause
