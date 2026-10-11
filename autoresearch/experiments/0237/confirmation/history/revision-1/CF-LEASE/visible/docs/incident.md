# On-call incident: duplicate delivery after deploy

A deploy paused worker cedar while it was sending a document. Another process
reopened the same spool file and retried that parcel after the timeout. Cedar
later reported success, and its stale acknowledgement removed the newer attempt
from the ready queue. A similar case made the new owner's lease disappear when
the older handler failed. Separately, producer retries appear to reset completed
jobs, creating new deliveries. These are durable-state bugs; keeping all workers
in one process would not address the deployment pattern.
