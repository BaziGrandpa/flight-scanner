from __future__ import annotations

import json
from datetime import datetime
from zoneinfo import ZoneInfo

from .db import connect, insert_results
from .fx import FxConverter
from .models import FlightResult
from .providers.amadeus_api import AmadeusApiClient
from .providers.trip_verifier import TripVerifier
from .query_builder import build_api_queries, build_local_neighborhood

TZ = ZoneInfo('Europe/Berlin')


def _run_id() -> str:
    return datetime.now(TZ).isoformat()


def _to_model(run_id: str, item: dict) -> FlightResult:
    return FlightResult(
        run_id=run_id,
        source=item['source'],
        origin=item['origin'],
        destination=item['destination'],
        departure_date=item['departure_date'],
        return_date=item['return_date'],
        price=item.get('price'),
        currency=item.get('currency'),
        airline=item.get('airline'),
        stops=item.get('stops'),
        duration_text=item.get('duration_text'),
        departure_time=item.get('departure_time'),
        arrival_time=item.get('arrival_time'),
        fetched_at=item['fetched_at'],
        raw_json=json.dumps(item.get('raw_payload', {}), ensure_ascii=False),
    )


def run_scan(config: dict) -> dict:
    run_id = _run_id()
    search_cfg = config['search']

    api_queries = build_api_queries(
        origins=config['origins'],
        destinations=config['destinations'],
        departure_start=config['departure_window']['start'],
        departure_end=config['departure_window']['end'],
        min_trip_days=config['trip_length_days']['min'],
        max_trip_days=config['trip_length_days']['max'],
        max_api_queries=search_cfg['max_api_queries'],
    )

    api_client = AmadeusApiClient(config)
    api_results_raw = []
    for query in api_queries:
        api_results_raw.extend(
            api_client.search(
                query,
                currency=search_cfg.get('api_request_currency', 'EUR'),
                adults=search_cfg.get('adults', 1),
            )
        )
    api_results_raw = [r for r in api_results_raw if r.get('price') is not None]

    target_currency = search_cfg.get('target_currency', 'CNY')
    fx = FxConverter(target_currency)
    fx.warm(r.get('currency') for r in api_results_raw)

    converted_api_results = []
    for item in api_results_raw:
        item = dict(item)
        original_price = item.get('price')
        original_currency = item.get('currency')
        converted_price, converted_currency, fx_rate = fx.convert(original_price, original_currency)
        item['price'] = converted_price
        item['currency'] = converted_currency
        item['raw_payload'] = {
            'original_price': original_price,
            'original_currency': original_currency,
            'fx_rate_to_target': fx_rate,
            'provider_payload': item.get('raw_payload'),
        }
        converted_api_results.append(item)
    converted_api_results.sort(key=lambda x: x['price'])

    seeds = converted_api_results[: search_cfg.get('cheapest_seed_count', 2)]

    trip_queries = []
    for seed in seeds:
        trip_queries.extend(build_local_neighborhood(seed))

    deduped_trip_queries = []
    seen = set()
    for q in trip_queries:
        key = (q['origin'], q['destination'], q['departure_date'], q['return_date'])
        if key in seen:
            continue
        seen.add(key)
        deduped_trip_queries.append(q)

    verifier = TripVerifier(config)
    verified_raw = verifier.verify_queries(deduped_trip_queries)
    fx.warm(r.get('currency') for r in verified_raw)

    verified_items = []
    for item in verified_raw:
        item = dict(item)
        original_price = item.get('price')
        original_currency = item.get('currency')
        converted_price, converted_currency, fx_rate = fx.convert(original_price, original_currency)
        item['price'] = converted_price
        item['currency'] = converted_currency
        item['source'] = 'trip_verifier'
        raw_payload = item.get('raw_payload', {})
        item['raw_payload'] = {
            'original_price': original_price,
            'original_currency': original_currency,
            'fx_rate_to_target': fx_rate,
            **raw_payload,
        }
        verified_items.append(item)
    verified_items.sort(key=lambda x: (x.get('price') is None, x.get('price') or 999999))

    models = [_to_model(run_id, item) for item in verified_items]

    db_path = config['data']['db_path']
    conn = connect(db_path)
    inserted = insert_results(conn, models)
    conn.close()

    return {
        'run_id': run_id,
        'api_queries_run': len(api_queries),
        'api_results_count': len(api_results_raw),
        'seed_count': len(seeds),
        'trip_queries_run': len(deduped_trip_queries),
        'verified_results': models,
        'inserted_count': inserted,
    }
