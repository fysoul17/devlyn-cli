# HANDOFF — for the next session

**Read [`NORTH-STAR.md`](NORTH-STAR.md) first** (project goal). **This file second** (operating context). **[`PRINCIPLES.md`](PRINCIPLES.md) before any iter file edit** (pre-flight 0 + P1-P7). **[`MISSIONS.md`](MISSIONS.md)** confirms which mission is active.

Last refined 2026-04-29 (post iter-0021 calibration ship + iter-0022 design close-out via 3-round Codex dialogue).

---

## 🚦 START-HERE — three things only

1. **iter-0022 has not started.** No iter-0022 code is shipped on disk. The shape was designed in iter-0021 close-out + R1-R3 Codex dialogue (2026-04-29 evening). A fresh session implements iter-0022 from scratch after the cold-start sanity check below.
2. **iter-0022 = build five infrastructure deliverables, real provider/model invocations = 0.** Schema doc + idgen script + lint script + preflight script + auto-resolve input contract change. Detail in "iter-0022 execution plan" below. Each deliverable has explicit acceptance gates.
3. **iter-0023 is BLOCKED until every iter-0022 acceptance gate passes.** iter-0023 is the measurement pilot — Arm A (control: solo PLAN + Codex BUILD) vs Arm B (test: pair PLAN + Codex BUILD) on F2 + F3 — that tests whether PLAN-pair architecture causally rescues Codex BUILD on iter-0020-class failures. It does not start as the "next obvious thing" after iter-0022 lands — it starts only after the explicit checklist in the iter-0023 stub clears.

Everything below this fold supports those three.

---

## ⛔ Hard operating rule, learned in iter-0021

**Pair-review is part of the work, not commentary on it.** Codex R-final on the iter-0021 draft caught a load-bearing fabrication: the draft claimed "F2 and F4 specs do NOT carry the lifecycle note." Codex pulled the actual files (`judge-prompt.txt:225/:219`) and proved the note IS present — the draft cited evidence I had not opened. Without that catch, iter-0022 design would have started from a false mechanism story and shipped a wrong-target fix.

**Apply to iter-0022**: no claim about fixture state, schema coverage, lint behavior, registry content, paired-arm wall-time, or measurement-pilot readiness may be made without **direct file verification** at the time of the claim. "Codex agreed" is not enough. Pair every non-trivial claim with `cat`/`grep`/`Read` evidence at the moment of writing.

---

## 🧭 STANDING USER DIRECTIVES

Block 1 is **strictly user-verbatim** (the 2026-04-28 directive logged on every HANDOFF.md commit since). Block 2 contains **binding operational excerpts** from each rapid-fire 2026-04-29 directive — they are NOT verbatim, since the originals had connecting words ("ㄱ.", "그리고", "오케이"), interleaved framing, and minor typos that have been edited out for compactness. The full original messages survive in the live conversation transcript; any reconstruction with disputed semantics should consult that transcript directly, not these excerpts. Block 3 is **Codex GPT-5.5's framing that the user adjudicated as canonical** — NOT user-authored, but binding because the user said "1번" to it.

Never re-summarize Block 1. If context auto-compacts, FIRST action on resume is re-load this whole section. If a future session finds Block 1 missing or summarized, restore from git history.

### Block 1 (2026-04-28 — North Star + 5/6 principles + Codex pair + 산으로 + docs continuous)

> 한가지만 더. 지금 하고있는 것들이 북극성의 목표를 향해서 no xxxx, worldclass xxx 5대 원칙들을 바탕으로 계속 개선을 해나가고 있는게 맞지? 그냥 오로지 점수를 위해서 하는게 아니고 말이야? 확실하게 해주고 항상 codex cli gpt 5.5 와 함께 compenion 으로서 pair 로 논의하고 최선의 결과에 도달할 수 있도록 끝까지 연구하고 개선해줘. 산으로만 가지마. 이제는 됐다 싶을때까지 계속 돌아. 하면서 계속 docs는 업데이트 해주고, 50% 이상 context가 차면 compact 하고 handoff 를 통해서 지금 내가 얘기한것 토씨하나 틀리지 않고 그대로 각인하고 계속 진화시켜나가.

### Block 2 (2026-04-29 evening — six rapid-fire directives that bind iter-0022)

> 우리 subscription 으로 하는거니까 무료니 얼마 드니 그런거 하지마 앞으로 메모리에 박아.

> L2 는 분업이 아니라 pair 협업을 기준으로 가자.

> 빌드도 협업이어야 할거 같은데??

> 효율과 정확성, 그리고 reasonable 한 속도라고. 무조건 빨라 오래걸려도 괜찮아가 아니라.

