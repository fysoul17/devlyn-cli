# iter-0018 — Measurement integrity + report-shape lock + iter-0016 final readout

**Status**: SHIPPED 2026-04-27.
**Risk**: low (diagnostic-only, no skill prompts touched, no benchmark behavior changed).
**Cost**: 0 paid suite runs ($0).

## Hypothesis

iter-0016's 5-fixture readout (F2/F4/F5/F6/F9) carries enough signal to direct iter-0019 / 0020 design without spending another suite run on F1/F3/F7/F8. Adding `wall_ratio_*` fields + locking the partial readout into HANDOFF.md / NORTH-STAR.md eliminates the L2-vs-L1 misread risk before the L1 arm lands.

Predicted change (filled in BEFORE):
- No suite-margin movement (this iter does not touch any prompt or run an arm).
- summary.json gains `wall_ratio_variant_over_bare` per fixture and `wall_ratio_variant_over_bare_avg` aggregate.
- HANDOFF.md gains the iter-0016 final-readout block with honest-claim language ("L2 beats L0 in partial readout; L2-vs-L1 unknown").
- F5 finding classified as surgical-scope failure, not pair-deliberation waste.
- F9 finding classified as pipeline-level spec-compliance failure (BUILD/EVAL prompt fold-in for iter-0019/0020), not pair vs solo.

## Mechanism

Three diagnostic moves, sequenced inside a single iter to keep attribution clean (Codex R3 explicit warning: do not bundle measurement and behavior changes — this iter changes only measurement and docs):

1. **wall_ratio_* in summary.json**: per Codex R3 Q3, the wall-time ratio is a comparison metric, not an arm metric. Lives in summary.json rows + suite aggregate, not in per-arm result.json. Future-generalizes to `L1_over_L0` / `L2_over_L1` once iter-0019 lands the L1 arm.
2. **Honest-claim language in NORTH-STAR.md + HANDOFF.md**: per Codex R4 hard pushback, +11.6 suite-avg margin is **L2 vs L0**, not L2 vs L1. iter-0016 partial does not imply release readiness. Phrase numbers conservatively until iter-0019 produces L1 data.
3. **F5/F9 failure classification**: read judge-axis breakdown to attribute losses correctly, so iter-0019/0020 BUILD/EVAL prompts target the actual failure mode, not the surface symptom.

## iter-0016 final readout (5 fixtures, partial — F1/F3/F7/F8 deferred to iter-0019)

| Fixture | V score | B score | Margin | V wall | B wall | Wall ratio | Verify (V/B) |
|---|---|---|---|---|---|---|---|
| F2 | 95 | 78 | +17 | 1201s **TO** | 156s | 7.7x | 100%/100% |
| F4 | 99 | 78 | +21 | 1012s | 177s | 5.7x | 100%/75% |
| F5 | 95 | 96 | **−1** | 770s | 45s | **17.1x** | 80%/80% |
| F6 | 97 | 87 | +10 | 876s | 82s | 10.7x | 83%/83% |
| F9 | 83 | 72 | +11 | 1393s | 87s | 16.0x | 40%/40% |

**Suite avg variant 93.8 / bare 82.2 / margin +11.6 / wall ratio 11.4x.** 0 hard-floor violations. SHIP-GATE FAIL: 4/5 fixtures ≥ +5 against absolute 7/9 floor.

### F2 — variant +17 despite watchdog timeout

State writes (iter-0014 protocol) confirmed: `phases.{build PASS/373s, build_gate PASS/29s, evaluate PASS/120s, critic verdict=- duration=0}`. CRITIC was killed mid-phase by the 1200s watchdog. Variant produced working code (verify=1.0, files_changed=2) but never reached terminal verdict. F2 metadata.timeout=1200s is too tight for the full iter-0014 4-phase pipeline + inter-phase gaps. **Inter-phase gap = 678s unaccounted** — sum of phase durations = 523s, arm wall = 1201s. Phase 1.4/1.5 routing time not measured by current state-write protocol; observability gap.

Bare hits CRITICAL findings: silent-catch DQ, $HOME/.claude WARN-vs-FAIL spec drift, --verbose absolute paths. +17 margin is genuine quality lift, but variant's terminal_verdict missing means the run cannot self-report "done."

**Fold-in for iter-0019/0020**: F2 metadata.timeout 1200→1500s (or 1800s — match F5/F6 budget). Inter-phase observability is a queued open question, not iter-0019 scope.

### F4 — variant +21, the largest L2 lift

Bare misses italic CSS marker (relies on `<em>` only, no `font-style: italic`) and adds out-of-scope `test-results/.last-run.json`. Variant clean.

