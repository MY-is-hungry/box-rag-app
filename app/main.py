from __future__ import annotations

from pathlib import Path

import streamlit as st

from app.core.config import get_settings


def _vector_count() -> int | None:
    try:
        from langchain_community.vectorstores import FAISS
        from app.core.ingest import build_embeddings
    except Exception:
        return None

    settings = get_settings()
    try:
        vs = FAISS.load_local(settings.vector_dir, build_embeddings(), allow_dangerous_deserialization=True)
        return int(getattr(vs.index, "ntotal", 0))
    except Exception:
        return None


def _manifest_info() -> tuple[int | None, str | None]:
    settings = get_settings()
    p = Path(settings.vector_dir) / "box_manifest.json"
    if not p.exists():
        return (None, None)
    try:
        import json, datetime

        data = json.loads(p.read_text(encoding="utf-8"))
        file_count = len(data)
        ts = datetime.datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        return (file_count, ts)
    except Exception:
        return (None, None)


def main() -> None:
    st.set_page_config(page_title="ダッシュボード", layout="wide")

    st.title("ダッシュボード")
    st.caption("アプリの状況と設定の概要を表示します。Q&Aや取り込み/同期は左のページから実行できます。")

    settings = get_settings()

    col1, col2, col3 = st.columns(3)
    with col1:
        vc = _vector_count()
        st.metric("ベクトル総数", f"{vc:,}" if vc is not None else "未作成")
    with col2:
        st.metric("TOP_K (検索件数)", settings.top_k)
    with col3:
        mf_count, mf_ts = _manifest_info()
        mf_label = "-" if mf_count is None else f"{mf_count} files"
        st.metric("Box同期マニフェスト", mf_label, help=f"最終更新: {mf_ts or '-'}")

    st.divider()
    st.subheader("設定の概要")
    st.write(
        "\n".join(
            [
                f"VECTOR保存先: {settings.vector_dir}",
                f"Embeddings/LLM: Bedrock（リージョン: {settings.aws_region or '-'}）",
                f"BoxフォルダID: {settings.box_folder_ids or '-'}",
                f"Box認証方式: {settings.box_auth_method or '-'}",
                f"LangSmith: " + ("有効" if (settings.langsmith_tracing == "true") else "無効"),
            ]
        )
    )

    st.info("Q&A はサイドバーの『Q&A』ページ、取り込み/同期は『データ取り込み・同期』ページから実行してください。")


if __name__ == "__main__":
    main()
