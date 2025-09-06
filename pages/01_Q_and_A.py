from __future__ import annotations

import streamlit as st

from app.core.rag import build_chain


st.set_page_config(page_title="Q&A", layout="wide")
st.title("Q&A")
st.caption("インデックス化済みの資料をもとに日本語で回答し、根拠も提示します。インデックスの作成・同期は左の『データ取り込み・同期』ページから実行できます。")

st.subheader("質問")
q = st.text_input("質問（日本語）", placeholder="例: 経費精算の締め切りはいつですか？")
if st.button("回答する") and q.strip():
    try:
        chain = build_chain()
        with st.spinner("検索と回答を生成中…"):
            answer = chain.invoke(q)
        st.markdown("### 回答")
        st.write(answer)
    except Exception as e:
        st.error(
            "エラーが発生しました。まず『データ取り込み・同期』ページでインデックスを作成し、環境変数（AWS/Box など）をご確認ください。"
        )
        st.exception(e)

