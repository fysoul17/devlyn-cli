# Migration runner contract

Migration batches restore the schema and durable journal to their exact pre-batch states when any step fails, migration keys apply at most once on successful runs, and replaying a batch whose first partially applied attempt rolled back starts from that clean state so every step is applied and journaled exactly once.

Each migration has a stable `key` and one schema change. The runner coordinates the
step applier with the durable journal; callers may retry the same batch after removing
the cause of a failed step.
