from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import requests


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AmadeusApiClient:
    def __init__(self, config: dict):
        provider_cfg = config['providers']['amadeus']
        self.base_url = provider_cfg['base_url'].rstrip('/')
        self.api_key = provider_cfg.get('api_key') or os.environ.get(provider_cfg['api_key_env'])
        self.api_secret = provider_cfg.get('api_secret') or os.environ.get(provider_cfg['api_secret_env'])
        if not self.api_key or not self.api_secret:
            raise RuntimeError('Missing Amadeus API credentials in config or environment')
        self._access_token: str | None = None

    def _get_token(self) -> str:
        if self._access_token:
            return self._access_token
        resp = requests.post(
            f'{self.base_url}/v1/security/oauth2/token',
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            data={
                'grant_type': 'client_credentials',
                'client_id': self.api_key,
                'client_secret': self.api_secret,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        token = data.get('access_token')
        if not token:
            raise RuntimeError('No access_token returned by Amadeus')
        self._access_token = token
        return token

    def search(self, query: dict, currency: str = 'EUR', adults: int = 1) -> list[dict[str, Any]]:
        token = self._get_token()
        resp = requests.get(
            f'{self.base_url}/v2/shopping/flight-offers',
            headers={'Authorization': f'Bearer {token}'},
            params={
                'originLocationCode': query['origin'],
                'destinationLocationCode': query['destination'],
                'departureDate': query['departure_date'],
                'returnDate': query['return_date'],
                'adults': adults,
                'currencyCode': currency,
                'max': 5,
            },
            timeout=60,
        )
        resp.raise_for_status()
        payload = resp.json()
        offers = payload.get('data', [])
        carriers = payload.get('dictionaries', {}).get('carriers', {})
        normalized = []
        for offer in offers:
            validating = offer.get('validatingAirlineCodes', [])
            airline_code = validating[0] if validating else None
            normalized.append({
                'source': 'amadeus_api',
                'origin': query['origin'],
                'destination': query['destination'],
                'departure_date': query['departure_date'],
                'return_date': query['return_date'],
                'price': float(offer.get('price', {}).get('total')) if offer.get('price', {}).get('total') else None,
                'currency': offer.get('price', {}).get('currency'),
                'airline': carriers.get(airline_code, airline_code),
                'stops': None,
                'duration_text': None,
                'departure_time': None,
                'arrival_time': None,
                'fetched_at': _now_iso(),
                'raw_payload': offer,
            })
        return normalized
