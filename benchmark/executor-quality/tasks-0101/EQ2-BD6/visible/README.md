# Warehouse pick-wave fixture

The service executes a wave of zoned bin picks against an in-memory inventory
store. Rejected rows are handed to a reporter that keeps a shortage ledger
across waves.

Repair `executePickWave` in `pick_executor.js` without changing the reporter,
store encoding, or public result shapes. Run the suite from this directory:

```sh
node --test
```
