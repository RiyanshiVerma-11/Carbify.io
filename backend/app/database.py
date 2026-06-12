"""
backend/app/database.py
─────────────────────────────────────────────────────────────
SQLAlchemy engine, session factory, and declarative base.

The module exposes a ``get_db()`` generator suitable for use as a
FastAPI dependency — it yields a scoped ``Session`` and guarantees
cleanup on exit.
"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from backend.app.config import settings

# For SQLite, we specify connect_args={"check_same_thread": False}
# because FastAPI might access the database from multiple threads.
connect_args: dict[str, bool] = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Yield a database session and close it after the request completes.

    Usage as a FastAPI dependency::

        @app.get("/items")
        def list_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


__all__ = ["engine", "Base", "SessionLocal", "get_db"]
