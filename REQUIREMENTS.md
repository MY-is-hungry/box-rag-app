# Box RAG 要件定義

---

## 1. 背景・目的

* 社内Box（以降、Box）に蓄積された資料を、自然言語で効率的に探索・要約・参照できる仕組みを構築する。
* まずは**単一アプリケーション（Streamlit）**で最短開発し、品質観測を通じて改善する**AI駆動開発**を実施する。
* 生成品質の可視化・回帰検証のため **LangSmith** を導入する。

## 2. スコープ

### 2.1 In Scope

* Box上資料（当面はPDF）を対象とした**検索・要約（RAG）**
* StreamlitによるWeb UI（社内ネットワークで利用）
* Embeddings生成とVectorStoreによる類似度検索
* 参照元（Box URL）の提示
* LangSmithによるトレーシング／評価

### 2.2 Out of Scope（初期PoC）

* 画像OCR・Office（Word/Excel/PowerPoint）等の高度抽出
* 複数言語の高度レイアウト保持要約、表/図の構造化
* SSO連携、きめ細かなRBAC、細粒度アクセス制御
* 大規模スケールアウト、SLA/SLO定義

## 3. 成果物と受入基準

* 成果物：Streamlitアプリ（Docker化）、FAISSインデックス、環境変数テンプレート、最小評価レポート
* 受入基準（PoC）：

  1. 任意の自然言語質問に対し、**要約テキスト＋参照リンク**を3秒～10秒程度で返却できること（小規模コーパス時）
  2. 代表質問で**参照リンクが実際に有用**であること（ヒット率/適合率は観測記録）
  3. LangSmithで**各実行のトレース**が確認できること

## 4. システム構成（概念）

```
[User] ──(HTTP)──> [Streamlit UI] ──(関数呼出)──> [RAG Core]
                                  ├─ Embeddings -> [VectorStore(FAISS)]
                                  ├─ Retriever   -> 上記検索
                                  ├─ LLM         -> 要約生成
                                  └─ LangSmith   -> トレース/評価
                    └─(Box SDK/Loader)──> [Box]
```

## 5. 機能要件

### 5.1 取り込み（Ingest）

* 対象：**特定フォルダ固定**（初期）。複数フォルダは検証後に対応可。
* 手順：

  1. Boxフォルダ内のPDFを走査
  2. テキスト抽出（抽出器は切替可能）
  3. チャンク分割（`RecursiveCharacterTextSplitter`）
  4. Embeddings生成→VectorStoreへ格納
* メタデータ：`file_id`, `folder_id`, `path`, `title`, `updated_at`, `page`, `chunk_index`, `box_shared_link(optional)`
* 冪等性：`file_id + page + chunk_index` をキーに近似重複除去

### 5.2 検索（Retrieval）

* VectorStoreから `.as_retriever()` を用いた類似度検索
* 既定 `top_k = 5`（UIまたは環境変数で変更可）
* 将来拡張：BM25とのハイブリッド検索、Rerankモデルの導入

### 5.3 要約（Synthesis）

* 取得チャンクを根拠として要約を生成（回答には**参照元**を必ず付与）
* 方式：map-reduce または refine（検証により選択）

### 5.4 UI（Streamlit）

* 質問入力欄、回答パネル、参照リンク（Box URL）
* （開発モード）デバッグ表示：取得チャンク、スコア、LangSmith Runリンク

### 5.5 観測（LangSmith）

* 全実行をトレース：プロンプト／Retriever設定／経過時間／エラー
* 回帰比較のためバージョンタグ付与

## 6. 非機能要件

* **言語**：日本語・英語入力に対応（初期は日本語主体）
* **性能**：小規模（数百～数千チャンク）でP95応答10秒以内を目標
* **可用性**：PoC段階のためベストエフォート
* **セキュリティ**：APIキー/認証情報は環境変数（`.env`）管理。ログには個人情報を極力残さない
* **ロギング**：アプリログ＋LangSmithトレース

## 7. 外部サービス・認証

### 7.1 Box

* 開発：Developer Tokenで動作確認
* 本番：**実装容易性を優先し、JWT または OAuth のいずれか**を選択（セットアップ時に最短の方を採用）

### 7.2 Embeddings（AWS Bedrock / 代替）

