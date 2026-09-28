# 0226 — recall screen for the held scripted VERIFY on fresh tasks

2026-09-28. **Status: REGISTERED, frozen before any corpus authoring or candidate call.** Design: independent R0s (root, from three angle drafts; Astra gpt-6-astra/ultra, read-only), then R1: corpus, repeats, witness and grading corrections converged; the pass bar and the invalid-reference rule went to the user. **User decisions (2026-09-28):** the strict bar ("완벽해야 통과 (Astra 추천)"); running only the judge script on synthesized spans, as the 0225 replay did, is not a resolve invocation ("괜찮음"); root merges 0226 PRs after Astra SHIP ("예, 병합해도 됨"). Registration review: see the end. Raw record: `.devlyn/0226/`.

## Why

[0225](0225-resolve-cost-cuts.md)'s replay failed twice by its letter ([RESULT](../experiments/0225/RESULT.md)): 4 of 5 archived binding HIGHs came back as HIGH; the fifth was found at the same line and bound the verdict, but as MEDIUM `verdict_binding: true`, which the frozen rule did not count. Steps 2–5 are held and the product was reverted to step 1 (PR #124). The 0225 corpus is exposed and cannot test an amended rule. The user chose a new registration: a recall criterion defined by the product's own binding rule, tested on fresh, unexposed tasks, with controls and a false-positive assessment.

**0226 decides one thing:** whether the held scripted VERIFY may re-enter development of the steps 2–5 bundle. It cannot establish non-regression against step 1, natural (model-error) recall, recall on defects not specified by a judge model (the author is gpt-6-astra, also a judge), recall after a repair round, population reliability, time or token savings, or anything about steps 3–6.

## Candidate and arms

