"""Market adapters — BIST + NASDAQ için MarketAdapter implementasyonları.

Kullanım:
    from finllm.markets import get_adapter

    adapter = get_adapter("nasdaq")
    for ticker in adapter.get_universe():
        prices = adapter.fetch_prices(ticker)
        ...
"""
from finllm.markets.base import (
    FilterThresholds,
    FundamentalSnapshot,
    MarketAdapter,
    MarketName,
    RegimeContext,
    Ticker,
    TransactionCostModel,
)
from finllm.markets.bist import BistAdapter
from finllm.markets.nasdaq import NasdaqAdapter

_REGISTRY: dict[MarketName, type[MarketAdapter]] = {
    "bist": BistAdapter,
    "nasdaq": NasdaqAdapter,
}


def get_adapter(market: MarketName) -> MarketAdapter:
    """Market adı verilen adapter instance'ını döner.

    Args:
        market: "bist" veya "nasdaq"

    Raises:
        ValueError: Tanınmayan market adı
    """
    if market not in _REGISTRY:
        raise ValueError(
            f"Bilinmeyen market: {market}. Geçerli: {list(_REGISTRY.keys())}"
        )
    return _REGISTRY[market]()


__all__ = [
    "BistAdapter",
    "FilterThresholds",
    "FundamentalSnapshot",
    "MarketAdapter",
    "MarketName",
    "NasdaqAdapter",
    "RegimeContext",
    "Ticker",
    "TransactionCostModel",
    "get_adapter",
]
