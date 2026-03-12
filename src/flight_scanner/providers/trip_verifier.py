from __future__ import annotations

import json
import random
import re
import time
from datetime import datetime, timezone
from urllib.parse import urlencode

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


UA_POOL = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_url(origin: str, destination: str, departure_date: str, return_date: str) -> str:
    params = {
        'dcity': origin,
        'acity': destination,
        'dcityname': origin,
        'acityname': destination,
        'ddate': departure_date,
        'rdate': return_date,
        'triptype': 'rt',
        'class': 'y',
        'quantity': '1',
        'searchboxarg': 't',
    }
    return 'https://www.trip.com/flights/showfarefirst?' + urlencode(params)


def _normalize_text(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()


KNOWN_AIRLINES = [
    'Finnair', 'Lufthansa', 'Cathay Pacific', 'British Airways', 'Air France', 'KLM',
    'Turkish Airlines', 'Qatar Airways', 'Emirates', 'SWISS', 'Austrian Airlines',
    'Juneyao Airlines', 'Hainan Airlines', 'Air China', 'China Eastern Airlines',
    'Singapore Airlines', 'Thai Airways', 'LOT Polish Airlines'
]


def _clean_airline(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = re.sub(r'\s+', ' ', value).strip()
    for airline in KNOWN_AIRLINES:
        if airline.lower() in cleaned.lower():
            return airline
    return cleaned


def _extract_cards(text: str, origin: str, destination: str, departure_date: str, return_date: str) -> list[dict]:
    pattern = (
        r'(?P<airline>[A-Z][A-Za-z&\- ]+?)'
        r'(?:\s+operated by[^\d]*)?\s+'
        r'(?P<dep>\d{2}:\d{2})\s+' + re.escape(origin) +
        r'\s+(?P<duration>\d+h\s+\d+m)'
        r'(?:\s+(?P<stopover>\d+h\s+\d+m\s+in\s+[A-Za-z\- ]+))?'
        r'\s+(?P<arr>\d{2}:\d{2})\s+' + re.escape(destination) +
        r'.{0,120}?(?P<price>US\$\s?\d+[\d,]*)'
    )
    matches = re.finditer(pattern, text)
    cards = []
    for m in matches:
        airline = _clean_airline(m.group('airline'))
        price_text = m.group('price').replace(' ', '')
        stopover_text = m.group('stopover').strip() if m.group('stopover') else None
        stops = None
        if stopover_text:
            stops = '1'
        card = {
            'origin': origin,
            'destination': destination,
            'departure_date': departure_date,
            'return_date': return_date,
            'price': float(price_text.replace('US$', '').replace(',', '')) if price_text else None,
            'currency': 'USD' if price_text else None,
            'airline': airline,
            'stops': stops,
            'duration_text': m.group('duration'),
            'departure_time': m.group('dep'),
            'arrival_time': m.group('arr'),
            'fetched_at': _now_iso(),
            'raw_payload': {
                'price_text': price_text,
                'stopover_text': stopover_text,
                'snippet': text[max(0, m.start()-120): min(len(text), m.end()+120)],
            },
        }
        if card['price'] is not None and card['airline']:
            cards.append(card)
    deduped = []
    seen = set()
    for c in cards:
        sig = (c['price'], c['airline'], c['departure_time'], c['arrival_time'], c['duration_text'])
        if sig in seen:
            continue
        seen.add(sig)
        deduped.append(c)
    return deduped

def _safe_is_visible(locator) -> bool:
    try:
        return locator.count() > 0 and locator.first.is_visible()
    except Exception:
        return False

def wait_trip_results_ready(page, timeout=45000, interval_ms=1000, stable_rounds=2) -> bool:
    deadline = time.time() + timeout / 1000
    stable_hits = 0

    while time.time() < deadline:
        frame_signals = [
            _safe_is_visible(page.get_by_text("Recommended", exact=True)),
            _safe_is_visible(page.get_by_text("Alliance", exact=True)),
            _safe_is_visible(page.get_by_text("Choose your flight", exact=False)),
            _safe_is_visible(page.get_by_text("Sort by", exact=True)),
        ]

        result_signals = [
            _safe_is_visible(page.get_by_text("Select", exact=True)),
            _safe_is_visible(page.get_by_text("Round-trip", exact=True)),
            _safe_is_visible(page.get_by_text("Cheapest", exact=True)),
        ]

        frame_ok = sum(frame_signals) >= 2
        result_ok = sum(result_signals) >= 1

        if frame_ok and result_ok:
            stable_hits += 1
            if stable_hits >= stable_rounds:
                return True
        else:
            stable_hits = 0

        page.wait_for_timeout(interval_ms)

    return False


class TripVerifier:
    def __init__(self, config: dict):
        search_cfg = config['search']
        self.sleep_min = int(search_cfg.get('request_spacing_seconds_min', 8))
        self.sleep_max = int(search_cfg.get('request_spacing_seconds_max', 18))

    def verify_queries(self, queries: list[dict]) -> list[dict]:
        results = []
        with sync_playwright() as p:
            for idx, query in enumerate(queries):
                results.extend(self._run_once(p, query))
                if idx < len(queries) - 1:
                    time.sleep(random.randint(self.sleep_min, self.sleep_max))
        return results

    def _run_once(self, playwright, query: dict) -> list[dict]:
        ua = random.choice(UA_POOL)
        browser = playwright.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled', '--lang=en-US'],
        )
        context = browser.new_context(
            locale='en-US',
            timezone_id='Europe/Berlin',
            user_agent=ua,
            viewport={'width': random.choice([1366, 1440, 1536]), 'height': random.choice([900, 1024, 1100])},
            extra_http_headers={'Accept-Language': 'en-US,en;q=0.9', 'DNT': '1'},
        )
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
            window.chrome = { runtime: {} };
        """)
        page = context.new_page()
        try:
            url = _build_url(query['origin'], query['destination'], query['departure_date'], query['return_date'])
            print(f"[trip] start query={query} url={url}")
            page.goto(url, wait_until='domcontentloaded', timeout=60000)
            page.wait_for_timeout(random.randint(2500, 4500))
            # for idx in range(3):
            #     try:
            #         page.wait_for_load_state('networkidle', timeout=7000)
            #         print(f"[trip] networkidle pass={idx + 1} query={query}")
            #     except PlaywrightTimeoutError:
            #         print(f"[trip] networkidle timeout pass={idx + 1} query={query}")
            #     page.wait_for_timeout(random.randint(1800, 3200))
            ok = wait_trip_results_ready(page, timeout=45000, interval_ms=1000)
            if not ok:
                print(f"[trip] results not ready in time, giving up query={query}")
                return []

            text = _normalize_text(page.locator('body').inner_text(timeout=15000))
            text_len = len(text)
            has_price = 'US$' in text or '$' in text
            has_select = 'Select' in text
            has_alliance = 'Alliance' in text
            print(f"[trip] body_summary len={text_len} has_price={has_price} has_select={has_select} has_alliance={has_alliance} query={query}")
            print(f"[trip] body_head query={query} text={text[:500]}")
            cards = _extract_cards(text, query['origin'], query['destination'], query['departure_date'], query['return_date'])
            print(f"[trip] extract_cards count={len(cards)} query={query}")
            return cards
        finally:
            context.close()
            browser.close()