> consult 라기보다는 협업모드야. 조언이 아니라. 최적의 결론을 낼때까지. pair 도 반드시 하는게 아니라, 비교해봐야해. pair 로 했을때와 혼자 했을때 크게 차이가 없다면 혼자 하는게 나을수도 있기 때문에.

> 원래 설계에 가장 많은 시간을 쏟고 가장 정확하고 확실한 context engineering을 해야한다고 생각해. build 는 오롯이 plan 에 잡힌 내용들을 정확하고 최선으로 구현하면 되는거고. 검증단계들은 혹시나 만에 하나 잘못 구현하거나 개선할 가치가 있거나, 기술부채를 남겼거나, 클린업을 덜했거나 등등의 케이스를 위해서 존재하는게 아닐까?

> 앞으로 이런거 설명할때 반드시 쉽게 설명해. 쉽고 간결하게. 결정하는 사람 입장에서.

### Block 3 (2026-04-29 architecture compromise, user-adjudicated)

User picked option 1 of "BUILD pure execution vs BUILD constrained judgment" trade-off after Codex Round 2 surfaced empirical evidence (F2 spec.md:36 has explicit "no silent catch" yet variant violated; F3 phase-1-build.md:44 has explicit "do not replace real HTTP with mocks" yet variant mock-swapped). Codex framing is canonical (NOT user-verbatim):

> PLAN은 non-negotiable invariants + acceptance contract을 만든다. BUILD는 그 안에서 *constrained design judgment*를 수행한다. EVAL/CRITIC은 BUILD의 judgment를 대체하지 않는 독립 품질 레이어다.

PLAN remains the heaviest phase per Block 2, but BUILD is not pure execution — it has constrained judgment latitude that EVAL/CRITIC must independently audit.

### Memory directives (loaded automatically — cite, do not duplicate)

Memory files at `~/.claude/projects/-Users-aipalm-Documents-GitHub-devlyn-cli/memory/`. The following are execution-critical for iter-0022:

- `feedback_no_cost_talk.md` — never frame work in $/cost terms; user is on subscription. Optimize effectiveness × accuracy × reasonable wall-time.
- `feedback_l2_pair_collaboration.md` — L2 = pair 협업, not 분업. All L2 phase designs must be 티키타카 / interactive.
- `feedback_pair_vs_solo_empirical.md` — pair fires at phase P only where measurement shows material lift over solo. Do NOT pre-bake all-phases-pair into mode map.
- `feedback_codex_collaboration_not_consult.md` — Codex is partner not advisor. Multi-round dialogue until convergence; not single-shot Q&A.
- `feedback_explain_simply.md` — every user-facing surface = plain language + concise + decision-maker-framed. Conclusion + options + recommendation + what to choose, in that order. Drop internal labels (α/β/D1-D7/P1-P6) from user-facing text.
- `feedback_codex_cross_check.md` — reason independently first; send Codex rich evidence + falsification ask; surface pushback transparently; user adjudicates.

**Conflict rule**: if HANDOFF and a memory file disagree, stop before editing and ask the user. Do NOT silently choose one.

---

## 📍 Branch + project state (verify before editing)

- **Branch**: `benchmark/v3.6-ab-20260423-191315`
- **Branch tip at this HANDOFF write**: `c79d45c` (iter-0021 SHA-rotation) on top of `9a9947f` (iter-0021 calibration ship).
- **Mission 1 active** ([`MISSIONS.md`](MISSIONS.md)). Hard NOs binding. L1-L0 = +4.4 (below +5 floor).
- **iter-0020** = FAILED-EXPERIMENT-REVERTED-POLICY (commit `948e4bd`). e2e BUILD=Claude routing deleted. Auto-resolve runtime default = `--engine claude`. ideate/preflight/team-* defaults unchanged.
- **iter-0021** = SHIPPED (calibration overlay only, no code change). L1's only-negative axis is Scope (-4 across F2+F4 from harness DOCS adding `completed:` field beyond lifecycle note's `status:` carve-out). Note-scope-narrow mechanism confirmed via judge `b_breakdown.notes`.

Cold-start sanity check (run before any edit; ~30s):

