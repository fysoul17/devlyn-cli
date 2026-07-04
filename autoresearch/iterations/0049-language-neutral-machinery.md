# iter-0049 — language-neutral decision machinery (F1-F6 closure)

**Status**: SHIPPED. Closes F1-F6 from
`autoresearch/iterations/0048-human-language-robustness.md`'s static audit —
all six English-natural-language-keyed decision points in
`config/skills/_shared/spec-verify-check.py` replaced with machine-structured
markers/declarations that carry no dependency on any human language. F7
(`verify-merge-findings.py`) and this file's own internal
`solo-headroom hypothesis` / `solo ceiling avoidance` validators remain
explicitly out of scope (rationale below) — both are dead code for ordinary
specs regardless of language, confirmed by re-reading their own guard
clauses, not assumed.

## Principle (repo's own CLAUDE.md, binding for this iteration)

The root cause iter-0048 named was **deciding anything based on
natural-language prose content at all**, not "the regexes happen to be
English." The fix therefore could not be "add Korean regexes next to the
English ones" — that is an unbounded per-language treadmill and re-violates
the same invariant on the next language. Every fix below either (a) replaces
a *classifier* (infer X from prose) with a *declaration* (the spec author
states X directly, in a form that is validated structurally — enum
membership, exact substring, JSON boolean — never regex-matched against
prose), or (b) replaces an *English-keyed locator* with an *opaque ASCII
sentinel* that is decoupled from the human-readable heading text next to it.

## Codex cross-check — two rounds to convergence, not rubber-stamped

Both rounds ran read-only, `model_reasoning_effort=xhigh`, via
`codex-monitored.sh` isolated mode.

**Round 1** (my initial design) → **substantive pushback**, not agreement:
1. Confirmed sentinel-comment locator over a fenced-code-block info-string
   (info-string + "whole-document derived_from scope" would let risk-probes
   justify themselves from Context/Requirements text instead of the visible
   Verification contract — a real semantic weakening I hadn't fully
   costed).
2. Flagged my F3 design (`required_risk_probe_tags: [...]` flat list) as
   "a declared contract, not an independently derived one" — sound against
   PLAN/IMPLEMENT narrowing the contract post-hoc (spec is read-only during
   a run), **not** sound against a single session running `ideate --quick`
   immediately followed by `resolve`. Proposed `required_risk_probe_requirements:
   [{tag, derived_from}]` (tag **paired** with the exact bullet, not a bare
   tag) instead — this also closes part of F5 without a prose regex.
3. Confirmed F4/F5 prose-regex deletion, but said dropping
   `asserts_exact_error_object` entirely loses real signal; recommended
   requiring it whenever `shape_contract` and `error_contract`/
   `http_error_contract` **co-occur on the same probe** — purely structural
   (tag-based), zero prose dependency.
4. Confirmed F6 boolean design; added: reject `pure_design: true` alongside
   a non-empty `verification_commands` (contradictory state).
5. Recommended hard-cut migration (no fallback) — an internal schema, no
   external consumers, and a fallback would keep the exact English decision
   path alive that this iteration exists to remove.
6. Caught a real residual gap I had not designed for: `extract_verification_block()`
   still conflated "sentinel absent" (legitimate no-op) with "sentinel
   present, no fenced JSON" (author clearly intended a contract and botched
   it) — recommended splitting into a tri-state so the second case fails
   loud, not silent.

I revised the design against all six points and sent it back.

**Round 2** (revised design) → **"Not converged as written,"** three more
concrete corrections, one of them a real bug:
1. **Regex bug, verified by hand-tracing.** My revised sentinel regex
   `r'...-->[ \t]*\n(.*?)(?=^##[ \t]+|\Z)'` produces an **empty capture
   group** whenever the sentinel is immediately followed by the heading (the
   authored, intended layout) — the lazy `(.*?)` matches zero characters and
   the lookahead succeeds immediately against the heading line itself.
   Fixed regex consumes the heading line as part of the mandatory prefix:
   `r'...-->[ \t]*\n(##[ \t]+[^\n]*\n.*?)(?=^##[ \t]+|\Z)'`.
2. Confirmed the F3 `{tag, derived_from}` structure is right, but flagged
   that `probe-derive.md` forbids reading `spec.expected.json` at all — so
   the declared array must be pasted into PHASE 1.5 by the orchestrator (tag
   + derived_from only, never the rest of the file — those strings are
   already visible spec substrings, so nothing hidden leaks).
