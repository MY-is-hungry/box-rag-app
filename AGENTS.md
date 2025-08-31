# Repository Guidelines

## プロジェクト構成
- `app/app.py`: Streamlit のエントリポイント（UI とオーケストレーション）。
- `app/core/`: 中核ロジック（`ingest.py` 取り込み、`rag.py` 検索/要約、`config.py` 設定、`utils.py` 共通）。
- `app/prompts/`: プロンプトテンプレート。
- `app/stores/`: FAISS のローカルベクタ格納先（再生成可能）。
- ルート: `.env` 環境変数、`requirements.txt` 依存、`REQUIREMENTS.md` 仕様/設計。

## セットアップ・開発コマンド
- 仮想環境: `python3 -m venv .venv && source .venv/bin/activate`
- 依存インストール: `pip install -r requirements.txt`
- 開発ツール: `pip install -r dev-requirements.txt`（black/ruff/pre-commit）
- ローカル起動: `streamlit run app/app.py`
- 環境変数: `.env` に `BOX_*`, `LANGSMITH_*`, `AWS_*` を設定。
- フォーマット: `black .` / リンタ: `ruff .`

### pre-commit（任意だが推奨）
- 初回: `pre-commit install`
- 手動実行: `pre-commit run --all-files`

## アーキテクチャ概要
- UI: Streamlit（`app/app.py`）。
- コア: RAG（`app/core/*`）— 取り込み、検索、要約の薄い関数に分割。
- ベクタDB: FAISS（`app/stores/`）に永続化。
- 外部: Embeddings/LLMともにAWS Bedrockを使用（OpenAIは不使用）。

## コーディング規約・命名
- Python 3.11+、PEP 8、インデント4スペース。
- 命名: 関数/変数 `snake_case`、クラス `PascalCase`、定数 `UPPER_SNAKE_CASE`。
- UI は `app/app.py` に、純粋ロジック/外部I/O は `app/core/*` に分離。
- パスのハードコード禁止。設定は `.env` と `config.py`（例: `VECTOR_DIR`, `TOP_K`）。

## 言語・出力ポリシー
- 思考・内部コメント: 英語可。
- ユーザー向け出力: 日本語で統一（UI/回答/表示ログ）。
- プロンプト既定: 日本語出力を明示（例:「最終出力は日本語で記述してください」）。

## 検索パラメータ（TOP_K）
- 役割: 検索時に取得する関連チャンク（文書断片）の件数。
- 既定値: `5`。`.env` の `TOP_K` で変更可能（整数）。
- 影響: 値が大きいほど根拠は増えるが、応答時間が延びる傾向。

## 環境変数サンプル
```
# Box
BOX_FOLDER_IDS="123456789"
BOX_AUTH_METHOD="oauth" # devtoken|jwt|oauth
BOX_DEVELOPER_TOKEN="..." # devtoken時のみ
BOX_CLIENT_ID="..."      # OAuth (CCG: サーバー認証)
BOX_CLIENT_SECRET="..."  # ※綴りに注意: SECRET
# 必要に応じて CCG の対象指定
# BOX_SUBJECT_TYPE="enterprise|user"
# BOX_SUBJECT_ID="<enterprise_id or user_id>"

# OpenAI / Embeddings
EMBEDDINGS_PROVIDER="bedrock"
EMBEDDINGS_MODEL="amazon.titan-embed-text-v2:0"
LLM_PROVIDER="bedrock"
LLM_MODEL="anthropic.claude-3-haiku-20240307-v1:0"
AWS_REGION="ap-northeast-1"     # Bedrock利用時

# VectorStore
VECTOR_DIR="./app/stores/box_index_v1"
TOP_K=5

# LangSmith
LANGSMITH_TRACING="true"
LANGSMITH_API_KEY="..."
LANGSMITH_PROJECT="box-rag-poc"
```


## コミット・PR ガイドライン
- コミット: Conventional Commits（`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`）。件名は命令形かつ簡潔（72字以内）。
- PR: 目的、関連Issue、動作手順、UI変更はスクショ。設定/仕様変更は `REQUIREMENTS.md` にも反映。
- 衛生: 機密値をコミットしない。フォーマッタ/リンタ実行、アプリ起動確認。

## 開発フロー（推奨）
- ブランチ作成: `feat/<短い説明>` or `fix/<短い説明>`。
- 変更後チェック: `black .` と `ruff .`、`streamlit run app/app.py` でUI起動確認。
- PR作成: 目的・変更点・動作手順・必要な環境変数の変更を記載。

## セキュリティ・設定
- 秘密情報は `.env` 管理（`python-dotenv` で読込）。ログに PII を残さない。
- 必須変数（Box/LangSmith/AWS）は起動時に検証。`LOG_LEVEL` で冗長度を調整。
- ベクタストアは `app/stores/` を既定。不要なら削除して再構築可能。
