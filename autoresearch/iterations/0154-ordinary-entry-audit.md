# 0154 — Historical ordinary entry and preserved project instructions

2026-09-12. Baseline `9e70a697b01b232ffc27163d2d4694ebd0bb40be`.
Root accepts the bounded audit **PASS_WITH_ISSUES**. No production code changes,
resolve invocation or speed claim. Proposed customer-file edits remain unapplied
pending explicit scope confirmation; this is not closure of current routing risk.

## Evidence and root cause

The user reports that most routine requests before 3.1.0 began resolve, naming
devlyn-os-v1, ai-rag-hub and archon-interface-v1. All three historical CLAUDE.md
files explicitly say at line 54: `Small tasks: invoke /devlyn:resolve` (the actual
text includes the quoted goal). Their default-entry heading is at line 52.
Historical commits and complete snapshots are in `.devlyn/0154/inventory.json`
and each project's evidence directory. This corroborates the historical source
mandate; it does not attribute individual model executions or all elapsed time.

The release 3.1.0 contract already has proportional entry. All three current
CLAUDE.md files also contain direct-entry criteria and full-route exceptions;
their installed Claude markers report 3.1.2. All three current AGENTS.md files
lack those paragraphs. Archon's line 41 still labels loop engineering the default
entry. The other two do not contain that label: do not attribute historical
Codex over-routing to an absent literal mandate in those files.

Why can updating leave this gap? `bin/devlyn.js:726` starts
`installInstructionsForCLI`; its existing marker-free AGENTS branch preserves
customer bytes and prints a comparison/merge notice. This deliberately differs
from Claude installation. `docs/specs/agent-instructions-update-notice/spec.md`
requires preservation and forbids a new overwrite/migration policy. The current
installer follows that contract; a second product fix is not justified.

## Actual checks and minimum proposal

Prediction was registered before the installer experiment. An audited package
from accepted 0153 source was installed using the normal `agents codex` command,
with an owned temporary project and Node `os.homedir` preload for each case.
All four cases pass: the three captured old AGENTS inputs retain exact bytes,
print the preservation/template notice and receive current helper bytes; a new
project receives the exact current AGENTS template. Customer homes are untouched.

The first apparatus incorrectly required installed SKILL.md to equal packaged
bytes despite installer path stamping. Its failed assertion and outputs remain;
the corrected check compares an unchanged shared helper. This was a test
assumption failure, not an installer failure. Final raw commands, output and
digests are in `installer-results.json` and `installer-final-*/`.

No overengineering / Goal-locked execution: reconcile only the missing route
criteria and full-route exceptions. The proposed patches add those two existing
canonical paragraphs; Archon's stale default-entry lead becomes full-route.
No task-completion or engine-policy modernization is included. All three
`git apply --check` calls pass; snapshots and live AGENTS bytes still match.
Deleting either new paragraph loses either decisive direct-route criteria or
the explicit risk/full-workflow boundary; no new route abstraction is needed.

Actual independent read-only native Fable 5.1/high (103.891s) and Grok 4.6/high
(152.466s) both return **PASS_WITH_ISSUES**, with zero observed tool calls.
Their complete prompt, raw results, identities and usage are retained in
`reviews/`; Grok's assistant header is `grok-4.6`, usage is `grok-4.6-build`.
This is static advice, not measured routing or complete MCP-isolation proof.
Root adjudicates no in-scope CRITICAL/HIGH. Fable's MEDIUM ai-rag downgrade and
LOW Archon engine-default conflicts are pre-existing customer policies outside
the route-only patch; they remain explicitly unresolved. Missing old pin
definitions do not justify adding an engine block solely for these references.

## Custody and remaining work

Retained checkout: `~/.local/share/nx01/core-continuation-20260912`; prospective
receipt `8793aed2ba033fe54961e3a7`. Source evidence is
`.devlyn/0154-evidence.tar.gz`; delivery is recorded separately. Original and
prior dirty research checkouts, customer files and frozen experiments remain
untouched. No npm release. Cross-repository local patch application awaits the
user's answer, because it expands the current CLI repository's edit scope.

The historical report is acknowledged without requiring a new current failure.
Current model adherence and speed remain unproven, as do full-route overhead
reduction, semantic coverage and matched quality/pair value. 0144 already records
the historical duplicate-check repair; fresh adherence evidence must precede
another change to that guidance.