3. Flagged that the staging normalizers (`spec-verify-check.py`'s own
   `stage_from_expected`/`stage_from_source` AND `run-fixture.sh`'s
   benchmark `expected.json` → `.devlyn/spec-verify.json` normalizer) drop
   any key besides `verification_commands` — if F3 obligations must survive
   staging, the normalizers need to carry them too.

Both were real, verified during implementation (see "Bugs Codex caught"
below) — this was not a courtesy second pass.

## Design shipped (per F1-F6)

**F1/F2 — sentinel locator, not header text.**
`config/skills/_shared/spec-verify-check.py`:
```python
VERIFICATION_SECTION_RE = re.compile(
    r'(?ms)^<!--[ \t]*devlyn:verification[ \t]*-->[ \t]*\n(##[ \t]+[^\n]*\n.*?)(?=^##[ \t]+|\Z)'
)
FILES_TO_TOUCH_SECTION_RE = re.compile(
    r'(?ms)^<!--[ \t]*devlyn:authorized-surface[ \t]*-->[ \t]*\n(##[ \t]+[^\n]*\n.*?)(?=^##[ \t]+|\Z)'
)
```
Authoring convention: `<!-- devlyn:verification -->` (or
`<!-- devlyn:authorized-surface -->`) on its own line, directly above the
heading, no blank line between. The heading text after the sentinel is pure
human decoration — `## Verification`, `## 검증`, anything — the mechanism
never reads it. `extract_verification_block()` / `extract_authorized_surface_block()`
now return a tri-state `(section_found, json_block)` instead of a bare
`str | None`:
- `section_found=False` — sentinel absent entirely. Legitimate silent no-op
  for a handwritten spec with no mechanical contract (unchanged backward
  compat from iter-0019.6).
- `section_found=True, json_block=None` — sentinel present, no fenced
  ```json``` block inside it. **Malformed carrier, CRITICAL** — the author
  clearly intended a contract. This is the F1 fail-closed gap Codex caught:
  before this split, "no header at all" and "header present but incomplete"
  were indistinguishable, so a Korean-titled section with a botched fence
  would have silently no-opped instead of failing loud.
`run_check_mode()` (ideate's `--check`) and `stage_from_source()` (BUILD_GATE's
staging) both consume the tri-state; `--check` now exits 2 (not 0) on
"sentinel present, no fence."

**F3 — declared risk-probe obligations, not a prose classifier.**
`required_risk_probe_tags()` (13 English keyword/phrase regexes) deleted
outright. Spec author declares, in the same JSON payload that carries
`verification_commands`:
```json
{"verification_commands": [...], "required_risk_probe_requirements": [
  {"tag": "rollback_state", "derived_from": "<exact ## Verification bullet>"}
]}
```
New `resolve_required_risk_probe_requirements()` resolves this from whichever
carrier `verification_commands` itself would come from (sibling
`spec.expected.json` wins, else the inline fenced block) — same priority
order the file already uses everywhere else, so no new trust boundary is
introduced. `load_risk_probes(require_present=True)` now requires, per
declared entry, a probe whose `tags` includes that `tag` **and** whose own
`derived_from` exactly equals the declared string — tighter than the old
tag-only check (also closes part of F5, per Codex's point 2). `derived_from`
must still be an exact substring of the visible verification text (unchanged,
already language-neutral). `probe-derive.md`'s `<input>` section now tells
the orchestrator to paste just the `{tag, derived_from}` pairs (not the rest
of `spec.expected.json`) into PHASE 1.5, so the probe-derivation agent isn't
blind to what BUILD_GATE will mechanically require.

**F4/F5 — delete the prose evidence-gates; structural co-occurrence
instead.** `shape_contract_requires_evidence()` and the two tag-specific
`derived_from` regex checks (`error_contract`, `http_error_contract`)
deleted. `shape_contract`'s base evidence (`uses_visible_input_key_names`,
`asserts_visible_output_key_names`, `asserts_no_unexpected_output_keys`) is
now **unconditionally** required whenever the tag is declared — this
actually makes the file *more* consistent, not less: every other tag in
`RISK_PROBE_REQUIRED_EVIDENCE` was already unconditional; `shape_contract`
was the sole exception via the deleted prose gate. The extra
`asserts_exact_error_object` requirement is now a pure tag-co-occurrence
rule:
```python
if "shape_contract" in tags and ({"error_contract", "http_error_contract"} & set(tags)):
    required_shape.add("asserts_exact_error_object")
```
Known, explicitly-accepted residual (not silently dropped): this only
catches co-occurrence on a **single probe**. If `shape_contract` and
`error_contract` are declared as coverage for the same bullet but split
across two separate probes, neither is forced to carry
`asserts_exact_error_object`. Codex offered a fully structural close (tie it
to `required_risk_probe_requirements` entries sharing one `derived_from`);
not implemented this iteration — scoped out to keep the change to what
actually closes F1-F6, flagged here rather than silently left.

