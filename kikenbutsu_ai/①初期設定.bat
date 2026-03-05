@echo off
chcp 65001 >nul 2>&1
title 危険物法令ナレッジAI - 初期設定

echo.
echo  ============================================
echo    危険物法令ナレッジグラフAI  初期設定
echo  ============================================
echo.

REM -------------------------------------------------------
REM  Python の存在確認
REM -------------------------------------------------------
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo  [!] Python が見つかりません。
    echo.
    echo      Python のインストールが必要です。
    echo      詳しくは「使い方ガイド.txt」をお読みください。
    echo.
    pause
    exit /b 1
)

echo  [OK] Python を検出しました。
for /f "tokens=*" %%i in ('python --version 2^>^&1') do echo        %%i
echo.

REM -------------------------------------------------------
REM  ライブラリのインストール（既に入っていればスキップ）
REM -------------------------------------------------------
echo  ライブラリを確認しています...
echo.

REM 主要ライブラリが入っているかチェック
python -c "import streamlit; import networkx" >nul 2>&1
if %errorlevel% equ 0 (
    echo  [OK] 主要ライブラリはインストール済みです。
    echo       （スキップします）
) else (
    echo  ライブラリをインストールしています...
    echo  （インターネット接続が必要です。数分お待ちください）
    echo.
    python -m pip install --upgrade pip >nul 2>&1
    python -m pip install -r "%~dp0requirements.txt"
    if %errorlevel% neq 0 (
        echo.
        echo  [!] インストール中にエラーが発生しました。
        echo      インターネット接続を確認してください。
        echo.
        pause
        exit /b 1
    )
    echo.
    echo  [OK] ライブラリのインストールが完了しました。
)
echo.

REM -------------------------------------------------------
REM  フォルダの自動作成
REM -------------------------------------------------------
echo  フォルダを準備しています...
if not exist "%~dp0input_pdf"          mkdir "%~dp0input_pdf"
if not exist "%~dp0database"           mkdir "%~dp0database"
if not exist "%~dp0logs"               mkdir "%~dp0logs"
if not exist "%~dp0ocr_text"           mkdir "%~dp0ocr_text"
if not exist "%~dp0notebooklm_export"  mkdir "%~dp0notebooklm_export"
echo  [OK] フォルダの準備が完了しました。
echo.

echo  ============================================
echo    初期設定が完了しました
echo  ============================================
echo.
echo  次にやること:
echo    1. 今から開く「input_pdf」フォルダに、
echo       読み込みたいPDFファイルを入れてください。
echo.
echo    2. PDFを入れたら「②データ取込」を
echo       ダブルクリックしてください。
echo.

REM input_pdf フォルダを自動で開く
explorer "%~dp0input_pdf"

pause
