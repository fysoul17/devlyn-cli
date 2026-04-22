# Findings Schema — `.devlyn/<phase>.findings.jsonl`

SARIF-aligned findings format for phase outputs. One JSON object per line (JSONL). Written by Evaluate, Challenge, Security Review, Build Gate, and any other phase that emits structured findings.

## Purpose

Separate structured findings from prose summaries. The orchestrator and fix-loop need machine-readable findings for:
- Filtering by severity, blocking, status
- Cross-round deduplication via `partial_fingerprints`
- Packing into fix-batch packets for fix-loop subagents
- Final report aggregation

Prose-only findings (the legacy `EVAL-FINDINGS.md` format) cannot do any of the above without re-parsing markdown.

## SARIF alignment

This schema is a FLAT projection of SARIF 2.1.0 concepts. We deliberately avoid the full SARIF wrapper (which requires `runs[]`, `tool.driver.rules[]`, etc.) because our pipeline is internal — we are not exporting to GitHub Code Scanning today. We keep the load-bearing SARIF concepts:

| Our field | SARIF concept | Why we keep it |
|-----------|---------------|----------------|
| `rule_id` | `ruleId` | Stable rule identifier across runs |
| `level` | `level` | Coarse severity bucket (none/note/warning/error) |
| `message` | `message.text` | Human-readable description |
| `file` + `line` | `locations[].physicalLocation` | Primary location (flattened — multi-location is rare for our use case) |
| `partial_fingerprints` | `partialFingerprints` | Cross-run dedup, per SARIF spec §3.27.17 |
| remaining fields | `properties` | Extension bag |

If full SARIF export is ever needed, each record converts cleanly one-to-one.

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
  "partial_fingerprints": {
    "location_hash": "<hex>",
    "rule_message_hash": "<hex>"
  },
  "phase": "<phase name, e.g. 'evaluate'>",
  "criterion_ref": "<anchor, e.g. 'spec://requirements/2'>" | null,
  "fix_hint": "<concrete action quoting file:line to change>",
  "blocking": true | false,
  "status": "open" | "resolved" | "suppressed"
}
```

## Field semantics

### Identity

- `id` — stable within a single run. Format: `<PHASE>-<4digit>` zero-padded. Examples: `EVAL-0007`, `BUILD-0001`, `CHLG-0003`, `SEC-0002`, `BGATE-0004`.
- `rule_id` — stable across runs. Format: `<category>.<kebab-case-name>`. Examples:
  - `correctness.non-atomic-state-transition`
  - `correctness.silent-auth-bypass`
  - `security.hardcoded-credential`
  - `security.missing-input-validation`
  - `ux.missing-error-state`
  - `types.any-cast-escape`
  - `style.let-vs-const`
  - `performance.unnecessary-refetch`

  **Use existing rule_ids before inventing new ones.** Each phase should read its own prior `.findings.jsonl` files (if present, e.g. from a prior fix round) and reuse any matching rule_id. This keeps fingerprint dedup working.

### Severity and level

- `level` — SARIF-aligned coarse bucket:
  - `error` — blocks ship
  - `warning` — should fix
  - `note` — informational
- `severity` — finer granularity for pipeline logic. Mapping:

  | severity | level | blocking default |
  |----------|-------|------------------|
  | `CRITICAL` | `error` | always true |
  | `HIGH` | `error` | usually true |
  | `MEDIUM` | `warning` | true if within fix-loop round budget |
  | `LOW` | `note` | false |

- `confidence` — reporter's self-rated confidence, `0.0`–`1.0`. Low confidence (< 0.5) means "might be a false positive". Fix-loop uses this to prioritize — high-confidence HIGH findings are addressed before low-confidence HIGH findings.

### Message and location

- `message` — one line, human-readable. Must NAME the issue, not describe symptoms.
  - Good: `"Token validated on read path but not write path"`
  - Bad: `"Potential security issue"` or `"The error handling could be improved"`
- `file` — repo-relative path. No leading `./`, no absolute paths. Forward slashes on all platforms.
- `line` — 1-based line number. For findings spanning multiple lines, use the primary (first) line.

### Partial fingerprints (dedup)

Two stable hashes following SARIF `partialFingerprints` convention. See SARIF 2.1.0 §3.27.17 for background.

**Who computes them**: the **orchestrator**, NOT the producing subagent. Subagents emit findings without the `partial_fingerprints` field (or with an empty `{}`). The orchestrator reads the JSONL after the phase completes and post-processes each line to compute and inject `partial_fingerprints`. This separation matters because fingerprint determinism is operational bookkeeping, not semantic judgment — delegating it to the subagent has empirically produced ~20% correct results because normalization rules are too subtle for ad-hoc interpretation.

1. **`location_hash`** — `sha1(rule_id + "|" + normalize_path(file) + "|" + line)` hex-encoded.
   - `normalize_path`: strip leading `./`, lowercase drive letters on Windows, always forward slashes.
   - Stable when re-evaluating at the same `(rule_id, file, line)`.
   - Breaks when the file is moved or the defect line shifts significantly.

2. **`rule_message_hash`** — `sha1(rule_id + "|" + normalize_message(message))` hex-encoded.
   - `normalize_message`: lowercase; collapse runs of whitespace to single space; replace digit sequences with `N`; strip trailing punctuation.
   - Stable across minor message rewording and line shifts.
   - Breaks when the rule semantics change.

**Reference implementation** (the orchestrator runs this after each phase that emits findings):

```python
import hashlib, re, json

def normalize_path(p):
    p = p.lstrip('./').replace('\\', '/')
    return p

