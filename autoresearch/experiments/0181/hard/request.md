Fix `async_map.map_limited(worker, items, limit)`.

It is an async function returning a list of worker results in input order.
`items` is a finite synchronous iterable, possibly one-shot. `worker(item)` is
an async function whose result may be any Python object. Run independent calls
concurrently up to `limit`; a free slot must be usable without waiting for an
earlier input's slower call. At any time, pulled items whose worker calls have
not finished must number at most `limit`; do not eagerly materialize the iterable
or pre-create a task for every item. Consume each item exactly once.

`limit` must be a positive integer, excluding bool. Invalid type raises
`TypeError`, and zero/negative raises `ValueError`, before calling `iter(items)`
or the worker. Empty input returns `[]` without invoking the worker.

On a worker exception or an exception from `iter`/`next`, stop taking new items
once the failure is observed, cancel any unfinished worker calls, and await
their completion (including async `finally` cleanup) before propagating the
original exception object, without an `ExceptionGroup` wrapper. The same cleanup
rule applies if the caller cancels `map_limited` or a worker raises
`asyncio.CancelledError`; cancellation must propagate as `CancelledError`.
If several failures race, any original failure may win; deterministic selection
is not required. Tests use a single caller cancellation and cooperative workers
that terminate after cancellation, possibly after async cleanup. Repeated
cancellation, workers swallowing cancellation indefinitely, threads, process
pools, and async iterables are outside scope. Do not cancel unrelated tasks.

Use the Python standard library only. Preserve `test_async_map.py` and
`NOTICE.txt` byte-for-byte. Add focused tests if useful and run
`python3 -m unittest`. Complete the edit and final response in this tree;
do not commit or publish.
