"""MarketAdapter protokolü — BIST ve NASDAQ pipeline'ları için ortak arayüz.

Pipeline kodu market-agnostic kalır; her market kendi Adapter'ında
threshold/source/timezone farklılığını encapsulate eder.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Literal, Protocol, runtime_checkable
from zoneinfo import ZoneInfo

import pandas as pd

MarketName = Literal["bist", "nasdaq"]


@dataclass(frozen=True, slots=True)
class Ticker:
    """Sembol + market — adapter ticker'ı kendi formatına çevirir."""

    symbol: str        # "AAPL" veya "THYAO" (raw, suffix YOK)
    market: MarketName
    name: str = ""
    sector: str = ""
    is_commodity: bool = False

    def __str__(self) -> str:
        return f"{self.symbol}@{self.market}"


@dataclass(slots=True)
class FundamentalSnapshot:
    """Adapter'ın Stage 0'da getirdiği fundamental data.

    Phase 3.1: 20+ field — valuation, profitability, growth, balance, dividend.
    """

    ticker: Ticker

    # ---- Market data ----
    market_cap: float | None = None        # Para birimi adapter.currency
    avg_volume_10d: float | None = None
    avg_volume_20d: float | None = None
    shares_outstanding: float | None = None
    float_shares: float | None = None      # halka açıklık
    short_ratio: float | None = None        # short interest / avg volume

    # ---- Valuation (F/K, F/PD, EV/FAVÖK) ----
    pe_ratio: float | None = None           # F/K — trailing
    forward_pe: float | None = None         # ileriye dönük F/K
    pb_ratio: float | None = None           # PD/DD (P/B)
    ps_ratio: float | None = None           # F/S (P/S)
    ev_to_ebitda: float | None = None       # EV/FAVÖK
    ev_to_revenue: float | None = None      # EV/Hasılat
    peg_ratio: float | None = None          # PEG (P/E ÷ growth)

    # ---- Profitability (karlılık) ----
    profit_margin: float | None = None      # Net kar marjı (decimal: 0.22 = %22)
    gross_margin: float | None = None       # Brüt kar marjı
    operating_margin: float | None = None   # Faaliyet kar marjı
    roe: float | None = None                # Özsermaye karlılığı (Return on Equity)
    roa: float | None = None                # Aktif karlılığı

    # ---- Growth (büyüme) ----
    revenue_growth_yoy: float | None = None       # Yıllık hasılat büyümesi
    earnings_growth_yoy: float | None = None      # Yıllık kar büyümesi
    revenue_growth_quarterly: float | None = None # Çeyreklik hasılat büyümesi
    earnings_growth_quarterly: float | None = None

    # ---- Balance sheet health (bilanço sağlığı) ----
    debt_to_equity: float | None = None     # Borç / Özsermaye
    current_ratio: float | None = None      # Cari oran
    quick_ratio: float | None = None        # Asit-test oranı
    total_cash: float | None = None         # Nakit
    total_debt: float | None = None         # Toplam borç
    free_cash_flow: float | None = None     # Serbest nakit akışı
    book_value: float | None = None         # Defter değeri (per share)

    # ---- Dividend (temettü) ----
    dividend_yield: float | None = None     # Temettü verimi (decimal)
    payout_ratio: float | None = None       # Dağıtım oranı
    five_year_avg_dividend_yield: float | None = None

    # ---- Earnings calendar ----
    earnings_date: datetime | None = None   # Bir sonraki bilanço açıklama tarihi
    last_earnings_surprise_pct: float | None = None  # Son sürpriz (beat/miss)

    # ---- Meta ----
    sector: str | None = None
    industry: str | None = None
    country: str | None = None
    as_of: datetime = field(default_factory=datetime.utcnow)

    # ---- Helper properties ----
    @property
    def days_to_earnings(self) -> int | None:
        if self.earnings_date is None:
            return None
        delta = self.earnings_date.replace(tzinfo=None) - datetime.utcnow()
        return delta.days

    @property
    def has_valuation_data(self) -> bool:
        return any(
            v is not None
            for v in (self.pe_ratio, self.pb_ratio, self.ev_to_ebitda)
        )

    @property
    def has_profitability_data(self) -> bool:
        return any(v is not None for v in (self.profit_margin, self.roe, self.roa))


@dataclass(slots=True)
class FilterThresholds:
    """Stage 1 hard filter eşikleri — market'a göre değişir.

    Niye dataclass: pipeline kodunda `adapter.thresholds.min_price` gibi
    tek nokta erişim. Test'lerde override kolay.
    """

    min_price: float                    # Para birimi adapter.currency
    min_market_cap: float
    min_avg_volume_10d: float
    min_daily_dollar_volume: float
    min_adr_pct: float = 2.0
    require_close_above_ema21: bool = True
    require_close_above_ema50: bool = True
    require_green_day: bool = True      # Bugün > dün kapanışı