```bash
# 1. Branch tip in expected range (top entries on this branch should include c79d45c iter-0021 SHA-rotation
#    or a later iter-0022 commit; if a different iter-0022 commit exists, treat as in-flight and inspect).
git log --oneline -10

# 2. Working tree clean (`.claude/scheduled_tasks.lock` is gitignored runtime artifact and may appear).
git status --short

# 3. Lint full pass.
bash scripts/lint-skills.sh
# Expected: "All checks passed."

# 4. Mirror parity (critical-path doc unchanged between source and installed).
diff -q config/skills/_shared/runtime-principles.md .claude/skills/_shared/runtime-principles.md
# Expected: silent.

# 5. iter-0021 calibration iter file exists.
ls autoresearch/iterations/0021-principle-bin-calibration.md
# Expected: file present.

# 6. iter-0022 deliverables NOT yet on disk (start-from-scratch confirmation).
#    `test ! -e` exits 0 only when the path does NOT exist; chained &&-list passes
#    iff all four are absent. NEVER use `ls ... 2>/dev/null` here — stderr swallow
#    silently turns a partially-shipped iter-0022 into "looks fine."
test ! -e config/skills/_shared/pair-plan-schema.md && \
test ! -e benchmark/auto-resolve/scripts/pair-plan-idgen.py && \
test ! -e benchmark/auto-resolve/scripts/pair-plan-lint.py && \
test ! -e autoresearch/scripts/pair-plan-preflight.sh && \
echo "iter-0022 not started — proceed"
# Expected: prints "iter-0022 not started — proceed". If exit non-zero or no
# output, at least one deliverable already exists; inspect commit history (git
# log --oneline | grep 0022) before adding.

# 7. Auto-resolve runtime default still `--engine claude` (iter-0020 closeout state).
grep -E '^[[:space:]]+- `--engine MODE`' config/skills/devlyn:auto-resolve/SKILL.md
# Expected: line includes `(claude)` not `(auto)`.
```

If any unexpected output, do NOT proceed. Surface to user.

---

## 🛠️ iter-0022 execution plan — 5 deliverables, real provider/model invocations = 0

### Why this iter exists (PRINCIPLES.md pre-flight 0 + #7)

iter-0021 calibration showed L1's only-negative axis is Scope (-4 across F2+F4) AND Mission 1 binding gate L1-L0=+4.4 < +5 floor. The user-adjudicated direction (post 3-round Codex dialogue 2026-04-29) is to test PLAN-pair architecture as the L2 redesign, NOT to chase the +0.4 scope delta directly. iter-0022 builds the infrastructure that lets iter-0023 measure causally whether pair PLAN rescues Codex BUILD on the iter-0020 failure set.

This iter is **the LAST attribution-infrastructure iter** before behavior change (iter-0023 = measurement pilot with real provider/model invocations, iter-0024+ = harness change based on iter-0023 outcome). PRINCIPLES.md:22 holds.

### Mission 1 service

Serves Mission 1 gate 1 (L1 vs L0 quality) indirectly: iter-0023 produces evidence on whether PLAN-pair architecture lifts L2 categorically; if YES, L2 product surface re-opens with empirical justification; if NO, L2 stays disabled per iter-0020 closeout and Mission 1 must close on L1-only path. Either outcome is mission-bound. Mission 1 hard NO list (worktree, parallel, resource-lease, run-scoped state, queue metrics) untouched.

### The 5 deliverables (with explicit acceptance gates)

**Deliverable 1 — `pair-plan.json` schema spec**

Location: `config/skills/_shared/pair-plan-schema.md`. Mirror to `.claude/skills/_shared/pair-plan-schema.md` per existing critical-path lint rule (Check 6). Add to lint allow-list.

Required top-level fields (inline executable contract — implementing session must build these exactly). Fence is `jsonc` because the example carries explanatory `// comment` annotations; the real `pair-plan.json` files written by tools MUST be strict JSON with no comments.

