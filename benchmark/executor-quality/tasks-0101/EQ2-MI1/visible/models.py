"""Input normalization for auction bids."""

from dataclasses import dataclass

from errors import AuctionError


@dataclass(frozen=True)
class Bid:
    id: str
    bidder: str
    lot: str
    amount: int
    fee: int

    @property
    def cost(self) -> int:
        return self.amount + self.fee


def normalize_bid(raw: dict) -> Bid:
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
    return Bid(bid_id, bidder, lot, amount, fee)
