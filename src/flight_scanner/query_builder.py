from __future__ import annotations

from datetime import date, timedelta
from itertools import product


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def generate_route_pairs(origins: list[str], destinations: list[str]) -> list[tuple[str, str]]:
    return list(product(origins, destinations))


def evenly_spaced_dates(start: str, end: str, count: int) -> list[str]:
    start_d = parse_date(start)
    end_d = parse_date(end)
    days = (end_d - start_d).days
    if days < 0:
        raise ValueError('departure_window end must be >= start')
    if count <= 1 or days == 0:
        return [start_d.isoformat()]
    positions = sorted(set(round(i * days / (count - 1)) for i in range(count)))
    return [(start_d + timedelta(days=pos)).isoformat() for pos in positions]


def representative_trip_lengths(min_days: int, max_days: int, count: int = 2) -> list[int]:
    if min_days > max_days:
        raise ValueError('trip_length_days.min must be <= max')
    if count <= 1 or min_days == max_days:
        return [min_days]
    if count == 2:
        return sorted(set([min_days, max_days]))
    mid = (min_days + max_days) // 2
    return sorted(set([min_days, mid, max_days]))


def build_api_queries(origins: list[str], destinations: list[str], departure_start: str, departure_end: str, min_trip_days: int, max_trip_days: int, max_api_queries: int) -> list[dict]:
    route_pairs = generate_route_pairs(origins, destinations)
    dep_samples = evenly_spaced_dates(departure_start, departure_end, 2)
    trip_samples = representative_trip_lengths(min_trip_days, max_trip_days, 2)
    queries = []
    for origin, destination in route_pairs:
        for dep in dep_samples:
            dep_date = parse_date(dep)
            for trip_len in trip_samples:
                queries.append({
                    'origin': origin,
                    'destination': destination,
                    'departure_date': dep,
                    'return_date': (dep_date + timedelta(days=trip_len)).isoformat(),
                })
    return queries[:max_api_queries]


def build_local_neighborhood(seed: dict) -> list[dict]:
    dep = parse_date(seed['departure_date'])
    ret = parse_date(seed['return_date'])
    points = [
        (dep - timedelta(days=1), ret),
        (dep, ret),
        (dep + timedelta(days=1), ret),
        (dep, ret - timedelta(days=1)),
        (dep, ret + timedelta(days=1)),
    ]
    out = []
    for d, r in points:
        out.append({
            'origin': seed['origin'],
            'destination': seed['destination'],
            'departure_date': d.isoformat(),
            'return_date': r.isoformat(),
        })
    deduped = []
    seen = set()
    for item in out:
        key = (item['origin'], item['destination'], item['departure_date'], item['return_date'])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped
