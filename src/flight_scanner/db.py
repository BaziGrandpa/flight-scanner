from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .models import FlightResult

SCHEMA_SQL = '''
CREATE TABLE IF NOT EXISTS flight_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL,
  source TEXT NOT NULL,
  origin TEXT NOT NULL,
  destination TEXT NOT NULL,
  departure_date TEXT NOT NULL,
  return_date TEXT NOT NULL,
  price REAL,
  currency TEXT,
  airline TEXT,
  stops TEXT,
  duration_text TEXT,
  departure_time TEXT,
  arrival_time TEXT,
  fetched_at TEXT NOT NULL,
  raw_json TEXT
);

CREATE TABLE IF NOT EXISTS api_query_cache (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  provider TEXT NOT NULL,
  origin TEXT NOT NULL,
  destination TEXT NOT NULL,
  departure_date TEXT NOT NULL,
  return_date TEXT NOT NULL,
  fetched_at TEXT NOT NULL,
  raw_json TEXT NOT NULL
);
'''


def connect(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    return conn


def get_api_cache(conn: sqlite3.Connection, provider: str, query: dict, ttl_hours: int) -> tuple[str, list[dict] | None]:
    row = conn.execute(
        '''SELECT fetched_at, raw_json
           FROM api_query_cache
           WHERE provider = ?
             AND origin = ?
             AND destination = ?
             AND departure_date = ?
             AND return_date = ?
           ORDER BY id DESC
           LIMIT 1''',
        (provider, query['origin'], query['destination'], query['departure_date'], query['return_date']),
    ).fetchone()
    if not row:
        return 'miss', None

    fetched_at = datetime.fromisoformat(row[0])
    age_seconds = (datetime.now(timezone.utc) - fetched_at).total_seconds()
    if age_seconds > ttl_hours * 3600:
        return 'expired', None

    data = json.loads(row[1])
    if not isinstance(data, list):
        return 'miss', None
    return 'hit', data


def put_api_cache(conn: sqlite3.Connection, provider: str, query: dict, fetched_at: str, results: list[dict]) -> None:
    conn.execute(
        '''INSERT INTO api_query_cache (
            provider, origin, destination, departure_date, return_date, fetched_at, raw_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?)''',
        (
            provider,
            query['origin'],
            query['destination'],
            query['departure_date'],
            query['return_date'],
            fetched_at,
            json.dumps(results, ensure_ascii=False),
        ),
    )
    conn.commit()


def insert_results(conn: sqlite3.Connection, results: Iterable[FlightResult]) -> int:
    rows = [(
        r.run_id, r.source, r.origin, r.destination, r.departure_date, r.return_date,
        r.price, r.currency, r.airline, r.stops, r.duration_text, r.departure_time,
        r.arrival_time, r.fetched_at, r.raw_json
    ) for r in results]
    if not rows:
        return 0
    conn.executemany(
        '''INSERT INTO flight_results (
            run_id, source, origin, destination, departure_date, return_date,
            price, currency, airline, stops, duration_text, departure_time,
            arrival_time, fetched_at, raw_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        rows,
    )
    conn.commit()
    return len(rows)


def reset_database(db_path: str | Path) -> None:
    path = Path(db_path)
    if path.exists():
        path.unlink()
