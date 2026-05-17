"""FinGPT FastAPI sunucusu — AWS EC2'de çalışır.

Çalıştır:
    uvicorn app.main:app --host 0.0.0.0 --port 8080

Endpoint'ler:
    GET  /health
    POST /sentiment          {texts: [...]}
    POST /forecast           {symbol, company, priceRecap, newsBlock, financials}
    POST /rag/build          {symbol}
    POST /rag/query          {symbol, q, topK}
"""
from __future__ import annotations

from fastapi import Depends, FastAPI, Header, HTTPException
from loguru import logger
from pydantic import BaseModel

from app.config import settings

app = FastAPI(title="FinGPT Server", version="0.1.0")


def _auth(authorization: str | None = Header(default=None)):
    if not settings.fingpt_api_key:
        return  # Auth devre dışı
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing bearer token")
    token = authorization.split(" ", 1)[1]
    if token != settings.fingpt_api_key:
        raise HTTPException(403, "Bad token")


@app.get("/health")
def health():
    import torch
    return {
        "ok": True,
        "device": settings.device,
        "cuda_available": torch.cuda.is_available(),
        "cuda_device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
    }


# --- Sentiment ---

class SentimentReq(BaseModel):
    texts: list[str]


@app.post("/sentiment", dependencies=[Depends(_auth)])
def sentiment(req: SentimentReq):
    from app.sentiment import score_batch
    return {"results": score_batch(req.texts)}


# --- Forecaster ---

class ForecastReq(BaseModel):
    symbol: str
    company: str
    priceRecap: str
    newsBlock: str
    financials: str | None = None


@app.post("/forecast", dependencies=[Depends(_auth)])
def forecast(req: ForecastReq):
    from app.forecaster import forecast as do_forecast
    return do_forecast(
        symbol=req.symbol,
        company=req.company,
        price_recap=req.priceRecap,
        news_block=req.newsBlock,
        financials=req.financials or "",
    )


# --- RAG ---

class RagBuildReq(BaseModel):
    symbol: str
    limit: int = 4


class RagQueryReq(BaseModel):
    symbol: str
    q: str
    topK: int = 5


@app.post("/rag/build", dependencies=[Depends(_auth)])
def rag_build(req: RagBuildReq):
    from app.rag_index import build_index
    return build_index(req.symbol, limit=req.limit)


@app.post("/rag/query", dependencies=[Depends(_auth)])
def rag_query(req: RagQueryReq):
    from app.rag_index import query
    return {"hits": query(req.symbol, req.q, top_k=req.topK)}
