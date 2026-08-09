"""Carrier-rate normalization."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Quote:
    service_code: str
    eta_days: int
    price_cents: int


def parse_quote(raw: dict) -> Quote:
    """Convert one carrier response into a quote."""
    return Quote(
        service_code=str(raw["service_code"]),
        eta_days=int(raw["eta_days"]),
        price_cents=int(raw["price_cents"]),
    )


def normalize_quotes(raw_quotes: list[dict]) -> list[Quote]:
    """Convert carrier responses for checkout consumption."""
    raise NotImplementedError("quote normalization is not implemented")
