# Loop executor

## Executor exchange

The packet (`<receipt dir>/packet.json`) carries everything a fresh executor needs:

| Field | Meaning |
|---|---|
| `task`, `title`, `kind` | Queue identity and deliverable description. |
| `worktree`, `branch`, `receipt`, `scratch` | Absolute owned worktree, branch, receipt and disposable build directory. |
| `allocation_base`, `inputs_sha` | Allocation base and the committed-inputs commit. |
| `contract`, `expected`, `meta` | `{path, sha256}` of the committed task contract, expected acceptance and meta-prompt. |
| `requirements`, `review_requirements` | Requirement IDs and those needing review evidence. |
| `shared_constraints` | The meta-prompt's `Constraints and exclusions`. |
| `dependencies` | `{task, receipt, source_sha}` of each accepted prerequisite. |
| `schema_version`, `harness` | New packets use version 2 and the bound release reference, or null for legacy unbound queues. Existing v1 packets execute unchanged. |
| `methodology` | `projectInstructions`: `{path, sha256}` of instruction bytes at the inputs commit. `defaults`: `{source: "release", path, sha256}` from the verified binding; for an unbound queue `{source: "skill", path, sha256}` of the installation's own `_shared/runtime-principles.md`. A task whose executor would get no principles at all (no defaults and no committed CLAUDE.md/AGENTS.md) waits with that reason instead of running. Read the named defaults; explicit user and native owner/project instructions take precedence, except a Devlyn managed block (devlyn:instructions markers), which the defaults replace. No native engine applicability is inferred from filenames. |
| `workerPrompt` | `{path, sha256}` of the task’s worker instructions, or null for legacy unbound queues. Read it before working. |
| `delivery` | `local-only`, `auto` or `pr`. |
| `evidence_dir`, `runner` | Where loop evidence lives (`<worktree>/.devlyn/loop`, ignored by Git) and the runner argv. |
| `submission`, `obligations` | Where to write the submission, and the completion obligations. |

Writable tool caches go under `scratch`, for example `npm_config_cache=<scratch>/npm`: Codex's sandbox keeps caches in HOME read-only.

Build in the worktree's default build directory, never one redirected into `scratch` or shared with another checkout: drain re-runs the checks without your environment. Allocation may have warmed it (`build_dirs` in the receipt).

Run `runner` (`acceptance.py run --packet <packet>`) on the committed candidate before review. It prints `{"result": <path>, "passed": ..., "reasons": [...]}`; listing a wholly clean result (empty `reasons`) lets drain reuse its outcomes. Then write the submission:

```json
{
  "schema_version": 1,
  "task": "<identity>",
  "source_sha": "<candidate commit on the owned branch>",
  "runner_results": ["<worktree>/.devlyn/loop/runs/<n>/result.json"],
  "reviews": ["<worktree>/.devlyn/reviews/<name>.json"],
  "assumptions": ["<each assumption, recorded once>"],
  "blockers": []
}
```

`schema_version`, `task` and `source_sha` are required. A blocker `{"kind": "failed" | "needs-review" | "blocked-infrastructure", "detail": "<concrete question or cause>"}` records `[F]` with that reason and runs no checks; material ambiguity becomes `needs-review`, never a weakened acceptance.

## Review records

Each `review_requirements` ID needs review evidence: a JSON record under `<worktree>/.devlyn/`, listed in the submission's `reviews`, in this shape:

```json
{
  "schema_version": 1,
  "kind": "devlyn-review",
  "task": "<identity>",
  "engine": "<engine>",
  "model": "<exact model id>",
  "source_sha": "<reviewed commit>",
  "contract_sha256": "<packet.contract.sha256>",
  "expected_sha256": "<packet.expected.sha256>",
  "requirements": ["R3"],
  "findings": [{"id": "F1", "binding": true, "disposition": "resolved", "requirement": "R3", "summary": "<finding>"}]
}
```

A record counts only when it binds this task, the candidate source and both contract digests; any other well-formed record is reported under `ignored_reviews` (a source change invalidates earlier reviews). A listed review or runner record that is unreadable or not this shape fails acceptance with its path named; keys a review record or finding adds beyond this shape are ignored. The counted records' `requirements` must cover `review_requirements`. Each finding's `disposition` is `open`, `resolved` or `rejected` (`rejected` needs a `reason`); an open binding finding blocks acceptance. The loop requires no particular engine or number of reviewers.
