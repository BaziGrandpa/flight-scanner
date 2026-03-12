from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Optional


@dataclass
class FlightResult:
    run_id: str
    source: str
    origin: str
    destination: str
    departure_date: str
    return_date: str
    price: Optional[float]
    currency: Optional[str]
    airline: Optional[str]
    stops: Optional[str]
    duration_text: Optional[str]
    departure_time: Optional[str]
    arrival_time: Optional[str]
    fetched_at: str
    raw_json: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
