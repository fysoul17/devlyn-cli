# Changes that hold state or resources

Before editing, use the request and affected code:

1. Identify protected state, owned resources, and the success or commit
   boundary, if any.
2. For applicable errors, timeouts, cancellation, competing operations,
   retries and target aliases, determine the required combination of
   restoration, recovery-data retention, release and error reporting.
   Preserve existing guarantees; do not invent new ones.
3. Order mutations and cleanup accordingly. Acquire required ownership
   before mutation; release only what you own. Recovery must not hide
   a failure the contract requires reporting.
4. Test the relevant failure transitions and assert their state and
   resource outcomes. Bound test waits and terminate or join test-created
   workers. Remove owned disposable resources when safe; retain and
   report required recovery data or unresolved cleanup.
