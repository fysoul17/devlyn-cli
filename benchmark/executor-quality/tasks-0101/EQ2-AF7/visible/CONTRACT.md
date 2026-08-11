# Meeting slot request contract

Slot retries sharing a request id must replay the first conflict report without emitting another notification, conflict reasons rank outside before attendee before room with source order breaking equal-reason ties, and when the calendar changes so an identical retry would now lose to a different conflict the original ranked report must remain sealed without another report or booking side effect.

`request_slot(calendar, reporter, request)` returns either a `ScheduledSlot` or a `ConflictReport`. A request id identifies one slot attempt across calendar revisions. Conflict detection may inspect every overlapping booking, but only the reporter's first selected conflict for that request may be published.

The conflict policy uses the order `outside`, `attendee`, then `room`. When two conflicts have the same reason, the smaller source index wins.
