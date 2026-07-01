"""Analiz Defteri — hisse not + fiyat takip endpoint'leri.

Veriler backend/data/notebook/entries.json dosyasinda saklanir.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from finllm.config.settings import DATA_DIR

router = APIRouter(prefix="/v2/notebook", tags=["notebook"])

_NOTEBOOK_DIR = DATA_DIR / "notebook"
_ENTRIES_FILE = _NOTEBOOK_DIR / "entries.json"


def _load() -> list[dict]:
    _NOTEBOOK_DIR.mkdir(parents=True, exist_ok=True)
    if not _ENTRIES_FILE.exists():
        return []
    try:
        return json.loads(_ENTRIES_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(entries: list[dict]) -> None:
    _NOTEBOOK_DIR.mkdir(parents=True, exist_ok=True)
    _ENTRIES_FILE.write_text(
        json.dumps(entries, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


@router.get("/entries")
def get_entries() -> list[dict]:
    return _load()


class AddEntryRequest(BaseModel):
    id: str
    ticker: str
    note: str = ""
    entryPrice: float
    entryDate: str
    currentPrice: float | None = None
    currentDate: str | None = None
    addedAt: str


@router.post("/entries")
def add_entry(req: AddEntryRequest) -> dict:
    entries = _load()
    entries.insert(0, req.model_dump())
    _save(entries)
    return {"status": "ok"}


class UpdateNoteRequest(BaseModel):
    note: str


@router.put("/entries/{entry_id}/note")
def update_note(entry_id: str, req: UpdateNoteRequest) -> dict:
    entries = _load()
    for e in entries:
        if e["id"] == entry_id:
            e["note"] = req.note
            break
    _save(entries)
    return {"status": "ok"}


class UpdatePricesRequest(BaseModel):
    prices: dict[str, Any]  # {entry_id: {currentPrice, currentDate}}


@router.put("/entries/prices")
def update_prices(req: UpdatePricesRequest) -> dict:
    entries = _load()
    for e in entries:
        if e["id"] in req.prices:
            p = req.prices[e["id"]]
            e["currentPrice"] = p.get("currentPrice")
            e["currentDate"] = p.get("currentDate")
    _save(entries)
    return {"status": "ok"}


@router.delete("/entries/{entry_id}")
def delete_entry(entry_id: str) -> dict:
    entries = _load()
    entries = [e for e in entries if e["id"] != entry_id]
    _save(entries)
    return {"status": "ok"}
