# Box RAG App (PoC)

## クイックスタート
- 仮想環境: `python3 -m venv .venv && source .venv/bin/activate`
- 依存: `pip install -r requirements.txt -r dev-requirements.txt`
- 環境変数: `.env.example` を参考に `.env` を作成
- 起動: `streamlit run app/app.py`

## 設定のポイント
- `TOP_K`: 検索で取得する関連チャンク数（既定5、環境変数で変更可）
- `VECTOR_DIR`: FAISSの保存先（既定 `./app/stores/box_index_v1`）
- Embeddings/LLM: AWS Bedrock を使用（OpenAIは不使用）。
  - Embeddings: `EMBEDDINGS_PROVIDER=bedrock`, `EMBEDDINGS_MODEL=amazon.titan-embed-text-v2:0`
  - LLM: `LLM_PROVIDER=bedrock`, `LLM_MODEL=anthropic.claude-3-haiku-20240307-v1:0`
  - 共通: `AWS_REGION` を指定
- Box認証: 開発はdevtoken、本番はOAuth(CCG)を推奨。
  - `BOX_AUTH_METHOD=oauth`
  - `BOX_CLIENT_ID`, `BOX_CLIENT_SECRET`（必要に応じて `BOX_SUBJECT_TYPE`, `BOX_SUBJECT_ID`）

## 開発ツール
- 整形: `black .` / 静的解析: `ruff .`
- pre-commit: `pre-commit install` → `pre-commit run --all-files`

詳細は `AGENTS.md` と `REQUIREMENTS.md` を参照してください。

## 使い方（PoC最小機能）
- サイドバーの「インデックス取り込み」でPDFをアップロードし「取り込み/更新」を押下。
- テキストボックスに日本語で質問を入力し「実行」。
- 回答は日本語で表示され、参照情報は回答末尾に付与されます（可能な場合）。

注意
- Box連携の実取り込みは今後実装予定です。まずはローカルPDFの取り込みで検証可能です。
