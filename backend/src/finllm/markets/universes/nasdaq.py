"""NASDAQ / US universe — S&P 500 + ek yüksek-momentum/likidite mid-cap'ler.

Phase 1 için ~50 hisselik core liste kullanıyoruz.
Phase 2'de tam S&P 500'e (504 hisse) genişletilecek; orada Wikipedia veya
Polygon API'den dinamik fetch yapılmalı (survivorship bias için PIT data).

Bu liste mevcut `config/universe.py` ile uyumlu — gradually buradan
populate edilecek; eski dosya legacy kalır.
"""
from __future__ import annotations

from finllm.markets.base import Ticker


# ---- Mega-cap (likidite + analist coverage en yüksek) ----
_MEGA_CAP = [
    ("AAPL",  "Apple",            "Technology"),
    ("MSFT",  "Microsoft",        "Technology"),
    ("GOOGL", "Alphabet A",       "Communication Services"),
    ("AMZN",  "Amazon",           "Consumer Discretionary"),
    ("META",  "Meta Platforms",   "Communication Services"),
    ("NVDA",  "NVIDIA",           "Technology"),
    ("TSLA",  "Tesla",            "Consumer Discretionary"),
    ("BRK-B", "Berkshire B",      "Financial"),
]

# ---- Semi / AI hardware (volatil + haber-yoğun) ----
_SEMI_AI = [
    ("AMD",   "Advanced Micro Devices", "Technology"),
    ("AVGO",  "Broadcom",         "Technology"),
    ("TSM",   "Taiwan Semi",      "Technology"),
    ("MU",    "Micron Technology", "Technology"),
    ("ASML",  "ASML Holding",     "Technology"),
    ("ARM",   "ARM Holdings",     "Technology"),
    ("INTC",  "Intel",            "Technology"),
    ("QCOM",  "Qualcomm",         "Technology"),
    ("AMAT",  "Applied Materials", "Technology"),
]

# ---- Software / Cloud ----
_SOFTWARE = [
    ("CRM",   "Salesforce",       "Technology"),
    ("ADBE",  "Adobe",            "Technology"),
    ("ORCL",  "Oracle",           "Technology"),
    ("NOW",   "ServiceNow",       "Technology"),
    ("SNOW",  "Snowflake",        "Technology"),
    ("PLTR",  "Palantir",         "Technology"),
    ("CRWD",  "CrowdStrike",      "Technology"),
    ("DDOG",  "Datadog",          "Technology"),
    ("NET",   "Cloudflare",       "Technology"),
    ("PANW",  "Palo Alto Networks","Technology"),
    ("MDB",   "MongoDB",          "Technology"),
]

# ---- Finance ----
_FINANCE = [
    ("JPM",   "JPMorgan Chase",   "Financial"),
    ("BAC",   "Bank of America",  "Financial"),
    ("GS",    "Goldman Sachs",    "Financial"),
    ("MS",    "Morgan Stanley",   "Financial"),
    ("WFC",   "Wells Fargo",      "Financial"),
    ("V",     "Visa",             "Financial"),
    ("MA",    "Mastercard",       "Financial"),
    ("AXP",   "American Express", "Financial"),
]

# ---- Consumer ----
_CONSUMER = [
    ("WMT",   "Walmart",          "Consumer Defensive"),
    ("COST",  "Costco",           "Consumer Defensive"),
    ("HD",    "Home Depot",       "Consumer Discretionary"),
    ("NKE",   "Nike",              "Consumer Discretionary"),
    ("MCD",   "McDonald's",       "Consumer Discretionary"),
    ("SBUX",  "Starbucks",        "Consumer Discretionary"),
    ("DIS",   "Disney",           "Communication Services"),
]

# ---- Healthcare ----
_HEALTHCARE = [
    ("JNJ",   "Johnson & Johnson","Healthcare"),
    ("UNH",   "UnitedHealth",     "Healthcare"),
    ("LLY",   "Eli Lilly",        "Healthcare"),
    ("PFE",   "Pfizer",           "Healthcare"),
    ("MRK",   "Merck",            "Healthcare"),
    ("ABBV",  "AbbVie",           "Healthcare"),
]

# ---- Energy / Industrials ----
_ENERGY_INDUSTRIAL = [
    ("XOM",   "ExxonMobil",       "Energy"),
    ("CVX",   "Chevron",          "Energy"),
    ("CAT",   "Caterpillar",      "Industrials"),
    ("BA",    "Boeing",           "Industrials"),
    ("GE",    "General Electric", "Industrials"),
]

# ---- High-beta / momentum (haber-duyarlı, swing fırsatları) ----
_HIGH_BETA = [
    ("COIN",  "Coinbase",         "Financial"),
    ("RIVN",  "Rivian",           "Consumer Discretionary"),
    ("LCID",  "Lucid",            "Consumer Discretionary"),
    ("SOFI",  "SoFi",             "Financial"),
    ("HOOD",  "Robinhood",        "Financial"),
    ("SHOP",  "Shopify",          "Technology"),
    ("UBER",  "Uber",             "Industrials"),
    ("ABNB",  "Airbnb",           "Consumer Discretionary"),
]

# ---- Benchmark ETF'leri (kıyas için, sinyal üretmiyoruz) ----
_BENCHMARKS = [
    ("SPY",   "SPDR S&P 500 ETF", "ETF"),
    ("QQQ",   "Invesco QQQ",      "ETF"),
    ("IWM",   "iShares Russell 2000", "ETF"),
]


def _make_tickers(raw: list[tuple[str, str, str]]) -> list[Ticker]:
    return [Ticker(sym, "nasdaq", name, sector) for sym, name, sector in raw]


# ---- Public ----
NASDAQ_CORE: list[Ticker] = (
    _make_tickers(_MEGA_CAP)
    + _make_tickers(_SEMI_AI)
    + _make_tickers(_SOFTWARE)
    + _make_tickers(_FINANCE)
    + _make_tickers(_CONSUMER)
    + _make_tickers(_HEALTHCARE)
    + _make_tickers(_ENERGY_INDUSTRIAL)
)

NASDAQ_HIGH_BETA: list[Ticker] = _make_tickers(_HIGH_BETA)
NASDAQ_BENCHMARKS: list[Ticker] = _make_tickers(_BENCHMARKS)

NASDAQ_ALL: list[Ticker] = NASDAQ_CORE + NASDAQ_HIGH_BETA

NASDAQ_TEST: list[Ticker] = _make_tickers([
    ("NVDA",  "NVIDIA",           "Technology"),
    ("MSFT",  "Microsoft",        "Technology"),
])
