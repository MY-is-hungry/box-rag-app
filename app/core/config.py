from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    # Box
    box_folder_ids: str | None
    box_auth_method: str | None
    box_developer_token: str | None

    # OpenAI / Embeddings
    openai_api_key: str | None

    # Vector Store / Retrieval
    vector_dir: str
    top_k: int

    # LangSmith
    langsmith_tracing: str | None
    langsmith_api_key: str | None
    langsmith_project: str | None

    # App
    log_level: str


def _to_int(value: str | None, default: int) -> int:
    try:
        return int(value) if value is not None else default
    except ValueError:
        return default


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load settings from environment (.env supported).

    Notes
    - TOP_K: 取得する関連チャンク数（既定: 5）。値が不正な場合は5にフォールバック。
    - VECTOR_DIR: ベクタインデックス保存先（既定: ./app/stores/box_index_v1）。
    """
    load_dotenv(override=False)

    return Settings(
        # Box
        box_folder_ids=os.getenv("BOX_FOLDER_IDS"),
        box_auth_method=os.getenv("BOX_AUTH_METHOD"),
        box_developer_token=os.getenv("BOX_DEVELOPER_TOKEN"),
        # OpenAI
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        # Vector / Retrieval
        vector_dir=os.getenv("VECTOR_DIR", "./app/stores/box_index_v1"),
        top_k=_to_int(os.getenv("TOP_K"), 5),
        # LangSmith
        langsmith_tracing=os.getenv("LANGSMITH_TRACING"),
        langsmith_api_key=os.getenv("LANGSMITH_API_KEY"),
        langsmith_project=os.getenv("LANGSMITH_PROJECT"),
        # App
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )


__all__ = ["Settings", "get_settings"]
