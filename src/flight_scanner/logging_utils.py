from __future__ import annotations

import traceback
from datetime import datetime, timezone
from pathlib import Path


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def write_error_log(log_dir: str | Path, prefix: str, exc: Exception, context: str | None = None) -> Path:
    log_path = ensure_dir(log_dir) / f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    lines = [
        f"timestamp={utc_now_iso()}",
        f"context={context or ''}",
        f"error_type={type(exc).__name__}",
        f"error_message={exc}",
        '',
        traceback.format_exc(),
    ]
    log_path.write_text('\n'.join(lines), encoding='utf-8')
    return log_path
