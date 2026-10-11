# Native foreground transport fixture

The immutable child workload reads scenario.json, waits the specified duration,
and prints its terminal JSON. Only the owner creates receipt.json after receiving
the child result, verifies it, and commits locally. The public check never waits
or launches a child. Native evidence, not receipt content, establishes transport.
