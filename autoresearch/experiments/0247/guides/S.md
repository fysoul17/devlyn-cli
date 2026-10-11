# Counterexample check

Only the outer implementation owner activates this check. Finish your
implementation and relevant checks first. On that stable source, make one
additional attempt to find a concrete input or operation order that violates
a requirement in the original request or existing public behavior. Inspect
relevant consumers as needed. Cite the obligation and state an executable
check with its expected result before running it. Do not add requirements or
treat unchanged passing checks as new evidence.

Run the proposed check. Resolve uncertainty with observed behavior and the
actual contract. Repair a reproduced finding and check its neighboring
invariants as well. Continue only to resolve a supported finding, not to obtain
repeated agreement. Any source change makes checks of affected behavior stale.
If you find no supported violation, say so. This check stays in your own
session; do not launch an independent peer for it. Keep native child behavior
unchanged.
