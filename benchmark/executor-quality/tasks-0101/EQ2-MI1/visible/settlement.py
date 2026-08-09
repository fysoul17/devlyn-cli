"""Balance and lot state used while settling bids."""


class Settlement:
    def __init__(self, balances: dict[str, int], sold: dict[str, str] | None = None) -> None:
        self._balances = dict(balances)
        self._sold = dict(sold or {})

    def debit(self, bidder: str, amount: int) -> bool:
        if self._balances.get(bidder, 0) < amount:
            return False
        self._balances[bidder] -= amount
        return True

    def refund(self, bidder: str, amount: int) -> None:
        self._balances[bidder] = self._balances.get(bidder, 0) + amount

    def claim(self, lot: str, bid_id: str) -> bool:
        if lot in self._sold:
            return False
        self._sold[lot] = bid_id
        return True

    def balances(self) -> dict[str, int]:
        return dict(sorted(self._balances.items()))

    def sold(self) -> dict[str, str]:
        return dict(sorted(self._sold.items()))
