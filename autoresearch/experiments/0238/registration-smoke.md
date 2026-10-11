# 0238 native pair transport registration

2026-10-10. Prospective operational sequence, fixed before any 0238 model call.
This registers transport only. It neither admits pair nor authorizes the ten-cell
F23 efficacy proposal. No 0239 comparison is reopened.

## Selected inputs and prerequisites

Solo B is original 4.2.3 plus the two accepted delivery fixes and the accepted
direct adjacent AGENTS import correction (0239/results/import-dedup-decision.md).
S/H/P add the fixed representation/ownership trigger and their respective guides;
H/P add the reviewed peer helper. Selected prospective archives:

| Arm | SHA256 |
| --- | --- |
| B | 050bc8d6f3af071461903f0c7efd77ae445828f232152cd4f52b6e81faa967b3 |
| S | c031f7d5e5ea752bf153092e059684f281cfd55a1241c643f57b525b22d334d5 |
| H | 1731e86ce031172ce87352146887e1ac28abbdf65266ee1cf05a28466ca53d3f |
| P | 10a748e9235f614b0c2f8091aa17fec88a6f762d77e5d4f8a830d3dc8ddb5d5e |

The tasks-smoke.json SHA is
b432112251fd93192abe7676fde042fa2f11d2581341cd092307ea9f646d0c92.
The selected v5 apparatus manifest SHA is
264cc1e494c48489479afc234b2afe232e0a05e5ad9436b8f29287345e36ac1a.
Dispatch requires its SHIP review, selected archive integrity checks, actual
staging, and model-free positive/no-op/deleted checks against that exact staged
runtime. Require H/P installed peer.py and platform-support.py hashes to match
the selected manifest. Save a runtime/control/tasks/package/runner input freeze
before the first call. A staged copy alone is not a passing control.

## Fixed serial sequence

| Cell | Task | Arm | Owner | Peer |
| --- | --- | --- | --- | --- |
| s01-h-claude | S2 | H | Claude Opus 5.5 / max | Same primary |
| s02-h-codex | S2 | H | Codex Astra / max | Same primary |
| s03-p-claude | S2 | P | Claude Opus 5.5 / max | Codex Astra / max |
| s04-p-codex | S2 | P | Codex Astra / max | Claude Opus 5.5 / max |

Use the exact model identifiers in tasks-smoke.json: claude-opus-5-5 and
gpt-6-astra. Codex native children stay gpt-6-sol/high; Claude peers are restricted
to Read/Grep/Glob. Native-child capability asymmetry is explicit. No separate
assessor/reviewer model is dispatched. Do not run independent study model calls
or heavy local checks while a registered owner is active.

The S2 request explicitly exercises one fresh peer call and one resume on stable
source, with the original request verbatim, a concrete rounding fact, complete
saved answers and one permitted Codex native child. Await each result and execute
the proposed check. This forced activation establishes transport, never automatic
trigger quality or independent-reasoning benefit. Report only the presence of
CLAUDECODE; do not print its value, remove it, or dump other environment values.

## Acceptance and stopping

For each cell require source/public/oracle correctness and attributable local
commit, source stability during both peer calls, actual primary/child model and
effort, the same resumed session, complete native captures/answer paths, all
attempts and native child costs, clean teardown and unchanged input seals. A
successful helper exit or owner statement alone does not prove these facts.
Inspect native receipts/transcripts as well as the runner's verdict.

Whole owner wall and all input including caches/output including reasoning are
retained. Do not add reasoning twice or subtract failed peer attempts. The v5
guard requires terminal accounting reconciliation for Claude owner/peer/resume/
child sessions; an unbound interrupted request remains UNKNOWN and STOP even if
an unrelated later result succeeds. Fully accounted recovery stays visible and
is evaluated without treating an earlier process failure as permanent source
failure. The inherited Codex per-inference accounting remains required.

Advance only after the preceding cell is finalized and these transport gates
pass. On failure retain the result and stop the sequence for a named diagnosis;
no favorable reroll or silent protocol replacement. Any justified repair and
fresh attempt need a separate prospective identity and frozen inputs. Authentication
faults stop dispatch; use only the supported normal login/refresh flow, preserving
the 6300-second preflight margin and account checks. No proactive credential edit.

Image remains sha256:0f472bb41685b7daa5923d51d31983f4b3c70053dd773fdf712bd0dcd6d87998,
with owner --init, PID256, memory4g, CPU2. Existing owner5400s/review600s/evaluator600s
watchdogs and peer540s watchdog remain unchanged; no token, cost or call budget.
Do not change native background-wait or Bash-timeout environment settings.

If all transport routes pass, register the ordinary F23 comparison separately
with measured startup-catalog expectations derived from retained native evidence.
Its source and request must remain free of the explicit smoke pair invocation.
