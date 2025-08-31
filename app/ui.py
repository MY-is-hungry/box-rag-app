from __future__ import annotations

import io
import os

import streamlit as st

from app.core.config import get_settings
from app.core.utils import pdf_bytes_to_documents
from app.core.ingest import upsert_documents, ingest_box_folders
from app.core.rag import build_chain


st.set_page_config(page_title="Box RAG PoC", layout="wide")
settings = get_settings()

st.title("Box RAG PoC")
st.caption("質問に日本語で回答し、参照を付与します。TOP_Kは環境変数で変更可能です。")

with st.sidebar:
    st.header("設定")
    st.write(f"TOP_K: {settings.top_k}")
    st.write(f"VECTOR_DIR: {settings.vector_dir}")
    st.write("LangSmith: " + ("有効" if (os.getenv("LANGSMITH_TRACING") == "true") else "無効"))

    st.divider()
    st.subheader("インデックス取り込み（ローカルPDF）")
    uploaded = st.file_uploader("PDF を選択", type=["pdf"], accept_multiple_files=True)
    if uploaded and st.button("取り込み/更新"):
        all_docs = []
        for uf in uploaded:
            data = uf.read()
            docs = pdf_bytes_to_documents(uf.name, data)
            all_docs.extend(docs)
        added, total = upsert_documents(all_docs)
        st.success(f"取り込み完了: 追加 {added} 件 / 総ベクトル {total}")

    st.divider()
    st.subheader("インデックス取り込み（Box CCG）")
    st.caption("BOX_CLIENT_ID/SECRET と BOX_SUBJECT_TYPE/ID を設定してください。フォルダは BOX_FOLDER_IDS で指定。")
    if st.button("Boxから取り込み"):
        try:
            if not settings.box_folder_ids:
                st.warning("BOX_FOLDER_IDS が未設定です。")
            else:
                added, total = ingest_box_folders(settings.box_folder_ids)
                st.success(f"Box取り込み完了: 追加 {added} 件 / 総ベクトル {total}")
        except Exception as e:
            st.error("Box取り込みに失敗しました。環境変数とアプリ承認、権限を確認してください。")
            st.exception(e)


st.subheader("質問")
q = st.text_input("質問を入力（日本語）")
if st.button("実行") and q.strip():
    try:
        chain = build_chain()
        with st.spinner("検索・生成中..."):
            answer = chain.invoke(q)
        st.markdown("### 回答")
        st.write(answer)
    except Exception as e:
        st.error("エラーが発生しました。インデックス作成やAPIキー設定を確認してください。")
        st.exception(e)
