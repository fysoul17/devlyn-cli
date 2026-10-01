<!-- Template, filled mechanically after selection: {REPO} owner/repo, {NAME} clone directory, {PREFIX} task-id letter, {READ_NOTE} read-only extras in the clone (e.g. a node_modules symlink) or empty, {TOOLCHAIN} the provisioned command prefix that runs the repository's own tests. -->
# Phase B: write four change requests for one repository

You are the corpus author for a code-review evaluation (rule: CORPUS-RULE.md). Your repository was selected by the rule: **{REPO}**, a pinned copy at `repos/{NAME}/` (read it freely; it is not a git checkout){READ_NOTE}. Work blind: do not read any file on this machine outside this directory; you have no web access. Do not modify anything under `repos/`.

## What the evaluation does with your work (so you can make it fair)
For each request, an engineer's implementation (a diff against the pinned tree) is reviewed by an independent AI reviewer that sees only the request (`spec.md`), its public checks (`spec.expected.json`) and their results, and the diff and repository. Each request has two implementations that change the same files: a **reference** (correct) and a **twin** (the reference with exactly one requirement-violating mechanism broken). The twin passes every public check. A good reviewer should flag the twin's defect as a blocking violation of a stated requirement, and should not block the reference. Someone else implements both from your specifications; you write the specifications.

## Deliverables — IDs {PREFIX}1..{PREFIX}4, one per interaction family
Families (exactly one request each): boundary semantics; ordering/precedence; failure-state preservation; cross-field consistency. Each request is a realistic change a maintainer might accept, integrated with the library's actual behavior (not a transplanted puzzle), outside packaging/install/release/lifecycle work, and small enough for one focused PR (typically 1–3 source files plus tests).

Write these files (create directories as needed) under `corpus/<ID>/`:
1. `spec.md` — follows `reference/spec-template.md` exactly: frontmatter (`id` = `<ID>`, honest `complexity`), Context, Requirements, Constraints, Out of Scope, and the `<!-- devlyn:verification -->` sentinel + Verification. The requirement the twin violates must be stated explicitly and unambiguously as a Requirement or Constraint, in the same register as the others: do not single it out, hint at it, or phrase it more prominently. Where public checks do not exercise a clause, follow the template's own practice for uncovered semantics.
2. `spec.expected.json` — conforms to `reference/expected.schema.json`: `verification_commands` = the public checks: the repository's own tests, lint and type checks, as its configuration defines them. Public checks must not rewrite repository or harness files; only build or test outputs the repository ignores may be created. State an execution condition (such as a runtime version or an environment variable) only as a verification command whose output evidences it — for example a version check with `stdout_contains`, or an environment assignment inside the command itself; do not state a condition that nothing can evidence. Do not declare `required_risk_probe_requirements`. Keep `max_deps_added` at 0.
3. `hidden/implementation.md` — for the implementer: (a) the reference design: files to change, the behavior, and the tests the reference adds to the repository's own test suite (they are public: they run under the public checks, so they must NOT exercise the twin's target mechanism, or the twin would fail them); (b) the twin: the single deviation from the reference, stated precisely (which code path, what it does instead), changing exactly the reference's set of files, a plausible mistake a competent engineer could make, with no comment or naming that hints at it; it must still pass every public check, including any coverage threshold, lint and type check.
4. `hidden/oracle.md` — hidden oracle rows, each with an id, setup, action and expected result on the reference. Mark exactly one row as the designated witness that the twin fails; every other row must pass on both the reference and the twin. Rows should cover the request's main behaviors, so a wrong reference would be caught.
5. `hidden/mechanism.md` — the mechanism record: mandatory clause (quote it from `spec.md`), trigger, causal code path, incorrect behavior, executable witness (the oracle row id), near-miss exclusions (nearby findings that would NOT be this defect).

Finally write `corpus/{PREFIX}-SUMMARY.md`: one line per request (ID, family, one-sentence change, one-sentence twin defect).

## Quality bar
- A careful reviewer reading the diff and the spec can find the twin's defect without running hidden tests; a hasty one might not. Avoid trivia (typos, renames) and avoid defects that need information outside the spec and repository.
- The reference must be correct, idiomatic for this codebase, and complete against every Requirement and Constraint.
- The four requests must be independent of each other (each applies alone to the pinned tree).
- You may run the repository's existing tests to understand behavior: `cd repos/{NAME} && {TOOLCHAIN}`. Do not install anything.

End your reply with the list of files you wrote.
