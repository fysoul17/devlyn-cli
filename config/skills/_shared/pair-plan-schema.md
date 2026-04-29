# Shared — `pair-plan.json` schema (iter-0022)

Single source of truth for `pair-plan.json` and its companion `canonical_id_registry.json`. Read this once before editing `pair-plan-idgen.py`, `pair-plan-lint.py`, `pair-plan-preflight.sh`, or any auto-resolve PHASE that consumes `state.plan`. The schema is self-contained: a fresh session can implement the surrounding tools from this file alone, without re-reading the iter-0022 Codex dialogue.

## Audience

- `benchmark/auto-resolve/scripts/pair-plan-idgen.py` — produces `canonical_id_registry.json` from `expected.json` + checked-in oracle scripts.
- `benchmark/auto-resolve/scripts/pair-plan-lint.py` — validates a `pair-plan.json` against its registry.
- `autoresearch/scripts/pair-plan-preflight.sh` — orchestrates solo + pair plan generation against blind-aliased fixtures (dry-run in iter-0022; real provider/model invocations land in iter-0023).
- `config/skills/devlyn:auto-resolve/SKILL.md` PHASE 0 — accepts `--plan-path` / JSON payload, sets `state.plan.{mode, path}`, runs lint before BUILD.
- `config/skills/devlyn:auto-resolve/references/phases/phase-{1-build,2-evaluate,3-critic}.md` — read `accepted_invariants[]` from `state.plan.path` when `state.plan.mode == "pair"` and treat each `operational_check` as binding.

## File locations and naming (canonical)

- Registry per fixture: `benchmark/auto-resolve/fixtures/<F>/expected-pair-plan-registry.json` (committed snapshot for diff-against-baseline; iter-0023 verifies the live idgen output equals this snapshot).
- Plan produced by preflight: `benchmark/auto-resolve/results/<run_id>/<blind_fixture>/plan-preflight/merged/pair-plan.json`.
- Plan supplied to `/devlyn:auto-resolve` by an external caller: any path the user chooses, passed via `--plan-path <path>`.
- The registry filename is `canonical_id_registry.json` for **runtime artifacts** — both inside the bundle dir and in the preflight output root. (HANDOFF.md:280 mentions `canonical-ids.json` for the preflight output dir; that name is deprecated — D4 emits `canonical_id_registry.json` to align with the rest of the toolchain.)
- The **committed fixture snapshot** is named `expected-pair-plan-registry.json` (one per fixture, under `benchmark/auto-resolve/fixtures/<F>/`) — distinct file name to make snapshots greppable separately from runtime artifacts. iter-0023 verifies the live idgen output equals the committed snapshot for the same fixture.

## `canonical_id_registry.json` shape

Top-level wrapper:

```jsonc
{
  "schema_version": "1",
  "fixture_id": "F2-cli-medium-subcommand",
  "generated_at": "2026-04-29T18:30:00Z",
  "generated_from": {
    "expected_path": "benchmark/auto-resolve/fixtures/F2-cli-medium-subcommand/expected.json",
    "expected_sha256": "...",          // raw file bytes sha256
    "metadata_path":  "benchmark/auto-resolve/fixtures/F2-cli-medium-subcommand/metadata.json",
    "metadata_sha256": "...",          // raw file bytes sha256
    "oracle_script_shas": {
      "test-fidelity":   "...",        // raw bytes sha256 of oracle-test-fidelity.py
      "scope-tier-a":    "...",
      "scope-tier-b":    "..."
    }
  },
  "required_invariants": [
    {
      "id": "...",
      "source_field": "expected.json/forbidden_patterns/0 | expected.json/verification_commands/3 | expected.json/required_files | expected.json/forbidden_files | expected.json/max_deps_added | expected.json/spec_output_files | oracle/<oracle-name>/<category-id>",
      "source_ref":   "expected.json:60 | expected.json/verification_commands/0 | oracle-test-fidelity.py",
      "operational_check": "...natural-language description of what the variant must do or must not do...",
      "severity": "disqualifier | hard | flag | warn",
      "authority": "expected.json/forbidden_patterns | expected.json/verification_commands | expected.json/required_files | expected.json/forbidden_files | expected.json/max_deps_added | expected.json/spec_output_files | metadata/oracle-allowlist"
    }
    // ...sorted lexicographically by id
  ]
}
```

