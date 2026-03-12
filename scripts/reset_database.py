#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from flight_scanner.config import load_config
from flight_scanner.db import reset_database
from flight_scanner.logging_utils import ensure_dir, write_error_log


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default=str(ROOT / 'config' / 'default.yaml'))
    args = parser.parse_args()
    config = load_config(args.config)
    log_dir = ROOT / config['data']['log_dir']
    ensure_dir(log_dir)
    try:
        db_path = ROOT / config['data']['db_path']
        reset_database(db_path)
        print(f'reset_database_ok path={db_path}')
        return 0
    except Exception as exc:
        log_path = write_error_log(log_dir, 'reset_database_error', exc, context='scripts/reset_database.py')
        print(f'ERROR: {exc}')
        print(f'error_log={log_path}')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
