# Parcel relay

Parcel relay is the local durable outbox used by a document delivery worker.
The producer uses `enqueue`; worker processes use separate `Store` connections
to the same SQLite file and call `process_one`. No network service is required.
Python 3.11+ and its standard library are the only dependencies.

Run `python3 -B checks/run_checks.py`. Operational and API contracts are in
`docs/delivery.md` and `docs/storage.md`; `examples/retry_demo.py` is a tiny caller.