**Hard rules**:
- `required_invariants` MUST be sorted lexicographically by `id`. idgen sorts before serializing; lint rejects an unsorted file.
- All file shas (`expected_sha256`, `metadata_sha256`, `oracle_script_shas.*`) are **raw file bytes sha256** — `sha256(open(path, "rb").read())`. NOT canonical-JSON form. (Canonical form is reserved for the pair-plan pre-stamp hash; see below.)
- `info`-severity oracle categories are NOT registry entries (e.g. scope-tier-b's `tier-b-reachable` is a positive signal, not an invariant violation).
- The umbrella oracle category `scope-tier-a:tier-a-violation` is ONE registry entry; the 5 path-glob groups (planning-doc, ci-config, node-modules, test-results-or-coverage, env-secrets) are described inside `operational_check`, not split into 5 entries.

**Determinism**: same `(expected.json, metadata.json, oracle scripts)` input → byte-identical `canonical_id_registry.json`. Achieved by:
- `json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False)` for the on-disk file.
- All lists pre-sorted before dumping (registry items by `id`).
- No timestamps that change run-to-run except `generated_at` — see exemption below.

`generated_at` is the ONE volatile field. Lint ignores it for sha-stability checks; lint's determinism check sets `generated_at` to a fixed value before comparing two consecutive idgen runs. (Implementation: idgen accepts `--generated-at <iso8601>` for testing.)

## `pair-plan.json` shape

```jsonc
{
  "schema_version": "1",
  "plan_status": "final | blocked | draft",
  "planning_mode": "solo | pair",
  "fixture_id": "F2-cli-medium-subcommand",          // human label; not authoritative
  "source": {
    "spec_path":          "benchmark/auto-resolve/fixtures/F2-cli-medium-subcommand/spec.md",
    "spec_sha256":        "...",                     // raw file bytes
    "expected_path":      "benchmark/auto-resolve/fixtures/F2-cli-medium-subcommand/expected.json",
    "expected_sha256":    "...",                     // raw file bytes (optional only when expected.json absent)
    "rubric_path":        "benchmark/auto-resolve/RUBRIC.md",
    "rubric_sha256":      "...",                     // raw file bytes
    "canonical_id_registry_path":   "benchmark/auto-resolve/fixtures/F2-cli-medium-subcommand/expected-pair-plan-registry.json",
    "canonical_id_registry_sha256": "..."            // raw file bytes of the registry file
  },
  "authority_order": [
    "spec.md",
    "expected.json/rubric",
    "phase prompt",
    "model preference"
  ],
  "rounds": [
    {
      "round": 1,
      "claude_draft_sha256": "...",                  // raw file bytes of the per-round draft artifact
      "codex_draft_sha256":  "...",
      "merged_sha256":       "...",
      "note": "..."
    }
    // up to 3 rounds; iter-0022 preflight stops at the first round where neither model has new substantive critique
  ],
  "accepted_invariants": [
    {
      "id":           "no_silent_catch_return_fallback",
      "paraphrase":   "...",                         // human-readable; informational only, NOT enforced
      "source_refs":  ["spec.md:36", "expected.json/forbidden_patterns/0"],
      "operational_check": "BUILD output must not contain `catch[^{]*\\{[^}]*return [^}]*\\}` in bin/cli.js",
      "authority":    "expected.json/forbidden_patterns"
    }
  ],
  "rejected_alternatives": [
    {
      "id":              "alt_silent_catch_with_log",
      "rationale":       "Authority order says expected.json/forbidden_patterns dominates; logging does not change visible-error contract.",
      "conflicts_with_ids": ["no_silent_catch_return_fallback"],
      "claude_stamp":    "rejected",
      "codex_stamp":     "rejected"
    }
  ],
  "unresolved":          [],                         // MUST be empty in final plans
  "escalated_to_user":   [],                         // populated only during draft / blocked status; final must have user_resolution per item if non-empty
  "model_stamps": {
    "claude": {
      "status":              "sign | block",
      "blocked_ids":         [],
      "signed_plan_sha256":  "...",                  // canonical pre-stamp sha (see below)
      "model":               "claude-opus-4-7",
      "timestamp":           "2026-04-29T..."
    },
    "codex": {
      "status":              "sign | block",
      "blocked_ids":         [],
      "signed_plan_sha256":  "...",
      "model":               "gpt-5.5",
      "timestamp":           "..."
    }
  }
}
```

## Severity decoupling (registry vs findings)

