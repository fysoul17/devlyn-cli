# Bank transfer fixture

`executeTransferBatch` coordinates the decision records returned by `MandateCheck` with the double-entry state owned by `LedgerWriter`.

`MandateCheck.review` returns one decision per instruction in submission order; it does not move denied decisions ahead of approvals.

Run the visible tests from this directory:

```sh
node --test
```

The project requires Node 20 or newer and has no third-party dependencies.
