"""Data Block Builder — lib.zip PromptBuilder'ın data block format Python port'u.

lib.zip'in en değerli parçası: "semantic label" tekniği.
LLM'e ham sayı vermek yerine label veriyor:
  RSI 58 → "BULLISH_MOMENTUM"
  MACD hist > prev → "BULLISH_ACCELERATING"
  ADX 32 rising → "MODERATE_STRENGTHENING|BULLISH_DI"
  Vol ratio 1.5+ → "HIGH"

LLM bu label'ları context olarak alır, halüsinasyon yapması zor.

Output format (lib.zip ile birebir uyumlu — Telegram/dashboard'da göstermek için kullanılabilir):

[STOCK: AAPL | Apple Inc. | Technology | PORTFOLIO]
PRICE: Last=195.50 | Chg=+1.24% | Vol=12.5M(Avg20:8.0M) | VolRatio=1.56x(HIGH)
RSI14: 58.34 | Momentum=BULLISH_MOMENTUM
MACD: 1.45/Signal=1.10/Hist=0.35 | Status=GOLDEN_CROSS
BB20: Upper=200.0 | Mid=190.0 | Lower=180.0 | %B=0.78 | Width=NARROWING
SMA: 20=189 | 50=185 | 200=170 | Formation=GOLDEN_CROSS
ADX14: 32.10 | Status=MODERATE_STRENGTHENING|BULLISH_DI
SETUP: pullback_ema (0.70)
WEEKLY: SMA20=188 | SMA50=180 | RSI=62 | Trend=UPTREND
TIMEFRAME: Alignment=ALIGNED
CONFLUENCE: Score=72/100 | weekly=20 adx=12 rsi=10 ...
CONFLUENCE_SIGNAL: AL (confidence: 0.50-0.69)
"""
from __future__ import annotations

from finllm.data.news.base import CorporateDisclosure, MarketAgenda
from finllm.data.news.kap_translator import format_kap_section
from finllm.indicators.confluence import confluence_to_signal_suggestion
from finllm.pipeline.context import Candidate


def _f(v: float | None, decimals: int = 2) -> str:
    """Format float-or-none — None için '-'."""
    if v is None:
        return "-"
    try:
        return f"{float(v):.{decimals}f}"
    except (TypeError, ValueError):
        return "-"


def _fmt_volume(v: float | None) -> str:
    if v is None:
        return "-"
    v = float(v)
    if v >= 1e9:
        return f"{v / 1e9:.1f}B"
    if v >= 1e6:
        return f"{v / 1e6:.1f}M"
    if v >= 1e3:
        return f"{v / 1e3:.1f}K"
    return f"{v:.0f}"


def _vol_label(ratio: float | None) -> str:
    if ratio is None:
        return "UNKNOWN"
    if ratio >= 3.0:
        return "EXTREME"
    if ratio >= 2.0:
        return "VERY_HIGH"
    if ratio >= 1.5:
        return "HIGH"
    if ratio >= 0.8:
        return "NORMAL"
    if ratio >= 0.5:
        return "LOW"
    return "VERY_LOW"


def _rsi_momentum(rsi: float | None, prev_rsi: float | None) -> str:
    if rsi is None:
        return "UNKNOWN"
    rising = prev_rsi is not None and rsi > prev_rsi
    falling = prev_rsi is not None and rsi < prev_rsi
    if rsi < 30 and rising:
        return "OVERSOLD_BOUNCING"
    if rsi < 30:
        return "OVERSOLD"
    if rsi > 70 and falling:
        return "OVERBOUGHT_FALLING"
    if rsi > 70:
        return "OVERBOUGHT"
    if rsi > 50 and rising:
        return "BULLISH_MOMENTUM"
    if rsi < 50 and falling:
        return "BEARISH_MOMENTUM"
    return "NEUTRAL"


def _macd_status(hist: float | None, prev_hist: float | None) -> str:
    if hist is None:
        return "UNKNOWN"
    if prev_hist is not None:
        if hist > 0 and prev_hist <= 0:
            return "GOLDEN_CROSS"
        if hist < 0 and prev_hist >= 0:
            return "BEARISH_CROSS"
    if hist > 0:
        if prev_hist is not None and hist > prev_hist:
            return "BULLISH_ACCELERATING"
        return "BULLISH_ABOVE"
    if prev_hist is not None and hist > prev_hist:
        return "BEARISH_DECELERATING"
    return "BEARISH_BELOW"


