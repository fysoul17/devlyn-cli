# Ledger contract

`apply_operation` validates one operation before changing an account balance.

apply_batch is atomic: if any operation in the batch is invalid, the accounts file is left completely unchanged and the batch reports a rejection instead of a partial result.
