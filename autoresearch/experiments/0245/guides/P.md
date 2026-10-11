# Independent counterexample check

Only the outer implementation owner activates this check. A peer reviews;
it does not implement, deliver, or delegate to native children or another
independent session.

Finish your implementation and relevant checks first. Hold the source stable
while the peer reads it. Give the peer the original request verbatim, the
candidate diff and relevant source paths, and raw check results, before any
summary of your reasoning. Ask:

> Find a concrete input or operation order that violates a requirement in this
> request or existing public behavior. Cite that obligation and give an
> executable check with its expected result. Inspect the relevant consumers
> as needed. Do not add requirements, edit source, or treat passing checks or
> agreement as proof. If you find no supported violation, say so.

Use one fresh independent check, not a scheduled sequence of discussions.
You remain the sole writer. Await the peer's completed result; run proposed
checks yourself against that source. Resolve disagreement with observed
behavior and the actual contract. Repair a reproduced finding and check its
neighboring invariants as well. Further peer work is only to resolve a supported
blocking finding, not to obtain repeated agreement. Any source change makes
checks of the affected behavior stale.

The peer is a separate CLI session of the other configured engine: Claude
for a Codex owner, Codex for a Claude owner, at its configured primary model
and reasoning effort.

The helper retains each call's records in ignored `.devlyn/pair/`; do not
delete them. Use the shared `peer.py` launcher with the explicit configured
primary model and effort, repository and prompt path.
Do not substitute a cheaper native-child model for the independent primary
peer. Claude peers use Read/Grep/Glob; Codex peers use the native read-only
sandbox. You execute the peer's proposed checks and own all source changes.
If the peer cannot run or finish, report that fact and continue the remaining
solo checks; never claim that peer validation occurred.

Resolve `<shared>` to this guide's containing directory; run from the checkout
root. Each call creates its own retained record directory:

```sh
python3 <shared>/peer.py --engine <engine> --model <primary-model> \
  --effort <configured-effort> --repo . --prompt .devlyn/pair/request.md \
  --watchdog-seconds 540
```

Read the final answer path returned by the helper; retain its native capture.
Do not end your session with a call still running. A resumed blocking-finding
check uses `--resume <session-id>` with the same explicit model and effort. A successful process exit alone is not proof of a
correct change.