def _sma_formation(
    close: float, sma20: float | None, sma50: float | None, sma200: float | None
) -> str:
    if not all([sma20, sma50, sma200]):
        return "UNKNOWN"
    if close > sma20 > sma50 > sma200:
        return "GOLDEN_CROSS"
    if close > sma50 > sma200:
        return "BULLISH_ALIGNED"
    if close > sma200:
        return "ABOVE_200"
    if sma20 < sma50 < sma200:
        return "DEATH_CROSS"
    return "BELOW_200"


def _adx_status(
    adx: float | None,
    di_plus: float | None,
    di_minus: float | None,
) -> str:
    if adx is None:
        return "UNKNOWN"
    if adx >= 50:
        strength = "VERY_STRONG"
    elif adx >= 40:
        strength = "STRONG"
    elif adx >= 25:
        strength = "MODERATE"
    elif adx >= 20:
        strength = "WEAK"
    else:
        strength = "NO_TREND"

    di_signal = ""
    if di_plus is not None and di_minus is not None:
        di_signal = "|BULLISH_DI" if di_plus > di_minus else "|BEARISH_DI"
    return strength + di_signal


def _bb_line(
    bb_squeeze: bool | None,
    bb_width_trend: str | None,
    bb_width: float | None,
) -> str:
    parts = []
    if bb_squeeze:
        parts.append("SQUEEZE")
    if bb_width_trend:
        parts.append(f"Width={bb_width_trend}")
    if bb_width is not None:
        parts.append(f"BW={bb_width:.4f}")
    return " | ".join(parts) if parts else ""


def _obv_line(
    obv: float | None,
    obv_trend: str | None,
    obv_ma20: float | None,
    obv_divergence_type: str | None,
) -> str:
    parts = []
    if obv_trend:
        parts.append(f"Trend={obv_trend}")
    if obv_ma20 is not None and obv is not None:
        above = "ABOVE" if obv > obv_ma20 else "BELOW"
        parts.append(f"vs_MA20={above}")
    if obv_divergence_type:
        parts.append(f"Div={obv_divergence_type}")
    return " | ".join(parts) if parts else "-"


