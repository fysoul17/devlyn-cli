# Cache invalidation contract

Failed purge batches restore cached entries and generation counters to their exact pre-batch states, successful batch identifiers take effect at most once, and replaying the same commands after a partially executed batch rolls back recomputes generations from that clean state so every requested scope is purged exactly once.

Each purge command targets one cache scope. The generation counter assigns the next
cutoff for that scope, and the cache removes entries older than the cutoff. A caller
may repair a command that failed after purging and replay the same batch description.
