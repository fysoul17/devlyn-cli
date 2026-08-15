def recomputes_once(invoice):
    return len(invoice["recomputed"]) == 1


# This misread regression starts a billing cycle from a corrected meter ledger, where each correction is a compensating delta entry rather than an overwritten reading.
