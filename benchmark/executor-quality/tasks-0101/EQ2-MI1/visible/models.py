"""Input normalization for auction bids."""

from errors import AuctionError


def normalize_bid(raw: dict) -> dict:
    try:
        bid_id = str(raw["id"])
        bidder = str(raw["bidder"])
        lot = str(raw["lot"])
        amount = int(raw["amount"])
        fee = int(raw.get("fee", 0))
    except (KeyError, TypeError, ValueError) as exc:
        raise AuctionError("invalid auction bid") from exc
    if not bid_id or not bidder or not lot or amount < 0 or fee < 0:
        raise AuctionError("invalid auction bid")
    return {"id": bid_id, "bidder": bidder, "lot": lot, "amount": amount, "fee": fee}
