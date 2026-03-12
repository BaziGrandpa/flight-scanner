from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from typing import Iterable

from .models import FlightResult


CURRENCY_SYMBOLS = {
    'CNY': '¥',
    'USD': '$',
    'EUR': '€',
}


def _fmt_price(currency: str | None, price: float | None) -> str:
    if price is None:
        return '?'
    symbol = CURRENCY_SYMBOLS.get((currency or '').upper(), '')
    if symbol:
        return f'{symbol}{price:,.2f} {currency}'
    return f'{price:,.2f} {currency or ""}'.strip()


def _dedupe_for_report(results: list[FlightResult]) -> list[FlightResult]:
    seen = OrderedDict()
    for item in sorted(results, key=lambda x: (x.price is None, x.price or 999999)):
        key = (item.origin, item.destination, item.departure_date, item.return_date, item.airline, item.price)
        if key not in seen:
            seen[key] = item
    return list(seen.values())


def write_markdown_report(report_path: str | Path, run_id: str, config: dict, api_count: int, browser_count: int, results: Iterable[FlightResult]) -> Path:
    path = Path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    all_results = list(results)
    top = _dedupe_for_report(all_results)[:5]
    currency = config['search'].get('target_currency', 'CNY')

    lines = [
        '# Flight Scanner Daily Summary',
        '',
        '## Scan Overview',
        '',
        f'- **Run ID:** `{run_id}`',
        f"- **Origins:** {', '.join(config['origins'])}",
        f"- **Destinations:** {', '.join(config['destinations'])}",
        f"- **Departure window:** {config['departure_window']['start']} -> {config['departure_window']['end']}",
        f"- **Trip length window:** {config['trip_length_days']['min']} -> {config['trip_length_days']['max']} days",
        f'- **API coarse queries:** {api_count}',
        f'- **Browser-verified results stored:** {browser_count}',
        f'- **Display currency:** {currency}',
        '',
        '## Cheapest Verified Options',
        '',
        '> Prices below are converted locally into the configured target currency for reporting. Original provider currencies may differ from the display currency.',
        '',
    ]

    if not top:
        lines.append('- No verified browser results found.')
    else:
        for idx, item in enumerate(top, start=1):
            lines.extend([
                f'### {idx}. {item.origin} → {item.destination}',
                '',
                f'- **Travel dates:** {item.departure_date} → {item.return_date}',
                f'- **Price:** {_fmt_price(item.currency, item.price)}',
                f'- **Airline:** {item.airline or "?"}',
                f'- **Stops:** {item.stops or "?"}',
                f'- **Duration:** {item.duration_text or "?"}',
                f'- **Departure / arrival:** {item.departure_time or "?"} → {item.arrival_time or "?"}',
                f'- **Source:** {item.source}',
                '',
            ])

    lines.extend([
        '## Notes',
        '',
        '- This run uses the Amadeus **test** API for coarse scanning, so seed quality may differ from production data.',
        '- Final ranking is based on Trip browser verification results gathered after the coarse scan.',
        '- Report output is optimized for Markdown reading and PDF rendering.',
        '',
    ])
    path.write_text('\n'.join(lines), encoding='utf-8')
    return path
