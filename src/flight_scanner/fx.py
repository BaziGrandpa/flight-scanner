from __future__ import annotations

from typing import Iterable

import requests


class FxConverter:
    def __init__(self, target_currency: str):
        self.target_currency = target_currency.upper()
        self._rates: dict[str, float] = {self.target_currency: 1.0}

    def warm(self, currencies: Iterable[str]) -> None:
        needed = sorted({c.upper() for c in currencies if c})
        missing = [c for c in needed if c not in self._rates]
        if not missing:
            return
        for currency in missing:
            if currency == self.target_currency:
                self._rates[currency] = 1.0
                continue
            resp = requests.get(
                'https://api.frankfurter.app/latest',
                params={'from': currency, 'to': self.target_currency},
                timeout=20,
            )
            resp.raise_for_status()
            data = resp.json()
            rate = data.get('rates', {}).get(self.target_currency)
            if rate is None:
                raise RuntimeError(f'No FX rate for {currency}->{self.target_currency}')
            self._rates[currency] = float(rate)

    def convert(self, amount: float | None, source_currency: str | None) -> tuple[float | None, str | None, float | None]:
        if amount is None or not source_currency:
            return amount, source_currency, None
        source = source_currency.upper()
        if source not in self._rates:
            self.warm([source])
        rate = self._rates[source]
        converted = round(float(amount) * rate, 2)
        return converted, self.target_currency, rate