**F6 — JSON boolean, not an English sentence.** `PURE_DESIGN_ESCAPE = "all
Requirements are pure-design"` deleted. `spec.expected.json` declares
`"pure_design": true` (added to `EXPECTED_TOP_LEVEL_KEYS` and
`_shared/expected.schema.json`); `validate_expected_against_sibling_spec()`
checks `data.get("pure_design") is True` — no longer needs to open `spec.md`
at all for this specific check (the two checks that still do —
solo-headroom/ceiling — are the explicitly out-of-scope internal vocabulary,
untouched). Added invariant per Codex: `pure_design: true` alongside a
non-empty `verification_commands` is now a rejected contradiction, not
silently accepted.

## Migration — hard-cut, with one exception discovered mid-implementation

Hard-cut confirmed safe for the skill surface: no live `docs/specs/*` spec
uses the old bare header (`docs/specs/` holds only `queue.md`); no
`lint-skills.sh` assertion pins the old regex source (checked before
committing to the policy).

**Benchmark fixtures — NOT migrated, by design, after a real regression was
caught and reverted.** `benchmark/auto-resolve/{fixtures,shadow-fixtures,test-cases}/*/spec.md`
(38 tracked files) were initially bulk-migrated (sentinel added ahead of
their prose `## Verification` heading) to satisfy Codex's round-2 finding
that `l2_risk_probes` benchmark arm passes the raw fixture `spec.md` directly
to `--spec` for non-F9 fixtures (`run-fixture.sh:428`), so
`extract_verification_text()` needs the sentinel to find the section for
`derived_from` substring matching. Running `bash scripts/lint-fixtures.sh`
against the migrated fixtures immediately failed 21/21 active fixtures:
these fixtures' real machine contract is a *sibling* `expected.json`
(benchmark-only convention, validated separately via `--check-expected`) —
the `## Verification` prose in `spec.md` is a human task description with no
inline fence *by design*, and the new tri-state correctly (for a real spec)
treats "sentinel, no fence" as malformed. Reverted the bulk fixture edit
(`git checkout --` on all 38 files) and instead patched
`benchmark/auto-resolve/scripts/run-fixture.sh`'s spec-mode branch to inject
the sentinel into the **work-dir copy only**, at the same point it already
stages other run-time artifacts — the source fixture repo keeps its original
prose-only shape (so `lint-fixtures.sh`'s existing, correct check keeps
passing), and the `l2_risk_probes` arm's copied spec.md gets the sentinel it
needs. `scripts/lint-fixtures.sh`, `scripts/lint-shadow-fixtures.sh`, and
`benchmark/auto-resolve/scripts/test-lint-fixtures.sh` all still pass after
the revert (see Verification below) — falsifies the assumption that a bulk
migration would be a clean no-op; the copy-time fix is the actually-correct
one, found only by running the fixture lint, not by static reasoning.

## Bugs Codex caught before they shipped (raw evidence, not a summary)

1. **Empty-capture regex bug** (round 2, point 1) — hand-traced, confirmed:
   my round-1 regex silently captured nothing whenever the sentinel
   immediately preceded the heading — i.e., on every correctly-authored
   spec. Would have made F1 appear fixed in isolated testing (a spec with
   blank-line padding between sentinel and heading would "work") while
   silently failing on the actual documented authoring convention. Fixed
   before any self-test was written against it.
2. **Error-swallowing in the F3 resolver** (self-caught during my own
   `--self-test` iteration, same class of bug Codex's round-2 point 3 was
   warning about): my first draft of `resolve_required_risk_probe_requirements()`
   did `if err or data is None: return ([], None)` — silently discarding a
   malformed-sibling error instead of propagating it, which would have made
   a spec with an **unknown risk-probe tag** in its declared requirements
   pass silently instead of failing closed (exactly the failure mode this
   whole iteration exists to eliminate, reintroduced by my own draft). Caught
   by the `required_risk_probe_requirements with an unknown tag was accepted`
   self-test assertion actually failing; fixed by propagating `err`.

