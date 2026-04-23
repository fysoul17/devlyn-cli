# Findings Schema — `.devlyn/<phase>.findings.jsonl`

Structured findings format for phase outputs. One JSON object per line (JSONL). Written by Evaluate, Build Gate, Browser Validate, Critic, and any other phase that emits structured findings.

## Purpose

Separate structured findings from prose summaries. The orchestrator and fix-loop need machine-readable data for:
- Filtering by severity / blocking / status.
- Cross-round dedup (single primary key — see below).
- Packing into fix-batch packets for the fix-loop subagent.
- Final report aggregation.

## Canonical schema (per line)

```json
{
  "id": "<PHASE>-<4digit>",
  "rule_id": "<category>.<kebab-name>",
  "level": "note" | "warning" | "error",
  "severity": "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
  "confidence": <float 0.0..1.0>,
  "message": "<one-line human description>",
  "file": "<path relative to repo root>",
  "line": <int, 1-based>,
  "phase": "<phase name, e.g. 'evaluate'>",
  "criterion_ref": "<anchor, e.g. 'spec://requirements/2'>" | null,
  "fix_hint": "<concrete action quoting file:line to change>",
  "blocking": true | false,
  "status": "open" | "resolved" | "suppressed"
}
```

## Field semantics

### Identity

- `id` — stable within a single run. Format: `<PHASE>-<4digit>` zero-padded. Examples: `EVAL-0007`, `BUILD-0001`, `CRIT-0003`, `BGATE-0004`.
- `rule_id` — stable across runs. Format: `<category>.<kebab-case-name>`. Use existing rule_ids before inventing new ones — keeps dedup working. Common categories:
  - `correctness.*` — logic errors, silent failures, null access, wrong API contracts
  - `design.*` — staff-engineer ship/no-ship concerns (non-atomic transactions, hidden assumptions, unidiomatic patterns)
  - `security.*` — OWASP-anchored (sql-injection, xss, hardcoded-credential, missing-input-validation, missing-auth-check, insecure-dependency, permissive-cors, missing-csrf, privilege-escalation, data-exposure, path-traversal, ssrf)
  - `ux.*` — missing error/loading/empty states
  - `architecture.*` — pattern violations, duplication, missing integration
  - `hygiene.*` — unused imports, dead code, unused deps (typically LOW)
  - `types.*` — any-cast escapes, unsafe casts
  - `scope.*` — out-of-scope violations (e.g. `scope.out-of-scope-violation`)
  - `performance.*`, `style.*` — typically LOW

### Severity and level

- `level` — SARIF-style coarse bucket: `error` blocks ship, `warning` should fix, `note` informational.
- `severity` — finer granularity for pipeline logic.

  | severity | level | blocking default |
  |----------|-------|------------------|
  | `CRITICAL` | `error` | always true |
  | `HIGH` | `error` | usually true |
  | `MEDIUM` | `warning` | true (stricter for `security.*` — see pipeline-routing terminal state) |
  | `LOW` | `note` | false |

- `confidence` — reporter's self-rating, `0.0`–`1.0`. Fix-loop prioritizes high-confidence HIGH findings first.

### Message and location

- `message` — one line. NAME the issue, not the symptom. Good: `"Token validated on read path but not write path"`. Bad: `"Potential security issue"`.
- `file` — repo-relative path. No leading `./`, no absolute paths. Forward slashes.
- `line` — 1-based line number. Multi-line spans → primary (first) line.

### Dedup primary key

**Simpler than v3.2**: the primary key is `(rule_id, file, line)`. Two findings with identical `(rule_id, file, line)` are the same issue. If EVAL runs again after a fix and the finding re-appears at the same coordinates, it's still unresolved. If the line shifted by a small amount after a fix, the next EVAL will regenerate the finding anyway with the new line — cross-round drift healing happens naturally via re-evaluation rather than hash normalization bookkeeping.

Deleted from v3.2: `partial_fingerprints.location_hash`, `partial_fingerprints.rule_message_hash`, `normalize_path`, `normalize_message`. The orchestrator no longer post-processes JSONL for hash injection — subagents write findings directly, and the orchestrator reads `(rule_id, file, line)` as the lookup key.

### Pipeline linkage

- `phase` — the phase that produced this finding (redundant with filename but keeps records self-describing when concatenated for fix-batch packets).
- `criterion_ref` — anchor to the criterion this finding affects, or `null` if cross-cutting.
- `fix_hint` — concrete action with file:line. Not "improve error handling" — e.g. `"Wrap read+write in db.transaction() at src/auth/session.ts:84-92; re-check order.status === 'pending' inside transaction before updating"`.

### Lifecycle

- `blocking` — does this block ship?
- `status`:
  - `open` — reported, awaiting action
  - `resolved` — a fix-loop round applied a fix AND subsequent evaluation confirms the finding is gone (via `(rule_id, file, line)` absence in the new EVAL run)
  - `suppressed` — intentionally not fixed with justification in the phase's `log.md`; requires user override or Out-of-Scope mapping in the spec

## Dedup and round handling

Each phase writes a fresh `.findings.jsonl` on each execution. Fix rounds re-run EVAL, which produces a new file.

**Cross-round reconciliation** (fix-loop rounds only):
1. Read prior round's `<phase>.findings.jsonl` (if any).
2. For each finding in the new file: if prior open finding has same `(rule_id, file, line)` → reuse the prior `id`, keep `status: open`. Otherwise → new `id`.
3. For each prior open finding not matched by the new file → set `status: resolved` in the prior file.

Fix-batch packet: orchestrator concatenates all phases' `.findings.jsonl`, filters `status == "open"`, drops `blocking == false` when round budget is tight, writes to `.devlyn/fix-batch.round-<N>.json`.

## Example — `evaluate.findings.jsonl`

```jsonl
{"id":"EVAL-0007","rule_id":"correctness.non-atomic-state-transition","level":"error","severity":"HIGH","confidence":0.91,"message":"Order status read and write are not atomic in cancel handler","file":"src/api/orders/cancel.ts","line":42,"phase":"evaluate","criterion_ref":"spec://requirements/1","fix_hint":"Wrap read+write in db.transaction() at src/api/orders/cancel.ts:40-50; re-check order.status === 'pending' inside transaction","blocking":true,"status":"open"}
{"id":"EVAL-0008","rule_id":"ux.missing-error-state","level":"warning","severity":"MEDIUM","confidence":0.85,"message":"Cancel button does not show error UI when API returns 409","file":"app/orders/[id]/page.tsx","line":87,"phase":"evaluate","criterion_ref":"spec://requirements/3","fix_hint":"Catch 409 at app/orders/[id]/page.tsx:85-92; show Alert with retry button","blocking":true,"status":"open"}
{"id":"EVAL-0009","rule_id":"hygiene.unused-import","level":"note","severity":"LOW","confidence":0.99,"message":"`unused` import from 'lodash' has no references","file":"src/api/orders/cancel.ts","line":3,"phase":"evaluate","criterion_ref":null,"fix_hint":"Remove `import { unused } from 'lodash'` at src/api/orders/cancel.ts:3","blocking":false,"status":"open"}
```

## Non-goals

- Full SARIF 2.1.0 export (can derive later by mapping our fields to SARIF).
- Cross-project aggregation.
- Rule metadata catalogs.
- Code fix patches — `fix_hint` is prose; fix-loop subagent writes the patch.