```jsonc
{
  "schema_version": "1",
  "plan_status": "final | blocked | draft",
  "planning_mode": "solo | pair",
  "source": {
    "spec_path": "...",
    "spec_sha256": "...",
    "expected_path": "...",        // optional, present when expected.json exists
    "expected_sha256": "...",      // optional, paired with expected_path
    "oracle_contract_sha256": "...", // present when oracle metadata is the registry source
    "rubric_sha256": "..."         // RUBRIC.md sha256 at plan time
  },
  "authority_order": [
    "spec.md", "expected.json/rubric", "phase prompt", "model preference"
  ],
  "canonical_id_registry_sha256": "...",
  "rounds": [
    {
      "round": 1,
      "claude_draft_sha256": "...",
      "codex_draft_sha256": "...",
      "merged_sha256": "...",
      "note": "..."
    }
    // up to 3 rounds
  ],
  "accepted_invariants": [
    {
      "id": "no_silent_catch_return_fallback",   // canonical ID — strict echo from registry
      "paraphrase": "...",                       // human-readable; informational only
      "source_refs": ["spec.md:36", "expected.forbidden_patterns/0"],
      "operational_check": "BUILD output must not contain `catch[^{]*\\{[^}]*return [^}]*\\}`",
      "authority": "expected.json/forbidden_patterns"
    }
  ],
  "rejected_alternatives": [
    {
      "id": "alt_silent_catch_with_log",
      "rationale": "Authority order says expected.json/forbidden_patterns dominates; logging does not change visible-error contract.",
      "conflicts_with_ids": ["no_silent_catch_return_fallback"],
      "claude_stamp": "rejected",
      "codex_stamp": "rejected"
    }
  ],
  "unresolved": [],                              // MUST be empty in final plans
  "escalated_to_user": [],                       // populated only during draft/blocked; final must have user_resolution per item if non-empty
  "model_stamps": {
    "claude": {
      "status": "sign | block",
      "blocked_ids": [],
      "signed_plan_sha256": "...",               // sha256 of THIS file pre-stamp
      "model": "claude-opus-4-7",
      "timestamp": "2026-04-29T..."
    },
    "codex": {
      "status": "sign | block",
      "blocked_ids": [],
      "signed_plan_sha256": "...",
      "model": "gpt-5.5",
      "timestamp": "..."
    }
  }
}
```

Hard rules in the spec doc:
- `unresolved.length > 0` → `plan_status` MUST be `blocked` or `draft`. Final accepted plan MUST have `unresolved == []`.
- `accepted_invariants[].id` MUST be drawn from the canonical registry (no paraphrase, no synonyms, no new IDs at plan-time). Paraphrase is informational only.
- `model_stamps.{claude,codex}.signed_plan_sha256` MUST equal the sha256 of the **canonical pre-stamp content**, defined precisely as: load the JSON object, set `model_stamps` to the empty object `{}`, serialize using `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)` (Python stdlib semantics; `allow_nan=False` raises on `NaN`/`Infinity`), encode UTF-8, then `sha256` those bytes. Both stamps sign the SAME canonical pre-stamp form, so both `signed_plan_sha256` values MUST be byte-identical. No trailing newline, no key reordering, no whitespace variation. Reject duplicate keys in the JSON object (Python `json.loads` accepts duplicates by default — use `object_pairs_hook=lambda pairs: dict(pairs) if len(pairs) == len({k for k,_ in pairs}) else (_ for _ in ()).throw(ValueError("duplicate key"))` or equivalent guard). Avoid floats in the schema unless explicitly required by a future field; integers and strings serialize byte-stably across implementations, floats do not. No Unicode normalization is applied — the input bytes are sha256'd as-is, so all writers must agree on input form (NFC recommended for any user-supplied strings).
- Both `model_stamps.claude.status` AND `model_stamps.codex.status` MUST equal `sign` for `plan_status: final`.
- `authority_order` MUST be the exact 4-string array above (snapshot at iter-0022 ship time; future iters can amend with explicit version bump).

Acceptance: doc exists at the path; lint Check 6 (mirror parity) passes; the schema is self-contained enough that a fresh session can implement deliverables 2-3 without re-reading R1-R3 Codex dialogue.

**Deliverable 2 — `pair-plan-idgen.py`**

Location: `benchmark/auto-resolve/scripts/pair-plan-idgen.py`.

**Critical clarification (Codex R-final catch)**: fixture roots (`benchmark/auto-resolve/fixtures/F2-cli-medium-subcommand/`, `.../F3-backend-contract-risk/`) currently contain only `expected.json` + `metadata.json` + `setup.sh` + `spec.md` + `task.txt` + `NOTES.md` — there are NO `oracle-*.json` files at fixture root. Oracle category definitions live in the **checked-in oracle scripts** at `benchmark/auto-resolve/scripts/oracle-test-fidelity.py` / `oracle-scope-tier-a.py` / `oracle-scope-tier-b.py`. Their JSON outputs (`oracle-*.json`) only exist in archived per-arm result dirs (`benchmark/auto-resolve/results/.../<fixture>/<arm>/oracle-*.json`) — using those would contaminate the blind preflight with iter-0020 evidence. **Idgen MUST invoke checked-in oracle scripts with the `--list-categories` flag** (which iter-0022 adds to the oracle scripts as part of this deliverable). Reading the script source files directly is also acceptable as a fallback. Reading any path under `benchmark/auto-resolve/results/` is FORBIDDEN.

Reads a fixture's `expected.json` + introspects checked-in oracle scripts; emits `canonical_id_registry.json` with `required_invariants[]`, each entry `{id, source_field, source_ref, operational_check}`. Behavior:

