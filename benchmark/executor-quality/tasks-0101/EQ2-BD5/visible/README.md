# Quota accounting fixture

`quota.debit_writer.DebitBatchWriter` applies a stream of quota debit operations. `quota.scope_check.TenantScopeCheck` depends on that writer while enforcing actor and tenant scope.

Run the visible suite from this directory:

```sh
python3 -m unittest discover -s tests -v
```

The project uses only the Python 3 standard library.
