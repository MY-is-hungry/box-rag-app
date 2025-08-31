from __future__ import annotations

from typing import Iterable, List, Tuple

from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document

from .config import get_settings
from .utils import ensure_dir


def build_embeddings() -> OpenAIEmbeddings:
    settings = get_settings()
    return OpenAIEmbeddings(model="text-embedding-3-small", api_key=settings.openai_api_key)


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
