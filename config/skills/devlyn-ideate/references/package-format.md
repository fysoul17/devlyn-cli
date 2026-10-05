# Loop package format

The formats `scripts/queue.py check|add` validate. One package per intent:

```text
docs/specs/<loop-id>/meta.md                         index: intent, shared constraints, manifest
docs/specs/<loop-id>/<task-id>/spec.md               self-contained task contract
docs/specs/<loop-id>/<task-id>/spec.expected.json    mechanical acceptance
docs/specs/queue.md                                  the one mutable queue
```

IDs match `[a-z0-9][a-z0-9-]{0,62}`. The queue identity `<loop-id>.<task-id>` never changes and is never reused; revised work gets new IDs. Headings below are fixed ASCII identifiers, like the verification sentinel; their content may be in any language.

## meta.md

Required `##` sections, each non-empty:

| Heading | Content |
|---|---|
| `Intent` | Original intent and referenced source documents (input documents are preserved, not rewritten); intended user outcome. |
| `Constraints and exclusions` | Shared requirements, prohibited changes, applicable delivery restrictions. Sent to every worker. |
| `Tasks` | Ordered task index, dependency graph and decomposition rationale. No prescribed task count; one task is a valid loop. |
| `Overall acceptance` | Every overall requirement assigned to a task; cross-task requirements assigned to the integration task's assembled-product check. |
| `Execution policy` | Baseline, installed-methodology rule, autonomous question policy, delivery policy, stop conditions. |
| `Decisions and assumptions` | Adopted decisions and defaults with reasons. No elicitation transcript. |

Exactly one fenced `json` block, the manifest. It is authoritative for order and dependencies and never carries status:

```json
{
  "schema_version": 1,
  "loop_id": "inventory",
  "base_ref": "main",
  "base_sha": "<exact 40- or 64-hex commit in this repository>",
  "delivery": "auto",
  "tasks": [
    {"id": "t01", "spec": "t01/spec.md", "depends_on": []},
    {"id": "t02", "spec": "t02/spec.md", "depends_on": ["t01"]}
  ],
  "integration_task_id": "t02"
}
```

- Keys are exactly these; `loop_id` equals its directory; each `spec` is `<id>/spec.md`.
- `delivery` is the inherited `auto` or `pr`, or an explicit `local-only` ([loop.md](loop.md) step 3).
- `depends_on` names earlier tasks; unknown dependencies, cycles and forward references are rejected before execution.
- `integration_task_id` is the last task and depends, directly or transitively, on every other task; its acceptance is the assembled-product check. Give the integration obligation to the final substantive task; add a separate integration task only for necessary work that cannot belong there.

## Task spec.md

```yaml
---
id: t02
loop_id: inventory
title: Reservation behavior
kind: feature
review_requirements: [R3]
---
```

`kind` (`feature`, `spike`, `prototype`) describes the deliverable and routes nothing. `review_requirements` lists requirement IDs that need semantic or source judgment (`[]` when none). An optional `complexity` is descriptive only. `status` is rejected: queue state lives in the queue and receipts.

Required `##` sections, each non-empty:

| Heading | Content |
|---|---|
| `Context and goal` | Outcome and why this task exists. |
| `Requirements` | One list item per obligation with a stable ID: `- R1: <concrete acceptance obligation>`. |
| `Scope and constraints` | Authorized implementation surface and the shared constraints that apply. |
| `Out of scope` | Explicit exclusions. |
| `Prerequisite inputs` | Predecessor interfaces, artifacts and assumptions this task relies on. |
| `Verification` | Commands, assertions and requirement coverage. The line directly above the heading is `<!-- devlyn:verification -->`. |
| `Deliverable and cleanup` | Result to retain, change-created residue to remove, permitted disposable output. |

A worker receives this file and its task packet only, never the planning conversation or other task specs, so state everything it needs here.

## spec.expected.json

Schema: [expected.schema.json](../../_shared/expected.schema.json), parsed strictly (duplicate keys and non-finite numbers are rejected) by `_shared/expected-contract.py`. Loop tasks use:

- `verification_commands`, each with exactly one of `argv` (preferred: no shell, portable to Windows) or `cmd` (shell); `exit_code` (default 0); `timeout_sec` (1-600, default 60); `stdout_contains` and `stdout_not_contains` (UTF-8 substrings of stdout plus stderr); and non-empty `contract_refs` naming this task's requirement IDs.
- `required_files` and `forbidden_files` (literal Git paths), `forbidden_patterns` (regex over the task's own diff; `disqualifier` blocks acceptance, `warning` is recorded), `max_deps_added` (default 0) and `pure_design`.

Rejected otherwise:

- Every requirement is covered by some command's `contract_refs`, by `review_requirements`, or both.
- A runtime task has at least one command. `pure_design: true` has no commands and lists every requirement in `review_requirements`.
- Phase-specific obligations (`process_evidence`, `required_risk_probe_requirements`, `tier_a_waivers`, `spec_output_files`) are rejected with an instruction to translate them into commands or review requirements without weakening them.

Coverage proves that every obligation has evidence. Whether the checks express the owner's intent stays a planning and review responsibility.

## Queue rows

```markdown
- [ ] inventory.t02 [Reservation behavior](docs/specs/inventory/t02/spec.md)
- [x] inventory.t01 [Stock model](docs/specs/inventory/t01/spec.md)
- [F] inventory.t03 [Report](docs/specs/inventory/t03/spec.md) — blocked-prerequisite:inventory.t02 (receipt <id>)
```

- Links are repository-relative and exactly `docs/specs/<loop-id>/<task-id>/spec.md`; titles escape `\`, `[` and `]`. Packets and reports carry absolute paths.
- `[ ]` is pending or active (the receipt tells which). `[x]` is an accepted product. `[F]` is failed, infrastructure-blocked, prerequisite-blocked or needs-review and ends with ` — <reason> (receipt <id>)`. Delivery state lives in receipts and the drain report; a pending PR never turns `[x]` into `[F]`.
- The only legal transition turns one pending row into `[x]` or `[F]` with every other byte unchanged. Terminal rows are never reinterpreted or rerun.
- Identities are unique; equal titles are fine.
- A row that does not fully match this grammar (trailing whitespace aside) is a legacy raw intent: readable, never executed. `add --materialize <line>` replaces one pending legacy row, at its position, with a package whose `## Intent` reproduces that intent verbatim (whitespace may reflow).

## Commands

```sh
python3 "$DEVLYN_SKILL_DIR/scripts/queue.py" check '<repo>/docs/specs/<loop-id>/meta.md'
python3 "$DEVLYN_SKILL_DIR/scripts/queue.py" add '<repo>/docs/specs/<loop-id>/meta.md' [--materialize <line>]
```

`check` validates without writing. `add` validates, then appends the rows in manifest order at the physical end of the queue under the queue lock, creating `docs/specs/queue.md` with its header when absent, and commits the package directory and the queue on the current branch, only those paths, as `devlyn loop: add <loop-id>`; `<common Gitdir>/devlyn-loops/<loop-id>/added.json` records that commit, the loop's first allocation base. It refuses without writing already queued identities, a detached HEAD, a current branch that does not descend from `base_sha` and package files committed with different content; a failed commit restores the queue. It never changes the package files. Both print one JSON object; exit 1 is `BLOCKED` with a `reason`.
