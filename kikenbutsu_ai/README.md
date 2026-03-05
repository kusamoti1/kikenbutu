# kikenbutsu_ai

日本の危険物関連法令資料を整理し、原文引用ベースで検索するための **危険物法令ナレッジグラフAI** です。

## 1. できること
- PDF群を処理し、段落単位でSQLiteへ格納
- OCR辞書補正・旧漢字変換
- 設備・通知・条文リンクのナレッジグラフ生成
- 差分比較（`difflib`）や改正理由抽出の土台
- Streamlit UIで「設備検索 / 年代検索 / 差分検索 / 査察AI」
- NotebookLM向けMarkdownエクスポート

## 2. フォルダ構成
```text
kikenbutsu_ai/
  input_pdf/
  processed_images/
  ocr_text/
  chunks/
  database/
  dictionary/
  notebooklm_export/
  inspection_ai/
  logs/
  src/
  run_pipeline.py
  requirements.txt
```

## 3. 初心者向けセットアップ（Windows）
### 3-1. Pythonのインストール
1. Python 3.11 を公式サイトからインストール
2. インストール時に「Add Python to PATH」をチェック

### 3-2. 必要ライブラリのインストール
```bash
pip install -r requirements.txt
```

### 3-3. OCRの準備
- `input_pdf/` にPDFを置く
- OCR済みテキストがある場合は `ocr_text/<PDF名>.txt` を配置
- OCR誤字補正は `dictionary/ocr_dictionary.tsv` を編集

> 注: フルOCR実行（pdf2image / OpenCV / PaddleOCR）を実運用で行う場合、`src/pdf_to_image.py`・`src/image_preprocess.py`・`src/run_ocr.py` をパイプラインに接続して使います。

## 4. 実行手順
### 4-1. パイプライン実行
```bash
python run_pipeline.py
```

成果物:
- `database/kikenbutsu.db`
- `database/knowledge_graph.graphml`
- `notebooklm_export/*.md`
- `logs/pipeline.log`

### 4-3. NotebookLMへ入れるファイルの場所
- NotebookLMに取り込むファイルは、パイプライン完了後に `notebooklm_export/` に出力される `*.md` です。
- 1ファイル10MBを超える場合は自動分割され、`*_part1.md` のように複数ファイルで出力されます。
- 出力が空の場合は、`input_pdf/` にPDFがあるか、または対応する `ocr_text/<PDF名>.txt` があるか確認してください。

### 4-2. UI起動
```bash
streamlit run src/app_streamlit.py
```

## 5. AI設計原則（重要）
- 推論禁止
- 解釈生成禁止
- 原文引用必須

UI表示は上記原則を常に明示します。
