# 0239: explicitly await required native children

Preparation only, 2026-10-10. No0239 model call has been registered or run.
This is distinct from withdrawn0237/C caller-discovery wording. Ideate remains
deferred. Product files still contain only the two admitted delivery fixes.

## Candidate, not adopted

In the direct completion guide only, replace:

> Wait for your children, stop your dev servers and task writers, then leave the task tree.

with:

> Wait for your children before the final response, using explicit foreground execution or a supported native wait for results needed to finish the request. Stop your dev servers and task writers, then leave the task tree.

The installed mirror must match if this is eventually adopted. No root
principle, review requirement, helper, engine setting or background-work ban
is added. Native tools differ: Claude's observed print-mode catalog supports
explicit foreground launch, while a supported wait can preserve parallel work
on an engine that actually exposes one. Inventing a wait tool is a failure.

Prediction: when a task owner chooses a child whose result it needs, the
candidate changes the execution choice before launch/final response so the
terminal result is received within the running task and delivery continues.
It must not create unnecessary reviews or claim completion merely because a
child started. Existing whole-request completion already requires consuming
relevant findings. f02/0232 license this hypothesis but do not validate it.

## Bounded development sequence to register

1. Two explicit Claude foreground transport smokes on the reviewed init runner:
   a short native child and a child with a controlled command lasting over600s.
   Record actual launch mode, child completion, parent final ordering, native
   identity/usage and local commit. These forced prompts test the mechanism,
   not spontaneous compliance or performance. Stop on a mechanism failure.
2. One ordinary Claude B/C pair on CFG-LIFE, with no prompt instruction to
   delegate or foreground. B is the two-fix baseline; C changes only the guide
   sentence above. The task reuses exposed CF-CONFIG visible bytes but has a
   separately audited public-boundary oracle, distinct identity and fresh cells.
   No old score changes. Record guide-read ordering, required-child decisions,
   mode/wait evidence, findings and source/delivery separately.
3. Stop without adopting if the needed behavior is not exercised, both arms
   already use the same safe lifetime behavior, C ends with a required child
   pending, or there is no concrete lifecycle/quality/resource signal. Do not
   repeat solely to obtain activation or a favorable draw.
4. A signal permits the corresponding Codex comparison and prospective
   confirmation/easy-orphan controls, not immediate admission. No larger study
   is authorized by this draft alone. Formal criteria and exact order must be
   fixed before calls. Report a lifecycle correction separately from any
   unproven wall/token or general bare-model improvement.

Use the same pinned image, auth/account checks, resource limits, primary
models/efforts/native-child routes and5400s owner watchdog. All new owners use
the init runner; old registrations remain closed. Do not change the native
post-final-turn ceiling. Charge complete owner/child/failure/retry costs;
missing usage is unknown and zero correct deliveries has no finite per-success
cost. The two forced smokes are separately reported research validation.

This draft sets the intended narrow scope. Fixture assertion provenance,
model-free controls, candidate/baseline package differences, exact runtime,
startup catalogs, dispatch order and stopping/admission criteria still require
a prospective registration before any model call.
