@echo off
chcp 65001 >nul 2>&1
title 危険物法令ナレッジAI - データ取込

echo.
echo  ============================================
echo    危険物法令ナレッジグラフAI  データ取込
echo  ============================================
echo.

REM -------------------------------------------------------
REM  Python の存在確認
REM -------------------------------------------------------
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo  [!] Python が見つかりません。
    echo      先に「①初期設定」を実行してください。
    echo.
    pause
    exit /b 1
)

REM -------------------------------------------------------
REM  input_pdf フォルダを自動作成して中身を確認
REM -------------------------------------------------------
if not exist "%~dp0input_pdf" mkdir "%~dp0input_pdf"

dir /b "%~dp0input_pdf\*.pdf" >nul 2>&1
if %errorlevel% neq 0 (
    echo  [!] 「input_pdf」フォルダにPDFファイルがありません。
    echo.
    echo      これから「input_pdf」フォルダを開きます。
    echo      そこにPDFファイルをコピーしてから、
    echo      もう一度このファイルをダブルクリックしてください。
    echo.
    explorer "%~dp0input_pdf"
    pause
    exit /b 0
)

echo  PDFファイルが見つかりました。
echo  データの取り込みを開始します。
echo.
echo  （ファイル数によって数分〜数十分かかります）
echo  （この画面は自動で閉じます。しばらくお待ちください）
echo.

cd /d "%~dp0"
python run_pipeline.py

if %errorlevel% neq 0 (
    echo.
    echo  [!] データ取込中にエラーが発生しました。
    echo      詳細は logs フォルダの pipeline.log を
    echo      確認してください。
    echo.
    pause
    exit /b 1
)

echo.
echo  ============================================
echo    データ取込が完了しました
echo  ============================================
echo.
echo  次にやること:
echo    「③アプリ起動」をダブルクリックしてください。
echo.
pause
