"""Commodities — gold (USD & gram-TRY), silver, USD/TRY (Faz E).

Free via yfinance. Gold matters to this system in two currencies: USD (GC=F) and
the Turkish 'gram altın' = gold_usd/oz ÷ 31.1035 × USD/TRY. The macro layer already
emits a Precious Metals appetite; this surfaces the actual instruments + prices so
gold is visible and tradeable in the UI, not just an abstract sector score.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from finllm.data.prices import fetch_prices
from finllm.utils.logging import logger

TROY_OZ_GRAMS = 31.1035

_TICKERS = {
    "gold_usd": "GC=F",     # gold futures, USD/oz
    "silver_usd": "SI=F",   # silver futures, USD/oz
    "usdtry": "USDTRY=X",
}


@dataclass(slots=True)
class Instrument:
    key: str
    label: str
    price: float
    unit: str
    change_5d_pct: float | None = None
    change_20d_pct: float | None = None


@dataclass(slots=True)
class Commodities:
    as_of: str
    instruments: list[Instrument] = field(default_factory=list)

    def get(self, key: str) -> Instrument | None:
        return next((i for i in self.instruments if i.key == key), None)

    def as_dict(self) -> dict:
        return {
            "as_of": self.as_of,
            "instruments": [
                {"key": i.key, "label": i.label, "price": round(i.price, 2), "unit": i.unit,
                 "change_5d_pct": (round(i.change_5d_pct, 2) if i.change_5d_pct is not None else None),
                 "change_20d_pct": (round(i.change_20d_pct, 2) if i.change_20d_pct is not None else None)}
                for i in self.instruments
            ],
        }


def _series(ticker: str, as_of: str | None):
    end = as_of or datetime.utcnow().strftime("%Y-%m-%d")
    start = (datetime.strptime(end, "%Y-%m-%d") - timedelta(days=60)).strftime("%Y-%m-%d")
    try:
        df = fetch_prices(ticker, start=start, end=end, use_cache=True)
        return df if not df.empty else None
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[COMMODITIES] {ticker} failed: {e}")
        return None


def _chg(closes, n: int) -> float | None:
    if len(closes) < n + 1:
        return None
    prev = float(closes.iloc[-(n + 1)])
    return (float(closes.iloc[-1]) / prev - 1) * 100 if prev else None


def fetch_commodities(as_of: str | None = None) -> Commodities:
    """Gold (USD + gram-TRY), silver, USD/TRY with recent changes."""
    raw = {k: _series(t, as_of) for k, t in _TICKERS.items()}
    out = Commodities(as_of=as_of or datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))

    def add(key, label, df, unit):
        if df is None or df.empty:
            return None
        c = df["close"].dropna()
        last = float(c.iloc[-1])
        out.instruments.append(Instrument(key, label, last, unit, _chg(c, 5), _chg(c, 20)))
        return last

    gold = add("gold_usd", "Altın", raw["gold_usd"], "USD/ons")
    add("silver_usd", "Gümüş", raw["silver_usd"], "USD/ons")
    usdtry_df = raw["usdtry"]
    usdtry = add("usdtry", "USD/TRY", usdtry_df, "₺")

    # Derived: gram altın (TRY)
    if gold is not None and usdtry is not None:
        gram = gold / TROY_OZ_GRAMS * usdtry
        gc = raw["gold_usd"]["close"].dropna()
        tc = usdtry_df["close"].dropna()
        g5 = (_chg(gc, 5) or 0) + (_chg(tc, 5) or 0) if len(gc) > 5 and len(tc) > 5 else None
        g20 = (_chg(gc, 20) or 0) + (_chg(tc, 20) or 0) if len(gc) > 20 and len(tc) > 20 else None
        out.instruments.insert(1, Instrument("gold_try_gram", "Gram Altın", gram, "₺/gram", g5, g20))
    return out


__all__ = ["Commodities", "Instrument", "fetch_commodities"]
