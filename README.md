# Box RAG App (PoC)

## クイックスタート
- 仮想環境: `python3 -m venv .venv && source .venv/bin/activate`
- 依存: `pip install -r requirements.txt -r dev-requirements.txt`
- 環境変数: `.env.example` を参考に `.env` を作成
- 起動: `streamlit run app/app.py`

## 設定のポイント
- `TOP_K`: 検索で取得する関連チャンク数（既定5、環境変数で変更可）
- `VECTOR_DIR`: FAISSの保存先（既定 `./app/stores/box_index_v1`）

## 開発ツール
- 整形: `black .` / 静的解析: `ruff .`
- pre-commit: `pre-commit install` → `pre-commit run --all-files`

詳細は `AGENTS.md` と `REQUIREMENTS.md` を参照してください。
