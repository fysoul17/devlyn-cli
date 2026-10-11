# Relay keyed loader

Relay shares asynchronous catalog loads between request handlers. It caches
successful documents, allows an administrator to invalidate a key while old
requests finish, and shuts down outstanding work at service exit.

Fix Relay so request cancellation, invalidation, and backend failures obey the
existing public contract in `docs/contract.md`. Keep the API. Product files are
`relay/*.py`; checks may be added or changed under `checks/`. The example in
`examples/catalog.py` is an ordinary consumer. Run `python3 -B checks/run_checks.py`.
Python 3.11+ standard library only; one asyncio event loop per loader instance.