## Adjacent, explicitly NOT touched this iteration

- `verify-merge-findings.py`'s `spec_has_solo_headroom_hypothesis()` (F7) and
  this file's own `validate_present_solo_headroom_hypothesis` /
  `validate_present_solo_ceiling_avoidance` — confirmed dead for ordinary
  specs (return `None`/`False` immediately absent the literal internal
  research phrases `solo-headroom hypothesis` / `solo ceiling avoidance` /
  `solo_claude`), deeply woven into ~6 ideate/resolve reference docs plus
  ~15 `lint-skills.sh` pins. Same class as F7, same reasoning: no real-user
  impact regardless of language, and converting it is a separate,
  much-larger benchmark-tooling-only project.
- `SKILL.md` PHASE 0's `risk_profile.high_risk` classification (English
  keyword list: "auth/authz, permissions, security, token/session,
  payment/..." over the free-form goal text) and `free-form-mode.md`'s
  `verb_class`/`pair_evidence_intent` classifiers — genuinely English-keyed,
  but this is prompt guidance an LLM reads and reasons over semantically in
  any language (not a Python regex), and it governs a *different* decision
  (whether risk-probes/pair-verify auto-escalate at all) than F1-F6 (which
  govern the mechanical gates once a spec already exists). Flagged as the
  next candidate, not fixed here — team-lead's brief scoped this iteration
  to `spec-verify-check.py`'s F1-F6.

## Verification

**Self-test**: `python3 config/skills/_shared/spec-verify-check.py --self-test`
— 0 exit, all scenarios pass (43 header-sentinel fixture writes migrated;
F3's 4 new scenarios — missing coverage / covered / unknown tag / bad
derived_from — added; F4/F5's ~10 English-keyword-classifier test blocks
deleted and replaced with structural co-occurrence tests; F6's contradiction
+ non-boolean tests added).

**Lint**: `bash scripts/lint-skills.sh` — full green (was 15 failures after
the mechanical edit, before the lint/test-script updates: 11×Check-6d
assertions pinning deleted regex source, 3× downstream fixture-lint scripts
failing on the reverted-fixture pure-design message, 1× stray).

**Direct mechanical Korean verification** (bypassing the LLM entirely — calls
`spec-verify-check.py` the same way BUILD_GATE does, in throwaway dirs under
the session scratchpad):
- F1 engagement: a Korean spec (`# 한국어 스펙` / `## 검증` heading, real
  content in Korean) with the sentinel + a **deliberately wrong**
  `verification_commands` entry (`printf fail-me` instead of `printf ok`) →
  `[spec-verify] 1/1 command(s) failed; 1 finding(s) written` — the net
  engaged, executed the command, and caught the deliberate mismatch (proves
  it isn't silently no-opping); corrected to `printf ok` → `all 1 command(s)
  passed`, exit 0.
- F2 engagement: a Korean PLAN (`## 수정할 파일` heading under
  `<!-- devlyn:authorized-surface -->`) declaring `authorized_surface:
  ["bin/cli.js"]`, then a diff touching `lib/secret.js` too → `scope.out-of-scope-file`
  CRITICAL naming `lib/secret.js`, exit 1.
- F3 engagement: `required_risk_probe_requirements` with a Korean
  `derived_from` bullet (`"실패 시 임시 상태를 되돌려서..."`) — a probe with the
  wrong tag (`prior_consumption`) → `risk-probes.jsonl missing required
  probe(s): rollback_state (derived_from='실패 시 임시 상태를 되돌려서...')`,
  exit 1; corrected to `rollback_state` with matching evidence → `risk
  probes valid`, exit 0.
- Fail-closed negative: a spec with **no sentinel at all** (genuinely
  handwritten, no mechanical contract intended) → exit 0, no
  `spec-verify.json`/findings written (silent no-op preserved, matching
  documented backward-compat).
- Fail-closed malformed: a spec **with** the sentinel and heading but no
  fenced JSON block → `[spec-verify] carrier malformed: ... has no fenced
  \`\`\`json\`\`\` block`, exit 1, CRITICAL finding written — the exact F1
  ambiguity Codex's round-1 point 6 flagged, now a clean binary.

**Real-pipeline regression (English, compliance cells, actual model
invocation via fresh `claude -p`/`omp -p` subprocesses, not direct script
calls)**:

