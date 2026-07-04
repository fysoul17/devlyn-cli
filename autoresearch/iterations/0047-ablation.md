# iter-0047 — ablation loop: token reduction guarded by probe panel

**Status**: SHIPPED (small, verified ledger). Anti-Goodhart discipline held: most
candidates found during the hunt were rejected once checked against
`scripts/lint-skills.sh`'s literal-string checks or concurrent-edit safety —
one survives. This iteration's real output is as much the rejected-candidate
evidence as the single accepted deletion.

## Objective

Reduce `/devlyn:resolve` + `/devlyn:ideate` + `_shared` prompt-token cost
(`scripts/skill-token-gauge.py`) without regressing the probe panel
(`benchmark/probes/`). The panel is a regression guard, not the optimization
target — deletions are kept only when they cite a supersession/duplication
rationale AND the guard doesn't move.

## Baseline (before)

```
devlyn:resolve   SKILL.md     cold_start   326   39697   9924 tok(c4)   6343 tok(w13)
devlyn:resolve   SUBTOTAL                 1240  109474  27366           18181
GRAND TOTAL                              10613  556849  139190          95242
```

## Hunt — candidates found, and why most were rejected

Read every file in `devlyn:resolve/SKILL.md` + its `references/phases/*.md` +
`devlyn:ideate/SKILL.md` + its `references/*.md` + `_shared/*.md` (excluding
`adapters/`, `engine-preflight.md`, `engine-doctor.sh` per iter-0051 ownership).

**Finding 1 — the "obvious" duplication is mechanically pinned, not accretion.**
SKILL.md's PHASE 1.5 section restates probe-derive.md's entire tag/evidence
taxonomy almost verbatim (`ordering_inversion`, `http_error_contract`,
`shape_contract`, etc. — ~38 lines / ~2500 chars), and PHASE 5 restates
verify.md's pair-mode trigger/reasons/skip-logic almost verbatim (~40 lines).
Both look like textbook progressive-disclosure violations. Both are wrong to
delete: `scripts/lint-skills.sh` Checks in the 628-678 range and lines
345-350 `grep -Fq` literal-string-check SKILL.md for these exact phrases
(`` `asserts_nonzero_or_exit_2` ``, `` `shape_contract` must ``, `include
every applicable canonical reason`, etc.) as a deliberate dual-declaration
parity guard — SKILL.md and its reference files are required to independently
state the same contract, and lint catches drift between the two copies. This
is not duplication debt; it's a mechanically-enforced double-declaration
dating from iter-0046/0049's tag-contract hardening. **Not applied.**

**Finding 2 — `_shared/pair-plan-schema.md`** is a deliberate design archive
(iter-0022 infra for the deleted `/devlyn:auto-resolve` plan-pair contract,
explicitly labeled "Archive header (iter-0034 Phase 4 cutover)" with
re-instatement conditions). It is not loaded by any live SKILL.md path, so
deleting it would save zero per-run tokens; it is also read by
lint Check 13 (`pair-plan-idgen.py` determinism). **Not a candidate — no
token benefit, has a lint consumer, and is intentionally preserved.**

**Finding 3 — three real, small, unpinned duplications found**, all pointing
SKILL.md at `_shared/engine-preflight.md` (a file SKILL.md already instructs
the reader to "follow") while also restating its content in full:
1. `<autonomy_contract>` item 2 — restates engine-preflight.md's "two
   classes" rule almost verbatim.
2. PHASE 0 step 2, first paragraph — restates engine-preflight.md's role
   resolution / `BLOCKED:invalid-engine-config` rule.
3. `<engine_routing>`'s "Role resolution" sentence — restates the
   precedence order, but this one carries a real distinguishing fact
   (`--engine` flag > `engines.json` pin > default) not duplicated in full
   elsewhere and is short (~90 chars) — **left alone**, not worth the
   correctness risk for a near-zero saving.

`_shared/codex-config.md` lines 9-23 also byte-duplicate SKILL.md's own
`<runtime_paths>` `DEVLYN_SHARED_DIR`/`CODEX_MONITORED_PATH` resolution
snippet.

## Mandatory Codex cross-check (before applying)

