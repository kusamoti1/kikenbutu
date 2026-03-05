@echo off
chcp 65001 >nul 2>&1
title 危険物法令ナレッジAI - データ取込

echo ============================================
echo   危険物法令ナレッジグラフAI  データ取込
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

REM --- input_pdf フォルダ確認 ---
if not exist "%~dp0input_pdf" mkdir "%~dp0input_pdf"

dir /b "%~dp0input_pdf\*.pdf" >nul 2>&1
if %errorlevel% neq 0 (
    echo [注意] input_pdf フォルダにPDFファイルがありません。
    echo.
    echo PDFファイルを input_pdf フォルダに入れてから
    echo もう一度このファイルを実行してください。
    echo.
    echo input_pdf フォルダを開きます...
    explorer "%~dp0input_pdf"
    pause
    exit /b 0
)

echo PDFファイルを検出しました。データ取込を開始します。
echo （ファイル数によって数分〜数十分かかります）
echo.

cd /d "%~dp0"
python run_pipeline.py

if %errorlevel% neq 0 (
    echo.
    echo [エラー] データ取込中にエラーが発生しました。
    echo 詳細は logs/pipeline.log を確認してください。
    pause
    exit /b 1
)

echo.
echo ============================================
echo   データ取込が完了しました！
echo ============================================
echo.
echo 次の手順:
echo   「③アプリ起動」をダブルクリックしてください。
echo.
pause
