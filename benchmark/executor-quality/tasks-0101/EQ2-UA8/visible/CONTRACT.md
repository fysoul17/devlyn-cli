# Precinct ballot intake contract

Within a poll, each ballot identifier must be finalized once in the precinct tally across accepted and rejected deliveries, rejection reasons rank poll-closed before ineligible before overvote before unknown-choice with earlier arrival breaking same-reason ties, and when changed duplicate deliveries would each fail differently the first delivery's ranked reason must remain the precinct ledger's sole error with neither a second log append nor a duplicate tally effect while other ballots in the batch accumulate exactly once.

`tabulateBatch(poll, tally, rejectionLog, ballots)` returns one outcome per delivery. The first delivery finalizes a ballot identifier; a retransmission returns a duplicate acknowledgement carrying the original status and reason rather than replaying the first outcome object.

Accepted choices increment only their precinct's running totals. Rejections append only to that precinct's log. The tally's decision journal spans both destinations so batch intake keeps the count and ledger consistent.
