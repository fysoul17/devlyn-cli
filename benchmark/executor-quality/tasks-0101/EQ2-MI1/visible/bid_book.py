"""Frozen evaluation plan for auction bids."""

from dataclasses import dataclass

from models import Bid


@dataclass(frozen=True)
class BookEntry:
    bid: Bid
    arrival: int


def freeze_book(bids: list[Bid]) -> tuple[BookEntry, ...]:
    return tuple(BookEntry(bid, arrival) for arrival, bid in enumerate(bids))
