"""DB engine factory — Postgres production + DuckDB local dev otomatik route.

DATABASE_URL formatları:
  postgresql+psycopg://user:pass@host:5432/dbname   — Neon Postgres
  duckdb:///path/to/file.duckdb                       — local DuckDB
  sqlite:///path/to/file.db                          — fallback
"""
from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from finllm.config.settings import settings
from finllm.storage.models import Base
from finllm.utils.logging import logger

_engine = None
_SessionLocal: sessionmaker | None = None


def _resolve_url() -> str:
    """v2 SQLAlchemy modelleri için DB URL'i çöz.

    - DuckDB v2 models için SERIAL desteği yok → SQLite fallback (local dev)
    - Postgres production'da tam destek
    - SQLite/Postgres explicit URL'ler direkt kullanılır
    """
    url = settings.database_url

    if url.startswith("duckdb://"):
        # v2 modeller için SQLite'a yönlendir (legacy DuckDB ayrı kalıyor)
        from finllm.config.settings import DATA_DIR

        sqlite_path = DATA_DIR / "finllm_v2.db"
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{sqlite_path}"

    return url


def get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        url = _resolve_url()
        connect_args = {}
        # SQLite ve DuckDB için single-connection optimizasyon
        if url.startswith("sqlite") or url.startswith("duckdb"):
            connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}

        _engine = create_engine(
            url,
            echo=False,
            future=True,
            connect_args=connect_args,
            pool_pre_ping=True,
        )
        _SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=_engine, expire_on_commit=False
        )
        logger.info(f"[DB] engine initialized: {url.split('@')[-1] if '@' in url else url}")
    return _engine


def init_schema() -> None:
    """Tüm tabloları oluştur — Alembic yerine geliştirme için."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    logger.info(f"[DB] schema created/verified ({len(Base.metadata.tables)} tables)")


@contextmanager
def session_scope() -> Session:
    """Context manager — auto commit + rollback on error."""
    if _SessionLocal is None:
        get_engine()
    assert _SessionLocal is not None
    sess = _SessionLocal()
    try:
        yield sess
        sess.commit()
    except Exception:
        sess.rollback()
        raise
    finally:
        sess.close()


__all__ = ["get_engine", "init_schema", "session_scope"]
