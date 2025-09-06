from __future__ import annotations

import os
import streamlit as st

from app.core.config import get_settings
from app.core.utils import pdf_bytes_to_documents
from app.core.ingest import upsert_documents, ingest_box_folders, sync_box_folders


st.set_page_config(page_title="データ取り込み・同期", layout="wide")
st.title("データ取り込み・同期")
st.caption("ローカルPDFの追加、Boxからの取り込み/同期を行います。ベクトル化してFAISSに保存します。")

settings = get_settings()

with st.sidebar:
    st.header("設定の概要")
    st.write(f"TOP_K: {settings.top_k}")
    st.write(f"VECTOR保存先: {settings.vector_dir}")
    st.write("LangSmith: " + ("有効" if (os.getenv("LANGSMITH_TRACING") == "true") else "無効"))

st.subheader("ローカルPDFを追加")
st.caption("アップロードしたPDFをチャンク分割し、Bedrock Embeddingsでベクトル化してFAISSへ保存します。画像のみのPDF（スキャン等）はテキスト抽出できない場合があります。")
uploaded = st.file_uploader("PDF を選択（複数可）", type=["pdf"], accept_multiple_files=True)
if uploaded and st.button("追加・更新する"):
    all_docs = []
    per_file = []
    for uf in uploaded:
        data = uf.read()
        docs = pdf_bytes_to_documents(uf.name, data)
        per_file.append((uf.name, len(docs)))
        all_docs.extend(docs)
    if not all_docs:
        st.warning("抽出可能なテキストが見つかりませんでした。スキャンPDFやパスワード保護の可能性があります。各ファイルの抽出結果を確認してください。")
        st.table({"ファイル名": [n for n, _ in per_file], "抽出チャンク数": [c for _, c in per_file]})
    else:
        try:
            added, total = upsert_documents(all_docs)
            st.success(f"完了: 追加 {added} 件 / ベクトル総数 {total}")
            st.caption("ファイル別の抽出チャンク数")
            st.table({"ファイル名": [n for n, _ in per_file], "抽出チャンク数": [c for _, c in per_file]})
        except Exception as e:
            st.error("取り込みに失敗しました。詳細を確認してください。")
            st.exception(e)

st.divider()
st.subheader("Box 取り込み・同期（CCG）")
st.caption("BOX_* を設定してください。対象フォルダは BOX_FOLDER_IDS（カンマ区切り）で指定します。")
col1, col2 = st.columns(2)
with col1:
    if st.button("Boxから追加（直下のみ）"):
        try:
            if not settings.box_folder_ids:
                st.warning("BOX_FOLDER_IDS が未設定です。")
            else:
                added, total = ingest_box_folders(settings.box_folder_ids)
                st.success(f"完了: 追加 {added} 件 / ベクトル総数 {total}")
        except Exception as e:
            st.error("取り込みに失敗しました。環境変数、アプリ承認、権限をご確認ください。")
            st.exception(e)
with col2:
    if st.button("Boxと同期（再帰・追加/更新/削除）"):
        try:
            if not settings.box_folder_ids:
                st.warning("BOX_FOLDER_IDS が未設定です。")
            else:
                a, u, d, total = sync_box_folders(settings.box_folder_ids)
                st.success(f"完了: 追加 {a} / 更新 {u} / 削除 {d} 件 / ベクトル総数 {total}")
        except Exception as e:
            st.error("同期に失敗しました。環境変数、アプリ承認、権限をご確認ください。")
            st.exception(e)

st.info("同期は削除も反映します。ファイル数が多い場合は時間がかかることがあります。")

