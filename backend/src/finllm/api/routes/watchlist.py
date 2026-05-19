"""/v2/watchlist — kullanıcı bazlı watchlist (Telegram DM ve web/mobile için)."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from finllm.api.auth import optional_bearer
from finllm.config.settings import DATA_DIR

router = APIRouter(prefix="/v2/watchlist", tags=["watchlist"])

_WATCHLIST_FILE = DATA_DIR / "telegram_watchlists.json"


class WatchlistItem(BaseModel):
    ticker: str


def _load() -> dict[str, list[str]]:
    if not _WATCHLIST_FILE.exists():
        return {}
    try:
        return json.loads(_WATCHLIST_FILE.read_text())
    except Exception:
        return {}


def _save(data: dict[str, list[str]]) -> None:
    _WATCHLIST_FILE.parent.mkdir(parents=True, exist_ok=True)
    _WATCHLIST_FILE.write_text(json.dumps(data, indent=2))


@router.get("/{user_id}")
def get_watchlist(user_id: str, _=Depends(optional_bearer)) -> dict:
    data = _load()
    return {"user_id": user_id, "tickers": data.get(user_id, [])}


@router.post("/{user_id}/add")
def add_to_watchlist(user_id: str, item: WatchlistItem, _=Depends(optional_bearer)) -> dict:
    data = _load()
    ticker = item.ticker.upper()
    user_list = data.get(user_id, [])
    if ticker not in user_list:
        user_list.append(ticker)
        data[user_id] = user_list
        _save(data)
    return {"user_id": user_id, "tickers": user_list, "added": ticker}


@router.post("/{user_id}/remove")
def remove_from_watchlist(user_id: str, item: WatchlistItem, _=Depends(optional_bearer)) -> dict:
    data = _load()
    ticker = item.ticker.upper()
    user_list = data.get(user_id, [])
    if ticker in user_list:
        user_list.remove(ticker)
        data[user_id] = user_list
        _save(data)
    return {"user_id": user_id, "tickers": user_list, "removed": ticker}
