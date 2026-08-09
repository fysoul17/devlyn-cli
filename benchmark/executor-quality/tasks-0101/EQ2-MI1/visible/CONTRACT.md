# Auction settlement contract

The bid book chooses evaluation order before settlement updates balances and sold lots.

Bid book entries settle by descending amount with arrival order breaking ties, every rejected claim refunds its tentative debit, and when reordering makes a middle bid fail after its debit the highest bid still wins while a later bid from the refunded account can settle another lot.

`settle_round(bids, balances, sold=None)` returns accepted and rejected bid ids in evaluation order together with final balances and sold lots.
