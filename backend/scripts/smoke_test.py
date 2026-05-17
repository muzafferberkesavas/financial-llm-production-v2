"""Uçtan uca pipeline smoke test.

Çalıştır:
    cd backend && python -m scripts.smoke_test

Test eder:
    1) Fiyat çekme (yfinance)
    2) Teknik feature engineering
    3) FinBERT sentiment (dummy haberlerle — Finnhub key opsiyonel)
    4) Eğer FINNHUB_API_KEY varsa gerçek haber + sentiment
"""
from __future__ import annotations

import sys

from rich.console import Console
from rich.table import Table

from finllm.config.settings import settings
from finllm.data.prices import fetch_prices
from finllm.features.technical import add_technical_features, make_swing_target
from finllm.sentiment.finbert import aggregate_polarity, score_batch

console = Console()


def test_price_pipeline(symbol: str = "AAPL") -> None:
    console.rule(f"[1] Fiyat + teknik göstergeler: {symbol}")
    prices = fetch_prices(symbol, start="2023-01-01")
    console.print(f"Çekilen satır sayısı: [bold]{len(prices)}[/bold]")
    console.print(f"Tarih aralığı: {prices.index.min().date()} → {prices.index.max().date()}")

    feats = add_technical_features(prices)
    feats["target"] = make_swing_target(feats, horizon_days=10, threshold=0.03)

    latest = feats.iloc[-1]
    table = Table(title=f"{symbol} — Son gün anlık görüntü")
    table.add_column("Metrik", style="cyan")
    table.add_column("Değer", style="green")
    for key in ["close", "ret_5d", "rsi_14", "macd", "bb_pct", "adx_14", "vol_ratio"]:
        val = latest.get(key)
        if val is not None:
            table.add_row(key, f"{val:.4f}" if isinstance(val, float) else str(val))
    console.print(table)

    pos_rate = feats["target"].mean()
    console.print(f"Pozitif örnek oranı (10g, %3+): [yellow]{pos_rate:.1%}[/yellow]")


def test_finbert() -> None:
    console.rule("[2] FinBERT sentiment (örnek metinlerle)")
    samples = [
        "Apple beats Q4 earnings estimates, raises guidance on strong iPhone demand.",
        "Tesla misses delivery targets; analysts cut price targets sharply.",
        "Microsoft announces a $10B partnership with OpenAI to accelerate AI rollout.",
        "Federal Reserve signals further rate hikes amid sticky inflation data.",
        "Boeing faces new SEC probe over 737 MAX quality control.",
    ]
    results = score_batch(samples)
    table = Table(title="Sentiment sonuçları")
    table.add_column("Metin", style="white", max_width=60)
    table.add_column("Etiket", style="cyan")
    table.add_column("Skor", style="green")
    table.add_column("Polarite", style="yellow")
    for r in results:
        table.add_row(r.text[:60] + "...", r.label, f"{r.score:.2f}", f"{r.polarity:+.2f}")
    console.print(table)
    console.print(f"Agrega polarite: [bold]{aggregate_polarity(results):+.3f}[/bold]")


def test_finnhub_news(symbol: str = "AAPL") -> None:
    if not settings.finnhub_api_key:
        console.print("[yellow]FINNHUB_API_KEY yok — gerçek haber testi atlanıyor[/yellow]")
        return
    console.rule(f"[3] Finnhub haber + sentiment: {symbol}")
    from finllm.data.news import fetch_news

    news = fetch_news(symbol, days_back=3)
    if not news:
        console.print("Haber bulunamadı.")
        return
    texts = [n.text for n in news[:20]]
    sentiments = score_batch(texts)
    agg = aggregate_polarity(sentiments)
    console.print(f"{symbol}: {len(news)} haber, agrega polarite [bold]{agg:+.3f}[/bold]")


def main() -> int:
    try:
        test_price_pipeline("AAPL")
        test_finbert()
        test_finnhub_news("AAPL")
        console.rule("[green]Smoke test PASSED[/green]")
        return 0
    except Exception as e:
        console.print_exception()
        console.rule(f"[red]Smoke test FAILED: {e}[/red]")
        return 1


if __name__ == "__main__":
    sys.exit(main())
