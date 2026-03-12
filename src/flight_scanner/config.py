from __future__ import annotations

from pathlib import Path
from datetime import date, datetime
import yaml


def _normalize(obj):
    if isinstance(obj, dict):
        return {k: _normalize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_normalize(v) for v in obj]
    if isinstance(obj, datetime):
        return obj.date().isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    return obj


def _load_yaml_mapping(path: Path) -> dict:
    with path.open('r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f'Config must be a mapping: {path}')
    return data


def _deep_merge(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(merged.get(key), dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(config_path: str | Path) -> dict:
    path = Path(config_path)
    data = _load_yaml_mapping(path)

    local_path = path.with_name('local.yaml')
    if local_path.exists() and local_path.resolve() != path.resolve():
        local_data = _load_yaml_mapping(local_path)
        data = _deep_merge(data, local_data)

    return _normalize(data)
