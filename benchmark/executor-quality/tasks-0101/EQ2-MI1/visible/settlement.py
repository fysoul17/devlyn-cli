"""Compensating journal for auction settlement."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DebitReceipt:
    sequence: int
    bid_id: str
    bidder: str
    lot: str
    amount: int


@dataclass(frozen=True)
class LedgerEntry:
    kind: str
    receipt: DebitReceipt


class SettlementJournal:
    def __init__(self, balances: dict[str, int], sold: dict[str, str] | None = None) -> None:
        self._balances = dict(balances)
        self._sold = dict(sold or {})
        self._entries: list[LedgerEntry] = []
        self._next_sequence = 0

    def debit(
        self, bid_id: str, bidder: str, lot: str, amount: int
    ) -> DebitReceipt | None:
        if self._balances.get(bidder, 0) < amount:
            return None
        receipt = DebitReceipt(self._next_sequence, bid_id, bidder, lot, amount)
        self._next_sequence += 1
        self._balances[bidder] -= amount
        self._entries.append(LedgerEntry("debit", receipt))
        return receipt

    def compensate(self, receipt: DebitReceipt) -> None:
        self._balances[receipt.bidder] = self._balances.get(receipt.bidder, 0) + receipt.amount
        self._entries.append(LedgerEntry("credit", receipt))

    def award(self, lot: str, bid_id: str) -> bool:
        if lot in self._sold:
            return False
        self._sold[lot] = bid_id
        return True

    def balances(self) -> dict[str, int]:
        return dict(sorted(self._balances.items()))

    def sold(self) -> dict[str, str]:
        return dict(sorted(self._sold.items()))
