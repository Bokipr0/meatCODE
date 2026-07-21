"""Database engine / session helpers. Works for SQLite (dev) and PostgreSQL (prod)."""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from .models import Base


def build_engine(db_url: str, echo: bool = False) -> Engine:
    """Create an Engine. SQLite gets check_same_thread=False so the cache/threads behave."""
    connect_args = {}
    if db_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(db_url, echo=echo, future=True, connect_args=connect_args)


def build_session_factory(engine: Engine) -> sessionmaker:
    """A configured sessionmaker (call it to get a Session)."""
    # autoflush=True so get-or-create queries see rows added earlier in the same
    # transaction (avoids duplicate synonyms/identifiers within one ingest).
    return sessionmaker(bind=engine, autoflush=True, expire_on_commit=False, future=True)


def init_db(engine: Engine) -> None:
    """Create all tables if they don't already exist (idempotent)."""
    Base.metadata.create_all(engine)
