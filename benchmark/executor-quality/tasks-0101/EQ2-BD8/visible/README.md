# Batched rate-limit configuration fixture

The fixture separates gate-owned approval and decision history from limit-writer validation and persistence. `admin-gate.js` composes the boundary for each request in a batch.

Run the tests with:

```sh
node --test
```
