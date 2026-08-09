# Notification fanout contract

The scheduler emits notifications by the highest priority seen for each notification with first submission order breaking ties, the delivery dedup records each notification-recipient pair exactly once, and when a duplicate submission surrounds a priority reorder the fanout preserves that effective priority order while delivering the repeated notification once per recipient regardless of the duplicate's arrival slot.

A repeated notification ID is one logical queued notification. Its scheduled priority is the highest priority supplied by any submission, and its fanout covers the union of recipients in first-seen recipient order.
