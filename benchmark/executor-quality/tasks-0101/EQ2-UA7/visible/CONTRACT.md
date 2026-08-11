# Inventory transfer contract

Rejected transfer batches restore the serialized multi-location stock ledger byte-for-byte to its pre-batch form, the discrepancy reporter ranks invalid quantity before destination lock before destination capacity with source order breaking equal-reason ties, and when an earlier move plus a later unpaired source debit precede validation and conflict failures the highest-priority discrepancy is returned with zero per-location drift across every touched endpoint.

`move_batch` owns the boundary around the stock mover. For each structurally
valid transfer, source stock is reserved before the destination's lock and
capacity checks run; a rejected destination can therefore leave an unpaired
source debit unless the whole batch boundary restores it.

`DiscrepancyReporter.build` compares the stock ledger at batch entry with the
ledger presented after rollback. Its report contains every discrepancy in
business order and any remaining `(location, sku, quantity)` drift. A rejected
batch must reach the reporter only after all touched locations have returned to
their entry values.