- **Candidate:** `22616b57` (PR #120 + PR #122); its `config/skills` tree equals `e5269205`'s. Nothing in it changes before or during the screen, including the Claude effort dispatch.
- **What runs:** only `verify-judges.py`, on synthesized open VERIFY spans built as its self-test builds them (`e5269205:config/skills/_shared/verify-judges.py:385-417`). No resolve entrypoint, no earlier phase, no repair.
- **No step-1 control arm.** Step-1 VERIFY needs an owner model to write the judge packets (no script renders them), which is a resolve run, and its owner focus hints were aimed at the defect class (0224 s6-04 `codex-judge.r1.prompt:348`). The controls are the positive (defective) and negative (believed-correct) twins below. NOT PASS does not prove regression, and PASS does not prove non-regression.

## Corpus (K-3, [0221](0221-subtraction-direction.md) §4; [0201](0201-harness-transformation-plan.md) "유한한 평가와 중단 기준")

**Repository rule** (frozen here, before authoring):
- two real public repositories, one Python and one JavaScript/TypeScript, each pinned to a SHA, with a license that allows local modification; at that SHA the repository's own test suite passes offline on the host with standard tools, and no agent instruction file exists anywhere in the tree (`CLAUDE.md`, `CLAUDE.local.md`, `AGENTS.md`, `.claude/`, `.agents/`, `.codex/`);
- never used in the research loop: no match for the repository name under `autoresearch/` or `benchmark/`. This excludes click and commander (D1–D4), django (SW1–5), pytest, and every 0224/0225 repository;
- selection: the author lists eligible candidates (at least two per language) with reasons before reading any code in depth; root clones each at its default-branch head and checks the rule without any model; per language, the eligible repository with the lowest sha256 of its canonical clone URL is chosen.

**Requests:** four per repository, eight in total, one per interaction family in each repository: boundary semantics, ordering/precedence, failure-state preservation, cross-field consistency. Each is a realistic change integrated with the repository's actual behavior, outside lifecycle/installer work.

**Per request:**
- the request text (the judges' `spec.md`) and its public checks (`spec.expected.json`);
- a hidden oracle;
- a reference patch, believed correct;
- one defective twin: the reference with exactly one target mechanism broken, changing exactly the reference's set of files (one target, because both pair rubrics stop at the first binding finding: `verify.md:246-249` at step 1, `:112-114` at `e5269205`). It passes the public checks and fails its designated hidden witness. The mandatory clause it violates is stated in the request;
- a mechanism record: mandatory clause, trigger, causal code path, incorrect behavior, executable witness, near-miss exclusions. File/line supports a match; it is not the identity.

**Authoring and blinding:**
- The author is a fresh, empty-context Astra (gpt-6-astra, ultra) session in a workspace holding only this corpus section, the authoring instructions and the pinned clones. It never sees step-2 code or prompts, 0225 findings, this repository or any candidate output. It selects the repositories and writes the requests, public checks, oracle specifications and mechanism records.
- gpt-6-sol implements the references, twins and hidden oracles from those specifications in a writable copy with no access to this repository.
- Calibration (0207 style) is model-free and run by root: each reference passes the public checks and every hidden oracle row; each twin passes the public checks, fails exactly its designated witness and changes exactly the reference's files. A fresh Astra session reviews calibration and mechanism records before the freeze.
- A request that fails calibration is repaired or replaced under the same rule before the freeze. No candidate or judge call touches corpus material before the freeze.

## Rounds

- **64 VERIFY rounds** = 8 tasks × 2 variants (reference, twin) × 2 role orientations × 2 fresh repetitions; 128 judge calls; a fresh isolated workspace and session per round.
- **Orientations** (the 0225 seats, `0225:99`): claude = `claude-opus-5-5` primary + `gpt-6-astra`/high pair; codex = `gpt-6-astra`/high primary + `claude-opus-5-5` pair. Codex seats get an explicit `high` profile. Claude seats keep the candidate's own dispatch (primary: no effort flag; pair: `medium`; `e5269205 verify-judges.py:33-34`), because explicit Opus effort has no adapter declaration; effective Claude effort is recorded as UNKNOWN unless attested.
- **Order:** four blocks, claude-rep1, codex-rep1, codex-rep2, claude-rep2; within a block the 16 (task, variant) rounds are sorted by sha256 of `block|task|variant`.
- **Span:** base = the repository at its pinned SHA; head = base + the variant patch; spec mode; authorized surface = the reference's files; the self-test's risk profile (`e5269205 verify-judges.py:409-410`: no high risk, no risk probes, pair default on) for every round; MECHANICAL = the candidate's own invocation (`e5269205 SKILL.md:312`) on that tree, with every declared tool provisioned, type checkers included where the repository declares them.
- **Opaque identity:** the workspace path, `run_id`, branch, commit messages and author metadata, all of which the rendered prompt can show (`e5269205 phase-prompt-render.py:109-110`), are opaque per-round tokens of the same form for both variants.
- **Judge environment:** `replay.py`'s `minimal_env` (`autoresearch/experiments/0225/replay.py:115`), the round's own `CODEX_HOME` for the HOME shim (`replay.py:80`), and the repository's toolchain on `PATH`; no owner variables.

## Apparatus and seal

- A new root outside `$HOME` with clean ancestors (0225 RESULT "Apparatus divergence"); codex-cli 0.156.1 (private install) with its model cache and the HOME shim; Claude Code 2.1.281; binary hashes recorded. Each Claude seat's instruction attachments are checked before the freeze and on every call.
- **Driver:** `replay.py`'s generic parts (pins, seal, run, score) are reused; span synthesis replaces archived-state reconstruction; the scorer imports the candidate's own `finding_rank` (`e5269205:config/skills/_shared/judge-output-parser.py:32-40`) in place of the HIGH/CRITICAL-only filter (`replay.py:543-545`). gpt-6-sol implements it and Astra verifies it to SHIP. A stub dry run of all 64 spans passes before the freeze and asserts that no rendered prompt byte contains a task id, variant name or label.
- **Seal:** hidden material (oracles, mechanism records, calibration outputs, author and implementer workspaces) and each round's other variant live only under the 0226 root, which is sealed per round as `replay.py:403` does. The research repository holds only digests until scoring ends. After the run every seat transcript and log is scanned for reads of the 0226 root outside the round's copy, of the research repository, or of the author/implementer workspaces.

## Freeze and witness

- **Freeze commit:** the driver, the scorer (including the infra-fault signature list below) and the manifest: candidate tree hash, pins, per-round span hashes, order, and sha256 digests of every corpus file and calibration output. The corpus contents are committed after scoring and must match. This registration is not edited.
- **Witness:** push the freeze commit and open a PR whose head is that SHA; nothing is pushed to that branch until scoring ends. Before spawning, retain the PR record (head SHA, server `createdAt`, and its commit list and timeline showing that SHA as the only head, with no force push) and verify that `git ls-remote` returns the frozen SHA. The PR's `createdAt` must precede the first seat's `started_at`.

## Scoring (pre-committed)

- **Rank:** product `finding_rank` 2 means HIGH/CRITICAL, or MEDIUM with literal `verdict_binding: true`.
- **Coverage finding:** a finding whose claim is that a clause lacks executable coverage or evidence, not that the code behaves incorrectly. The rubric requires these (`e5269205 verify.md:65-77`), and a twin necessarily escapes the public checks, so they are reported and have no effect: never a hit, a false alarm or an unsupported extra. A finding that also claims incorrect behavior is scored as behavioral.
- **Hit** (twin round): an authenticated behavioral finding from either seat, retained through the merge, with rank 2, that matches the target mechanism record, in a round whose merged verdict is NEEDS_WORK. Rank ≤ 1 findings that match are reported as detections.
- **Masked pool:** every rank ≥ 1 finding is pooled per task with round type, orientation, repetition and seat masked, in a seeded order. Root labels each as coverage or behavioral and as matching the target mechanism or not. For each rank-2 behavioral finding, root writes one executable check of the clause it claims is violated (a clause of the task's `spec.md`/`spec.expected.json` or of the repository's existing tests) and runs it on the base, reference and twin trees. Astra audits every label, check and result. All of it is committed and pushed before the join. A root–Astra disagreement left open after one exchange of cited evidence resolves against PASS (behavioral, no match, not reproduced).
- **After the join**, each rank-2 behavioral finding that is not a hit is, in this order:
  - its check passes on the finding's own tree: a **false alarm** on a reference round, an **unsupported extra** on a twin round;
  - its check exercises the repository's existing tests and also fails on the base: pre-existing, reported, no effect;
  - its check fails on the reference: **invalid reference**, whichever round it came from;
  - otherwise (it fails only on the twin): a twin-only extra, reported, no effect.
- **Unsupported terminal:** a reference round whose merged verdict is NEEDS_WORK is also a false alarm unless it carries a rank-2 finding that is a coverage finding, pre-existing or an invalid reference.
- **Grading corrections:** an independently audited fix to the scorer code that restores the frozen semantics re-grades the preserved evidence. Labels, mechanisms, thresholds and eligibility never change after the join.

## Registered outcome (strict bar)

**PASS** iff all hold; anything else is **NOT PASS**, reported with every violated condition and the classification of every event:
1. 32/32 target hits: every task × orientation × repetition ("found at least once" never counts);
2. 0/32 reference rounds with a false alarm (including an unsupported terminal);
3. 0 unsupported extras;
4. no invalid reference;
5. every round ends with a merged verdict that is not BLOCKED, and every seat in every round completes, is authenticated and has its output accepted by the merge: no seat timeout, malformed output or seat BLOCKED, and no retry. Input BLOCKEDs (harness rows or early refusals carrying one of 0225's input tags, as `replay.py:84-86,607-608` computes them) are reported as such;
6. sealed inputs unchanged (inventory before and after), seat execution overlapping in every round, no excluded read in the scan, and the witness intact.

- **PASS:** step 2 (`22616b57`) is readmitted as an experimental candidate for bundle development, and steps 3–5 may be prepared. A live comparison of the bundle needs its own registration and the user's approval to run resolve; 0225's approval does not transfer. Nothing ships from 0226, the 0225 release rule (bundle, both configs) stands, and step 6 stays conditional on bundle adoption.
- **NOT PASS:** steps 2–5 stay held; any next move needs a new registration.

## Faults

- A frozen classifier reads only each seat's exit status, transport outcome and stderr, matches the listed infra signatures (usage or rate limit, capacity, network, authentication, a CLI binary crash), and emits only the class, before any output file is opened. An expiry or failure that matches no signature is candidate-caused (condition 5).
- Infra faults, and stops on hash, pin or account drift or on an instruction-file load: keep the row as `.stop-N`, name and fix the cause, and re-dispatch the affected bundle: every round whose execution the cause could have changed ([0224 DESIGN](../experiments/0224/DESIGN.md) "Before any rule is computed" 3). The same cause recurring after its fix is NOT PASS.
- Never re-dispatch because of a verdict.

## Predictions (before authoring)

- **Astra:** 32/32 hits; no false alarm or unsupported extra; at least one hit labeled MEDIUM `verdict_binding: true`.
- **Root:** at least 31/32 hits; at least one false alarm or unsupported extra, so P(PASS) ≈ 0.3; at least one MEDIUM `verdict_binding: true` hit; 0 input BLOCKEDs; Codex seats author most hits; median round wall ≤ 120 s.

## Work order

1. This registration: Astra FREEZE, then a PR that root merges.
2. Corpus: repository selection, blind authoring, implementation, calibration, calibration review.
3. Apparatus: driver, Astra SHIP, stub dry run.
4. Freeze commit and witness, 64 rounds, masked scoring with Astra audit, RESULT.

## Addendum A1 (2026-09-28, before any candidate call)

A Claude seat reports CLI and API errors (usage or rate limit, overload, authentication) in its result envelope rather than on stderr: a probe of Claude Code 2.1.281 with an unknown model exited 1 with `is_error: true`, `api_error_status: 404` and `terminal_reason: "api_error"` in the envelope, and only a `[claude-code:unrecognized_model]` tag line on stderr. The infra classifier ("Faults") therefore also reads those three envelope fields of a Claude seat, never `result` or any other judge-authored text. Nothing else changes. Review: Astra (see "Registration review").

## Registration review

Astra (gpt-6-astra, ultra, read-only), in parallel with three Claude critics (gaming, executability, subtractive lenses): R0 REVISE (4; the critics added coverage-finding scoring, the timeout/INCONCLUSIVE overlap, masked support, opaque identity, the seal, the witness head and the instruction-file rule) → R1 REVISE (6: coverage exemption scope, own-tree first, base failure, unsupported terminal, `CODEX_HOME`, input-BLOCKED field) → R2 FREEZE. The user's two further decisions came between R0 and R1. Raw: `.devlyn/0226/reg-*`.

Addendum A1: Astra driver-spec review R1 (legitimate before the freeze and any candidate call; the three-field allowlist keeps judge text out) → R2 SHIP. Raw: `.devlyn/0226/driver-spec-r*`.