**Plausibly tool-attached** per Codex R3 Q5: F4 has `metadata.browser=true`, so browser_validate phase fired on variant only. Native security-review also engaged. The +21 lift may be tool-phase attribution, not pair-deliberation attribution. iter-0020 must instrument the two signals separately before claiming pair lift here. **F4 is not yet evidence for "pair > solo."**

### F5 — variant −1 on scope (Codex R4 verdict: surgical-change failure, not pair waste)

Both arms: spec=25, constraint=25, quality=21. Variant scope=24 vs bare scope=25. Judge note: variant added `completed=` field to roadmap frontmatter beyond strict scope. 17.1× wall to gain 0 quality, lose 1 scope.

Codex R4 verdict (verbatim): *"root cause is surgical-change failure, not pairing is inherently waste. The waste signal is real: 17x wall for no quality gain and -1 scope. But the actionable fix is BUILD policy: stricter scope boundary, no opportunistic metadata edits, and audit must explicitly reject unrelated file/frontmatter/status changes."*

Note: F5 spec.md has a "Lifecycle note" stating *"the harness's DOCS phase flips this spec's frontmatter `status` after implementation completes — that is benchmark lifecycle bookkeeping, not a scope violation."* — so a `status:` flip is legitimate. Variant added `completed=` *in addition* to the lifecycle status flip — the extra field is what scored the −1.

**Fold-in for iter-0019**:
- BUILD prompt: explicit instruction "do not add fields to spec frontmatter beyond the lifecycle `status` flip the DOCS phase performs."
- EVAL/CRITIC prompt: scope check rejects opportunistic metadata edits (added fields, reformatted YAML, additional notes outside the lifecycle bookkeeping).
- This is **not** evidence against pair-deliberation. It is evidence the BUILD policy needs stricter scope guardrails.

### F6 — variant +10, genuine constraint lift

Bare hits two CRITICALs: (a) non-ENOENT errors from `statSync` rethrown instead of reported with informative error/exit code, (b) hashing implementation does not follow the explicit `createReadStream → hash` pipe constraint. Variant catches both. This is a real pair-or-tool lift on constraint discipline. iter-0020 must again separate which phase produced the lift (BUILD with first-pass constraint awareness vs EVAL/CRITIC catching it).

### F9 — both arms verify=0.4, spec=16/13 (Codex R4 verdict: pipeline spec-compliance, not pair vs solo)

Variant judge breakdown: spec=16/25, quality=18/25, plus three CRITICAL-finding equivalents (wrong `Error:` prefix, wrong exit 2, wrong JSON top-level shape with ranked authors). Bare same misses + DQ silent-catch.

F9 spec.md is **clear and specific** — line-by-line output format, ISO date, ranked author lines, exit-code 2 + literal `Error: not a git repository`, JSON top-level `commits` + `authors` keys. Both arms missed all three. **Spec is not the issue.** BUILD didn't enforce per-spec verification literally; EVAL didn't catch the divergence; CRITIC (variant only) didn't catch.

Codex R4 verdict (verbatim): *"measurement/report integrity adjacent because both arms failed the same output contract. Do not use F9 for pair-policy conclusions until fixed."*

**Fold-in for iter-0019/0020**:
- BUILD prompt: "Re-read the spec's Verification section before declaring done. Each `verification_command`'s expected stdout/exit must be matched literally — do not paraphrase error messages, exit codes, or JSON keys."
- EVAL prompt: explicit checklist line-by-line: every `verification_command` in expected.json must have its `stdout_contains` substrings present in the actual command output AND its `exit_code` matched. EVAL emits `verify_score < 1.0` only when this checklist is concrete.
- F9 is **excluded** from iter-0020 tool-vs-deliberation attribution data until iter-0019 BUILD/EVAL fix lands and F9 produces clean spec=25 data.

### Honest claim boundary (locked into NORTH-STAR.md operational test #13)

- **L2 vs L0 (5-fixture partial)**: PASS quality margin (+11.6 > +8 preferred), 0 hard-floor violations. FAIL volume rule (5 fixtures only).
- **L2 vs L1**: UNKNOWN. L1 arm does not exist yet.
- **Release readiness**: NOT IMPLIED. L2-vs-L1 compression risk: if L1 lands at +9 over L0, L2's effective lift over L1 is +2.6 — below the +5 floor for L2 vs L1.

## Diff plan

Files changed in this iter (diagnostic + docs only — no skill prompts):

