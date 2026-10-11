# Public contract

Construct `KeyedLoader(fetch)` with an async callable `fetch(key)` accepting a
string and returning a JSON-compatible dictionary. `await get(key)` loads one
value. `invalidate(key)` is synchronous. `snapshot()` returns a dictionary of
completed cached values only. `await close()` ends this loader's lifetime.
`ClosedError` is public. Calls use one asyncio loop; threads are out of scope.

C1 — Sharing. Concurrent get calls for the same key and current generation share
one fetch operation. Different keys progress independently. After success,
further get calls use the cached value until invalidation. `snapshot()` never
reports unfinished or failed loads. Generation means the period between
invalidations of that key; callers do not need to provide a generation number.

C2 — Ownership. Each get result and snapshot is a recursive detached copy,
independent of the cache, the object returned by fetch, all other callers, and
later results. Mutating any of those caller/backend-owned objects after
completion cannot alter the cached value or other returned objects.

C3 — Invalidation. invalidate removes the key's cached value immediately and
starts a new generation even when a fetch is in progress. Existing callers keep
waiting for their original operation and receive its success/failure. A get
started after invalidate uses a fresh operation; it must not join the retired
operation. Retired operations may finish in any order but cannot publish a cached
value for, remove, cancel, or otherwise disturb the current generation. Repeated
invalidations, including of unknown keys, are valid. Other keys are unaffected.

C4 — Caller cancellation. Cancelling one get caller raises CancelledError to
that caller only. It never cancels the shared fetch or other callers. This also
applies when the cancelled caller was the sole waiter: the fetch still finishes
and may populate the cache if its generation is current. A later caller may
join that ongoing operation. An abandoned fetch failure must be consumed so it
does not become an event-loop 'Task exception was never retrieved' report.

C5 — Failure and recovery. Fetch exceptions propagate with their original type
and message to all waiting callers. Neither exceptions nor backend cancellation
are cached. The next get in that same generation starts a fresh operation and
can recover. An old-generation failure or cancellation cannot remove a newer
in-flight operation or completed cached value. Previously cached other keys
remain available after a failure.

C6 — Shutdown. close marks the instance closed, empties its cache, cancels and
awaits all unfinished fetches it owns, including operations retired by
invalidation or abandoned by callers. Waiting callers observe cancellation when
their fetch is cancelled. close is idempotent; on return no owned fetch remains
running. get and invalidate on a closed loader raise ClosedError; snapshot is
empty. No completion may repopulate it after close. Fetch functions cooperate
with cancellation, possibly after asynchronous cleanup; close waits for that
cleanup. Closing an instance does not affect a different loader instance.
