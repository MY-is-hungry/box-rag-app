from __future__ import annotations

from typing import Iterable, List, Tuple

from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_aws import BedrockEmbeddings
from langchain_core.documents import Document

from .config import get_settings
from .utils import ensure_dir, pdf_bytes_to_documents

try:
    from boxsdk import Client
    from boxsdk.auth.ccg_auth import CCGAuth
except Exception:  # pragma: no cover - optional import until Box接続時に使用
    Client = None  # type: ignore
    CCGAuth = None  # type: ignore


def build_embeddings():
    settings = get_settings()
    if settings.embeddings_provider == "bedrock":
        if not settings.aws_region:
            raise RuntimeError("AWS_REGION を設定してください（Bedrock Embeddings）")
        return BedrockEmbeddings(
            model_id=settings.embeddings_model,
            region_name=settings.aws_region,
        )
    # fallback: OpenAI
    return OpenAIEmbeddings(model=settings.embeddings_model or "text-embedding-3-small", api_key=settings.openai_api_key)


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
            raise ValueError("ドキュメントが空です。初期インデックス作成にはドキュメントが必要です。")
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


def _get_box_client() -> "Client":
    settings = get_settings()
    if settings.box_auth_method != "oauth":
        raise RuntimeError("BOX_AUTH_METHOD=oauth が必要です（CCG）")
    if Client is None or CCGAuth is None:
        raise RuntimeError("boxsdk が見つかりません。requirements.txt を確認してください。")

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
        raise RuntimeError(
            "BOX_SUBJECT_TYPE と BOX_SUBJECT_ID を設定してください（user か enterprise）。"
        )
    return Client(auth)


def ingest_box_folder(folder_id: str) -> Tuple[int, int]:
    """指定フォルダ直下のPDFを取り込み、ベクタストアに反映する（再帰はしない）。"""
    client = _get_box_client()
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
        added, vectors = ingest_box_folder(fid)
        total_added += added
        total_vectors = vectors
    return total_added, total_vectors