The registry's `required_invariants[].severity` taxonomy is **metadata for human review only**: `disqualifier | hard | flag | warn`. It is NOT mapped onto the `references/findings-schema.md` taxonomy used by EVAL / CRITIC findings (`CRITICAL | HIGH | MEDIUM | LOW`). When a phase emits a finding for a missed plan invariant, severity is assigned by that phase's own existing severity policy (per `findings-schema.md`), not by reading the registry severity directly. The two taxonomies serve different audiences (registry severity = "how the oracle classifies it"; findings severity = "what the orchestrator should do about it") and are intentionally not coupled in iter-0022.

## Hard rules (lint-enforced)

1. `unresolved.length > 0` → `plan_status` MUST be `blocked` or `draft`. Final accepted plan MUST have `unresolved == []`.
2. `escalated_to_user[]` non-empty → each item MUST carry a `user_resolution` field, OR `plan_status` MUST be `blocked` / `draft`.
3. Every `accepted_invariants[].id` MUST appear in the registry's `required_invariants[].id` exactly (string match — no paraphrase, no synonym, no new IDs at plan-time). `paraphrase` is informational only.
4. **Final-plan coverage**: when `plan_status == "final"`, every registry entry MUST be accounted for in the plan — each `required_invariants[].id` is in `accepted_invariants[].id` OR in some `rejected_alternatives[].conflicts_with_ids[]` OR in `escalated_to_user[].id` OR in `unresolved[].id`. (`draft` and `blocked` plans are NOT subject to full coverage; they may still carry un-decided ids in `unresolved[]` per Rule #1.)
5. `authority_order` MUST be the exact 4-string array `["spec.md", "expected.json/rubric", "phase prompt", "model preference"]` (snapshot at iter-0022 ship time; future iters can amend with explicit `schema_version` bump).
6. `model_stamps.{claude,codex}.status == "sign"` MUST hold for `plan_status: "final"`. A `block` from either model forces `plan_status` to `blocked` or `draft`.
7. `model_stamps.{claude,codex}.signed_plan_sha256` MUST be byte-identical AND MUST equal the canonical pre-stamp sha256 of the file (see "Two sha256 contracts" below).
8. `source.{spec_sha256, expected_sha256, rubric_sha256, canonical_id_registry_sha256}` MUST equal the actual raw-bytes sha256 of the referenced files at lint time (catches stale plans against changed sources).
9. `source.canonical_id_registry_path` MUST resolve to an existing registry file. lint reads it from this field; if `--registry <path>` is passed on the lint command line, the override wins.
10. `planning_mode: "pair"` requires `rounds.length >= 1`. `planning_mode: "solo"` requires `rounds.length == 0` (no merge artifacts).

## Two sha256 contracts (DO NOT CONFLATE)

### Contract A — raw file bytes

Used for: every `source.*_sha256` field (spec, expected, rubric, registry), every `generated_from.*_sha256` field in the registry, every `rounds[].*_draft_sha256` and `merged_sha256`.

```python
import hashlib
with open(path, "rb") as f:
    sha = hashlib.sha256(f.read()).hexdigest()
```

No canonicalization. The bytes on disk are what gets hashed. This catches "the plan claims spec.md is sha X but spec.md actually has bytes producing sha Y" drift.

### Contract B — canonical pre-stamp form (pair-plan stamps only)

Used for: `model_stamps.claude.signed_plan_sha256` and `model_stamps.codex.signed_plan_sha256`. Both stamps sign **byte-identical** canonical bytes, so both sha values are byte-identical.

Algorithm (writers and verifiers MUST implement exactly):

```python
import json
import hashlib
import copy

def canonical_pre_stamp_sha256(plan: dict) -> str:
    # Reject duplicate keys when LOADING the plan; this function assumes a clean dict.
    pre = copy.deepcopy(plan)
    pre["model_stamps"] = {}                       # replace value, keep key
    s = json.dumps(
        pre,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return hashlib.sha256(s.encode("utf-8")).hexdigest()
```

When LOADING the plan, reject duplicate keys:

```python
def _strict_pairs(pairs):
    keys = [k for k, _ in pairs]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate key in pair-plan.json")
    return dict(pairs)

with open(path, "r", encoding="utf-8") as f:
    plan = json.load(f, object_pairs_hook=_strict_pairs)
```

**Why no Unicode normalization**: the canonical form hashes input bytes as-is. Writers and verifiers must agree on input form (NFC recommended for any user-supplied free-text strings, but not enforced — the scheme survives because both sides derive from the same source bytes).

**Why no floats**: integer + string serialize byte-stably across implementations. Floats vary (e.g. `1.0` vs `1`). Avoid floats in this schema until a future field absolutely requires one; if added, document the canonical float-printing rule in this file.

## Slug rules for registry IDs (idgen)

When an `expected.json` item lacks an explicit `id` field, idgen synthesizes a deterministic slug.

### `forbidden_patterns[i]` slug

```
forbidden_pattern__<sanitize(description, 60)>__<sanitize(files[0], 30)>
```

`sanitize(s, max_len)`: lowercase; replace any non-`[a-z0-9]` run with a single `_`; strip leading/trailing `_`; truncate to `max_len` (right-truncate, no hash suffix at this level).

If two items in the same `forbidden_patterns[]` array produce the same slug after sanitization, the FIRST one (by source-array index) keeps the bare slug; each subsequent collision appends `__i<index>`. idgen detects this deterministically by walking the array in order.

Example F2:
- `forbidden_patterns[0]` (description="silent catch returning a fallback value — violates no-silent-catches policy", files=["bin/cli.js"]) → `forbidden_pattern__silent_catch_returning_a_fallback_value_violate__bin_cli_js`
- `forbidden_patterns[1]` (description="@ts-ignore escape hatch", files=["bin/cli.js"]) → `forbidden_pattern__ts_ignore_escape_hatch__bin_cli_js`

### `verification_commands[i]` slug

```
verification__<sha8(canonical_json(verification_obj))>
```

`canonical_json(obj)`: same compact form as Contract B (`json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)`).
`sha8(s)`: first 8 hex chars of `sha256(s.encode("utf-8"))`.

The full verification object is hashed (cmd + exit_code + stdout_contains + stdout_not_contains), so reordering the array does not change the slug. Array-index lives in `source_ref` (`expected.json/verification_commands/<i>`) for human navigation only.

### Other expected.json fields

- `required_files`: one registry entry per file path: `required_file__<sanitize(path, 60)>`.
- `forbidden_files`: same shape: `forbidden_file__<sanitize(path, 60)>`.
- `max_deps_added`: one registry entry: `max_deps_added__<value>` (e.g. `max_deps_added__0`).
- `spec_output_files`: one registry entry per path: `spec_output_file__<sanitize(path, 60)>`.

### Oracle category IDs (no slug — fixed strings)

Oracle `--list-categories` returns category IDs in the form `<oracle-name>:<finding-type>`. These are stable strings that idgen passes through verbatim into `required_invariants[].id`. Each oracle script defines its own enum; iter-0022 ship snapshot:

- `test-fidelity:test-file-deleted`
- `test-fidelity:test-file-renamed`
- `test-fidelity:mock-swap`
- `test-fidelity:assertion-regression`
- `scope-tier-a:lockfile-deletion`
- `scope-tier-a:tier-a-violation`
- `scope-tier-b:scope-unmatched`

`scope-tier-b:tier-b-reachable` is `info`-severity and NOT a registry entry.

## metadata.json field for per-fixture oracle allowlist

iter-0022 adds one new field to each fixture's `metadata.json`:

```json
{
  "id": "F2-cli-medium-subcommand",
  // ... existing fields unchanged ...
  "pair_plan_oracle_categories": [
    "test-fidelity:test-file-deleted",
    "test-fidelity:test-file-renamed",
    "test-fidelity:mock-swap",
    "test-fidelity:assertion-regression",
    "scope-tier-a:lockfile-deletion",
    "scope-tier-a:tier-a-violation",
    "scope-tier-b:scope-unmatched"
  ]
}
```

Hard rule: idgen filters oracle categories to exactly this allowlist. If the field is missing, idgen treats it as the empty array (no oracle categories registered) — `expected.json`-derived invariants still appear. Schema-version bump if the allowlist semantics change.

The runner `run-fixture.sh` reads `timeout_seconds` (line 54) and the report reads `category` (compile-report.py line 76); no other consumer reads metadata.json today, so adding a new field is a pure metadata enrichment with no scoring implication.

## Plan field minimum/maximum policy

- A field listed in this schema with no "optional" annotation is REQUIRED.
- Fields explicitly marked optional: `source.expected_path` / `source.expected_sha256` (only when `expected.json` is genuinely absent — not the case for any current fixture).
- Unknown extra fields in `pair-plan.json` are NOT rejected by lint (forward-compat), but the canonical pre-stamp sha is computed over the whole object so unknown fields participate in the signature.
- Unknown extra fields in `canonical_id_registry.json` ARE rejected by lint (idgen owns the registry shape; drift here is a bug).

## Versioning

`schema_version` starts at `"1"`. A breaking change to any hard rule above bumps the version and the lint script gains a per-version dispatcher. iter-0022 ships version `1`. Future iters MUST update this file before bumping the version field anywhere else.
