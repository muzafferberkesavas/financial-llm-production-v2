"""Point-in-time fundamentals from Finnhub financials-reported (look-ahead-safe).

Faz A taught us never to backtest with current fundamentals. Finnhub's
financials-reported (ANNUAL / 10-K) returns historical statements WITH a
`filedDate`, so for a backtest as-of date D we use only the latest 10-K filed
on/before D. Annual (not quarterly) is used deliberately: quarterly `ic` values
are YTD-cumulative for many filers, which corrupts TTM sums (ROE 327%, rev growth
98%); full-year figures are unambiguous and reliable. Combined with point-in-time
price (yfinance end=D) this yields a look-ahead-safe FundamentalSnapshot.

Tradeoff: fundamentals update yearly → up to ~12-15 months stale mid-year. That is
acceptable and conservative for a robustness backtest. us-gaap tags vary by filer,
so each metric tries several variants and degrades to None if absent.

Limits (free tier): earnings-surprise + analyst history are NOT available far back
→ those overlays are live-only; the backtest measures the fundamental RATIO ranking.
"""
from __future__ import annotations

import httpx

from finllm.config.settings import settings
from finllm.data.prices import fetch_prices
from finllm.markets.base import FundamentalSnapshot, Ticker
from finllm.utils.logging import logger

_BASE = "https://finnhub.io/api/v1"

_CONCEPTS = {
    "revenue": ["us-gaap_RevenueFromContractWithCustomerExcludingAssessedTax",
                "us-gaap_Revenues", "us-gaap_RevenueFromContractWithCustomerIncludingAssessedTax",
                "us-gaap_SalesRevenueNet"],
    "net_income": ["us-gaap_NetIncomeLoss", "us-gaap_ProfitLoss"],
    "equity": ["us-gaap_StockholdersEquity",
               "us-gaap_StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
    "eps_diluted": ["us-gaap_EarningsPerShareDiluted", "us-gaap_EarningsPerShareBasicAndDiluted"],
    "total_debt": ["us-gaap_LongTermDebtNoncurrent", "us-gaap_LongTermDebt"],
    "current_assets": ["us-gaap_AssetsCurrent"],
    "current_liabilities": ["us-gaap_LiabilitiesCurrent"],
    "op_cash_flow": ["us-gaap_NetCashProvidedByUsedInOperatingActivities"],
    "capex": ["us-gaap_PaymentsToAcquirePropertyPlantAndEquipment"],
    "shares": ["us-gaap_WeightedAverageNumberOfDilutedSharesOutstanding",
               "us-gaap_WeightedAverageNumberOfSharesOutstandingBasic"],
}

_CACHE: dict[str, list] = {}  # symbol → annual reports (process-lifetime)


def _val(items: list, concepts: list[str]) -> float | None:
    by_concept = {it.get("concept"): it.get("value") for it in items}
    for c in concepts:
        v = by_concept.get(c)
        if isinstance(v, (int, float)):
            return float(v)
    return None


def _annual_reports(symbol: str) -> list[dict]:
    if symbol in _CACHE:
        return _CACHE[symbol]
    key = settings.finnhub_api_key
    if not key:
        return []
    try:
        r = httpx.get(f"{_BASE}/stock/financials-reported?symbol={symbol}&freq=annual&token={key}", timeout=25)
        r.raise_for_status()
        data = r.json().get("data", [])
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[FINNHUB-PIT] {symbol} failed: {e}")
        data = []
    _CACHE[symbol] = data
    return data


def _metrics(report: dict) -> dict:
    rep = report.get("report", {})
    ic, bs, cf = rep.get("ic", []), rep.get("bs", []), rep.get("cf", [])
    return {
        "revenue": _val(ic, _CONCEPTS["revenue"]),
        "net_income": _val(ic, _CONCEPTS["net_income"]),
        "eps": _val(ic, _CONCEPTS["eps_diluted"]),
        "shares": _val(ic, _CONCEPTS["shares"]),
        "equity": _val(bs, _CONCEPTS["equity"]),
        "debt": _val(bs, _CONCEPTS["total_debt"]),
        "cur_assets": _val(bs, _CONCEPTS["current_assets"]),
        "cur_liab": _val(bs, _CONCEPTS["current_liabilities"]),
        "ocf": _val(cf, _CONCEPTS["op_cash_flow"]),
        "capex": _val(cf, _CONCEPTS["capex"]),
    }


def fetch_pit_fundamentals(ticker: Ticker, symbol: str, as_of: str) -> FundamentalSnapshot | None:
    """Look-ahead-safe snapshot as-of `as_of` (YYYY-MM-DD): latest 10-K filed
    on/before that date, priced at that date."""
    reports = _annual_reports(symbol)
    avail = [r for r in reports if (r.get("filedDate", "")[:10] or "9999") <= as_of]
    if not avail:
        return None
    avail.sort(key=lambda r: r.get("filedDate", ""), reverse=True)
    cur = _metrics(avail[0])
    prior = _metrics(avail[1]) if len(avail) >= 2 else {}

    roe = (cur["net_income"] / cur["equity"]) if (cur.get("net_income") and cur.get("equity")) else None
    margin = (cur["net_income"] / cur["revenue"]) if (cur.get("net_income") and cur.get("revenue")) else None
    de = (cur["debt"] / cur["equity"] * 100) if (cur.get("debt") and cur.get("equity")) else None
    current_ratio = (cur["cur_assets"] / cur["cur_liab"]) if (cur.get("cur_assets") and cur.get("cur_liab")) else None
    fcf = (cur["ocf"] - abs(cur["capex"])) if (cur.get("ocf") is not None and cur.get("capex") is not None) else None

    rev_growth = ni_growth = None
    if prior.get("revenue") and cur.get("revenue"):
        rev_growth = cur["revenue"] / prior["revenue"] - 1
    if prior.get("net_income") and cur.get("net_income") and prior["net_income"] > 0:
        ni_growth = cur["net_income"] / prior["net_income"] - 1

    # Valuation (P/E, P/B) intentionally OMITTED: split-adjusted prices vs
    # as-reported EPS/shares corrupt historical multiples. The PIT snapshot carries
    # only the reliable price-independent signals (quality, growth, leverage), so
    # the backtest measures a clean quality+growth+leverage ranking.
    return FundamentalSnapshot(
        ticker=ticker, pe_ratio=None, pb_ratio=None, roe=roe, profit_margin=margin,
        revenue_growth_yoy=rev_growth, earnings_growth_yoy=ni_growth,
        debt_to_equity=de, current_ratio=current_ratio, free_cash_flow=fcf,
        sector=ticker.sector,
    )


__all__ = ["fetch_pit_fundamentals"]
