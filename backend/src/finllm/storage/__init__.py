"""Storage — SQLAlchemy v2 models + repository + legacy DuckDB.

v2 (Phase 3.2): Run, Signal, Outcome, FundamentalCache, Watchlist
Legacy (Phase 1): DuckDB connection + ad-hoc tables (signals_history, positions, orders)
"""
from finllm.storage import db as legacy_db  # eski sistem korunur
from finllm.storage import repository
from finllm.storage.engine import get_engine, init_schema, session_scope
from finllm.storage.models import (
    Base,
    FundamentalCache,
    Outcome,
    Run,
    Signal,
    SignalScenario,
    Watchlist,
)

__all__ = [
    "Base",
    "FundamentalCache",
    "Outcome",
    "Run",
    "Signal",
    "SignalScenario",
    "Watchlist",
    "get_engine",
    "init_schema",
    "legacy_db",
    "repository",
    "session_scope",
]
