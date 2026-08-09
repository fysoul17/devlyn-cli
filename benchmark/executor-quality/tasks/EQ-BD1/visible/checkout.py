"""Checkout presentation built on normalized carrier quotes."""

from rates import Quote, normalize_quotes


def format_option(quote: Quote) -> dict:
    return {
        "service_code": quote.service_code,
        "eta_days": quote.eta_days,
        "price_cents": quote.price_cents,
    }


def build_checkout(raw_quotes: list[dict]) -> dict:
    quotes = normalize_quotes(raw_quotes)
    return {
        "recommended": quotes[0].service_code if quotes else None,
        "options": [format_option(quote) for quote in quotes],
    }
