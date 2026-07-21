"""Configuration for the deduplication pipeline.

All knobs are here and overridable from environment variables so the same code
runs against SQLite in development and PostgreSQL in production.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Config:
    # --- database ---
    # SQLite for dev; set DATABASE_URL=postgresql+psycopg2://user:pass@host/db for prod.
    db_url: str = "sqlite:///moldedup.db"

    # --- HTTP / resolver behaviour ---
    request_timeout: float = 20.0      # seconds per HTTP request
    min_request_interval: float = 0.25 # >= 0.2s → <=5 req/s (PubChem's published ceiling)
    max_retries: int = 4               # retries on 5xx / timeouts / "ServerBusy"
    backoff_base: float = 0.5          # exponential backoff base (seconds)
    user_agent: str = "moldedup/1.0 (molecular-dedup-pipeline)"

    # --- cache ---
    cache_path: str = ".moldedup_cache.sqlite"  # persistent HTTP cache
    cache_ttl: float | None = None               # seconds; None = never expire

    # --- logging ---
    log_level: str = "INFO"

    @classmethod
    def from_env(cls, **overrides) -> "Config":
        """Build a Config from environment variables, then apply explicit overrides."""
        cfg = cls(
            db_url=os.environ.get("DATABASE_URL", cls.db_url),
            request_timeout=float(os.environ.get("MOLDEDUP_TIMEOUT", cls.request_timeout)),
            min_request_interval=float(os.environ.get("MOLDEDUP_MIN_INTERVAL", cls.min_request_interval)),
            max_retries=int(os.environ.get("MOLDEDUP_MAX_RETRIES", cls.max_retries)),
            backoff_base=float(os.environ.get("MOLDEDUP_BACKOFF", cls.backoff_base)),
            user_agent=os.environ.get("MOLDEDUP_USER_AGENT", cls.user_agent),
            cache_path=os.environ.get("MOLDEDUP_CACHE", cls.cache_path),
            cache_ttl=(float(os.environ["MOLDEDUP_CACHE_TTL"]) if os.environ.get("MOLDEDUP_CACHE_TTL") else cls.cache_ttl),
            log_level=os.environ.get("MOLDEDUP_LOG_LEVEL", cls.log_level),
        )
        for k, v in overrides.items():
            setattr(cfg, k, v)
        return cfg
