# Print queue contract

The spooler emits queued jobs by descending priority with arrival order breaking ties, the job dedup index absorbs every repeated job ID exactly once, and when a duplicate submission surrounds a priority reorder the emitted queue preserves that priority order while containing one copy of the repeated job regardless of its arrival slot.
