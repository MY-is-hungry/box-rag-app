# Box RAG App (PoC)

## クイックスタート
- 仮想環境: `python3 -m venv .venv && source .venv/bin/activate`
- 依存: `pip install -r requirements.txt -r dev-requirements.txt`
- 環境変数: `.env.example` を参考に `.env` を作成
- 起動: `streamlit run main.py`

## 機能概要（現状）
- 検索/要約（RAG）: Bedrock Embeddings/LLM + FAISS
- 取り込み/同期: ローカルPDF追加、Box取り込み（直下）、Box同期（再帰・追加/更新/削除、manifest差分）
- 複数フォルダID対応: `BOX_FOLDER_IDS` はカンマ区切り可能
- Box管理UI: フォルダ内容/PDF一覧、フォルダ移動、PDFアップロード

## ページ構成
- 「質問に回答」: Q&A（`app/main.py`）
- 「データ取り込み・同期」: ローカルPDF追加、Box取り込み/同期（`pages/01_ingest_sync.py`）
- 「Box 管理」: コンテンツ一覧/アップロード（`pages/02_box_admin.py`）

## 設定のポイント
- `TOP_K`: 検索で取得する関連チャンク数（既定5、環境変数で変更可）
- `VECTOR_DIR`: FAISSの保存先（既定 `./app/stores/box_index_v1`）
- Embeddings/LLM: AWS Bedrock（OpenAIは未対応）。
  - Embeddings: `EMBEDDINGS_PROVIDER=bedrock`, `EMBEDDINGS_MODEL=amazon.titan-embed-text-v2:0`
  - LLM: `LLM_PROVIDER=bedrock`, `LLM_MODEL=anthropic.claude-3-haiku-20240307-v1:0`
  - 共通: `AWS_REGION` を指定
- Box認証: 開発はdevtoken、本番はOAuth(CCG)を推奨。
  - `BOX_AUTH_METHOD=oauth`
  - `BOX_CLIENT_ID`, `BOX_CLIENT_SECRET`（必要に応じて `BOX_SUBJECT_TYPE`, `BOX_SUBJECT_ID`）
  - JWTは未対応（将来検討）

## 使い方
1) 「データ取り込み・同期」でローカルPDFを追加、または「Boxから追加」/「Boxと同期」を実行。
2) 「質問に回答」で日本語で質問を入力し「回答する」。
3) 必要に応じて「Box 管理」でフォルダ内容の確認やPDFアップロードを行う。

## 開発ツール
- 整形: `black .` / 静的解析: `ruff .`
- pre-commit: `pre-commit install` → `pre-commit run --all-files`

詳細は `AGENTS.md` と `REQUIREMENTS.md` を参照してください。
