# Box RAG 要件定義

---

## 1. 背景・目的

* 社内Box（以降、Box）に蓄積された資料を、自然言語で効率的に探索・要約・参照できる仕組みを構築する。
* まずは単一アプリケーション（Streamlit）で最短開発し、品質観測を通じて改善するAI駆動開発を実施する。
* 生成品質の可視化・回帰検証のため LangSmith を導入する。

## 2. スコープ

### 2.1 In Scope（現状実装ベース）

* Box上PDFを対象とした検索・要約（RAG）
* StreamlitによるWeb UI（Q&A、取り込み/同期、Box管理）
* AWS Bedrock のEmbeddings/LLM＋FAISS（ローカル）
* TOP_Kによる取得チャンク数制御（環境変数）
* Box取り込み（直下）および再帰同期（追加/更新/削除、manifest差分）
* 複数フォルダID（カンマ区切り）の取り込み/同期
* Box管理（内容一覧、PDF一覧、フォルダ移動、PDFアップロード）

### 2.2 Out of Scope（初期PoC）

* 画像OCR・Office（Word/Excel/PowerPoint）等の高度抽出
* 複雑なレイアウト保持要約、表/図の構造化
* SSO連携、細粒度アクセス制御
* 大規模スケールアウト、SLA/SLO定義

## 3. 成果物と受入基準（PoC）

* 成果物：Streamlitアプリ、FAISSインデックス、環境変数テンプレート、最小評価レポート
* 受入基準（現状の到達点に合わせて調整）

  1. 任意の自然言語質問に対し、要約テキスト＋参照情報（ファイル名/ページ）を3〜10秒程度で返却できること（小規模コーパス時）。
  2. 代表質問で参照情報が有用であること（ヒット率/適合率は観測記録）。
  3. LangSmithで各実行のトレースが確認できること（環境変数を設定した場合）。
  4. Box共有リンク（URL）の提示は今後の実装検討とする。

## 4. システム構成（概念）

```
[User] ──(HTTP)──> [Streamlit UI] ──(関数呼出)──> [RAG Core]
                                  ├─ Embeddings -> [VectorStore(FAISS)]
                                  ├─ Retriever   -> 上記検索
                                  ├─ LLM         -> 要約生成
                                  └─ LangSmith   -> トレース/評価
                    └─(Box SDK)──> [Box]
```

## 5. 機能要件

### 5.1 取り込み（Ingest）

* 対象：PDF
* 手順：
  1. Boxフォルダ内PDFの列挙（直下取り込み／再帰同期）
  2. テキスト抽出（`pypdf`）
  3. チャンク分割（`RecursiveCharacterTextSplitter`）
  4. Embeddings生成（Bedrock）→ FAISSへ格納
* メタデータ（現状）：`source`（ファイル名）、`page`、`chunk_index`
* 冪等性：`box:<file_id>:<chunk_index>` 形式の安定IDで登録（同期時はfingerprintで差分検知）
* 複数フォルダID：カンマ区切り指定に対応（単一インデックスに統合）

### 5.2 検索（Retrieval）

* FAISSから`.as_retriever()`で類似度検索
* `TOP_K=5`を既定（`.env`で変更可）
* 将来拡張：BM25とのハイブリッド、Rerank導入（検討）

### 5.3 要約（Synthesis）

* 取得チャンクを根拠として要約を生成
* 出力は日本語、重要点の箇条書き、可能な範囲で参照情報を付与

### 5.4 UI（Streamlit）

* Q&Aページ：質問入力、回答表示
* 取り込み・同期：ローカルPDF追加、Box取り込み（直下）、Box同期（再帰・追加/更新/削除）
* Box管理：フォルダ内容／PDF一覧、フォルダ移動、PDFアップロード
* デバッグ表示（チャンク/スコア/Runリンク）は今後の実装検討

### 5.5 観測（LangSmith）

* 環境変数設定でLangSmithトレース有効化
* Run名/タグ付け、UIからRunリンク表示は今後の実装検討

## 6. 非機能要件

* 言語：日本語・英語入力に対応（初期は日本語主体）
* 性能：小規模（数百〜数千チャンク）でP95応答10秒以内を目標
* セキュリティ：APIキー/認証情報は`.env`管理。PIIログ抑制
* ロギング：アプリログ＋LangSmith（有効時）

## 7. 外部サービス・認証

### 7.1 Box

* 開発：Developer Tokenで動作確認（短命）
* 本番：OAuth（CCG, サーバー認証）をサポート
* JWT対応は今後の実装検討

### 7.2 Embeddings/LLM（AWS Bedrock）

* Embeddings：`amazon.titan-embed-text-v2:0`
* LLM：`anthropic.claude-3-haiku-20240307-v1:0`
* 共通：`AWS_REGION` 必須

### 7.3 VectorStore

