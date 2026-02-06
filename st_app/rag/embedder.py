from __future__ import annotations

import json
from pathlib import Path
from typing import List
import os

import pandas as pd
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_upstage import UpstageEmbeddings
from langchain_community.vectorstores import FAISS

# .env 파일 로드
load_dotenv()

# 경로 수정 부분
# __file__은 st_app/rag/embedder.py이다.
# parents[0]은 st_app/rag/ 이다.
# parents[1]은 st_app/ 이다.
BASE_DIR = Path(__file__).resolve().parents[1] 

# BASE_DIR이 이미 st_app이므로 바로 db를 연결한다.
DB_DIR = BASE_DIR / "db"
REVIEWS_CSV = DB_DIR / "reviews.csv"
INDEX_DIR = DB_DIR / "faiss_index"


def load_reviews(csv_path: Path) -> List[Document]:
    if not csv_path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없다: {csv_path}")

    df = pd.read_csv(csv_path)
    required_cols = {"title", "source", "text"}
    if not required_cols.issubset(df.columns):
        raise ValueError(f"reviews.csv에는 {required_cols} 컬럼이 포함되어야 한다.")

    docs: List[Document] = []
    for i, row in df.iterrows():
        text = str(row["text"]).strip()
        if not text:
            continue
        docs.append(
            Document(
                page_content=text,
                metadata={
                    "row_id": int(i),
                    "title": str(row["title"]),
                    "source": str(row["source"]),
                },
            )
        )
    return docs


def build_index(docs: List[Document], chunk_size: int = 700, chunk_overlap: int = 80) -> None:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "。", ".", "!", "?", " ", ""],
    )
    chunks = splitter.split_documents(docs)
    if not chunks:
        raise ValueError("분할된 텍스트가 없다.")

    embeddings = UpstageEmbeddings(model="solar-embedding-1-large")
    vectordb = FAISS.from_documents(chunks, embeddings)

    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    vectordb.save_local(str(INDEX_DIR))

    meta = {
        "source_csv": str(REVIEWS_CSV),
        "num_docs": len(docs),
        "num_chunks": len(chunks),
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
    }
    with open(INDEX_DIR / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    print("--- 인덱스 구축 시작 ---")
    try:
        docs = load_reviews(REVIEWS_CSV)
        build_index(docs)
        print(f"[성공] FAISS 인덱스가 생성되었다: {INDEX_DIR}")
    except Exception as e:
        print(f"[오류] 생성 실패: {e}")