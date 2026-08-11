# Rate-limit administration contract

The admin gate must bind every rate-limit change in a batch to that change's current operator-and-security approval before the limit writer may publish a validation result, writer errors select unknown-bucket before invalid-window before invalid-limit with rule source order breaking same-reason ties, and when an unauthorized malformed change follows authorized and rejected changes in the same batch its result must remain admin_denied with a denied gate decision and no inherited admission, validation entry, or stored revision while later authorized changes continue from the accumulated journal state.

Each request contributes a fresh approval entry and a decision entry to the gate-owned batch ledger. A denied entry replaces the current admission just as an accepted entry does; prior approvals never carry forward to another change.

The limit writer prepares rule outcomes without publishing them. Only the current request's admission may release a validation entry or revision into durable state.