def normalize_message(m):
    m = m.lower()
    m = re.sub(r'\s+', ' ', m).strip()
    m = re.sub(r'\d+', 'N', m)
    m = re.sub(r'[.,;:!?]+$', '', m)
    return m

def compute_fingerprints(finding):
    loc = hashlib.sha1(f"{finding['rule_id']}|{normalize_path(finding['file'])}|{finding['line']}".encode()).hexdigest()
    msg = hashlib.sha1(f"{finding['rule_id']}|{normalize_message(finding['message'])}".encode()).hexdigest()
    return {"location_hash": loc, "rule_message_hash": msg}
```

**Dedup rule**: findings A and B are the SAME logical issue if `A.location_hash == B.location_hash` OR `A.rule_message_hash == B.rule_message_hash`.

Both hashes are needed — one alone misses a common case:
- `location_hash` alone misses "same bug, line shifted after a previous fix".
- `rule_message_hash` alone misses "same bug at same location, different evaluator reworded the message".

### Pipeline linkage

- `phase` — the phase that produced this finding. Redundant with the filename but keeps each JSONL record self-describing after concatenation (e.g., when building a fix-batch packet from multiple phases' findings).
- `criterion_ref` — anchor to the criterion this finding affects, if any. Populates `pipeline.state.json:criteria[].failed_by_finding_ids`. `null` if the finding is scope-broader than any single criterion.
- `fix_hint` — concrete action with file:line. Not "improve error handling"; must be e.g. `"Wrap read+write in db.transaction() at src/auth/session.ts:84-92; re-check order.status === 'pending' inside transaction before updating"`.

### Lifecycle

- `blocking` — does this block ship? Influences whether fix-loop must address it before declaring PASS.
- `status`:
  - `open` — reported, awaiting action
  - `resolved` — a fix-loop round applied a fix AND a subsequent evaluation confirmed the finding is gone (via fingerprint absence)
  - `suppressed` — intentionally not fixed with justification recorded in the phase's `log.md`; requires either user override via flag or explicit Out-of-Scope mapping in the spec

## Dedup and round handling

Each phase writes a fresh `.findings.jsonl` on each execution (fix rounds re-run Evaluate, which produces a new file). The orchestrator reconciles across rounds in TWO steps:

**Step 1 — Fingerprint injection** (deterministic, always runs):
- Immediately after the phase subagent finishes, the orchestrator reads the new `<phase>.findings.jsonl`.
- For every line with missing or empty `partial_fingerprints`, compute the two hashes using the Reference implementation above and write the JSONL back in place.
- This centralizes normalization rules so every finding shares the same fingerprint convention regardless of which subagent/model produced it.

**Step 2 — Cross-round reconciliation** (fix-loop rounds only):
1. Read prior round's `<phase>.findings.jsonl` (if any).
2. For each finding in the new file:
   - If a prior open finding has a matching fingerprint (either hash matches) → reuse the prior `id`, keep `status: open`.
   - Otherwise → assign a new `id`.
3. For each prior open finding NOT matched by the new file:
   - Set its `status: resolved` in the prior file (findings files are mutated only for status transitions; content is append-only otherwise).

Fix-batch packet construction (see fix-loop phase docs): orchestrator concatenates all phases' `.findings.jsonl`, filters for `status == "open"`, drops `blocking == false` findings when the round budget is tight, and writes the result to `.devlyn/fix-batch.round-<N>.json`.

## Example — `evaluate.findings.jsonl`

```jsonl
{"id":"EVAL-0007","rule_id":"correctness.non-atomic-state-transition","level":"error","severity":"HIGH","confidence":0.91,"message":"Order status read and write are not atomic in cancel handler","file":"src/api/orders/cancel.ts","line":42,"partial_fingerprints":{"location_hash":"a1b2c3d4e5f67890abcdef1234567890abcdef12","rule_message_hash":"d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3"},"phase":"evaluate","criterion_ref":"spec://requirements/1","fix_hint":"Wrap read+write in db.transaction() at src/api/orders/cancel.ts:40-50; re-check order.status === 'pending' inside transaction","blocking":true,"status":"open"}
{"id":"EVAL-0008","rule_id":"ux.missing-error-state","level":"warning","severity":"MEDIUM","confidence":0.85,"message":"Cancel button does not show error UI when API returns 409","file":"app/orders/[id]/page.tsx","line":87,"partial_fingerprints":{"location_hash":"b2c3d4e5f67890abcdef1234567890abcdef1234","rule_message_hash":"e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4"},"phase":"evaluate","criterion_ref":"spec://requirements/3","fix_hint":"Catch 409 response at app/orders/[id]/page.tsx:85-92; show Alert with retry button","blocking":true,"status":"open"}
{"id":"EVAL-0009","rule_id":"style.let-vs-const","level":"note","severity":"LOW","confidence":0.99,"message":"status could be const","file":"src/api/orders/cancel.ts","line":38,"partial_fingerprints":{"location_hash":"c3d4e5f67890abcdef1234567890abcdef123456","rule_message_hash":"f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5"},"phase":"evaluate","criterion_ref":null,"fix_hint":"Change `let status = ...` to `const status = ...` at src/api/orders/cancel.ts:38","blocking":false,"status":"open"}
```

## Non-goals

- Full SARIF 2.1.0 export (can be derived later via one-to-one mapping if needed).
- Cross-project finding aggregation. This schema is per-run.
- Rule metadata / documentation catalogs. `rule_id` values are self-documenting by convention.
- Code fix suggestions as patches. `fix_hint` is prose; fix-loop subagent generates patches.
