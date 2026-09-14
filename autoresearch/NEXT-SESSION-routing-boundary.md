# Next session: when does additional orchestration earn its cost?

Prepared at the user's request during0174. **NOT RUN.** Finish0174 first;
`.devlyn/0174-delivery/FINAL.md` is authoritative for its delivery/validation.
Read this file and `autoresearch/HANDOFF.md` in the next session. Do not replay
completed0173 draws, reopen parked A16, or infer a goal to exhaust a token budget.

User objective: identify which observable task properties predict a useful
difference between bare, solo and pair, then use evidence to improve selection.
There is no assumed ordering. The0173 prepared Decimal task tied69/69; bare was
much shorter. That establishes neither universal equivalence nor a threshold.

## Scope and decision rule

Compare three execution routes with the same primary engine/model/effort and
the same original source and task inputs:

- Bare: ordinary direct implementation and its own required checks.
- Solo: canonical devlyn pipeline with one engine and independent verification.
- Pair: the same pipeline plus the registered OTHER-engine reviewer, actually run.

Keep full-route behavior and explicit pins intact. Explicit resolve/spec/queue
requests retain their contract; an empirical policy change cannot silently
downgrade them. Risk/ambiguity decisions depend on inspected behavior, not file
count, a word such as "cache", or a single invented difficulty score.

Judge intent correctness, regressions and substantive defects first. Among
routes meeting the same quality floor, prefer lower total verified completion
time, then observed token/cost burden. Additional phases or tests are not quality
credit. Pair value must appear in the final result, not merely a second PASS.

## Task selection before any model draw

Inspect candidate tasks without running solutions. Describe each using:

| Dimension | Evidence to record |
|---|---|
| Requirement ambiguity | Decisions absent from the initial request; available clarifications |
| Coupling | Callers, modules and invariants affected by the actual behavior change |
| Hidden risk | Authorization, durable data, ordering, concurrency or public contracts |
| Verification difficulty | Existing oracle strength; integration or adversarial checks needed |
| Repair burden | Whether failures can be localized with available evidence |

Start with three fresh, justified tasks across local/clear, coupled and hidden-risk
conditions, one draw per route: a nine-draw exploratory ceiling, strictly serial.
This is screening, not sufficient evidence for a production threshold. Register
task IDs, immutable source/spec/check hashes, cases unseen by implementers,
scope/quality rules, native identities, roles, time bounds and stop rules first.
Do not choose tasks because a prior route has already failed on them. Do not
repeat already-direct README/label toys to manufacture routing savings.

If all routes tie, report that the tested range shows no quality lift. If a
plausible difference appears, register a separate untouched confirmation set
in that difficulty class before expanding work. Use multiple fresh tasks and
repeated draws sufficient to distinguish task effects from sampling variation;
declare sample size and resource ceiling prospectively. Do not grow the study
until a preferred route wins, or tune on the confirmation set.

## Fairness and evidence requirements

- Explicitly qualify model-visible project instructions and skill catalogs.
  Bare excludes devlyn metadata and invocation; full routes load only the current
  canonical devlyn surface. Preserve other inputs. CODEX_HOME/ignore-config/
  skip_host_skill_discovery alone did not certify isolation in0173. Offline
  prompt rendering is diagnostic; never call it a captured provider request.
- If testing requirements discovery, give every route the same original request
  and clarification access. Supplying a prepared spec measures execution given
  that spec; record spec-construction cost separately or include it for all arms.
- Use fresh source/session per draw and prohibit sibling/prior-result access.
  Balance route order across tasks; record cache policy, preparation and warm-up.
- Preserve all native failures, timeouts, internal repairs and raw streams.
  No root product rescue, silent retries, model substitution or favorable rerolls.
  Infrastructure failure is distinct from product failure; follow the registered
  stop rule rather than assigning it an invented quality score.
- Score each frozen product on identical independent checks and scope preservation.
  Review anonymously; include known good/bad controls, adjudicate factual reviewer
  disagreements against source or runnable probes, and retain rejected advice.
- Record end-to-end native wall, checks, dispatch/review/repair time where observable,
  and every parent/worker/judge's available input/cache/output counters. Include
  failed attempts. Unsplit counters remain UNKNOWN; no inferred billing total.
  External assessment/preparation cost stays visible alongside native task time.

## Deliverable

A per-task quality/time/coverage table with raw evidence links, observed failure
mechanisms, uncertainty and a proposed selection rule tied to inspected properties.
Confirm the rule on untouched cases before changing runtime selection. State where
bare suffices, where solo adds demonstrated value, where pair adds value over solo,
and where the evidence is insufficient. Preserve quality and existing safety/explicit
workflow obligations. Do not add a classifier, new engine layer or generic benchmark
harness unless an observed failure makes that addition necessary.
