# Veritabani

## Motorlar

| Ortam | Motor | Baglanti |
|-------|-------|----------|
| Lokal gelistirme | DuckDB | `backend/data/finllm.duckdb` (git-ignored) |
| Production | PostgreSQL 16 | `DATABASE_URL` env var |

Sema tanimi: `backend/src/finllm/storage/db.py`

## Tablolar

### positions

Acik ve kapanmis pozisyonlar.

```sql
CREATE TABLE positions (
    id INTEGER PRIMARY KEY,
    symbol VARCHAR NOT NULL,
    entry_price DOUBLE NOT NULL,
    entry_date TIMESTAMP NOT NULL,
    target_price DOUBLE,
    stop_loss DOUBLE,
    max_holding_days INTEGER DEFAULT 15,
    weight_pct DOUBLE NOT NULL,
    capital_usd DOUBLE NOT NULL,
    entry_confidence DOUBLE,
    entry_rationale TEXT,
    exit_price DOUBLE,
    exit_date TIMESTAMP,
    exit_reason VARCHAR,          -- TARGET_HIT, STOP_HIT, MAX_HOLDING, SIGNAL_FLIP, NEGATIVE_NEWS
    pnl_pct DOUBLE,
    pnl_usd DOUBLE,
    status VARCHAR DEFAULT 'open' -- open / closed
);
CREATE INDEX idx_positions_status ON positions(status);
CREATE INDEX idx_positions_symbol ON positions(symbol);
```

### orders

Bekleyen, gerceklesen ve iptal edilen emirler.

```sql
CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    symbol VARCHAR NOT NULL,
    side VARCHAR NOT NULL,        -- BUY / SELL
    status VARCHAR NOT NULL,      -- pending / executed / cancelled
    suggested_price DOUBLE NOT NULL,
    target_price DOUBLE,
    stop_loss DOUBLE,
    weight_pct DOUBLE,
    capital_usd DOUBLE,
    rationale TEXT,
    reason_code VARCHAR,
    related_position_id INTEGER,
    executed_price DOUBLE,
    executed_at TIMESTAMP
);
CREATE INDEX idx_orders_status ON orders(status);
```

### signals_history

Uretilen sinyal gecmisi.

```sql
CREATE TABLE signals_history (
    id INTEGER PRIMARY KEY,
    symbol VARCHAR NOT NULL,
    direction VARCHAR NOT NULL,   -- BUY / SELL / HOLD
    confidence DOUBLE NOT NULL,
    entry_price DOUBLE,
    target_price DOUBLE,
    stop_loss DOUBLE,
    technical_score DOUBLE,
    sentiment_score DOUBLE,
    rationale TEXT,
    risk_factors TEXT,            -- JSON array string
    raw_signal JSON,              -- Tam Signal objesi
    generated_at TIMESTAMP NOT NULL,
    refresh_mode VARCHAR
);
CREATE INDEX idx_signals_symbol_date ON signals_history(symbol, generated_at);
```

## CRUD

`storage/db.py` ve `portfolio/repository.py` DuckDB/PostgreSQL CRUD islemleri saglar.
