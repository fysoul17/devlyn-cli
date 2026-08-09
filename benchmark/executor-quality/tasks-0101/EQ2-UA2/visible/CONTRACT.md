# Print queue contract

The spooler fills each bounded printer queue by descending priority with arrival order breaking ties, the job dedup index absorbs every repeated job ID exactly once before it can consume queue capacity, and when a duplicate submission surrounds a priority reorder the emitted queue contains the highest-priority unique jobs in that order with one copy of the repeated job regardless of its arrival slot.
