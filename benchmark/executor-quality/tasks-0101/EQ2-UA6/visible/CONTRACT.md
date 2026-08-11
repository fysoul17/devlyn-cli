# Bank transfer batch contract

Mandates are reviewed as a complete decision set, while the ledger writer owns the double-entry balances, posting journal, and next posting sequence.

When a transfer batch mixes authorized and unauthorized instructions, all mandate decisions must be collected and the batch authorized before the ledger writer records any debit or credit, the denied instruction must abort the whole batch with balances, posting journal, and sequence exactly at their pre-batch values, and any ledger posting or journal failure must roll back that same complete ledger state.

Callers receive either one committed receipt for the batch or the first denied instruction. A failed batch is safe to submit again.
