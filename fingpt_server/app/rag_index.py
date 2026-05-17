"""SEC filings (10-K, 10-Q) RAG index — FAISS + sentence-transformers.

İlk versiyon: basit query → top-K chunks.
build_index() bir kez çalıştırılır (yeni filings için periyodik).
"""
from __future__ import annotations

from pathlib import Path

from loguru import logger

from app.config import settings


def _index_path(symbol: str) -> Path:
    p = Path(settings.rag_index_dir) / symbol.upper()
    p.mkdir(parents=True, exist_ok=True)
    return p


def build_index(symbol: str, limit: int = 4) -> dict:
    """SEC EDGAR'dan son 10-K/10-Q'ları indir, parçala, embed et, FAISS'a kaydet."""
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from langchain_community.vectorstores import FAISS
    from sec_edgar_downloader import Downloader

    out_dir = _index_path(symbol)
    raw_dir = out_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    dl = Downloader("FinLLM", "you@example.com", str(raw_dir))
    dl.get("10-K", symbol, limit=limit, download_details=True)
    dl.get("10-Q", symbol, limit=limit, download_details=True)

    docs: list[str] = []
    metadatas: list[dict] = []
    for f in raw_dir.rglob("*.txt"):
        try:
            txt = f.read_text(errors="ignore")[:200_000]   # capped, full doc çok uzun
            docs.append(txt)
            metadatas.append({"path": str(f), "symbol": symbol})
        except Exception as e:
            logger.warning(f"skip {f}: {e}")

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    chunks = []
    chunk_meta = []
    for doc, meta in zip(docs, metadatas):
        for i, chunk in enumerate(splitter.split_text(doc)):
            chunks.append(chunk)
            chunk_meta.append({**meta, "chunk": i})

    if not chunks:
        return {"symbol": symbol, "chunks": 0, "status": "no_filings"}

    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vs = FAISS.from_texts(chunks, embeddings, metadatas=chunk_meta)
    vs.save_local(str(out_dir / "faiss"))
    return {"symbol": symbol, "chunks": len(chunks), "status": "ok"}


def query(symbol: str, q: str, top_k: int = 5) -> list[dict]:
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from langchain_community.vectorstores import FAISS

    out_dir = _index_path(symbol) / "faiss"
    if not out_dir.exists():
        return []
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vs = FAISS.load_local(str(out_dir), embeddings, allow_dangerous_deserialization=True)
    hits = vs.similarity_search_with_score(q, k=top_k)
    return [
        {"text": h.page_content[:800], "score": float(score), "metadata": h.metadata}
        for h, score in hits
    ]
