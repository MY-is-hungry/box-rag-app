from __future__ import annotations

import math
from datetime import datetime

import streamlit as st

from app.core.config import get_settings
from app.core.ingest import upload_files_to_box, list_box_items, list_box_pdfs


def _default_folder_id() -> str:
    settings = get_settings()
    raw = settings.box_folder_ids or ""
    return next((p.strip() for p in raw.split(",") if p.strip()), "")


def _fmt_size(n: int | None) -> str:
    if not n:
        return "-"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if n < 1024:
            return f"{n:.0f} {unit}"
        n = n / 1024
    return f"{n:.0f} PB"


def _fmt_time(s: str | None) -> str:
    if not s:
        return "-"
    try:
        # BoxはISO8601形式
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return s


st.set_page_config(page_title="Box管理", layout="wide")
st.title("Box 管理")
st.caption("Boxフォルダの内容を確認し、PDFをアップロードできます。検索への反映は『インデックス管理』ページで実行してください。")

# フォルダIDをセッションに保持
if "box_folder_id" not in st.session_state:
    st.session_state.box_folder_id = _default_folder_id()

with st.container():
    col1, col2, col3 = st.columns([3, 1, 1])
    fid = col1.text_input("対象フォルダID", value=st.session_state.box_folder_id, placeholder="例: 123456789 / https://app.box.com/folder/123456789 / d_123456789")
    if col2.button("移動"):
        st.session_state.box_folder_id = fid.strip()
        st.rerun()
    reload_clicked = col3.button("再読み込み")

tabs = st.tabs(["内容一覧", "PDF一覧", "アップロード"])

with tabs[0]:
    st.subheader("フォルダ内容")
    page_size = st.selectbox("表示件数", [25, 50, 100, 200], index=1)
    name_filter = st.text_input("名前でフィルタ", value="")
    type_filter = st.selectbox("種別", ["すべて", "フォルダ", "ファイル"], index=0)

    try:
        rows = list_box_items(st.session_state.box_folder_id, limit=1000)
    except Exception as e:
        st.error("一覧の取得に失敗しました。環境変数とアプリ承認、権限をご確認ください。")
        st.exception(e)
        rows = []

    # サマリ
    total = len(rows)
    folders = sum(1 for r in rows if r.get("type") == "folder")
    files = total - folders
    pdfs = sum(1 for r in rows if str(r.get("name", "")).lower().endswith(".pdf"))
    st.caption(f"件数: 合計 {total}（フォルダ {folders} / ファイル {files} / PDF {pdfs}）")

    # フィルタ
    if name_filter:
        rows = [r for r in rows if name_filter.lower() in str(r.get("name", "")).lower()]
    if type_filter == "フォルダ":
        rows = [r for r in rows if r.get("type") == "folder"]
    elif type_filter == "ファイル":
        rows = [r for r in rows if r.get("type") == "file"]

    # 整形
    view = [
        {
            "ID": r.get("id"),
            "種別": r.get("type"),
            "名前": r.get("name"),
            "更新日時": _fmt_time(r.get("modified_at")),
            "サイズ": _fmt_size(r.get("size")),
        }
        for r in rows
    ]

    # ページング（ローカルスライス）
    pages = max(1, math.ceil(len(view) / page_size))
    if "box_page" not in st.session_state:
        st.session_state.box_page = 1
    colp1, colp2, colp3 = st.columns([1, 2, 1])
    if colp1.button("前へ", disabled=st.session_state.box_page <= 1):
        st.session_state.box_page -= 1
    colp2.markdown(f"ページ {st.session_state.box_page} / {pages}")
    if colp3.button("次へ", disabled=st.session_state.box_page >= pages):
        st.session_state.box_page += 1

    start = (st.session_state.box_page - 1) * page_size
    end = start + page_size
    st.dataframe(view[start:end], use_container_width=True, hide_index=True)

    # サブフォルダへ移動
    subfolders = [r for r in rows if r.get("type") == "folder"]
    if subfolders:
        choices = {f"{sf.get('name')} ({sf.get('id')})": sf.get("id") for sf in subfolders}
        sel = st.selectbox("サブフォルダに移動", list(choices.keys()))
        if st.button("移動する"):
            st.session_state.box_folder_id = choices[sel]
            st.rerun()

with tabs[1]:
    st.subheader("PDF一覧")
    recursive = st.checkbox("配下を再帰的に検索", value=False)
    name_filter2 = st.text_input("名前でフィルタ（PDF）", value="")
    try:
        pdfrows = list_box_pdfs(st.session_state.box_folder_id, recursive=recursive)
    except Exception as e:
        st.error("PDF一覧の取得に失敗しました。環境変数とアプリ承認、権限をご確認ください。")
        st.exception(e)
        pdfrows = []

    if name_filter2:
        pdfrows = [r for r in pdfrows if name_filter2.lower() in str(r.get("name", "")).lower()]

    pdfview = [
        {
            "ID": r.get("id"),
            "名前": r.get("name"),
            "更新日時": _fmt_time(r.get("modified_at")),
            "サイズ": _fmt_size(r.get("size")),
        }
        for r in pdfrows
    ]
    st.dataframe(pdfview, use_container_width=True, hide_index=True)

with tabs[2]:
    st.subheader("PDFをアップロード")
    st.caption("アップロード後、検索に反映するには『インデックス管理』ページで取り込み/同期を実行してください。")
    files = st.file_uploader("PDF を選択（複数可）", type=["pdf"], accept_multiple_files=True)
    if st.button("アップロード実行"):
        if not st.session_state.box_folder_id:
            st.warning("フォルダIDを入力してください。")
        elif not files:
            st.warning("ファイルを選択してください。")
        else:
            try:
                payload = [(f.name, f.read()) for f in files]
                progress = st.progress(0, text="アップロード中…")
                # 単純進捗（ベストエフォート）
                uploaded_ids = []
                total = len(payload)
                for i, item in enumerate(payload, start=1):
                    ids = upload_files_to_box(st.session_state.box_folder_id, [item])
                    uploaded_ids.extend(ids)
                    progress.progress(int(i / total * 100))
                progress.empty()
                st.success(f"アップロードが完了しました（{len(uploaded_ids)} 件）。")
                st.caption("ファイルID:")
                st.write(uploaded_ids)
            except Exception as e:
                st.error("アップロードに失敗しました。環境変数とアプリ承認、権限をご確認ください。")
                st.exception(e)