* 既定：FAISS（ローカル、`VECTOR_DIR`に保存）
* 他のVectorDB置換は今後の実装検討

## 8. 設定・環境変数（例）

```
# Box
BOX_FOLDER_IDS="123456789,234567890"   # カンマ区切りで複数可
BOX_AUTH_METHOD="oauth"                # devtoken|oauth をサポート
BOX_DEVELOPER_TOKEN="..."              # devtoken時のみ
BOX_CLIENT_ID="..."                    # OAuth (CCG)
BOX_CLIENT_SECRET="..."                # OAuth (CCG)
# 必要に応じて CCG の対象指定
# BOX_SUBJECT_TYPE="enterprise|user"
# BOX_SUBJECT_ID="<enterprise_id or user_id>"

# Embeddings / LLM (Bedrock)
EMBEDDINGS_PROVIDER="bedrock"
EMBEDDINGS_MODEL="amazon.titan-embed-text-v2:0"
LLM_PROVIDER="bedrock"
LLM_MODEL="anthropic.claude-3-haiku-20240307-v1:0"
AWS_REGION="ap-northeast-1"

# VectorStore
VECTOR_DIR="./app/stores/box_index_v1"
TOP_K=5

# LangSmith
LANGSMITH_TRACING="true"
LANGSMITH_API_KEY="..."
LANGSMITH_PROJECT="box-rag-poc"

# App
LOG_LEVEL="INFO"
```

## 9. ディレクトリ構成（現状）

```
.
├─ main.py                 # ルートエントリ（app/main.pyを呼び出し）
├─ pages/                  # Streamlit複数ページ（取り込み/Box管理など）
└─ app/
   ├─ main.py             # Q&A UIエントリ
   ├─ core/
   │   ├─ ingest.py       # 取込/同期（Box→抽出→分割→埋め込み→格納）
   │   ├─ rag.py          # Retriever/要約チェーン
   │   ├─ config.py       # 設定ロード
   │   └─ utils.py        # 共通ユーティリティ
   ├─ prompts/            # プロンプト群
   └─ stores/             # FAISSインデックス（永続）
```

## 10. 抽出・分割の方針

* 対象ファイル：PDF優先
* 抽出器：現状`pypdf`固定。`pdfminer.six` / `unstructured`切替は今後の実装検討
* 分割：`RecursiveCharacterTextSplitter`、`chunk_size/overlap`はLangSmith観測で最適化

## 11. 複数フォルダ対応（現状）

* 取り込み/同期ともに複数`folder_id`（カンマ区切り）を受け取り、単一インデックスに統合
* UIで対象フォルダの確認/移動が可能（Box管理）

## 12. エラーハンドリング・運用

* 例外はUIで通知。詳細はスタックトレース表示
* LangSmithトレース（有効時）
* Box APIレート制限の明示対応・再試行制御は今後の実装検討

## 13. 同期・更新

* 手動同期（Streamlit UIボタン）
* 再帰的に追加/更新/削除を検出（fingerprint＋manifest方式）
* 将来：Box Webhooks/Events APIでの増分更新を検討

## 14. テスト計画（PoC）

* 機能：
  * 単一質問→要約＋参照情報（ファイル名/ページ）が返る
  * `TOP_K`変更の反映
  * 日本語/英語クエリの応答
* 品質：代表質問セットでヒューマン評価（適合/冗長/根拠明示）
* 運用：Boxトークン失効時の挙動、エラートレース確認

## 15. フェーズ計画

1. Phase 1（PoC）：PDF・FAISS・手動同期・LangSmith導入
2. Phase 2（改善）：ハイブリッド検索／Webhook同期／メタデータ拡充
3. Phase 3（準本番）：LangServe/FastAPIでAPI化、Managed Vector DB、SSO/認可

## 16. 将来拡張

* Office（docx/xlsx/pptx）対応、画像OCR
* マネージドVectorDB（Pinecone/Weaviate/pgvector）
* 再ランカー・長文圧縮（LLM-Tokenizer最適化）
* 監査ログ、アクセス権限連動（部署/役職）

## 17. 未実装・今後の実装検討

* Box共有リンク（URL）の取得・参照情報への付与（manifestへのキャッシュ含む）
* `Document.metadata`の拡充：`file_id/folder_id/path/title/updated_at/box_shared_link` 等
* UIデバッグ表示：取得チャンク、スコア、LangSmith Runリンク
* LangSmithのRun名/タグ付け、評価パイプライン整備
* Box JWT認証対応
* 抽出器の切替（`pdfminer.six`/`unstructured`）
* APIレート制限・指数バックオフ・再試行方針
* Webhook/Eventsによる増分同期
* ハイブリッド検索（BM25）・Rerankモデル導入
* Managed Vector DB対応
* SSO/認可、監査要件の具体化
