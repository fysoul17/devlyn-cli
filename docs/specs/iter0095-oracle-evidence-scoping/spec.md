---
complexity: medium
---

# iter-0095 — plan-dispatch-oracle evidence scoping (orphan-correlation rule)

Instrument follow-up A from DECISIONS 0094.1, adjudicated at the iter-0095
R0 freeze round (2026-08-05; receipts `~/.local/share/nx01/iter0095-reg/`,
seat split Codex F1-fired vs Grok not-fired resolved by the orchestrator to
the minimal orphan-correlation rule below; decisive criterion: fail-closed
against real malformation, not against benign format variance). Target:
`benchmark/ceiling/scripts/plan-dispatch-oracle.py` (current sha
`b6808aa1…`). Motivating defect: the collector emits
`parent-session-shape:message-not-object` for EVERY JSONL record without a
dict `message` — live current-format sessions carry benign non-message
records (summary/file-history/hook attachments), so evidence-completeness
caps every live arm at INCOMPLETE (0091 C1 full-dir replay = INCOMPLETE/82;
0094 candidate-simple = INCOMPLETE/111).

## Requirements

### R1 — no-`message` record scoping with Agent-identity orphan correlation

In the parent-session record scan (the loop containing the current
`message-not-object` emission at `:139-141`):

1. A record WITHOUT a `message` key is no longer flagged
   `message-not-object`. Instead:
   - If the record REFERENCES an Agent tool-use identity, it must
     CORRELATE. A record references an Agent tool-use identity when it
     contains (at top level or inside its `attachment` object) a
     `hookName` string naming the `Agent` tool (`PreToolUse:Agent` or
     `PostToolUse:Agent`) together with a `toolUseID` (or `tool_use_id`)
     string — the pinned-CLI 2.1.222 hook-attachment shape — or when a
     `system`/`task_*`-typed record carries a `tool_use_id` string
     alongside Agent task metadata (`subagent_type` or `prompt`) — the
     2.1.220 dual-write shape.
   - Correlation may be resolved AFTER the full session scan: the
     referenced id must appear among the message-path collected Agent
     `tool_use` ids or Agent `tool_result` `tool_use_id`s of the same
     session set. A non-correlating reference emits ONE evidence issue
     `parent-session-shape:agent-evidence-orphan:<file>:<line>` (feeds
     the existing evidence-completeness cap → INCOMPLETE). `<file>` is
     the session file's collision-free `source` identity (the
     result-relative path already computed for candidates, with its
     existing str(path) fallback), NOT the basename — two same-basename
     session files in different subdirectories with an orphan at the
     same line number must yield TWO distinct issues in the final
     analyze() payload (`evidence.issues`), surviving its
     `sorted(set(...))` dedup. [Outer-loop amendment 2026-08-05 after
     run rs-20260805T100034Z BLOCKED:verify-exhausted — both VERIFY
     judges converged on the basename-collision collapse at the payload
     boundary.]
   - A no-`message` record WITHOUT any Agent identity reference is
     benign: skipped, no issue, no typed record-`type` allowlist.
2. A record WITH a present non-dict `message` keeps the existing
   `message-not-object` issue unchanged.

### R2 — `subagent_type` absent-key validity

In the Agent tool_use input validation (`:223-227`): an ABSENT
`subagent_type` key is VALID (0092 freeze: selection left to the parent,
no key-set pin; live 0094 candidate arms omit the key). A PRESENT key
that is null, non-string, or empty stays `agent-subagent-type-malformed`.
Candidate rows keep recording `subagent_type` and `subagent_type_valid`.

### R3 — self-tests (in-file `--self-test`)

Add deterministic cases; all existing assertions stay green:

1. Benign no-`message` record (e.g. a `summary` record) appended to a
   clean COMPLETE attempt → still COMPLETE, no `message-not-object`, no
   orphan issue, `evidence.complete == true`.
2. CORRELATED Agent-hook no-`message` record (hook shape above whose
   `toolUseID` equals the attempt's Agent tool_use id) → COMPLETE, no
   issue.
3. ORPHAN Agent-hook no-`message` record (`toolUseID` matching no
   collected Agent id) → classification INCOMPLETE with
   `agent-evidence-orphan`. Same-basename collision regression: two
   session files with identical basenames in different subdirectories,
   each with one orphan reference at the same line number → TWO
   `agent-evidence-orphan` issues asserted through the analyze()
   payload's `evidence.issues` (not through collect_agent_calls()'s raw
   list). [Outer-loop amendment 2026-08-05.]
4. No-`message` record carrying unrelated ids (no Agent hook name, no
   task metadata) → clean skip.
5. Agent tool_use WITHOUT a `subagent_type` key → no
   `agent-subagent-type-malformed`, candidate `subagent_type_valid` is
   true, disposition unchanged (ACCEPTED on the clean fixture).
6. Existing present-but-malformed cases unchanged: non-dict `message`
   still `message-not-object`; `subagent_type: 7` still
   `agent-subagent-type-malformed`.

## Out of scope

- No collection of parallel metadata as delivery evidence: digest
  comparison, violation logic, window/ledger/startup logic unchanged.
- No typed record-`type` allowlist.
- No changes to any other script; no changes under `config/skills/` or
  mirrors.
- Full-dir replay conservation proofs on retained receipts are the
  iter-0095 registration freeze gate's job (external receipt dirs), not
  this spec's verification.

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    {
      "cmd": "python3 benchmark/ceiling/scripts/plan-dispatch-oracle.py --self-test",
      "stdout_contains": ["SELFTEST PASS"],
      "exit_code": 0,
      "timeout_sec": 300
    },
    {
      "cmd": "grep -cF 'agent-evidence-orphan' benchmark/ceiling/scripts/plan-dispatch-oracle.py | awk '{exit ($1>=2)?0:1}'",
      "exit_code": 0
    },
    {
      "cmd": "git diff --check",
      "exit_code": 0
    }
  ],
  "max_deps_added": 0
}
```
