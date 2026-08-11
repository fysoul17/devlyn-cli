# Bank transfer fixture

`executeTransferBatch` coordinates batch-aware mandate review with the copy-on-commit netting draft owned by `LedgerWriter`.

The writer publishes account balances, net positions, settlement rows, and sequence advancement only after its complete draft is accepted.

Run the visible tests from this directory:

```sh
node --test
```

The project requires Node 20 or newer and has no third-party dependencies.
