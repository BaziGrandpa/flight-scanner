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
from flight_scanner.logging_utils import ensure_dir, write_error_log
from flight_scanner.report import write_markdown_report
from flight_scanner.scan import run_scan


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default=str(ROOT / 'config' / 'default.yaml'))
    args = parser.parse_args()

    config = load_config(args.config)
    log_dir = ROOT / config['data']['log_dir']
    ensure_dir(log_dir)

    try:
        result = run_scan(config)
        report_dir = ROOT / config['data']['report_dir']
        report_path = report_dir / config['data']['latest_report_name']
        write_markdown_report(
            report_path=report_path,
            run_id=result['run_id'],
            config=config,
            api_count=result['api_queries_run'],
            browser_count=result['inserted_count'],
            results=result['verified_results'],
        )
        print(f"run_id={result['run_id']}")
        print(f"api_queries_run={result['api_queries_run']}")
        print(f"api_results_count={result['api_results_count']}")
        print(f"seed_count={result['seed_count']}")
        print(f"trip_queries_run={result['trip_queries_run']}")
        print(f"inserted_count={result['inserted_count']}")
        print(f"report_path={report_path}")
        return 0
    except Exception as exc:
        log_path = write_error_log(log_dir, 'run_scan_error', exc, context='scripts/run_scan.py')
        print(f'ERROR: {exc}')
        print(f'error_log={log_path}')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
