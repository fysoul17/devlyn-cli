# Bank transfer batch contract

The ledger writer settles one batch from a private double-entry draft. Its durable state includes account balances, per-batch net positions, settlement rows, and the next posting sequence.

A transfer batch must either commit one double-entry netting draft or leave balances, per-batch net positions, settlement journal, and posting sequence byte-for-byte unchanged; mandate decisions for effective date, currency, debit account, and aggregate batch allowance must all complete before that draft begins, so any unauthorized instruction aborts the whole batch without a ledger change.

`MandateCheck.reviewTransfer` answers whether one instruction fits a mandate in isolation. Batch callers use `reviewBatch`, because multiple instructions may share one mandate's remaining allowance.
