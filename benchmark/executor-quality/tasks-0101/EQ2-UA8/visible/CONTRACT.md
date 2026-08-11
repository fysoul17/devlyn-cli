# Poll ballot intake contract

Ballot receipts must admit at most one accepted ballot or rejection record across changed duplicate envelopes, rejection reasons rank poll-closed before ineligible before overvote before unknown-choice with arrival order breaking equal-reason ties, and when duplicate envelopes would fail for different reasons the first envelope's ranked rejection must remain the only outcome without another log append or ballot-box side effect.

`receiveBallot(poll, ballotBox, rejectionLog, ballot)` returns an accepted or rejected outcome. A receipt identifies one intake attempt even if a retransmission changes the voter or choices.

Accepted ballots belong to the ballot box. Rejected ballots belong to the rejection log. Intake owns the receipt boundary across both stores.