def build_data_block(
    cand: Candidate,
    market_agenda: MarketAgenda | None = None,
    kap_disclosures: list[CorporateDisclosure] | None = None,
) -> str:
    """Bir Candidate için zengin data block üret — LLM'e gönderilecek prompt parçası.

    Args:
        cand: indicators + confluence dolu Candidate (Stage 1C sonrası)
        market_agenda: opsiyonel MARKET AGENDA (Stage 0B'den) — Layer 0 news context
        kap_disclosures: opsiyonel per-ticker KAP disclosures (rule-based TR→EN)
    """
    ind = cand.indicators
    ticker = cand.ticker
    type_label = "COMMODITY" if ticker.is_commodity else "STOCK"

    tags = []
    if ticker.is_commodity:
        tags.append("COMMODITY")
    else:
        if cand.setup_type != "none":
            tags.append(f"SETUP_{cand.setup_type.upper()}")
        if cand.confluence_score >= 65:
            tags.append("HIGH_CONFLUENCE")
        if cand.regime == "STRONG_TREND":
            tags.append("STRONG_TREND")

    header = f"[{type_label}: {ticker.symbol} | {ticker.name} | {ticker.sector} | {' | '.join(tags) if tags else 'TOP_SCORE'}]"

    close = ind.get("close")
    ret_1d = ind.get("ret_1d")
    chg_pct = (ret_1d * 100) if ret_1d is not None else 0.0

    # Volume
    volume = ind.get("vol_sma_20")
    avg_vol_20 = ind.get("vol_sma_20")
    vol_ratio = ind.get("vol_ratio")
    today_vol = vol_ratio * avg_vol_20 if (vol_ratio and avg_vol_20) else volume

    price_line = (
        f"PRICE: Last={_f(close)} | Chg={chg_pct:+.2f}% | "
        f"Vol={_fmt_volume(today_vol)}(Avg20:{_fmt_volume(avg_vol_20)}) | "
        f"VolRatio={_f(vol_ratio, 2)}x({_vol_label(vol_ratio)})"
    )

    rsi_line = f"RSI14: {_f(ind.get('rsi_14'))} | Momentum={_rsi_momentum(ind.get('rsi_14'), ind.get('prev_rsi_14'))}"

    macd_line = (
        f"MACD: {_f(ind.get('macd'))}/Signal={_f(ind.get('macd_signal'))}/"
        f"Hist={_f(ind.get('macd_hist'), 3)} | "
        f"Status={_macd_status(ind.get('macd_hist'), ind.get('prev_macd_hist'))}"
    )

    bb_line = (
        f"BB20: Upper={_f(ind.get('bb_upper'))} | Mid={_f(ind.get('bb_mid'))} | "
        f"Lower={_f(ind.get('bb_lower'))} | %B={_f(ind.get('bb_pct'))} | "
        f"{_bb_line(ind.get('bb_squeeze'), ind.get('bb_width_trend'), ind.get('bb_width'))}"
    )

    sma_line = (
        f"SMA: 20={_f(ind.get('sma_20'))} | 50={_f(ind.get('sma_50'))} | "
        f"200={_f(ind.get('sma_200'))} | "
        f"Formation={_sma_formation(close or 0, ind.get('sma_20'), ind.get('sma_50'), ind.get('sma_200'))}"
    )

    adx_line = (
        f"ADX14: {_f(ind.get('adx_14'))} | "
        f"Status={_adx_status(ind.get('adx_14'), ind.get('di_plus'), ind.get('di_minus'))}"
    )

    obv_line = (
        f"OBV: {_f(ind.get('obv'), 0)} | "
        f"{_obv_line(ind.get('obv'), ind.get('obv_trend'), ind.get('obv_ma20'), ind.get('obv_divergence_type'))} | "
        f"TSCORE={cand.confluence_score}"
    )

    atr_line = f"ATR14: {_f(ind.get('atr_14'))}"

    # Candlestick patterns
    candle_parts = []
    if ind.get("pattern_bull_engulf") and ind["pattern_bull_engulf"] > 0:
        candle_parts.append("BULL_ENGULF")
    if ind.get("pattern_hammer") and ind["pattern_hammer"] > 0:
        candle_parts.append("HAMMER")
    if ind.get("pattern_doji") and ind["pattern_doji"] > 0:
        candle_parts.append("DOJI")
    candle_line = f"CANDLE_PATTERNS: {', '.join(candle_parts) if candle_parts else 'NONE'}"

    setup_line = f"SETUP: {cand.setup_type} ({cand.setup_confidence:.2f}) | meta={cand.setup_metadata}"

    weekly_line = (
        f"WEEKLY: SMA20={_f(ind.get('weekly_sma20'))} | SMA50={_f(ind.get('weekly_sma50'))} | "
        f"RSI={_f(ind.get('weekly_rsi'))} | Trend={ind.get('weekly_trend', 'UNKNOWN')}"
    )

    timeframe_line = f"TIMEFRAME: Alignment={ind.get('timeframe_alignment', 'UNKNOWN')}"

    fib_zone = ind.get("fib_zone", "NO_FIB")
    fib_line = f"FIB_ZONE: {fib_zone}"

    swing_line = (
        f"SWING20: High={_f(ind.get('swing_high_20'))} | Low={_f(ind.get('swing_low_20'))}"
    )

    confluence_line = (
        f"CONFLUENCE: Score={cand.confluence_score}/100 | "
        + " | ".join(f"{k}={v}" for k, v in cand.confluence_detail.items())
    )
    suggested_signal, conf_range = confluence_to_signal_suggestion(cand.confluence_score)
    confluence_signal_line = (
        f"CONFLUENCE_SIGNAL: {suggested_signal} (confidence: {conf_range[0]:.2f}-{conf_range[1]:.2f})"
    )

    # ---- Phase 3.1: FUNDAMENTALS block ----
    fund_snap = cand.ingested.fundamentals
    fund_lines: list[str] = []
    if fund_snap and (fund_snap.has_valuation_data or fund_snap.has_profitability_data):
        fund_lines.append("FUNDAMENTALS:")
        # Valuation
        val_parts = []
        if fund_snap.pe_ratio:
            val_parts.append(f"P/E={fund_snap.pe_ratio:.1f}")
        if fund_snap.forward_pe:
            val_parts.append(f"Fwd_P/E={fund_snap.forward_pe:.1f}")
        if fund_snap.pb_ratio:
            val_parts.append(f"P/B={fund_snap.pb_ratio:.1f}")
        if fund_snap.ev_to_ebitda:
            val_parts.append(f"EV/EBITDA={fund_snap.ev_to_ebitda:.1f}")
        if fund_snap.peg_ratio:
            val_parts.append(f"PEG={fund_snap.peg_ratio:.2f}")
        if val_parts:
            fund_lines.append(f"  Valuation: {' | '.join(val_parts)}")

        # Profitability
        prof_parts = []
        if fund_snap.profit_margin is not None:
            prof_parts.append(f"Net_Margin={fund_snap.profit_margin * 100:.1f}%")
        if fund_snap.gross_margin is not None:
            prof_parts.append(f"Gross={fund_snap.gross_margin * 100:.1f}%")
        if fund_snap.roe is not None:
            prof_parts.append(f"ROE={fund_snap.roe * 100:.1f}%")
        if fund_snap.roa is not None:
            prof_parts.append(f"ROA={fund_snap.roa * 100:.1f}%")
        if prof_parts:
            fund_lines.append(f"  Profitability: {' | '.join(prof_parts)}")

        # Growth
        growth_parts = []
        if fund_snap.revenue_growth_yoy is not None:
            growth_parts.append(f"Revenue_YoY={fund_snap.revenue_growth_yoy * 100:+.1f}%")
        if fund_snap.earnings_growth_yoy is not None:
            growth_parts.append(f"Earnings_YoY={fund_snap.earnings_growth_yoy * 100:+.1f}%")
        if growth_parts:
            fund_lines.append(f"  Growth: {' | '.join(growth_parts)}")

        # Balance
        bal_parts = []
        if fund_snap.debt_to_equity is not None:
            bal_parts.append(f"D/E={fund_snap.debt_to_equity:.2f}")
        if fund_snap.current_ratio is not None:
            bal_parts.append(f"Current_Ratio={fund_snap.current_ratio:.2f}")
        if fund_snap.free_cash_flow:
            fcf_val = fund_snap.free_cash_flow / 1e9
            bal_parts.append(f"FCF=${fcf_val:.1f}B")
        if bal_parts:
            fund_lines.append(f"  Balance: {' | '.join(bal_parts)}")

        # Dividend (varsa)
        if fund_snap.dividend_yield and fund_snap.dividend_yield > 0:
            div_parts = [f"Yield={fund_snap.dividend_yield * 100:.2f}%"]
            if fund_snap.payout_ratio is not None:
                div_parts.append(f"Payout={fund_snap.payout_ratio * 100:.0f}%")
            fund_lines.append(f"  Dividend: {' | '.join(div_parts)}")

        # Earnings calendar (kritik — yakın bilanço açıklaması varsa flag)
        if fund_snap.earnings_date:
            days = fund_snap.days_to_earnings
            if days is not None:
                if 0 <= days <= 5:
                    fund_lines.append(
                        f"  ⚠️ EARNINGS_UPCOMING: {fund_snap.earnings_date.strftime('%Y-%m-%d')} "
                        f"({days}d) — VOLATILITY EXPECTED"
                    )
                elif 0 <= days <= 30:
                    fund_lines.append(
                        f"  Earnings: {fund_snap.earnings_date.strftime('%Y-%m-%d')} ({days}d away)"
                    )

        # Fundamental score
        fd = cand.fundamental_detail
        if fd:
            fund_lines.append(
                f"  FUND_SCORE: {cand.fundamental_score}/100 "
                f"(value={fd.get('value', 0)}/40, quality={fd.get('quality', 0)}/30, "
                f"growth={fd.get('growth', 0)}/30) | "
                f"labels: pe={fd.get('pe_label', '-')}, quality={fd.get('quality_label', '-')}, "
                f"growth={fd.get('growth_label', '-')} | sector_bench={fd.get('sector', '-')}"
            )

    fundamentals_block = "\n".join(fund_lines) if fund_lines else ""

    regime_line = f"MARKET_REGIME: {cand.regime}"

    # Master scorecard line
    master_line = ""
    if cand.master_score is not None and hasattr(cand.master_score, 'summary_line'):
        master_line = f"MASTER_SCORE: {cand.master_score.summary_line()} | RANK_BASIS=true"

    sections = [
        header,
        regime_line,
        price_line,
        rsi_line,
        macd_line,
        bb_line,
        sma_line,
        adx_line,
        atr_line,
        obv_line,
        candle_line,
        setup_line,
        weekly_line,
        timeframe_line,
        fib_line,
        swing_line,
        confluence_line,
        confluence_signal_line,
    ]

    if master_line:
        sections.append(master_line)

    # Fundamental block (Phase 3.1) — confluence'tan sonra ekle
    if fundamentals_block:
        sections.append(fundamentals_block)

    # Per-ticker KAP disclosures (rule-based TR→EN, no LLM cost)
    if kap_disclosures:
        kap_block = format_kap_section(kap_disclosures)
        if kap_block:
            sections.append(kap_block)

    # Layer 0: MARKET AGENDA — header'dan önce prepend
    if market_agenda is not None and not market_agenda.is_empty:
        agenda_block = (
            "== MARKET AGENDA (last 24h) ==\n"
            + market_agenda.formatted_agenda
            + f"\n(news_sources: {','.join(market_agenda.sources)})\n=="
        )
        return agenda_block + "\n\n" + "\n".join(sections)

    return "\n".join(sections)
