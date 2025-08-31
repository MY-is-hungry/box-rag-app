# Repository Guidelines

## プロジェクト構成
- `app/app.py`: Streamlit のエントリポイント（UI とオーケストレーション）。
- `app/core/`: 中核ロジック（`ingest.py` 取り込み、`rag.py` 検索/要約、`config.py` 設定、`utils.py` 共通）。
- `app/prompts/`: プロンプトテンプレート。
- `app/stores/`: FAISS のローカルベクタ格納先（再生成可能）。
- ルート: `.env` 環境変数、`requirements.txt` 依存、`REQUIREMENTS.md` 仕様/設計。

## ビルド・テスト・開発コマンド
- 仮想環境: `python3 -m venv .venv && source .venv/bin/activate`
- 依存インストール: `pip install -r requirements.txt`
- ローカル起動: `streamlit run app/app.py`
- 環境変数: `.env` に `OPENAI_API_KEY`, `BOX_*`, `LANGSMITH_*` を設定。
- 任意: フォーマット `black .`、リンタ `ruff .`（導入時）。

## コーディング規約・命名
- Python 3.11+、PEP 8、インデント4スペース。
- 命名: 関数/変数 `snake_case`、クラス `PascalCase`、定数 `UPPER_SNAKE_CASE`。
- UI は `app/app.py` に、純粋ロジック/外部I/O は `app/core/*` に分離。
- パスのハードコード禁止。設定は `.env` と `config.py`（例: `VECTOR_DIR`, `TOP_K`）。

## 言語・出力ポリシー
- 思考・内部コメント: 英語可。
- ユーザー向け出力: 日本語で統一（UI/回答/表示ログ）。
- プロンプト既定: 日本語出力を明示（例:「最終出力は日本語で記述してください」）。

## テスト方針
- フレームワーク: `pytest` を推奨（必要に応じ `pip install pytest`）。
- 配置: `app/tests/`、ファイル名 `test_*.py`（例: `app/tests/test_utils.py`）。
- 範囲: `utils.py` の単体、`rag.py` の合成ロジック。外部APIはモック。
- 実行: `pytest -q`（`-k` でテスト名フィルタ）。`.env` は `monkeypatch` で注入。

## コミット・PR ガイドライン
- コミット: Conventional Commits（`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`）。件名は命令形かつ簡潔（72字以内）。
- PR: 目的、関連Issue、動作手順、UI変更はスクショ。設定/仕様変更は `REQUIREMENTS.md` にも反映。
- 衛生: 機密値をコミットしない。フォーマッタ/リンタ実行、アプリ起動確認。

## セキュリティ・設定
- 秘密情報は `.env` 管理（`python-dotenv` で読込）。ログに PII を残さない。
- 必須変数（OpenAI/Box/LangSmith）は起動時に検証。`LOG_LEVEL` で冗長度を調整。
- ベクタストアは `app/stores/` を既定。不要なら削除して再構築可能。
