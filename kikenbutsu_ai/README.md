# 危険物法令ナレッジAI（実務プロトタイプ）

消防職員向けに、危険物関連法令・通知・基準文書を**原文重視**で検索・比較するためのツールです。  
このシステムは法解釈を自動決定しません。必ず原本確認を前提とした支援ツールです。

## 1. このアプリの目的
- 原文確認（条文・通知の該当箇所）
- 旧基準 / 新基準の差分確認
- 改正理由候補の抽出
- 査察時の確認候補提示
- NotebookLMに投入しやすい形への整形

## 2. 必要なもの
- Windows 10/11
- Python 3.11
- VS Code（推奨）
- PDFファイル（`input_pdf/`）
- OCR済みテキスト（任意、`ocr_text/<PDF名>.txt`）

## 3. インストール
### 3-1. Python
1. Python公式サイトから 3.11 をインストール
2. インストール時に **Add Python to PATH** をON

### 3-2. ライブラリ
```bash
pip install -r requirements.txt
```

### 3-3. PaddleOCR利用の注意
- 初回実行時にモデル取得で時間がかかることがあります。
- ネットワーク制限環境ではOCR処理を先に実施したテキスト（`ocr_text/*.txt`）利用を推奨。

## 4. フォルダ構成（主要）
- `input_pdf/` : 入力PDF
- `ocr_text/` : OCRテキスト
- `database/kikenbutsu.db` : 検索DB
- `notebooklm_export/` : NotebookLM投入用Markdown
- `logs/` : 実行ログ

## 5. 実行方法
### 5-1. パイプライン実行
```bash
python src/run_pipeline.py
```

### 5-2. UI起動
```bash
streamlit run src/app_streamlit.py
```

## 6. NotebookLMへの渡し方
- パイプライン実行後、`notebooklm_export/*.md` をNotebookLMへアップロードします。
- 出力形式:
  - 設備別（例: `地下タンク貯蔵所.md`）
  - 改正差分別（例: `地下タンク貯蔵所_改正差分.md`）
  - 法令別（例: `消防法_関係条文.md`）
- 10MB超は自動分割（`*_part1.md` 形式）されます。

## 7. よくあるエラー
### 7-1. `Python が見つかりません`
- Python再インストール時にPATH設定をONにしてください。

### 7-2. `pip` 失敗
- `python -m ensurepip --upgrade`
- `python -m pip install --user -r requirements.txt`

### 7-3. 結果が出ない
- `input_pdf/` にPDFがあるか
- `ocr_text/` に対応テキストがあるか
- `logs/pipeline.log` を確認

### 7-4. GitHubコンフリクト解消後に実行エラー
- `.bat/.vbs/.py` に `<<<<<<<` `=======` `>>>>>>>` が残っていないか確認

## 8. 安全設計（重要）
- UI表示は「原文引用」と「信頼度」を明示
- 低信頼箇所には `OCR低信頼` / `原本確認推奨`
- 本システムの結論は参考候補であり、最終判断は原本確認と人手審査


## 9. v2改善メモ（今回反映）
- OCR信頼度は「高信頼 / OCR低信頼 / 信頼度不明」を明示します。
- `ocr_text/*.txt` 取り込み時は信頼度不明として保存し、原本確認推奨になります（1.0固定はしません）。
- 差分比較は、設備重なり・タイトル類似・年次順・文書種別を使って比較候補を作り、段落も複数候補から選定します。
- 年代検索は専用絞り込み（年代のみ、または年代+キーワード）で検索します。