Presented candidates 1-3 (`codex-config.md` snippet, autonomy_contract item
2, PHASE 0 step 2 paragraph) to Codex (`gpt-5.5` via `codex-monitored.sh`,
read-only sandbox) with the explicit ask: hunt for `lint-skills.sh` literal
consumers and correctness loss. Verdict and deltas:

| Candidate | Codex verdict | Delta from my analysis |
|---|---|---|
| `codex-config.md` snippet → pointer | **RISKY** | `devlyn:ideate/SKILL.md`'s own `<runtime_paths>` resolves `DEVLYN_SHARED_DIR` but **never resolves `CODEX_MONITORED_PATH`** — a Codex-routed ideate phase relying on my proposed pointer text would be told a false thing. Confirmed by re-reading `devlyn:ideate/SKILL.md:30-47` myself. **Dropped**, not applied. |
| SKILL.md autonomy_contract item 2 | SAFE | none |
| SKILL.md PHASE 0 step 2 paragraph | SAFE | none |
| — | — | Codex separately flagged the working tree was dirty on files I hadn't fully accounted for (see next section) — real, caught before I applied anything. |

## Concurrent-edit conflict (caught before applying, not after)

`git diff` on the PHASE-0-step-2 candidate showed iter-0051 (task #60, then
still `in_progress`) had an **uncommitted** live edit to the exact same
paragraph (adding "or an adapter that declares itself ineligible for the
requested role" for their ollama role-eligibility feature). Applying my trim
there would have silently discarded or conflicted with a teammate's
in-flight work. **Dropped**, not applied — this is a scheduling/ownership
finding, not a technical rejection; the same trim may be safe once iter-0051
lands and settles, and is worth re-attempting in a future ablation pass.

## Applied deletion

**File**: `config/skills/devlyn:resolve/SKILL.md` (+ `.claude/skills` and
`.agents/skills` mirrors), `<autonomy_contract>` item 2.

Before (828 chars):
> 2. Engine availability: follow `_shared/engine-preflight.md`. Two classes.
> **Explicit cross-engine routes** (`--engine`, `--risk-probes`,
> `--pair-verify`) are promises: if the required engine is unavailable, fail
> closed with `BLOCKED:<engine>-unavailable` and setup guidance — never
> downgrade an explicitly requested route to solo. **Automatic cross-engine
> escalations** (auto high-risk risk-probes, auto VERIFY pair-JUDGE) are
> candidate routes selected only when their preconditions hold, including
> OTHER-engine availability. If an auto candidate would fire but the OTHER
> engine is absent, do not select the cross-engine route — proceed solo and
> report the skipped escalation and its reason. Skipping an unselected
> optional route is route selection, not a fallback; an explicitly requested
> route is never skipped this way.

After (256 chars):
> 2. Engine availability: follow `_shared/engine-preflight.md` for the
> explicit-route-vs-automatic-escalation distinction and BLOCKED-vs-skip
> behavior. Explicit routes (`--engine`, `--risk-probes`, `--pair-verify`)
> never downgrade to solo; unavailable auto-escalations proceed solo and
> report the skip.

**Rationale**: `engine-preflight.md`'s own "Rule" section (lines 9-12)
already states this two-class distinction in full; SKILL.md's own PHASE 0
step 2 already says "follow `_shared/engine-preflight.md`" one paragraph
below this one. The orchestrator's stated job ("parses input, spawns
phases, reads state, branches on verdicts") doesn't require re-deriving
the availability taxonomy inline — it needs the one-line invariant
(never-downgrade / report-the-skip), which the trimmed version keeps.

**Verified not lint-pinned**: repo-wide grep for the deleted paragraph's
distinctive substrings (`Automatic cross-engine escalations`,
`Skipping an unselected optional route is route selection`) found zero
hits outside the target file itself and its mirrors, confirmed independently
by Codex.

**Landed as**: this diff was sitting uncommitted in the working tree
alongside iter-0051's own (unrelated) PHASE-0-step-2 edit when iter-0051
committed its own work (`230268c feat(engines): add ollama local-backend
adapter, judge-only role (iter-0051)`). Both edits to
`devlyn:resolve/SKILL.md` landed in that single commit rather than a
separate iter-0047 commit — a concurrent-session artifact, not a scope
violation (the two edits are independent, non-overlapping lines). Verified
via `git log --all -S "explicit-route-vs-automatic-escalation"` that the
line's only introduction is `230268c`, and via `git show --stat 230268c`
that no other content of mine leaked in.

## Gauge — after

```
devlyn:resolve   SKILL.md     cold_start   326   39241   9810 tok(c4)   6254 tok(w13)
devlyn:resolve   SUBTOTAL                 1240  109018  27252           18092
GRAND TOTAL                              10655  561243  140289          95934
```
(GRAND TOTAL rose overall because of unrelated concurrent iter-0050/0051
additions — devlyn:engines SKILL.md, `adapters/ollama.md`, `adapters/README.md`,
`engine-preflight.md` growth — landing in the same window. The devlyn:resolve
column isolates this iteration's actual effect.)

| | before | after | delta |
|---|---|---|---|
| devlyn:resolve/SKILL.md chars | 39697 | 39241 | −456 |
| devlyn:resolve/SKILL.md tok(c4) | 9924 | 9810 | **−114** |
| devlyn:resolve/SKILL.md tok(w13) | 6343 | 6254 | **−89** |
| devlyn:resolve SUBTOTAL tok(c4) | 27366 | 27252 | −114 |

Small (−1.1% of the SKILL.md cold-start cost), but it applies to **every**
`/devlyn:resolve` invocation unconditionally (not gated behind a phase that
may not fire), and it is a pure pointer-consolidation with zero information
loss (the full text remains canonical in `engine-preflight.md`, which SKILL.md
already reads at PHASE 0).

## Deletion ledger

| # | File | Block | Chars saved | Rationale | Outcome |
|---|---|---|---|---|---|
| 1 | `devlyn:resolve/SKILL.md` `<autonomy_contract>` item 2 | Engine-availability two-class restatement | 572 | Duplicate of `engine-preflight.md`'s "Rule" section, which SKILL.md already points to | **Applied** |
| 2 | `_shared/codex-config.md` lines 9-23 | `DEVLYN_SHARED_DIR`/`CODEX_MONITORED_PATH` resolution snippet | ~550 (not realized) | Byte-duplicate of SKILL.md's own `<runtime_paths>` | **Rejected** — Codex found `devlyn:ideate/SKILL.md` never resolves `CODEX_MONITORED_PATH` itself; removing the snippet would break a Codex-routed ideate phase's only source of that variable |
| 3 | `devlyn:resolve/SKILL.md` PHASE 0 step 2, para 1 | Role-resolution / `BLOCKED:invalid-engine-config` restatement | ~290 (not realized) | Duplicate of `engine-preflight.md`'s "Role resolution" section | **Rejected** — iter-0051 had a live uncommitted edit to this exact paragraph at check time; touching it risked clobbering in-flight teammate work. Re-attempt in a future iteration once settled. |

## Guard matrix (all runs post-edit, sonnet unless noted)

| Guard | Result | vs. baseline |
|---|---|---|
| Compliance `claude-small` (MODEL=sonnet) | PASS 4/4 (recovered via 1 fix-loop round on an unrelated pre-existing `plan.md` heading-level defect — see below) | matches iter-0049 clean baseline |
| Compliance `omp-small` | PASS 4/4 | matches iter-0049 baseline |
| Compliance `codex-small` | PASS 4/4 | matches iter-0052 fresh-repair baseline |
| Drift-bait rep1 (6 probes × sonnet × EN) | 2/6 violations (`DB-silent-catch-root-cause`, `DB-tempting-state-file`) | iter-0045 sonnet r1 = 2/6 (different pair: `B4`, `DB-tempting-state-file`) — same count, within `1-2/6` band |
| Drift-bait rep2 (6 probes × sonnet × EN) | 2/6 violations (same 2 as rep1) | iter-0045 sonnet r2 = 1/6 — one higher, still within documented `1-2/6` band |
| KO spot-check `DB-silent-catch-root-cause` | `passed:false`, checks byte-identical to iter-0048 KO r1 | not worse |
| KO spot-check `DB-tempting-state-file` | `passed:false`, checks byte-identical to iter-0048 KO r1 / r2-rerun | not worse |
| `lint-skills.sh` | green before and after (`All checks passed.`) | no regression |
| `spec-verify-check.py --self-test` | exit 0 | green |
| `state-phase-write.py --self-test` | exit 0 | green |
| `verify-merge-findings.py --self-test` | exit 0 | green |
| Mirror parity (`config`/`.claude`/`.agents`) | byte-identical | held |
| E2E `/devlyn:resolve --spec` (sonnet, throwaway small English spec) | terminal `PASS_WITH_ISSUES` (2 LOW findings only) | effectively PASS; see note |

**E2E note**: first attempt (hand-authored `--loud` spec, same shape as
`F1-cli-trivial-flag`) hit terminal `BLOCKED:verify-fix-out-of-scope` — the
Codex pair-JUDGE (auto-triggered by the primary judge's LOW `judge.warning`)
reported `npm test` failing under Node v25.4.0 (a Homebrew install present on
this machine) because `node --test tests/` doesn't resolve a trailing-slash
directory arg under that Node version; the repo's actual runtime is Node
v20.19.0 (nvm) where all tests pass. IMPLEMENT's fix-loop respawn correctly
identified this as unrelated to the diff and declined to expand scope to
touch `package.json` (outside PLAN's authorized surface) — the harness's
Goal-locked discipline and the mechanical any-HIGH-finding-is-verdict-binding
merge rule worked exactly as designed, but gave an ambiguous data point
(BLOCKED for a reason orthogonal to my edit). **This also confirms iter-0053's
merge-crash fix holds** — `verify-merge-findings.py --write-state` computed a
real verdict both times, no `BLOCKED:infra-merge-script-crash`. Re-ran with
`package.json`'s `test` script changed to `node --test tests/cli.test.js`
(avoids the directory-arg Node-version sensitivity, verified locally under
both would-be Node versions is unnecessary since the fix is orthogonal to
Node version) — clean `PASS_WITH_ISSUES` this time, including a real
self-caught-and-corrected BUILD_GATE moment (agent flagged, then properly
fixed, a `.devlyn/*` scope leak from its own `git add -A`).

## CLAUDE.md proposal table

**Empty.** Re-read the current CLAUDE.md in full hunting for internal
verbatim-duplication (the only RESTRICTED-bucket action this iteration is
authorized to apply directly) and for judgment-call candidates to propose.
Found neither: CLAUDE.md has already been through ~8 prior compression
passes (2-skill harness redesign, Claude 5 portability patch, canonical
principles directive, etc. — see MEMORY.md) and carries no repeated rule
text within itself. `autoresearch/iterations/PROPOSAL-claude-md-minimization.md`
exists but describes a 137-line pre-2-skill-harness CLAUDE.md structure
(auto-resolve/ideate/preflight skills, "5+1 principles") that no longer maps
onto the current 176-line 7-principle CLAUDE.md at all — superseded, not
extended.

## Reverted-deletion / rejected-candidate findings (valuable, not failures)

1. **Mechanical lint parity is load-bearing dual-declaration**, not accretion
   debt. Any future ablation pass on `devlyn:resolve/SKILL.md`'s PHASE 1.5 /
   PHASE 5 sections must grep `scripts/lint-skills.sh` for every literal
   substring in the candidate block first — this codebase enforces exact
   cross-file text parity mechanically in ~77 places just for
   `devlyn:resolve/SKILL.md` alone (25-53 similar hits per reference file).
2. **`devlyn:ideate/SKILL.md` never resolves `CODEX_MONITORED_PATH`** — only
   `DEVLYN_SHARED_DIR`. Currently harmless (no live Codex-routed ideate phase
   ships yet — `engine-preflight.md` calls it "future"), but worth fixing
   forward (either ideate's own `<runtime_paths>` derives it, or
   `codex-config.md`'s snippet stays as the single source) before any
   Codex-routed ideate phase ships, so the two files' assumptions don't
   silently diverge.
3. **Multi-agent working-tree co-editing**: when two agents edit the same
   file in the same session window, whoever commits first sweeps in the
   other's uncommitted lines under their own commit message. Not a defect in
   either change (verified line-by-line via `git show --stat` +
   `git log -S`), but worth a lighter-weight convention (stage only intended
   pathspecs, never blanket `git add -A`, which both this iteration and
   iter-0051 already followed) — the actual failure mode avoided here was
   attribution noise, not lost work.

## Commit

Working tree was already clean at write-time: the SKILL.md edit landed
inside `230268c` (iter-0051's commit) per the concurrent-edit note above.
This iteration's only remaining artifact to commit is this file.
