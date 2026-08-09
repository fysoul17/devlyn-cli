# Auction settlement contract

The bid book freezes arrivals before the settlement journal updates balances and sold lots in a separate pass.

In a frozen bid book, entries settle by descending amount with arrival order breaking ties, rejected claims are reversed by a compensating ledger credit tied to the exact debit receipt, and when a lower bid arrives first before a middle bid is debited but loses its lot to a reordered higher bid, the higher bid remains the winner while compensating the middle bid's exact receipt lets a later bid from that bidder settle another lot.

Each successful debit returns an immutable receipt, and a rejected claim is compensated with that receipt rather than a lot or bidder lookup.

`settle_round(bids, balances, sold=None)` returns accepted and rejected bid ids in evaluation order together with final balances and sold lots.
