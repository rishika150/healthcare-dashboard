"""Shared helpers: paths, .env loading, MySQL engine, and a tiny SQL-file runner."""
from __future__ import annotations

import os
import re
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
SQL_DIR = ROOT / "sql"
DOCS_DATA_DIR = ROOT / "docs" / "data"

RAW_CSV = RAW_DIR / "diabetic_data.csv"
IDS_CSV = RAW_DIR / "IDS_mapping.csv"


def load_env() -> None:
    """Read KEY=VALUE pairs from .env without overriding real environment variables."""
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def db_name() -> str:
    load_env()
    return os.environ.get("DB_NAME", "diabetes_readmission")


def get_engine(with_db: bool = True) -> Engine:
    load_env()
    user = os.environ.get("DB_USER", "root")
    password = os.environ.get("DB_PASSWORD", "")
    host = os.environ.get("DB_HOST", "127.0.0.1")
    port = os.environ.get("DB_PORT", "3306")
    database = f"/{db_name()}" if with_db else "/"
    url = f"mysql+pymysql://{user}:{password}@{host}:{port}{database}?charset=utf8mb4"
    return create_engine(url, pool_pre_ping=True)


def split_sql(sql: str) -> list[str]:
    """Split a .sql file into statements. Statements end with ';' at end of line."""
    sql = re.sub(r"--[^\n]*", "", sql)
    parts = re.split(r";\s*(?:\n|$)", sql)
    return [p.strip() for p in parts if p.strip()]


def run_sql_file(engine: Engine, name: str) -> None:
    statements = split_sql((SQL_DIR / name).read_text(encoding="utf-8"))
    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))
    print(f"  ran {name} ({len(statements)} statements)")
