# F35 retired

Retired from the active golden suite after headroom run
`iter-0039-headroom-f34-f35`.

Reason: `solo_claude` scored 97, exceeding the headroom ceiling of 80, while
bare scored 50. `solo_claude` correctly implemented the `{ "ops": [...] }`
input contract, priority ordering, rollback, and duplicate-op handling; bare
failed only because it assumed a bare top-level array instead of the required
object shape — an input-shape slip, not evidence the task is hard. The
solo_claude arm also ran to the full 1500s timeout before finishing
(elapsed_seconds 1501, INVOKE_EXIT=124), but its diff still verified clean, so
the fixture is not pair-lift evidence.

Future use: rework the visible contract or hidden verifiers so the task
creates a fair pair-risk-probe gap without hiding requirements from the spec.