- `benchmark/auto-resolve/scripts/compile-report.py` — add `wall_ratio_variant_over_bare` per row, `wall_ratio_variant_over_bare_avg` suite aggregate, `Wall ratio` column in report.md.
- `benchmark/auto-resolve/results/20260427T121636Z-27d1636-iter-0016-verify/{summary.json,report.md}` — re-compiled with new fields (judges unchanged, scores unchanged).
- `autoresearch/HANDOFF.md` — iter-0016 final readout block, honest-claim language, queue note.
- `autoresearch/NORTH-STAR.md` — operational test #13 (L2-vs-L1 compression risk).
- `CLAUDE.md` — Codex companion pair-review section under "Codex invocation" (iteration-loop pair vs auto-resolve pair distinction).
- `autoresearch/iterations/0018-measurement-integrity.md` (this file).

No skill prompts changed. No fixture or arm behavior changed (compile-report.py post-processes existing artifacts; arms still produce the same `result.json` shape). Lint unchanged.

## Falsification gate

No paid run. Local checks:

1. `python3 benchmark/auto-resolve/scripts/compile-report.py --run-id 20260427T121636Z-27d1636-iter-0016-verify --label iter-0016-verify` → re-emits summary.json with new fields. Verified: `wall_ratio_variant_over_bare_avg = 11.44`, per-fixture ratios populated (F2=7.7, F4=5.72, F5=17.11, F6=10.68, F9=16.01).
2. `bash scripts/lint-skills.sh` → 10/10.
3. `diff -rq config/skills/ .claude/skills/ 2>&1 | grep -v "Only in"` → silent.

## Principles check (per `autoresearch/PRINCIPLES.md` 1–6)

1. **No overengineering** ✅ — single-file Python edits in `compile-report.py`, no new abstractions, no schema extension beyond what Codex R3 prescribed. Doc edits are confined to clarification + readout, no new doc surfaces invented.
2. **No guesswork** ✅ — predictions filled in BEFORE re-compile (no margin movement, new fields populate). Actual ratios filled in AFTER from raw data. F5 / F9 classifications grounded in judge axis breakdown + Codex R4 verdict, not vibe.
3. **No workaround** ✅ — F5 and F9 failure modes are *recorded for fold-in to iter-0019/0020* with concrete prompt-text changes, not patched here. Root-cause language uses 3+ step why-chain (F5: variant added `completed=` → BUILD didn't enforce scope → BUILD prompt lacks frontmatter-edit ban; F9: both arms missed exact spec text → BUILD/EVAL didn't enforce literal verification → prompt lacks "match literally" guardrail).
4. **Worldclass production-ready** ✅ — diagnostic-only iter, no code shipped to runtime. Doc surfaces use `[L2 vs L0 partial; L2-vs-L1 unknown; release not implied]` honest-claim language to prevent a future session shipping under wrong assumption.
5. **Best practice** ✅ — `wall_ratio_*` field uses idiomatic Python `round(x, 2)` + None for div-by-zero guard, no custom defensive helper. Report.md column added in existing table format.
6. **Layer-cost-justified** ✅ — this iter changes nothing run-time, so no L1/L2 cost added. Adds the *measurement* infrastructure that iter-0019/0020 will use to gate layer-cost decisions empirically. The L2 11.4× wall ratio is now first-class in the report.

## Codex collaboration

R1 (cached) — release-gate numbers, 3-iter sequence proposal.
R2 (cached) — per-phase decision-mode taxonomy, EVAL=gated solo not unconditional pair, profile-neutral as text-only.
R3 (cached) — re-ordered iter-0019 (L1 arm) vs iter-0020 (pair policy); L1-codex defer; F4 lift plausibly tool-attached not pair-attached; L2 release gate split from L1 release gate.
R4 (this iter, 27s elapsed, 18,875 tokens) — start iter-0018 on 5-fixture data, defer F1/F3/F7/F8 to iter-0019; F5 root cause = surgical-scope failure not pair waste; F9 = measurement integrity adjacent, do not use for pair-policy conclusions until fixed; L2-vs-L1 compression is the load-bearing risk to lock in doc language now. All R4 verdicts adopted verbatim.

## Lessons (cumulative add)

- **Diagnostic iters are cheap and high-value before behavior iters.** iter-0016 5-fixture data answered five questions about the next two iters' design without spending another paid run. Codex R4 endorsed.
- **Wall-time ratio belongs in summary.json, not per-arm result.json.** Comparison metric, not arm metric. iter-0019 will generalize to `L1_over_L0` / `L2_over_L1` columns.
- **F5 / F9 are NOT pair-vs-solo evidence.** Future iters must avoid citing them as such. F4 and F6 are the only two fixtures in iter-0016 partial that *might* be pair-or-tool lift; iter-0020 must instrument tool-vs-deliberation to decide which.
