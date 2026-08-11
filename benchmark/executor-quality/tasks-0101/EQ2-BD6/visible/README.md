# Warehouse pick-wave fixture

The service executes a wave of bin picks against an in-memory inventory store.
Rows that cannot be picked are handed to a separate shortage reporter.

Repair `executePickWave` in `pick_executor.js` without changing the reporter,
store encoding, or public result shapes. Run the suite from this directory:

```sh
node --test
```
