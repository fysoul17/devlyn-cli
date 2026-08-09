"""Auction round coordinator."""

from bid_book import order_bids
from models import normalize_bid
from settlement import Settlement


def settle_round(
    bids: list[dict], balances: dict[str, int], sold: dict[str, str] | None = None
) -> dict:
    normalized = [normalize_bid(bid) for bid in bids]
    state = Settlement(balances, sold)
    accepted: list[str] = []
    rejected: list[str] = []

    for bid in order_bids(normalized):
        cost = bid["amount"] + bid["fee"]
        if not state.debit(bid["bidder"], cost):
            rejected.append(bid["id"])
            continue
        if not state.claim(bid["lot"], bid["id"]):
            rejected.append(bid["id"])
            continue
        accepted.append(bid["id"])

    return {
        "accepted": accepted,
        "rejected": rejected,
        "balances": state.balances(),
        "sold": state.sold(),
    }
