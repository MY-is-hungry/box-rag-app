from __future__ import annotations

from typing import Iterable, List, Tuple, Dict, Any
import io
import json
from pathlib import Path
import re

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from .config import get_settings
from .utils import ensure_dir, pdf_bytes_to_documents

try:
    from boxsdk import Client, OAuth2
    from boxsdk.auth.ccg_auth import CCGAuth
except Exception:  # pragma: no cover - optional import until Box接続時に使用
    Client = None  # type: ignore
    OAuth2 = None  # type: ignore
    CCGAuth = None  # type: ignore


def build_embeddings():
    settings = get_settings()
    if settings.embeddings_provider != "bedrock":
        raise RuntimeError("Embeddings は Bedrock のみをサポートしています。EMBEDDINGS_PROVIDER=bedrock を設定してください。")
    if not settings.aws_region:
        raise RuntimeError("AWS_REGION を設定してください（Bedrock Embeddings）")
    try:
        from langchain_aws import BedrockEmbeddings  # type: ignore
    except Exception as e:  # pragma: no cover - インポート時のエラーは実行環境依存
        raise RuntimeError(
            "langchain-aws が見つかりません。仮想環境を有効化し、`pip install -r requirements.txt` を実行してください。"
        ) from e
    return BedrockEmbeddings(
        model_id=settings.embeddings_model,
        region_name=settings.aws_region,
    )


def load_or_create_index(docs: List[Document] | None = None) -> FAISS:
    settings = get_settings()
    ensure_dir(settings.vector_dir)
    try:
        vs = FAISS.load_local(settings.vector_dir, build_embeddings(), allow_dangerous_deserialization=True)
        if docs:
            vs.add_documents(docs)
            vs.save_local(settings.vector_dir)
        return vs
    except Exception:
        # 新規作成
        if not docs:
            raise ValueError(
                "インデックスが未作成で、追加するドキュメントが空です。画像のみのPDFや空文書ではテキスト抽出できない場合があります。"
            )
        vs = FAISS.from_documents(docs, build_embeddings())
        vs.save_local(settings.vector_dir)
        return vs


def upsert_documents(docs: List[Document]) -> Tuple[int, int]:
    """ドキュメントをベクタストアに追加/更新し保存。

    Returns: (追加件数, 総件数)
    """
    vs = load_or_create_index(docs)
    total = vs.index.ntotal
    return len(docs), total


# =============================
# Box 同期（追加/更新/削除）
# =============================
def _manifest_path() -> Path:
    settings = get_settings()
    return Path(settings.vector_dir) / "box_manifest.json"


def _load_manifest() -> Dict[str, Any]:
    p = _manifest_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_manifest(data: Dict[str, Any]) -> None:
    p = _manifest_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _list_box_pdfs_recursive(client: "Client", folder_id: str) -> List[Dict[str, Any]]:
    """フォルダ配下を再帰的に走査しPDFファイルを列挙する。

    Returns: [{id,name,sha1,etag,modified_at,size}]
    """
    result: List[Dict[str, Any]] = []

    def _walk(fid: str) -> None:
        fid = _normalize_folder_id(fid)
        items = client.folder(folder_id=fid).get_items(
            limit=1000,
            fields=["id", "type", "name", "sha1", "etag", "modified_at", "size"],
        )
        for it in items:
            itype = getattr(it, "type", "")
            if itype == "folder":
                _walk(it.id)
            elif itype == "file" and str(it.name).lower().endswith(".pdf"):
                result.append(
                    {
                        "id": it.id,
                        "name": it.name,
                        "sha1": getattr(it, "sha1", None),
                        "etag": getattr(it, "etag", None),
                        "modified_at": getattr(it, "modified_at", None),
                        "size": getattr(it, "size", None),
                    }
                )

    _walk(folder_id)
    return result


def _fingerprint(meta: Dict[str, Any]) -> str:
    """ファイルの変更検知用フィンガープリント（sha1 > etag > modified_at > size > name）。"""
    for k in ("sha1", "etag", "modified_at", "size", "name"):
        v = meta.get(k)
        if v:
            return f"{k}:{v}"
    return meta.get("id", "unknown")


