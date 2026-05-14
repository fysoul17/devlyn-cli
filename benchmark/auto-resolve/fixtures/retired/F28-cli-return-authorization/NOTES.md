# F28 - Notes

## Failure Mode

This fixture detects return-policy implementations that look plausible but get
policy precedence or cents math wrong: applying expiration before
nonreturnable, charging restocking fees on defective items, merging exchange
credit into refunds, accepting malformed enum/date/SKU input, mishandling the
return-window boundary, or mutating the request file during authorization.

## Pipeline Phases

It stresses IMPLEMENT and VERIFY. The visible spec requires exact JSON output
and validation behavior, while hidden verifiers assert policy precedence,
integer-cent totals, invalid quantity handling, and input immutability.
The validation boundary verifier also covers duplicate order SKUs, unknown
requested SKUs, invalid calendar dates, invalid return-line enums, and the
purchase-day-as-day-0 return-window edge.

## Why Existing Fixtures Do Not Cover This

F16 covers quote math, F23 covers warehouse allocation rollback, and F25 covers
cart promotions. None combine business rejection precedence with separate
refund versus exchange-credit ledgers and an immutability requirement.

## Retirement Criteria

Retire or rotate this fixture if both `solo_claude` and the selected pair arm
score near the ceiling for two shipped versions, or if a future fixture covers
return-policy precedence, exchange credit, and immutable input with clearer
headroom.

## Headroom Status

Initial headroom smoke `20260511-f28-headroom-smoke-085307` measured
bare 59 / solo_claude 66 and passed a one-fixture headroom gate with solo
headroom 14 under the older threshold-only gate. Under the current default
margin gate, the same score fails because bare headroom is only 1 point.

Follow-up pair smoke `20260511-f28-pair-smoke-091021` reused the same
bare/solo artifacts but re-judged the headroom step at bare 65 / solo_claude
66, failing the `bare <= 60` precondition. The pair arm was not executed.

Those runs were superseded when the hidden policy oracle was corrected: it had
expected a defective item to bypass expiration, but the visible spec only says
defective items waive restocking fees. `policy-precedence.js` now keeps the
defective exchange line inside the return window and leaves the nonreturnable
line as the expired-plus-nonreturnable precedence case.

Corrected-oracle reverify `20260511-f28-policy-oraclefix-reverified-pair`
reused the same provider diffs and scored bare 50 / solo_claude 98 /
`l2_risk_probes` 96, margin -2, failing headroom and the pair gate. Treat F28
as rejected for pair-lift evidence. Rework or rotate it before spending more
pair arms.
