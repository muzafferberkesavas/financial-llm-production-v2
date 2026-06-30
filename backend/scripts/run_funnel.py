"""CLI: tek komutla funnel pipeline çalıştır.

Usage:
    python -m scripts.run_funnel --market nasdaq --mode pre_market --capital 10000
    python -m scripts.run_funnel --market bist --mode pre_market

Çıktı:
    backend/out/signals_<market>_<timestamp>_<mode>.json
    + console log + telegram stub
"""
from __future__ import annotations

import argparse
import logging
import sys
import warnings
from pathlib import Path

# Make src/ importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)


def main() -> int:
    parser = argparse.ArgumentParser(description="FinLLM cross-market signal funnel")
    parser.add_argument(
        "--market",
        choices=["bist", "nasdaq"],
        default="nasdaq",
        help="Pazar adı (default: nasdaq)",
    )
    parser.add_argument(
        "--mode",
        choices=["pre_market", "intraday", "end_of_day"],
        default="pre_market",
        help="Pipeline mode (default: pre_market)",
    )
    parser.add_argument(
        "--capital",
        type=float,
        default=10_000.0,
        help="Toplam sermaye (adapter para birimi) (default: 10000)",
    )
    parser.add_argument(
        "--lookback",
        type=int,
        default=400,
        help="Stage 0 fiyat geçmişi gün sayısı (default: 400)",
    )
    parser.add_argument(
        "--quota",
        type=int,
        default=12,
        help="Stage 1C master_score → Stage 3 max hisse sayısı (default: 12)",
    )
    parser.add_argument(
        "--min-setup-score",
        type=float,
        default=0.3,
        help="Stage 1B setup detector minimum score (default: 0.3)",
    )
    parser.add_argument(
        "--llm",
        choices=["mock", "claude", "claude-deep-only"],
        default="mock",
        help="LLM backend (default: mock — gerçek API call yok)",
    )
    parser.add_argument(
        "--skip-backtest",
        action="store_true",
        help="Stage 4.5 (backtest gate) atla — hızlı test için",
    )
    parser.add_argument(
        "--max-tickers",
        type=int,
        default=None,
        help="Stage 0'da universe'i kısalt (smoke test için)",
    )
    parser.add_argument(
        "--skip-news",
        action="store_true",
        help="Stage 0b (market agenda fetch) atla",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="JSON output klasörü (default: backend/out/)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="DEBUG-level logging",
    )

    args = parser.parse_args()

    # Logging setup
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format="%(message)s")
    # Yfinance verbose'unu kıs
    logging.getLogger("finllm.data.prices").setLevel(logging.WARNING)

    # Import after path setup
    from finllm.markets import get_adapter
    from finllm.pipeline.orchestrator import run_pipeline

    # Optional universe truncation (smoke test için)
    if args.max_tickers:
        from finllm.markets import get_adapter as _ga

        adapter_cls = type(_ga(args.market))
        orig_get_universe = adapter_cls.get_universe

        def _truncated(self):
            return orig_get_universe(self)[: args.max_tickers]

        adapter_cls.get_universe = _truncated
        print(f"⚠️  Universe truncated to first {args.max_tickers} tickers")

    # Cost warning
    if args.llm == "claude":
        print(f"⚠️  Real Claude API: estimated ${args.quota * 0.20:.2f}-${args.quota * 0.40:.2f} for this run")
        print("    (Opus deep analysis × stage3_queue tickers + Haiku screen)")

    ctx = run_pipeline(
        market=args.market,
        mode=args.mode,
        capital=args.capital,
        llm_backend=args.llm,
        lookback_days=args.lookback,
        max_pass_to_stage3=args.quota,
        min_setup_score=args.min_setup_score,
        skip_backtest_gate=args.skip_backtest,
        skip_news_agenda=args.skip_news,
        output_dir=args.output_dir,
    )

    # Exit code: actionable signal varsa 0, yoksa 0 (her zaman success — sinyal yokluğu hata değil)
    print()
    print(f"✓ Pipeline complete: {len(ctx.actionable_signals)} actionable signals")
    print(f"  Run ID: {ctx.run_id}")
    print(f"  Total: {sum(ctx.stage_durations_sec.values()):.1f}s")
    print(f"  Cost:  ${ctx.total_cost_usd:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
