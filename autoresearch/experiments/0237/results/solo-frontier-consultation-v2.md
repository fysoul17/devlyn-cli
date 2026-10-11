# Independent decision: minimal solo frontier after two measurement defects

You are advising devlyn-cli's owner, not implementing or approving a release.
Use only the evidence below. Recommend no product change when warranted.
Do not treat a raw failing assertion as proof of a supported user requirement,
or a successful gold fixture as proof that an oracle is fair.

## User objective and current state

The user wants the smallest CLAUDE.md/AGENTS.md harness that improves capable
models' engineer-quality, hands-free delivery and efficiency. Establish solo
first, then consider automatic pair for residual failures; defer ideate.
The user authorized implementation and sustained testing, including actual
Opus/max and Grok consultation. There is no token/call budget. This does not
license endless experiments, arbitrary requirements or claiming a global optimum.

Two product fixes have passed relevant Linux/macOS checks and independent review:
correct Linux writer observation for a confirmed single-thread zombie versus a
zombie leader with live siblings; move an unchanged 42-word local-delivery rule
earlier in the completion guide. Both are present in B and C below. No product
change from this consultation is admitted yet.

C provisionally adds this exact sentence to core principle No guesswork:

> Before editing behavior, follow its callers and consumers far enough to identify the contracts the change must preserve; use those contracts to choose the smallest fix and its checks.

A is native; B is the installed solo baseline with the two admitted fixes.
In an earlier one-draw-per-engine AF1 screen all A/B/C cells completed correctly;
C used less wall/input/output than B on each engine, but A was cheaper than both
on every resource. This weak resource signal licensed fresh confirmation, not
adoption or a bare-model gain. The registered confirmation would use 12 CF-CONFIG
cells, then 12 CF-LEASE only if the first block passed conservative per-engine
quality and wall/input/output-per-correct non-regression. Easy/orphan controls
would follow only two passing blocks. No pooling away a weak engine/domain.

Five CF-CONFIG cells have finalized; the fifth finished unchanged after the
dispatcher was held and then terminated. That Codex/C cell passed source and
local delivery (435.635s /621,831 processed input /15,940 output, COMPLETE usage).
A/C quality must not be inferred from this partial block.
Keep all raw records and failed costs; do not rerun/regrade an old cell under
its old identity, subtract guessed environment costs, or adopt C from a partial
or defective comparison. The new findings below require deciding whether this
block can support its intended conclusion at all.

## Finding 1: a required native child outlived a final response

f02 Claude/C (Claude Code2.1.296, Opus5.5/max, `claude -p`) passed 12 hidden rows
and 22 public tests but never committed. It read the **complete** completion
guide, including whole-request completion and “Wait for your children, stop your
dev servers and task writers, then leave the task tree.” It launched a read-only
native review explicitly with `run_in_background:true`, then ended its turn
promising to commit after the result. Launch metadata promised a notification
and allowed a response meanwhile.

The reviewer was system-killed 600.134seconds after that final response. Native
stderr explicitly names `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS`; this is the default
noninteractive post-final-turn ten-minute ceiling, not the experiment's5400s
watchdog or a child stall. Native stats: one child, zero completed, one killed.
The last killed operation was a local Bash command; parent and child terminal
usage independently reconciled exactly with the native final aggregate. All
2269.698s /7,218,661 processed input /240,858 output remain charged.

Official docs checked2026-10-10 say foreground children block the owner; with
fork mode off (`-p` default), explicit `run_in_background:false` requests foreground,
while omission defaults to background. This startup catalog had no TaskOutput;
do not invent a wait tool. No foreground counterfactual has been tested.
Ideate has an explicit foreground/await drain rule, but direct completion does
not; ideate remains out of scope. 0232 already recorded a lost background final
review. 0235 rejected a **generic** extra done/verification sentence (2/4 versus
2/4 completions with false-completion cases); do not relabel that as new evidence.

An offline, untested proposal replaces the current child-wait sentence in place:

> For a child whose result is needed to complete this request, use an explicitly foreground call or a supported native wait until its terminal result arrives; handle that result before the final response. Wait for any remaining task children, stop your dev servers and task writers, then leave the task tree.

That is a proposal to critique or shorten, not a preferred answer. It mandates
no review and preserves native parallel work when actually awaited. A small
foreground transport smoke would establish mechanism only; an ordinary task
that never creates a dependent child would not establish lifecycle benefit.

## Finding 2: measured owner had no orphan reaper

Finished f04 Claude/B ran for3276.344s, with44,253,577 processed input and400,250
output, and delivered an attributable local commit. Mid-run, the owner chose
to run the installed delivery helper's71-test self-test, though the helper was
unchanged and the task was to fix Beacon. Twenty seconds later26 tests failed
to fork Git processes. Native process records then establish PID1=`claude`,
238 orphan zombie Git processes plus4 zombie shells, and253/256 task slots in
use. The242 zombies remained until near exit. Owner and reviewer spent visible
work diagnosing capacity and making local subreaper wrappers; five wrappers
each actually reaped one newer orphan. No pre-self-test census proves where
every old zombie originated.