@dataclass(slots=True)
class TransactionCostModel:
    """Backtest gate ve allocator transaction cost'u modellemek için."""

    commission_per_share: float = 0.0   # NASDAQ: ~$0.005, BIST: 0
    commission_pct: float = 0.0          # BIST: ~0.15% (broker)
    tax_pct: float = 0.0                 # BIST: BSMV 0.5%
    slippage_atr_mult: float = 0.05      # 5% of ATR per fill (varsayım)
    half_spread_pct: float = 0.05        # 0.05% half-spread proxy

    def round_trip_cost_pct(self, price: float, atr: float) -> float:
        """Bir round trip'in fiyatın yüzdesi olarak toplam maliyeti."""
        slippage = (atr * self.slippage_atr_mult / price) * 100 if price > 0 else 0
        spread = self.half_spread_pct * 2
        commission_share_pct = (
            (self.commission_per_share / price) * 100 * 2 if price > 0 else 0
        )
        return slippage + spread + commission_share_pct + self.commission_pct * 2 + self.tax_pct


@runtime_checkable
class MarketAdapter(Protocol):
    """Tek pazar için tüm yapılandırma ve veri kaynaklarını paketleyen Protocol.

    Pipeline kodu Adapter'a şöyle güvenir:
        for ticker in adapter.get_universe():
            prices = adapter.fetch_prices(ticker)
            ...

    Adapter swap edilince aynı pipeline farklı pazar çalıştırır.
    """

    # ---- Identification ----
    name: MarketName
    currency: str                        # "TRY" | "USD"
    timezone: ZoneInfo

    # ---- Trading mechanics ----
    open_time: time                      # 09:50 BIST | 09:30 ET
    close_time: time
    settlement_days: int                 # 1 (BIST T+1) | 2 (NASDAQ T+2)

    # ---- Configuration ----
    thresholds: FilterThresholds
    transaction_cost: TransactionCostModel
    benchmark_symbol: str                # "XU100" | "SPY"

    # ---- Universe ----
    def get_universe(self) -> list[Ticker]:
        """Pazar evrenini döner. BIST ~100, NASDAQ ~500-1500 hisse."""
        ...

    def format_yahoo_symbol(self, ticker: Ticker) -> str:
        """Yahoo Finance API için ticker'ı formatla.

        BIST: THYAO → THYAO.IS
        NASDAQ: AAPL → AAPL
        Emtia: GC=F → GC=F (her ikisinde de raw)
        """
        ...

    # ---- Data fetch (Stage 0) ----
    def fetch_prices(
        self,
        ticker: Ticker,
        start: str | datetime | None = None,
        end: str | datetime | None = None,
        interval: str = "1d",
    ) -> pd.DataFrame:
        """OHLCV DataFrame döner. Index: DatetimeIndex (UTC).

        Emtia ticker'ı için adapter USD/oz → currency/gram dönüşümünü yapar.
        """
        ...

    def fetch_fundamentals(self, ticker: Ticker) -> FundamentalSnapshot | None:
        """Market cap, avg volume, sector. None: data alınamadı."""
        ...

    # ---- News (untrusted input, Anthropic 3-tier isolation noktası) ----
    def fetch_news(self, ticker: Ticker | None = None, hours: int = 24) -> list[dict]:
        """Ticker bazlı (varsa) veya genel piyasa haberi.

        Dönen dict'lerin field'ları:
            {title, description, pub_date, source, category, ticker?}

        UNTRUSTED — bu çıktıyı asla doğrudan LLM system prompt'a koymayın;
        önce news/translator.py ile JSON schema'lı parse'tan geçirin.
        """
        ...

    # ---- Market-specific quirks ----
    def is_market_open(self, dt: datetime | None = None) -> bool:
        """Şu an piyasa açık mı? Adapter timezone'a göre."""
        ...

    def is_commodity(self, ticker: Ticker) -> bool:
        """BIST: GC=F/SI=F True. NASDAQ: default False (ETF olarak işlenir)."""
        return ticker.is_commodity

    def convert_commodity_price(
        self, raw_price: float, currency_rate: float | None = None
    ) -> float:
        """USD/oz fiyatı adapter.currency/gram'a çevir.

        BIST için: USD/oz × USDTRY / 31.1035 = TRY/gram
        NASDAQ için: no-op (zaten USD).
        """
        ...


@dataclass(slots=True)
class RegimeContext:
    """Stage 1'den önce piyasa rejimi kontrolü — kill-switch için.

    Adapter'dan bağımsız; her pipeline çalışmasının başında bir kez hesaplanır.
    """

    market: MarketName
    vix: float | None = None             # NASDAQ için doğrudan, BIST için proxy
    benchmark_change_5d: float | None = None
    benchmark_above_200d_ma: bool | None = None
    fear_level: Literal["calm", "elevated", "extreme"] = "calm"
    trade_enabled: bool = True
    halt_reason: str | None = None       # neden trade durduruldu (loglanır)

    def block(self, reason: str) -> "RegimeContext":
        """Trade'i durdur, sebep işaretle."""
        self.trade_enabled = False
        self.halt_reason = reason
        return self
