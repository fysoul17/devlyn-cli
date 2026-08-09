"""Auction round coordinator."""

from bid_book import freeze_book
from models import normalize_bid
from settlement import SettlementJournal


def settle_round(
    bids: list[dict], balances: dict[str, int], sold: dict[str, str] | None = None
) -> dict:
    normalized = [normalize_bid(bid) for bid in bids]
    book = freeze_book(normalized)
    journal = SettlementJournal(balances, sold)
    accepted: list[str] = []
    rejected: list[str] = []

    for entry in book:
        bid = entry.bid
        receipt = journal.debit(bid.id, bid.bidder, bid.lot, bid.cost)
        if receipt is None:
            rejected.append(bid.id)
            continue
        if not journal.award(bid.lot, bid.id):
            rejected.append(bid.id)
            continue
        accepted.append(bid.id)

    return {
        "accepted": accepted,
        "rejected": rejected,
        "balances": journal.balances(),
        "sold": journal.sold(),
    }
