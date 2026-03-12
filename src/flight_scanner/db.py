from __future__ import annotations

import sqlite3
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
'''


def connect(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute(SCHEMA_SQL)
    conn.commit()
    return conn


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
