"""DuckDB connection + schema yönetimi. Tek noktadan yönetilir."""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

import duckdb

from finllm.config.settings import DATA_DIR

DB_PATH = DATA_DIR / "finllm.duckdb"

SCHEMA = """
CREATE SEQUENCE IF NOT EXISTS positions_id_seq;
CREATE SEQUENCE IF NOT EXISTS orders_id_seq;
CREATE SEQUENCE IF NOT EXISTS signals_id_seq;

CREATE TABLE IF NOT EXISTS positions (
    id            INTEGER PRIMARY KEY DEFAULT nextval('positions_id_seq'),
    symbol        VARCHAR NOT NULL,
    entry_price   DOUBLE NOT NULL,
    entry_date    TIMESTAMP NOT NULL,
    target_price  DOUBLE,
    stop_loss     DOUBLE,
    max_holding_days INTEGER NOT NULL DEFAULT 15,
    weight_pct    DOUBLE NOT NULL,           -- portföydeki ağırlık (%, 0-100)
    capital_usd   DOUBLE NOT NULL,           -- pozisyona ayrılan dolar
    entry_confidence DOUBLE,
    entry_rationale TEXT,
    exit_price    DOUBLE,
    exit_date     TIMESTAMP,
    exit_reason   VARCHAR,
    pnl_pct       DOUBLE,
    pnl_usd       DOUBLE,
    status        VARCHAR NOT NULL DEFAULT 'open',   -- open / closed
    created_at    TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status);
CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol);

CREATE TABLE IF NOT EXISTS orders (
    id            INTEGER PRIMARY KEY DEFAULT nextval('orders_id_seq'),
    symbol        VARCHAR NOT NULL,
    side          VARCHAR NOT NULL,          -- BUY / SELL
    status        VARCHAR NOT NULL,          -- pending / executed / cancelled
    suggested_price DOUBLE NOT NULL,
    target_price  DOUBLE,
    stop_loss     DOUBLE,
    weight_pct    DOUBLE,
    capital_usd   DOUBLE,
    rationale     TEXT,
    reason_code   VARCHAR,                   -- exit için: TARGET_HIT, STOP_HIT, SIGNAL_FLIP, MAX_HOLDING, NEGATIVE_NEWS
    related_position_id INTEGER,             -- SELL ise hangi pozisyon
    executed_price DOUBLE,
    executed_at   TIMESTAMP,
    created_at    TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);

CREATE TABLE IF NOT EXISTS signals_history (
    id            INTEGER PRIMARY KEY DEFAULT nextval('signals_id_seq'),
    symbol        VARCHAR NOT NULL,
    direction     VARCHAR NOT NULL,
    confidence    DOUBLE NOT NULL,
    entry_price   DOUBLE,
    target_price  DOUBLE,
    stop_loss     DOUBLE,
    technical_score DOUBLE,
    sentiment_score DOUBLE,
    rationale     TEXT,
    risk_factors  TEXT,                      -- JSON array string
    raw_signal    JSON,                      -- tam Signal nesnesi
    generated_at  TIMESTAMP NOT NULL,
    refresh_mode  VARCHAR                    -- pre_open / post_close / manual
);

CREATE INDEX IF NOT EXISTS idx_signals_symbol_date ON signals_history(symbol, generated_at);
"""


def init_schema() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(DB_PATH)) as conn:
        conn.execute(SCHEMA)


@contextmanager
def connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(DB_PATH))
    try:
        yield conn
    finally:
        conn.close()
