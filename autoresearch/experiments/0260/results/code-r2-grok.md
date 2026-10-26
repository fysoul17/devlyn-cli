VERDICT: SHIP
FINDINGS:
none

Both round-1 HIGHs and the LOWs are fixed. A completed probe or witness attempt is written before the next one starts, a later call runs only the missing attempt, and a finished cell is returned unchanged. A failed `docker create` still records nothing. After a started container, `docker rm` failure is stored as `cleanup_error` and the exit or probe class is kept. Exits `[2, 1]` stay `unresolved`, with the Docker stderr kept on exit 2. The `quota.py` docstring now states 0259's retry-only authentication shape.

Resuming a partial cell, the stored `witness_sha256` check, and `cleanup_error` do not drop, replace, or double-count an attempt, and they do not record a container that never started. A hash mismatch raises before Docker and leaves the stored record in place. Nothing else in `autoresearch/experiments/0260/` shows a path to a wrong result.
