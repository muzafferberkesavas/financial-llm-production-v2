"""DuckDB CRUD layer'ı portfolio için."""
from __future__ import annotations

import json
from datetime import datetime

from finllm.portfolio.models import Order, Position
from finllm.signals.schema import Signal
from finllm.storage.db import connection, init_schema


def ensure_schema() -> None:
    init_schema()


# ---------- Positions ----------

def insert_position(p: Position) -> int:
    with connection() as c:
        row = c.execute(
            """
            INSERT INTO positions (symbol, entry_price, entry_date, target_price, stop_loss,
                max_holding_days, weight_pct, capital_usd, entry_confidence,
                entry_rationale, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id
            """,
            [
                p.symbol, p.entry_price, p.entry_date, p.target_price, p.stop_loss,
                p.max_holding_days, p.weight_pct, p.capital_usd, p.entry_confidence,
                p.entry_rationale, p.status,
            ],
        ).fetchone()
        return int(row[0])


def close_position(position_id: int, exit_price: float, exit_reason: str) -> None:
    with connection() as c:
        # PnL hesapla
        row = c.execute("SELECT entry_price, capital_usd FROM positions WHERE id=?", [position_id]).fetchone()
        if not row:
            return
        entry_price, capital = float(row[0]), float(row[1])
        pnl_pct = (exit_price / entry_price - 1) * 100
        pnl_usd = capital * (pnl_pct / 100)
        c.execute(
            """
            UPDATE positions
            SET status='closed', exit_price=?, exit_date=?, exit_reason=?,
                pnl_pct=?, pnl_usd=?
            WHERE id=?
            """,
            [exit_price, datetime.utcnow(), exit_reason, pnl_pct, pnl_usd, position_id],
        )


def open_positions() -> list[Position]:
    with connection() as c:
        rows = c.execute("SELECT * FROM positions WHERE status='open' ORDER BY entry_date").fetchall()
        cols = [d[0] for d in c.description]
    return [Position(**dict(zip(cols, r))) for r in rows]


def all_positions(limit: int = 100) -> list[Position]:
    with connection() as c:
        rows = c.execute(
            "SELECT * FROM positions ORDER BY created_at DESC LIMIT ?", [limit]
        ).fetchall()
        cols = [d[0] for d in c.description]
    return [Position(**dict(zip(cols, r))) for r in rows]


# ---------- Orders ----------

def insert_order(o: Order) -> int:
    with connection() as c:
        row = c.execute(
            """
            INSERT INTO orders (symbol, side, status, suggested_price, target_price,
                stop_loss, weight_pct, capital_usd, rationale, reason_code, related_position_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id
            """,
            [
                o.symbol, o.side, o.status, o.suggested_price, o.target_price,
                o.stop_loss, o.weight_pct, o.capital_usd, o.rationale, o.reason_code,
                o.related_position_id,
            ],
        ).fetchone()
        return int(row[0])


def pending_orders() -> list[Order]:
    with connection() as c:
        rows = c.execute("SELECT * FROM orders WHERE status='pending' ORDER BY created_at DESC").fetchall()
        cols = [d[0] for d in c.description]
    return [Order(**dict(zip(cols, r))) for r in rows]


def execute_buy_order(order_id: int, executed_price: float) -> int:
    """BUY emrini executed işaretle ve karşılığında bir Position yarat."""
    with connection() as c:
        row = c.execute("SELECT * FROM orders WHERE id=?", [order_id]).fetchone()
        if not row:
            raise ValueError(f"Order {order_id} not found")
        cols = [d[0] for d in c.description]
        order = dict(zip(cols, row))
        if order["status"] != "pending":
            raise ValueError(f"Order {order_id} not pending (status={order['status']})")
        if order["side"] != "BUY":
            raise ValueError(f"Order {order_id} is not BUY")
        c.execute(
            "UPDATE orders SET status='executed', executed_price=?, executed_at=? WHERE id=?",
            [executed_price, datetime.utcnow(), order_id],
        )

    position = Position(
        symbol=order["symbol"],
        entry_price=executed_price,
        entry_date=datetime.utcnow(),
        target_price=order["target_price"],
        stop_loss=order["stop_loss"],
        weight_pct=order["weight_pct"] or 0.0,
        capital_usd=order["capital_usd"] or 0.0,
        entry_rationale=order["rationale"],
        status="open",
    )
    return insert_position(position)


def execute_sell_order(order_id: int, executed_price: float) -> None:
    """SELL emrini executed işaretle ve ilgili Position'ı kapat."""
    with connection() as c:
        row = c.execute("SELECT * FROM orders WHERE id=?", [order_id]).fetchone()
        if not row:
            raise ValueError(f"Order {order_id} not found")
        cols = [d[0] for d in c.description]
        order = dict(zip(cols, row))
        if order["status"] != "pending":
            raise ValueError(f"Order {order_id} not pending")
        c.execute(
            "UPDATE orders SET status='executed', executed_price=?, executed_at=? WHERE id=?",
            [executed_price, datetime.utcnow(), order_id],
        )
    if order["related_position_id"]:
        close_position(order["related_position_id"], executed_price, order["reason_code"] or "MANUAL")


def cancel_pending_orders(side: str | None = None) -> int:
    with connection() as c:
        if side:
            r = c.execute(
                "UPDATE orders SET status='cancelled' WHERE status='pending' AND side=? RETURNING id",
                [side],
            ).fetchall()
        else:
            r = c.execute(
                "UPDATE orders SET status='cancelled' WHERE status='pending' RETURNING id"
            ).fetchall()
    return len(r)


# ---------- Signals history ----------

def log_signal(s: Signal, refresh_mode: str = "manual") -> None:
    with connection() as c:
        c.execute(
            """
            INSERT INTO signals_history (symbol, direction, confidence, entry_price,
                target_price, stop_loss, technical_score, sentiment_score, rationale,
                risk_factors, raw_signal, generated_at, refresh_mode)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                s.symbol, s.direction, s.confidence, s.entryPrice,
                s.targetPrice, s.stopLoss,
                s.signals.technical.score, s.signals.sentiment.score,
                s.rationale, json.dumps(s.riskFactors),
                s.model_dump_json(), s.generatedAt, refresh_mode,
            ],
        )


# ---------- Stats ----------

def portfolio_stats() -> dict:
    with connection() as c:
        realized = c.execute(
            "SELECT COALESCE(SUM(pnl_usd), 0) FROM positions WHERE status='closed'"
        ).fetchone()[0]
        open_count = c.execute("SELECT COUNT(*) FROM positions WHERE status='open'").fetchone()[0]
        pending_count = c.execute("SELECT COUNT(*) FROM orders WHERE status='pending'").fetchone()[0]
        win_loss = c.execute(
            """SELECT
                SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END),
                SUM(CASE WHEN pnl_pct <= 0 THEN 1 ELSE 0 END)
               FROM positions WHERE status='closed'"""
        ).fetchone()
    wins = int(win_loss[0] or 0)
    losses = int(win_loss[1] or 0)
    total = wins + losses
    return {
        "realized_pnl_usd": float(realized),
        "open_positions": int(open_count),
        "pending_orders": int(pending_count),
        "closed_positions": total,
        "wins": wins,
        "losses": losses,
        "win_rate": (wins / total) if total else None,
    }
