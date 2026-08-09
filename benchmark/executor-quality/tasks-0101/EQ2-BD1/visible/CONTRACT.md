# Encoder feed contract

Manifest dedup schedules encoder-feed entries by descending priority with arrival order breaking ties, absorbs every repeated submission ID exactly once, and when a duplicate submission surrounds a priority reorder the dependent manifest output preserves that priority order while containing only one manifest for the repeated entity regardless of its arrival slot.
