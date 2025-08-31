from __future__ import annotations

import io
import os
from typing import Iterable, List

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def pdf_bytes_to_documents(name: str, data: bytes) -> List[Document]:
    try:
        from pypdf import PdfReader
    except Exception as e:
        raise RuntimeError("pypdf の読み込みに失敗しました。requirements.txt を確認してください。") from e

    reader = PdfReader(io.BytesIO(data))
    docs: List[Document] = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if not text.strip():
            continue
        docs.append(
            Document(
                page_content=text,
                metadata={
                    "source": name,
                    "page": i,
                },
            )
        )

    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=200)
    chunks = splitter.split_documents(docs)
    # 追加メタ
    for idx, d in enumerate(chunks):
        d.metadata.setdefault("chunk_index", idx)
    return chunks
