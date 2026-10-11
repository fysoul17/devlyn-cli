# Producer and persistence contract

A job ID identifies an immutable JSON payload. Enqueuing a fresh job stores a
snapshot of that payload, and returns True. Enqueuing an existing ID with an
identical JSON value returns False and changes nothing: availability, attempts,
lease, error, completion, and the originally stored payload are preserved.
Object key ordering is irrelevant. A different payload under the same ID raises
PayloadConflict without modifying the original. This holds in every job state,
including done, and across reopened Store connections. Do not coalesce distinct
job IDs that happen to contain the same payload.

`Store` creates the schema if needed, commits successful transactions, and rolls
back exceptions. A process can reopen the database after any completed API call.
Time values are finite epoch seconds supplied by callers. Each Store connection
belongs to its worker thread; claims from different connections can overlap.

`get_job` returns a detached Job snapshot or None. Payload dictionaries and lists
passed into or returned from the package never become mutable database state.
The existing exported function signatures and Job/Receipt fields are public.
