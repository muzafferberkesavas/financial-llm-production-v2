"""Hisse evrenleri. MVP için likit, haber-zengin US large-caps ile başlıyoruz."""
from __future__ import annotations

# Başlangıç evreni — likit, opsiyon piyasası olan, haber akışı yoğun isimler
US_CORE = [
    # Mega-cap tech
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA",
    # Semi & AI
    "AMD", "AVGO", "TSM", "MU", "ASML", "ARM",
    # Finance
    "JPM", "BAC", "GS", "MS", "WFC", "V", "MA",
    # Consumer & retail
    "WMT", "COST", "HD", "NKE", "MCD", "SBUX", "DIS",
    # Healthcare
    "JNJ", "UNH", "LLY", "PFE", "MRK",
    # Energy & industrials
    "XOM", "CVX", "CAT", "BA", "GE",
    # ETF benchmarks
    "SPY", "QQQ", "IWM",
]

# Spekülatif / haber-duyarlı liste — sentiment modelimizin parladığı yer
US_HIGH_BETA = [
    "PLTR", "COIN", "RIVN", "LCID", "SOFI", "HOOD", "SNOW",
    "NET", "DDOG", "SHOP", "CRWD", "MDB", "PANW",
]

DEFAULT_UNIVERSE = US_CORE + US_HIGH_BETA


US_TEST = ["NVDA", "MSFT"]  # smoke test için minik evren


def get_universe(name: str = "default") -> list[str]:
    return {
        "default": DEFAULT_UNIVERSE,
        "core": US_CORE,
        "high_beta": US_HIGH_BETA,
        "test": US_TEST,
    }[name]
