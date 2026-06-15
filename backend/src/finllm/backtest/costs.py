"""Transaction-cost model for the backtest — commission + slippage.

The research (arXiv:2603.27539) flags *transaction-cost neglect* as one of the
five systematic failures that make published LLM-trading returns non-credible.
Every fill in the backtest now passes through a CostModel so reported PF/Sharpe
reflect real-world drag.

Defaults are calibrated to **Midas Menkul Değerler** (the broker actually used):
  • US stocks  → flat $1.5 per trade, no percentage commission
                 (+$0.005/share above 300 shares for sub-$1 penny stocks)
  • BIST       → zero commission
Slippage is a market-microstructure assumption (not a broker fee), defaulting to
5 bps per side; tune via the preset or CLI.

Source: https://www.getmidas.com/ucretler/ (verified 2026-06).
"""
from __future__ import annotations

from dataclasses import dataclass

_BPS = 10_000.0


@dataclass(frozen=True)
class CostModel:
    """Per-side commission + slippage applied at every fill.

    Attributes:
        commission_bps: Percentage commission per side, in basis points.
        flat_fee_usd:   Flat fee charged per trade (per side), in account currency.
        slippage_bps:   Adverse price move modelled at each fill, per side (bps).
        penny_price_usd / penny_share_threshold / penny_per_share_usd:
                        Midas penny-stock surcharge — for fills priced below
                        ``penny_price_usd``, each share above ``penny_share_threshold``
                        adds ``penny_per_share_usd`` to the trade fee.
    """

    commission_bps: float = 0.0
    flat_fee_usd: float = 1.5
    slippage_bps: float = 5.0
    penny_price_usd: float = 1.0
    penny_share_threshold: int = 300
    penny_per_share_usd: float = 0.005

    # ---------- fill prices (slippage) ----------

    def entry_fill_price(self, ref_price: float) -> float:
        """Buy fills are worse (higher) than the reference price."""
        return ref_price * (1.0 + self.slippage_bps / _BPS)

    def exit_fill_price(self, ref_price: float) -> float:
        """Sell fills are worse (lower) than the reference price."""
        return ref_price * (1.0 - self.slippage_bps / _BPS)

    # ---------- commission ----------

    def commission(self, fill_price: float, shares: float) -> float:
        """Total fee for one fill of ``shares`` at ``fill_price`` (one side)."""
        if shares <= 0 or fill_price <= 0:
            return 0.0
        notional = fill_price * shares
        fee = self.flat_fee_usd + notional * self.commission_bps / _BPS
        if fill_price < self.penny_price_usd and shares > self.penny_share_threshold:
            fee += (shares - self.penny_share_threshold) * self.penny_per_share_usd
        return fee

    # ---------- presets ----------

    @classmethod
    def midas_us(cls) -> "CostModel":
        """Midas US-equities tariff: flat $1.5/trade, 0% commission, 5 bps slippage."""
        return cls(commission_bps=0.0, flat_fee_usd=1.5, slippage_bps=5.0)

    @classmethod
    def midas_bist(cls) -> "CostModel":
        """Midas BIST tariff: zero commission, 5 bps slippage (no penny surcharge)."""
        return cls(
            commission_bps=0.0,
            flat_fee_usd=0.0,
            slippage_bps=5.0,
            penny_per_share_usd=0.0,
        )

    @classmethod
    def zero(cls) -> "CostModel":
        """Frictionless — for ablation only (reproduces the old inflated numbers)."""
        return cls(
            commission_bps=0.0,
            flat_fee_usd=0.0,
            slippage_bps=0.0,
            penny_per_share_usd=0.0,
        )


PRESETS: dict[str, "CostModel"] = {
    "midas-us": CostModel.midas_us(),
    "midas-bist": CostModel.midas_bist(),
    "zero": CostModel.zero(),
}
