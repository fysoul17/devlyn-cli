# Seat reservation contract

The hold queue ranks requests before the seat map applies them.

Seat holds are processed by descending priority with arrival order breaking ties, every failed request releases all tentative seats, and when reordering makes a middle request fail after a partial hold the higher-priority request still wins while a later request can use every released seat.

`reserve_batch(requests, seats)` returns accepted request ids in processing order, rejected request ids in processing order, committed assignments, and the remaining available seats.