- For each `expected.json.forbidden_patterns[i]`: emit ID. If item has explicit `id` field, use it; otherwise generate slug deterministically (e.g. `forbidden_pattern_silent_catch_return_fallback`).
- For each `expected.json.verification_commands[i]`: emit ID covering exit + stdout-contains + stdout-not-contains assertions.
- `required_files`, `forbidden_files`, `max_deps_added`, `spec_output_files`: each becomes a registry entry.
- **Oracle category enumeration**: idgen invokes each oracle script with a `--list-categories` flag (which iter-0022 must add to the oracle scripts as part of this deliverable, returning JSON like `{"categories": [{"id": "real_http_server_helper", "applies_when": "fixture has tests/ that touch HTTP server"}, ...]}`). Idgen filters categories to those that apply to the current fixture (gate via `applies_when` predicate or per-fixture allowlist in `metadata.json`). Each applicable category becomes a registry entry. **Do not read archived `oracle-*.json` result artifacts under any circumstance** — that path leaks iter-0020 outcome data into the registry source-of-truth.
- Output JSON sorted deterministically (key order, list order); same input ⇒ same SHA256.
- Allow `expected.json` items to carry optional `id` field for stable canonical naming. Slug fallback for items without explicit `id`.

Acceptance:
- Run against `benchmark/auto-resolve/fixtures/F2-cli-medium-subcommand/` → registry contains explicit ID for the silent-catch-return-fallback forbidden pattern (origin: `expected.json.forbidden_patterns[0]`).
- Run against `benchmark/auto-resolve/fixtures/F3-backend-contract-risk/` → registry contains explicit ID for `real_http_server_helper`-class invariant (origin: oracle-test-fidelity script's `--list-categories` output, predicate-matched against F3's spec/expected).
- Idgen never opens any path under `benchmark/auto-resolve/results/`. Acceptance test (mandatory): instrument idgen's open/read calls (e.g. via `unittest.mock.patch('builtins.open')` wrapper, or by trapping `os.open` syscalls) so that any path containing `/results/` raises an explicit assertion. Run idgen against F2 + F3 with the trap installed; both must succeed. The symlink-fake-into-fixture-root test is INSUFFICIENT because it only proves "fixture-root oracle-*.json is ignored," not "results/ tree is never read."
- Same input, two consecutive runs → identical SHA256 of output (deterministic).
- F2 and F3 generated registry snapshots committed under `benchmark/auto-resolve/fixtures/<F>/expected-pair-plan-registry.json` so iter-0023 can diff against the snapshot.

**Deliverable 3 — `pair-plan-lint.py`**

Location: `benchmark/auto-resolve/scripts/pair-plan-lint.py`.

Reads a `pair-plan.json` and the corresponding `canonical_id_registry.json` (from deliverable 2). Verifies:

- Every `accepted_invariants[].id` exists in the registry exactly (string match, no paraphrase).
- Every registry entry marked `required: true` (or by default if no flag) appears in `accepted_invariants[]` OR `rejected_alternatives[].conflicts_with_ids[]` OR `escalated_to_user[]` (must be accounted for somewhere).
- `unresolved == []` for `plan_status: final`.
- `model_stamps.claude.signed_plan_sha256 == model_stamps.codex.signed_plan_sha256` AND equals the canonical pre-stamp sha256 of the file.
- Both stamps `status: sign` for `plan_status: final`.
- `authority_order` is the canonical 4-string snapshot (no drift).
- Source SHA256s in `source.{spec_sha256, expected_sha256, oracle_contract_sha256, rubric_sha256}` match actual file SHA256 at lint time (catches stale plans against changed sources).

Exit codes: 0 = pass, 1 = fail. Output: machine-readable JSON verdict on stdout (`{ok: bool, errors: [...]}`) + human summary on stderr.

Acceptance:
- Lint a fixture-passing sample plan (committed under `benchmark/auto-resolve/fixtures/F2-cli-medium-subcommand/pair-plan.sample-pass.json`) → exit 0 + `ok: true`.
- Lint a fixture-failing sample plan (missing `no_silent_catch_return_fallback` ID, committed under `benchmark/auto-resolve/fixtures/F2-cli-medium-subcommand/pair-plan.sample-fail.json`) → exit 1 + `ok: false` + error `missing_required_id`.
- Lint a sample with `unresolved: [...]` → exit 1.
- Lint a sample with mismatched stamps → exit 1.

**Deliverable 4 — `pair-plan-preflight.sh`**

Location: `autoresearch/scripts/pair-plan-preflight.sh`.