* 既定：AWS Bedrock の埋め込みモデルを利用（例: `cohere.embed-multilingual-v3`）
* 切替: .env で EMBEDDINGS_PROVIDER=bedrock を指定し、AWS_REGION などの認証情報を設定
* オプション: 将来的に OpenAI text-embedding-3-small/-large を利用することも可能（Team APIキー）

### 7.3 VectorStore

* 既定：**FAISS（ローカル）**
* 将来置換：Chroma / Pinecone / Weaviate / pgvector など

## 8. 設定・環境変数（例）

```
# Box
BOX_FOLDER_IDS="123456789"        # カンマ区切りで複数対応可（将来）
BOX_AUTH_METHOD="devtoken|jwt|oauth"
BOX_DEVELOPER_TOKEN="..."          # devtoken時
BOX_JWT_CONFIG_PATH="..."          # jwt時（JSON）

# Embeddings
EMBEDDINGS_PROVIDER="openai|bedrock|hf"
EMBEDDINGS_MODEL="text-embedding-3-small"
OPENAI_API_KEY="..."
AWS_REGION="ap-northeast-1"        # bedrock利用時

# VectorStore
VECTOR_STORE="faiss|chroma|pinecone|pgvector"
VECTOR_DIR="./stores/box_index_v1"
TOP_K=5

# LangSmith
LANGSMITH_TRACING="true"
LANGSMITH_API_KEY="..."
LANGSMITH_PROJECT="box-rag-poc"

# App
LOG_LEVEL="INFO"
```

## 9. ディレクトリ構成（案）

```
app/
  ├─ app.py                 # Streamlitエントリ
  ├─ core/
  │   ├─ ingest.py          # 取込（Box→抽出→分割→埋め込み→格納）
  │   ├─ rag.py             # Retriever/要約チェーン
  │   ├─ config.py          # 設定ロード
  │   └─ utils.py
  ├─ prompts/               # プロンプト群
  ├─ stores/                # FAISSインデックス（永続）
  └─ requirements.txt
```

## 10. 抽出・分割の方針

* **対象ファイル**：当面は**PDF優先**
* **抽出器**：`pypdf` / `pdfminer.six` / `unstructured` を選択可能（表/図が多い場合は`unstructured`検討）
* **分割**：`RecursiveCharacterTextSplitter`、`chunk_size`/`overlap`はLangSmith観測で最適化

## 11. 複数フォルダ対応（方針）

* 実装可否を検証し、**精度劣化が無ければ有効化**
* 実装案：

  * 取り込み時に複数`folder_id`を受け取り、**単一インデックスに統合**
  * フィルタ：UIでフォルダ指定/タグ指定
  * スコア補正：`updated_at`やフォルダ重要度の微加点

## 12. エラーハンドリング・運用

* 取り込み失敗時の再試行（指数バックオフ）
* Box APIレート制限の検知とスロットリング
* 欠落メタデータの検出・スキップログ
* 例外をLangSmithおよびアプリログに記録

## 13. 同期・更新

* 初期：**手動再取込**（ボタン/CLI）
* 将来：**Box Webhooks/Events API**で増分更新（`FILE.UPLOADED`/`FILE.PREVIEWED`など必要に応じ）

## 14. テスト計画（PoC）

* 機能：

  * 単一質問→要約＋参照リンクが返る
  * `top_k`変更の反映
  * 日本語/英語クエリの応答
* 品質：代表質問セット（後日提供）でヒューマン評価（適合/冗長/根拠明示）
* 運用：Boxトークン失効時の挙動、エラートレース確認

## 15. フェーズ計画

1. **Phase 1（PoC）**：特定フォルダ・PDF・FAISS・手動同期・LangSmith導入
2. **Phase 2（改善）**：複数フォルダ対応可否の検証／ハイブリッド検索／Webhook同期
3. **Phase 3（準本番）**：LangServeまたはFastAPIでAPI化、Managed Vector DB、SSO/認可

## 16. 将来拡張

* Office（docx/xlsx/pptx）対応、画像OCR
* マネージドVectorDB（Pinecone/Weaviate/pgvector）
* 再ランカー・長文圧縮（LLM-Tokenizer最適化）
* 監査ログ、アクセス権限連動（部署/役職）

## 17. 未確定事項・要アクション

* **BoxフォルダIDの指定**（初期固定）
* **Embeddings利用方針**：OpenAI Teamキーを使用するか、もしくはBedrockを使用するか（どちらでも可）
* **評価用質問セット**（後日提供）
* 監査要件（ログ保持期間、PIIの扱い）
