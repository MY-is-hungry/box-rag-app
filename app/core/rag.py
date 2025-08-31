from __future__ import annotations

from typing import Dict, List

from langchain_community.vectorstores import FAISS
from langchain_aws import ChatBedrock
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

from .config import get_settings
from .ingest import build_embeddings


def get_retriever():
    settings = get_settings()
    vs = FAISS.load_local(settings.vector_dir, build_embeddings(), allow_dangerous_deserialization=True)
    return vs.as_retriever(search_kwargs={"k": settings.top_k})


def format_docs(docs):
    parts = []
    for d in docs:
        src = d.metadata.get("source")
        page = d.metadata.get("page")
        parts.append(f"[source:{src} page:{page}]\n{d.page_content}")
    return "\n\n".join(parts)


def build_llm():
    settings = get_settings()
    if settings.llm_provider != "bedrock":
        raise RuntimeError("LLM は Bedrock のみをサポートしています。LLM_PROVIDER=bedrock を設定してください。")
    if not settings.aws_region:
        raise RuntimeError("AWS_REGION を設定してください（Bedrock LLM）")
    return ChatBedrock(model=settings.llm_model, region_name=settings.aws_region, temperature=0)


def build_chain():
    settings = get_settings()
    llm = build_llm()

    system_path = "app/prompts/system_ja.md"
    answer_path = "app/prompts/answer_ja.md"
    with open(system_path, "r", encoding="utf-8") as f:
        system_text = f.read()
    with open(answer_path, "r", encoding="utf-8") as f:
        answer_text = f.read()

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_text),
            ("human", "質問: {question}\n\nコンテキスト:\n{context}\n\n出力要件:\n" + answer_text),
        ]
    )

    retriever = get_retriever()
    chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    return chain