def _delete_ids_from_faiss(ids: List[str]) -> None:
    settings = get_settings()
    vs = FAISS.load_local(settings.vector_dir, build_embeddings(), allow_dangerous_deserialization=True)
    if ids:
        try:
            vs.delete(ids)
            vs.save_local(settings.vector_dir)
        except Exception:
            # ベストエフォート削除
            pass


def sync_box_folders(folder_ids: str) -> Tuple[int, int, int, int]:
    """Boxの指定フォルダ（再帰）をFAISSに同期する。

    Returns: (added, updated, deleted, total_vectors)
    """
    client = _get_box_client()
    settings = get_settings()
    manifest = _load_manifest()

    # 現状ファイル一覧
    current: Dict[str, Dict[str, Any]] = {}
    for fid in [f.strip() for f in folder_ids.split(",") if f.strip()]:
        for meta in _list_box_pdfs_recursive(client, fid):
            current[meta["id"]] = meta

    # 追加/更新/削除の判定
    added = 0
    updated = 0
    deleted = 0

    to_delete_ids: List[str] = []

    # 削除(現行にないファイル)
    for file_id, prev in list(manifest.items()):
        if file_id not in current:
            ids = prev.get("vector_ids", [])
            to_delete_ids.extend(ids)
            manifest.pop(file_id, None)
            deleted += 1

    if to_delete_ids:
        _delete_ids_from_faiss(to_delete_ids)

    # 追加/更新
    vs = load_or_create_index([])
    for file_id, meta in current.items():
        fp = _fingerprint(meta)
        prev = manifest.get(file_id)
        if prev and prev.get("fingerprint") == fp:
            continue  # 変更なし

        # 変更あり → 既存削除（あれば）→ 再取り込み
        if prev and prev.get("vector_ids"):
            try:
                vs.delete(prev["vector_ids"])  # 既存を削除
            except Exception:
                pass

        # ダウンロードして分割
        data = client.file(file_id=file_id).content()
        docs = pdf_bytes_to_documents(meta["name"], data)

        # 安定IDを生成: box:<file_id>:<index>
        ids = [f"box:{file_id}:{d.metadata.get('chunk_index', i)}" for i, d in enumerate(docs)]
        vs.add_documents(docs, ids=ids)
        vs.save_local(settings.vector_dir)

        manifest[file_id] = {"fingerprint": fp, "name": meta["name"], "vector_ids": ids}
        if prev:
            updated += 1
        else:
            added += 1

    _save_manifest(manifest)

    total_vectors = vs.index.ntotal
    return added, updated, deleted, total_vectors


def _get_box_client() -> "Client":
    settings = get_settings()
    if Client is None or CCGAuth is None:
        raise RuntimeError("boxsdk が見つかりません。requirements.txt を確認してください。")
    method = (settings.box_auth_method or "").lower()
    if method == "devtoken":
        if OAuth2 is None:
            raise RuntimeError("boxsdk が見つかりません。requirements.txt を確認してください。")
        if not settings.box_developer_token:
            raise RuntimeError("BOX_DEVELOPER_TOKEN を設定してください（開発トークン）。")
        # Developer Token は短命・更新不可。テスト用途のみ。
        oauth = OAuth2(client_id=settings.box_client_id, client_secret=settings.box_client_secret, access_token=settings.box_developer_token)
        return Client(oauth)
    elif method == "oauth":  # CCG（Server-side OAuth）
        if settings.box_subject_type == "user" and settings.box_subject_id:
            auth = CCGAuth(
                client_id=settings.box_client_id,
                client_secret=settings.box_client_secret,
                user=settings.box_subject_id,
            )
        elif settings.box_subject_type == "enterprise" and settings.box_subject_id:
            auth = CCGAuth(
                client_id=settings.box_client_id,
                client_secret=settings.box_client_secret,
                enterprise_id=settings.box_subject_id,
            )
        else:
            raise RuntimeError("BOX_SUBJECT_TYPE と BOX_SUBJECT_ID を設定してください（user か enterprise）。")
        return Client(auth)
    else:
        raise RuntimeError("BOX_AUTH_METHOD は 'oauth'（CCG）または 'devtoken' をサポートしています。設定を確認してください。")


