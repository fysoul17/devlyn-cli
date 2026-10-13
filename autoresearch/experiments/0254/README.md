# 0254 — Offline native receipt accounting

0253 established native request/terminal-response capture for one operational
Claude owner and foreground child. This standalone, read-only auditor makes the
prospective accounting rule explicit. It is not connected to a study runner.
0252 remains closed with UNKNOWN whole cost; no old result is repaired or graded.

`audit.py` accepts a frozen model, effort, 12-hex SHA256 account prefix and evidence
manifest digest. Every observed inference needs its exact transcript identity
anchor, indexed request and native terminal response. Native terminal bodies
supply the counters. A nonterminal transcript anchor can have provisional or
missing usage, while every terminal copy must agree before repeated blocks are
deduplicated. No arithmetic residual is assigned to a missing message.

The supported scope is one successful owner with native foreground, noninteractive,
first-level children, under the observed Claude Code 2.1.296 schema. Child identity
uses transcript paths/agent IDs, metadata, the parent Agent tool call, lifecycle
and returned usage. Only `end_turn` and `tool_use` are admitted; other stop reasons,
retries, errors, interruption, ambiguous continuation and incomplete evidence are
UNKNOWN. The API documents additional [stop reasons](https://platform.claude.com/docs/en/build-with-claude/handling-stop-reasons);
their existence does not establish support in this audit. Native capture uses the
[official local-file facility](https://code.claude.com/docs/en/monitoring-usage).

Scope amended **2026-10-13** for rp-d1 after live smoke: an owner-session
foreground `local_bash` task with an owner Bash tool-use anchor present in its
terminal response body, no `run_in_background: true` contradiction, exactly one
start and one matching `completed` or `failed` notification is admitted (updates
allowed). It adds no inference usage. Agent notifications still require
`completed`; `stopped` and other unbound task lifecycles remain UNKNOWN. Old
results are unchanged.

The sealed and actual native inventories must agree, including unindexed attempts.
Relevant files must be regular and hash-matched; symlinks, duplicate JSON keys,
truncated JSONL, malformed counters and conflicting identities fail visibly.
Whole receipt sums must match `result.modelUsage`; the owner subset separately
matches `result.usage`, and each child matches its returned usage and totalTokens.
Processed input includes uncached input, cache creation and cache reads. Thinking
is an included output component and is never added twice.

```sh
python3 -B autoresearch/experiments/0254/audit.py <capture-output> \
  --manifest-sha256 <frozen-seal-sha256> --model <frozen-model> \
  --effort <frozen-effort> --account <frozen-account-hash>
python3 -B -m unittest discover -s autoresearch/experiments/0254 -p test_audit.py -v
```

The CLI exits 0 for MATCH or 2 for UNKNOWN. Reports contain identifiers, hashes,
counters and fixed diagnostics, never raw prompts or account UUIDs. UNKNOWN keeps
whole totals null and retains observations already parsed and checked before the
first gap in `messages`, `reported_aggregate` and `reported_owner_usage`. Those
observations are not a certified whole cost or lower bound. MATCH is an accounting
statement within this scope, not provider billing, source correctness, delivery,
lifecycle safety or instruction efficacy. These other gates still apply.

The prospective [owner contract](results/owner-contract-r0.md) and independent
[design freeze](results/design-r0.md) precede implementation. The first review
found census, identity and cancellation gaps; all original predictions and failed
checks remain in completion custody. Two test-only error shapes were corrected
to observed `system/api_error`, and the cancellation fixture was corrected to the
observed text-block list. The repair adds regression coverage rather than treating
those invented forms as native behavior. See [verification](results/verification.json)
for exact hashes, review and results.

The unchanged private 0253 capture is a read-only compatibility control: three
messages, 49,313 processed input and 468 output, with 274 thinking included.
This is not a new native invocation or an independent study observation. Synthetic
failures test refusal behavior; they do not prove capture completeness under real
failure. Raw bodies remain private under `~/.local/share/nx01/0253-live`.

**No workaround** requires complete identity-bound receipts. **No guesswork**
preserves old UNKNOWN results and predictions. **No overengineering** keeps this
one offline module; product wording, prior runners and package versions do not
change. Runner integration or a new efficacy comparison needs its own prospective
contract. Minimal solo stays first, pair only when earned, ideate deferred.