Orchestrates the no-code negative-screen preflight per Codex R3 D4. For each requested fixture:

1. Stage blind input bundle: original `spec.md` + `expected.json` + `metadata.json` + `task.txt` + the registry generated by deliverable 2 (`canonical_id_registry.json`, derived from idgen running over expected.json + oracle scripts' `--list-categories`). DO NOT stage any `oracle-*.json` file from anywhere — fixture roots don't have them, and archived ones at `benchmark/auto-resolve/results/.../<fixture>/<arm>/oracle-*.json` are FORBIDDEN per the oracle-source clarification above. Hide archived diffs/judge/labels. Blind fixture name (random ID).
2. Generate `canonical_id_registry.json` via deliverable 2 → snapshot to output dir.
3. Run `solo-plan` (one model, one pass — Claude OR Codex via `claude -p` / `codex-monitored.sh` subprocess) to produce `solo-plan.json`. Apply lint.
4. Run `pair-plan` simulation: independent Claude draft + independent Codex draft → merge/challenge round (max 3 rounds per Codex R3 stopping rule) → final `pair-plan.json`. Apply lint.
5. Compare: does pair plan capture canonical IDs that solo plan missed?
6. Write `verdict.json` (machine-readable): `{run_id, fixture_id, blind_alias, canonical_ids_total, solo_caught_count, pair_caught_count, pair_minus_solo_lift, verdict: "advance | abort", reason: "..."}`.

Output dir: `benchmark/auto-resolve/results/<run_id>/<blind_fixture>/plan-preflight/{input.bundle/, canonical-ids.json, solo-plan.json, drafts/claude.json, drafts/codex.json, merged/pair-plan.json, lint.json, verdict.json}`.

Subprocess hygiene: `claude -p` and `codex-monitored.sh` invocations with explicit context (only the staged blind bundle + registry; no archived state). `codex-monitored.sh` per `_shared/codex-monitored.sh` rules (no piping output).

Acceptance:
- Script runs end-to-end against a synthetic test bundle (committed under `autoresearch/scripts/test-fixtures/synthetic-preflight/`) without invoking real provider/model subprocesses (use `--dry-run` mode that swaps `claude -p` / `codex-monitored.sh` with deterministic stub responses).
- Verdict structure validates against an inline JSON schema in the script.
- Output dir layout exactly matches the spec above.

**Deliverable 5 — `/devlyn:auto-resolve` input contract change**

Location: `config/skills/devlyn:auto-resolve/SKILL.md` (PHASE 0 step 1) + supporting references where invocation contract is documented.

Behavior:

- Legacy invocation `/devlyn:auto-resolve "Implement per spec at <path>"` continues to work unchanged (`plan_mode=legacy_none`). PHASE 0 records `state.plan.mode = "legacy_none"`.
- New invocation accepts JSON-style payload `{spec_path: "...", plan_path: "..."}` OR named flag `--plan-path <path>`. Sets `state.plan.mode = "pair"`.
- When `plan_mode == "pair"`:
  - Run `pair-plan-lint.py` on `plan_path` BEFORE PHASE 1 BUILD. Failure → terminal verdict `BLOCKED:plan-invalid` (no fallback to legacy_none).
  - `state.plan.path` records the validated path. BUILD/EVAL/CRITIC reference accepted_invariants from the plan.
  - Metric collection (per-arm scores, fix-loop counts, etc.) is tagged `plan_mode=pair`.
- When `plan_mode == "legacy_none"`: pipeline runs as today; no plan validation; metrics tagged `plan_mode=legacy_none`. PLAN-pair statistics MUST NOT be aggregated for legacy_none runs (iter-0023 measurement integrity).

Acceptance:
- Existing 9-fixture suite runs cleanly under legacy_none (regression test: no ship-gate behavior change for runs without `plan_path`).
- A run with malformed `plan_path` (lint fail) terminates with `BLOCKED:plan-invalid` before BUILD.
- A run with `plan_path` pointing to a `unresolved.length > 0` plan terminates with `BLOCKED:plan-invalid`.
- `pipeline.state.json:plan.mode` is one of `legacy_none | pair` and matches invocation form.
- README / SKILL.md examples show both invocation forms.

### iter-0022 ship gate (every item must pass)

- All 5 deliverables exist at their canonical paths.
- Lint Check 6 (mirror parity) covers `pair-plan-schema.md` mirror.
- New lint check (Check 13 candidate) verifies idgen output deterministic across two runs (sha256 stable). Add to `scripts/lint-skills.sh`.
- `pair-plan-lint.py` ships with both pass and fail sample fixtures.
- `pair-plan-preflight.sh --dry-run` exits 0 against the synthetic test bundle.
- 9-fixture suite legacy-mode run (single `--engine claude` arm, dry-run) confirms no regression in legacy invocation path.
- F2 + F3 canonical ID registries committed as snapshots; iter-0023 can diff against them.
- iter-0022 file at `autoresearch/iterations/0022-pair-plan-infrastructure.md` cites pre-flight 0 + P1-P7 with concrete evidence.
- Codex pair-review trail ≥ 2 rounds (R0 design, R1 diff). All findings adopted or surfaced as user-adjudicated divergence.
- DECISIONS.md appended with `0022 | SHIPPED | ...` line.

### iter-0022 hard NO list

- ❌ NO real provider/model auto-resolve invocations during iter-0022. All work is local code + local lint + dry-run subprocess stubs. iter-0022's contract is "infrastructure only; the measurement pilot lives in iter-0023."
- ❌ NO change to RUBRIC.md or judge-prompt logic. Scoring is frozen.
- ❌ NO new fixtures. F2/F3 are existing; registry snapshots are derivative artifacts.
- ❌ NO restart of iter-0020 e2e routing. Deleted scripts stay deleted.
- ❌ NO change to ideate / preflight / team-* defaults.
- ❌ NO touching Mission 2 surfaces (worktree, parallel, leases). Mission 1 hard NOs binding.

---

## 🚧 iter-0023 stub — measurement pilot (real provider/model invocations). BLOCKED until checklist passes

iter-0023 measures whether pair PLAN materially improves Codex BUILD over solo PLAN on F2 + F3.

### Checklist before iter-0023 R0 starts (verify each path / behavior)

- [ ] `config/skills/_shared/pair-plan-schema.md` exists; mirror at `.claude/skills/_shared/pair-plan-schema.md` byte-identical.
- [ ] `benchmark/auto-resolve/scripts/pair-plan-idgen.py` exists; running it on F2 produces a registry containing the silent-catch-class invariant; running on F3 produces one containing the real-HTTP-server invariant; two consecutive runs same SHA256.
- [ ] `benchmark/auto-resolve/scripts/pair-plan-lint.py` exists; passes the sample-pass plan; fails the sample-fail plan with `missing_required_id`.
- [ ] `autoresearch/scripts/pair-plan-preflight.sh --dry-run` produces a verdict.json whose schema validates inline.
- [ ] `/devlyn:auto-resolve` accepts `--plan-path` and BLOCKS on lint-fail/unresolved>0/missing.
- [ ] 9-fixture legacy-mode dry-run passes lint without behavior change.
- [ ] iter-0022 SHIPPED in DECISIONS.md.

If any item fails, iter-0023 does not start. Surface the failing item to user.

### iter-0023 design (pre-registered, do not edit during execution)

- **Negative-screen step (no measurement-pilot invocations yet)**: run `pair-plan-preflight.sh` against F2 + F3 in real (not dry-run) mode. Pair PLAN must capture every must-hit canonical ID for F2 (no_silent_catch_return_fallback, EACCES_specific_handling, ...) AND for F3 (preserve_real_http_server_helper, no_mock_swap, scoped_file_set, ...). If pair plan misses any must-hit ID OR `unresolved > 0` after 3 rounds OR either model `block` stamp → preflight FAIL.
- **Preflight FAIL action**: label outcome `plan_omission`. iter-0023 closes with verdict "PLAN-pair candidate failed cheap negative screen on this fixture set; not falsified globally; pivot next iter to CRITIC-first measurement." iter-0024+ candidate = inverted CRITIC pair.
- **Preflight PASS action**: proceed to measurement pilot.
- **Measurement pilot design**:
  - Arm A (control): solo PLAN + Codex BUILD + solo CRITIC + solo EVAL on F2 + F3. Measures iter-0020 baseline (Codex-as-builder).
  - Arm B (test): pair PLAN (output of preflight) + Codex BUILD + solo CRITIC + solo EVAL on F2 + F3. Measures whether pair-PLAN rescues Codex BUILD.
  - Same git baseline, same Codex BUILD invocation, same downstream phases. Only PLAN differs.
- **Pre-registered acceptance** (no retroactive edits):
  - Arm B beats Arm A by ≥ +5 on judge-axis-sum on at least one of {F2, F3}, AND no fixture regresses by > -3.
  - Arm B has 0 forbidden_pattern DQ on F2 (the iter-0020 silent-catch failure must not recur).
  - Arm B has 0 mock-swap oracle hits on F3 (the iter-0020 test-fidelity failure must not recur).
- **Outcome attribution labels** (pre-registered): `plan_omission` (preflight FAIL), `plan_capture_no_lift` (preflight PASS but Arm B ≤ Arm A — pair PLAN wrote IDs but Codex BUILD violated anyway → confirms BUILD has constrained-judgment latitude), `plan_capture_with_lift` (preflight PASS + Arm B > Arm A — PLAN-pair architecture validated for next-iter L2 ship discussion).
- **Wall ratio guard**: Arm B / Arm A wall ratio recorded. Per NORTH-STAR ops test #7, if `Arm-B-best-of-M` does not beat `Arm-A-best-of-M` where M = wall ratio, efficiency contract fails even on quality lift. Document but do not gate iter-0023 verdict on this — surface as separate ship-decision input.

### iter-0023 hard NO list

- ❌ NO start before iter-0022 checklist clears.
- ❌ NO retroactive edits to acceptance criteria after data lands.
- ❌ NO bundling iter-0024 (verdict-driven harness change) into iter-0023.
- ❌ NO changing RUBRIC.md mid-window.

---

## 📋 Mission 1 hard NO list (binding for iter-0022 + iter-0023)

- ❌ No worktree-per-task substrate (Mission 2).
- ❌ No parallel-fleet smoke / N≥2 simultaneous runs.
- ❌ No resource-lease helper / SQLite leases / port pools / queue metrics.
- ❌ No run-scoped state migration (`.devlyn/pipeline.state.json` stays at worktree root).
- ❌ No multi-agent coordination beyond what `pipeline.state.json` already provides.
- ❌ No cross-vendor / qwen / gemma infrastructure.
- ❌ No restart of iter-0020 e2e routing.
- ❌ No edit to ideate / preflight / team-* `--engine auto` defaults without skill-specific benchmark evidence.
- ❌ No aggregate-margin chasing.
- ❌ No "while I'm here" cross-mission additions.

---

## 📚 Read-order on cold start

1. [`NORTH-STAR.md`](NORTH-STAR.md) — project goal (L0/L1/L2 contract, 14 ops tests, real-project trial gate).
2. **This file** — operating context. `START-HERE` block + `STANDING USER DIRECTIVES` + `iter-0022 execution plan` are load-bearing for the next session's entire run.
3. [`PRINCIPLES.md`](PRINCIPLES.md) — pre-flight 0 + P1-P7. Cite each in iter-0022's iter file.
4. [`MISSIONS.md`](MISSIONS.md) — confirms Mission 1 active, hard NOs binding.
5. [`CLAUDE.md`](../CLAUDE.md) — runtime contract (Subtractive-first, Goal-locked, No-workaround, Evidence — mirrored to `_shared/runtime-principles.md`).
6. `autoresearch/DECISIONS.md` — append-only ship/revert log. Latest entries: `0020 | FAILED-EXPERIMENT-REVERTED-POLICY` + `0021 | SHIPPED`.
7. [`autoresearch/iterations/0021-principle-bin-calibration.md`](iterations/0021-principle-bin-calibration.md) — most recent iter file. Read for the per-axis L1-L0 readout AND for the explicit P2 ⚠️ rescue-note about the fabrication caught at R-final. iter-0022 inherits the discipline.
8. `config/skills/_shared/runtime-principles.md` — runtime contract sub-agents consume.
9. Memory directives (auto-loaded; cited above; do not duplicate without conflict-rule check).

---

## 🤝 Codex pair-review pattern for iter-0022 (mandatory)

Per `feedback_codex_collaboration_not_consult.md` + `feedback_codex_cross_check.md`:

- **Multi-round, not one-shot.** Plan for 2-3+ rounds: R0 = design draft, R1 = diff review, R-final = pre-commit lock. Sometimes more.
- **Position-stating, not verdict-asking.** I state position with evidence; Codex pushes back; I respond; iterate to convergence.
- **Convergence is the stop.** Not "Codex agreed." Stop when neither has new substantive critique.
- **Per-round prompt shape**: rich evidence + falsification ask + my response to prior round. Use `bash config/skills/_shared/codex-monitored.sh -C /Users/aipalm/Documents/GitHub/devlyn-cli -s read-only -c model_reasoning_effort=xhigh "<prompt>"`. Never pipe wrapper output.
- **Verify before claim.** Per the iter-0021 lesson at the top of this file: every cited file:line must be opened at the time of citation, not assumed from memory.

---

## ⏭️ End of HANDOFF

Current iter focus: **iter-0022 (build the 5 deliverables, real provider/model invocations = 0)**. iter-0023 BLOCKED until checklist clears. Mission 1 active. North Star intact.