def _normalize_folder_id(value: str) -> str:
    """様々な入力形式からフォルダID（数値部分）を抽出して正規化する。

    例:
    - 'https://app.box.com/folder/123456' -> '123456'
    - 'd_123456' -> '123456'
    - '123456' -> '123456'
    不明な形式はそのまま返します。
    """
    if not value:
        return value
    m = re.search(r"(\d+)$", str(value))
    return m.group(1) if m else value


def ingest_box_folder(folder_id: str) -> Tuple[int, int]:
    """指定フォルダ直下のPDFを取り込み、ベクタストアに反映する（再帰はしない）。"""
    client = _get_box_client()
    folder_id = _normalize_folder_id(folder_id)
    items = client.folder(folder_id=folder_id).get_items(limit=1000)
    docs: List[Document] = []
    for item in items:
        if getattr(item, "type", "") == "file" and str(item.name).lower().endswith(".pdf"):
            data = client.file(file_id=item.id).content()
            docs.extend(pdf_bytes_to_documents(item.name, data))
    if not docs:
        return (0, load_or_create_index([]).index.ntotal)  # 何も追加なし
    return upsert_documents(docs)


def ingest_box_folders(folder_ids: str) -> Tuple[int, int]:
    total_added = 0
    total_vectors = 0
    for fid in [f.strip() for f in folder_ids.split(",") if f.strip()]:
        added, vectors = ingest_box_folder(_normalize_folder_id(fid))
        total_added += added
        total_vectors = vectors
    return total_added, total_vectors


# =============================
# Box アップロード
# =============================
def upload_files_to_box(folder_id: str, files: List[Tuple[str, bytes]]) -> List[str]:
    """ローカルのファイルバイト列をBoxの指定フォルダにアップロードする。

    Args:
        folder_id: アップロード先のBoxフォルダID
        files: (ファイル名, バイト列) のリスト

    Returns:
        生成されたBoxファイルIDのリスト
    """
    client = _get_box_client()
    folder_id = _normalize_folder_id(folder_id)
    uploaded_ids: List[str] = []
    for name, data in files:
        stream = io.BytesIO(data)
        item = client.folder(folder_id=folder_id).upload_stream(stream, file_name=name)
        uploaded_ids.append(item.id)
    return uploaded_ids


def list_box_items(folder_id: str, limit: int = 500, offset: int = 0) -> List[Dict[str, Any]]:
    """Boxフォルダ直下のアイテム一覧を取得（非再帰）。

    Note: limit/offset はベストエフォート。大量アイテムの場合は繰り返し呼び出して集計してください。
    """
    client = _get_box_client()
    folder_id = _normalize_folder_id(folder_id)
    items = client.folder(folder_id=folder_id).get_items(
        limit=limit,
        offset=offset,
        fields=["id", "type", "name", "modified_at", "size"],
    )
    rows: List[Dict[str, Any]] = []
    for it in items:
        rows.append(
            {
                "id": getattr(it, "id", None),
                "type": getattr(it, "type", None),
                "name": getattr(it, "name", None),
                "modified_at": getattr(it, "modified_at", None),
                "size": getattr(it, "size", None),
            }
        )
    return rows


def list_box_pdfs(folder_id: str, recursive: bool = False, limit: int = 1000, offset: int = 0) -> List[Dict[str, Any]]:
    """PDFファイル一覧を取得。recursive=True で配下を再帰的に列挙。"""
    client = _get_box_client()
    if recursive:
        return _list_box_pdfs_recursive(client, folder_id)
    rows: List[Dict[str, Any]] = []
    folder_id = _normalize_folder_id(folder_id)
    items = client.folder(folder_id=folder_id).get_items(
        limit=limit,
        offset=offset,
        fields=["id", "type", "name", "sha1", "etag", "modified_at", "size"],
    )
    for it in items:
        if getattr(it, "type", "") == "file" and str(getattr(it, "name", "")).lower().endswith(".pdf"):
            rows.append(
                {
                    "id": getattr(it, "id", None),
                    "name": getattr(it, "name", None),
                    "sha1": getattr(it, "sha1", None),
                    "etag": getattr(it, "etag", None),
                    "modified_at": getattr(it, "modified_at", None),
                    "size": getattr(it, "size", None),
                }
            )
    return rows