The frozen container runner has `--pids-limit256 --memory4g --cpus2`, with no
`--init`. A separate retained model-free cleanup validation on the same image
had previously failed50/71 tests from fork/thread exhaustion without init at
PID128; identical source and limits with `--init` passed71/71. Thus lack of
reaping is concretely relevant. The first f04 fork error was already1826s into
the run, with another1450s until its final response. Neither interval is a
causal environment-cost estimate. Do not blame all44M input on the environment.
No old source verdict or cost is being rewritten.

A prospective experiment-only fix is Docker's standard `--init`, preserving
the same PID/memory/CPU limits, auth checks, routes and outer watchdog. This is
not a product instruction, a global host configuration change, or a way to
rescue old cells. It requires a new recorded runner/registration. The old
runner and sealed evidence remain immutable. No further owner starts while
these measurement concerns are unresolved.

## Finding 3: the sole f04 oracle failure may overstate the contract

f04 public23 tests passed; the hidden evaluator ran normally (exit0, no timeout,
empty stderr):11 rows passed, one `recursive-merge-value-kinds` assertion failed.
The original4 public QA files were unchanged;18 tests were added. All source,
snapshot, commit and evidence hashes checked. The evaluator's failed assertion
was not a fork error.

Exact visible format contract:

> When both values at a key are objects, merge recursively; otherwise the later value replaces the earlier one. Lists replace, never concatenate, and null is an ordinary value rather than a deletion marker. Do not mutate either input while merging.

Exact visible supervisor reload contract:

> All returned values are detached: mutating a Loader result, reload result, or current Snapshot, including nested dictionaries and lists, cannot affect future loads, the manager's stored state, or another caller's snapshot.

The caller asks to repair include resolution, merging and snapshot publication
to honor these existing contracts and preserve exported APIs. `merge()` is an
internal module-level helper, absent from the package's `beacon.__all__`; it is
directly importable, not underscore-private. Its original docstring only says
“Combine an earlier layer with a later layer.”

The failing hidden check imports `beacon.merge.merge`, calls it with nested
objects and a right-hand `tags` list, checks correct merged values, then changes
the returned nested object and appends to the returned list. **Only afterwards**
does it assert the original inputs are unchanged. f04 performs recursive
functional merges but shares replacement lists; it leaves inputs unchanged
during the call. Its Loader and manager boundary detach returned values and
the separate public-result isolation oracle passed. The check therefore tests
direct-helper result/input separation beyond merge-time non-mutation. The
broad phrase “All returned values” is a possible counterargument; its heading
and enumerated Loader/reload/current endpoints are the scope concern.

No repaired oracle has been run on f04, no source regrade has occurred, and
no new requirement may be added after observing the failure to justify it.
The current raw PRODUCT_INCOMPLETE remains a historical observation, with
the assertion's requirement provenance explicitly under review.

A read-only audit of the **never-run CF-LEASE** fixture also found an overstrong
predicate: its hidden test requires all eight claim tokens to be distinct
across eight different jobs, while the visible contract requires a new token
when reclaiming the **same** job. Fencing checks the full receipt including job
ID, owner, token and attempt, so per-job token generation can satisfy that
contract without global token uniqueness. Another error-injection check
assumes an `UPDATE jobs.state` implementation. Thus simply moving to CF-LEASE
does not avoid provenance work. Neither fixture is being changed/regraded here.

## Decisions requested

Give a concise independent recommendation and strongest counterargument:

1. Is direct `merge()` result/input detachment clearly required by the visible
   contract above, or is it unsupported/ambiguous enough to exclude this block
   from the intended quality/efficiency admission? Distinguish assertion
   execution from requirement validity. Do not infer unseen requirements.
2. What is the smallest defensible next step for C: close without adoption for
   insufficient valid evidence, or prospectively confirm with corrected
   measurement? If more testing is justified, identify a decisive stopping
   rule and why that work is worth doing; do not reflexively add a larger suite.
3. Does the independent child-lifetime failure license a separate minimal solo
   candidate, or is no new wording better? Give the exact smallest delta,
   placement, falsifiable prediction, and evidence that would reject it.
   Distinguish native mechanism, spontaneous compliance and final delivery.
4. Before pair, what minimum controls distinguish independent reasoning from
   simply awaited execution? Proposed pair has B(best solo), S(owner does the
   same check), H(fresh same-model/effort session), P(other primary model),
   automatic risk trigger and whole-run accounting. The awaited peer launcher
   cannot receive reasoning credit merely for avoiding native child loss.

Always charge every owner/child/peer/retry/failure to task wall/input/output per
correct delivery; zero successes has no finite per-success cost. Research
validation costs are separate and still reported. Missing usage is unknown.
No claim of global optimality, a bare-model gain, or a sentence fixing a trace
without its prospective evidence. Preserve authentication/account checks,
native capabilities and registered outer watchdogs. No new framework,
mandatory-review expansion or ideate work.

Official native references: https://code.claude.com/docs/en/env-vars,
https://code.claude.com/docs/en/sub-agents#run-subagents-in-foreground-or-background,
https://code.claude.com/docs/en/agent-sdk/subagents#agentdefinition-configuration.
Repository evidence:0237/results/f02-child-lifecycle-audit.md,
f02-usage-boundary-audit.md, f04-source-audit.md, f04-process-lifetime-audit.md,
confirmation-registration.md. These paths identify retained evidence; the
necessary facts and exact contested quotes have been provided above.
