Fix the durable event inbox in `store.py` and `cli.py`. Retried imports currently
fail and a bad event late in a batch can leave partial writes.

Keep `connect(path)`, `ingest(connection, events)`, `list_events(connection)` and
the CLI invocation `python cli.py DB FILE` (`FILE` is a UTF-8 JSON array).
Use only the Python standard library. The existing SQLite schema and rows must
remain compatible: `events(seq INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT
UNIQUE NOT NULL, payload TEXT NOT NULL)`, with payloads stored as JSON objects.
No schema migration, table replacement or deletion of existing events.

`events` may be any finite iterable. Each event must be a dict with exactly
`id` and `payload`; id is a nonempty string, and payload is a dict mapping string
keys to string values (including an empty dict). Strings contain Unicode scalar
values (no lone surrogates). Do not trim or normalize strings.
Reject invalid events with `ValueError`. Repeating an id with the same payload
is a no-op, including within a batch and after reconnecting; payload key order
does not matter. Repeating an id with different payload is a `ValueError`.
Return the count of newly inserted events. Preserve first-insertion order.
`list_events` returns `[{'id': ..., 'payload': ...}, ...]` in that order.

Each ingest call is atomic: on invalid input, conflicting id, an exception while
iterating, or a SQLite insert failure, commit none of that call's new events.
Propagate errors; leave prior rows intact and the connection usable for retry.
Successful calls must be durable when the connection is closed and reopened.
Calls start with no active transaction; concurrent writers, caller-owned
transactions and corrupt pre-existing rows are out of scope.

The CLI prints exactly `{"inserted": N}` plus newline on success and exits 0.
Malformed JSON, a top-level JSON value other than an array, invalid events,
conflicts, file I/O and SQLite errors must exit 2,
print no stdout, and emit a nonempty single-line `error: ...` on stderr without
a traceback. A failed CLI import must not leave a partial batch. Do not change
the existing tests or `NOTICE.txt`; add tests if useful.

Complete the implementation, verification and final response in this working
tree. Do not commit or publish. No operator replies are available during this run.