- `benchmark/probes/scripts/run-compliance-cell.sh --cli claude --size small
  --run-id iter0049-verify-claude-small` (sonnet, free-form mode against
  `F1-cli-trivial-flag`) — **PASS**, 4/4 mechanical assertions
  (`state_found`, `phases_ordered`, `verify_evidence` via
  `sub_verdicts_with_artifacts`, `archive_ran`); results at
  `benchmark/probes/results/iter0049-verify-claude-small/compliance/claude-small/compliance-check.json`.
  Elapsed 1150s. Workdir git log confirms a real commit (`b132bc3`) adding
  `--loud` to `bin/cli.js` plus a test — not a fabricated pass. Clean
  regression vs. iter-0042/0046/0048's claude-small cells.
- `--cli omp --size small --run-id iter0049-verify-omp-small` — **PASS**,
  same 4/4; `benchmark/probes/results/iter0049-verify-omp-small/compliance/omp-small/compliance-check.json`.
  Elapsed 1550s.
- Hand-authored English spec-mode `/devlyn:resolve --spec` run (throwaway
  repo, trivial `bin/cli.js`, spec using the post-iter-0049
  `<!-- devlyn:verification -->` sentinel + sibling `spec.expected.json`,
  invoked via a fresh `claude -p --model sonnet` subprocess for the same
  filesystem-isolation reason Check A/B use subprocess isolation) —
  **terminal `BLOCKED:infra-merge-script-crash`, but the sentinel/JSON
  mechanism itself is confirmed correct**: `spec-verify.json` staged exactly
  `spec.expected.json`'s `verification_commands`; `spec-verify-findings.jsonl`
  is empty (**no `correctness.spec-verify-malformed` finding** — the
  well-formed spec was accepted cleanly, not silently rejected);
  `build_gate.log.md` shows Gate 4 actually running
  `spec-verify-check.py --include-risk-probes`, catching a genuine round-0
  literal-mismatch (`BGATE-0001`, output was `HELLO` not `...LOUD`), driving
  the fix loop, and passing round 1 (`node bin/cli.js --loud` → `HELLO
  LOUD`); VERIFY's own merge computation succeeded
  (`PASS_WITH_ISSUES`, 0 HIGH/CRITICAL) before the crash. The BLOCKED verdict
  traces to `verify-merge-findings.py:789` (`verify.setdefault("sub_verdicts",
  {})` returns `None`, not `{}`, because `state-phase-write.py` always writes
  `sub_verdicts` as JSON `null` rather than omitting the key, so the next
  line's item-assignment raises `TypeError`) — this is the **exact,
  already-documented pre-existing bug** from iter-0048's "Next classes" list
  item 3 ("found during iter-0046's negative-control run, not fixed,
  reported for triage"), confirmed via `git status` to have zero
  modifications in this iteration's diff. Not a regression; a known,
  separate follow-up (one-line fix: replace the `setdefault` with an
  explicit `isinstance` guard, mirroring the pattern two lines above it).

## Token / line delta

`scripts/skill-token-gauge.py` (cold_start column, ideate+resolve producer
docs only — `spec-verify-check.py` is an executed script, not loaded skill
context, so its own reduction doesn't show here):

| File | Before | After | Δ |
|---|---|---|---|
| ideate/SKILL.md | 2971 | 2988 | +17 |
| ideate/spec-template.md | 1612 | 1977 | +365 |
| resolve/SKILL.md | 9924 | 9924 | 0 |
| resolve/free-form-mode.md | 1872 | 1930 | +58 |
| resolve/build-gate.md | 1194 | 1217 | +23 |
| resolve/plan.md | 1081 | 1137 | +56 |
| resolve/probe-derive.md | 3833 | 3982 | +149 |
| **ideate+resolve subtotal** | **38179** | **38847** | **+668** |

The producer-doc token cost is a real, accepted addition (authors need to be
told the new sentinel/declaration conventions) — but the mechanism itself
went the other way: `config/skills/_shared/spec-verify-check.py` is
**3768 → 3671 lines (-97)** despite adding 4 new F3 self-test scenarios and
2 new F6 self-test scenarios, because deleting the 13-regex classifier plus
its ~10 dedicated self-test fixtures outweighed everything added. Full diff
across every changed file: **486 insertions(+), 548 deletions(-) — net -62
lines.** Consistent with this repo's subtractive-first mandate: the
prose-classifier deletion is the load-bearing win; the producer-doc growth is
the accepted cost of teaching the replacement contract.

## Commit

See `git log --oneline -- autoresearch/iterations/0049-language-neutral-machinery.md`.
