# rp-d1 — default-delivery cost: instrumentation gate

> **2026-10-14:** after this gate the owner approved building the delivery apparatus ([DESIGN.md](DESIGN.md)); rp-d1 was registered ([registration.md](registration.md)) and measured. See [results.md](results.md).

**GATE FAIL (2026-10-13). Stopped before registration and before any live run.**
No prediction was frozen, no task was exposed and no measurement cell was launched.
Product wording, versions and closed studies are unchanged.

HANDOFF step 5 requires the 0254/0255 accounting path, used as is, to count a
live GitHub delivery with all children; otherwise stop and report the exact
prerequisite. Astra ultra and Grok 4.7 each answered that question
independently and read-only ([prompt](results/gate-review-prompt.md),
[Astra](results/gate-review-astra.md), [Grok](results/gate-review-grok.md)).
Both ended `GATE: FAIL`. Their key citations were rechecked against `83c5eccc`.

## Why it fails

The blocker both reviewers name is the inherited cell, not token accounting.
A cell can neither perform nor prove a GitHub delivery:

- The owner prompt always appends "Do not publish"
  (`0237/runner.py:70-73`, `0237/local-delivery.txt`).
- `origin` is the local bare mirror `/harness/mirror.git`, and the cell STOPs if
  that remote, its refs or its objects change (`0233/run_cell.py:136-148`).
  With that origin, `task-completion.md` sends the owner down the local-only
  route, and `task-complete.py` refuses to publish to a non-GitHub remote.
- The image has no `gh`, and only Claude and Codex credentials are mounted
  (`0232/Dockerfile`, `0251/cell.py`).
- `0237/delivery.py` proves a local descendant commit, never a merged PR.

Accounting limits, which the planned prediction already treats as UNKNOWN
rather than as blockers:

- Claude (0254/0255): one owner plus same-model, first-level, foreground native
  children. Independent CLI launches force UNKNOWN by design.
- Codex: 0255 delegates to the inherited trace accounting
  (`0234/record_usage.py`). It was COMPLETE for all three Codex observations
  in 0252 and all but one in 0248. In 0248 d10, a stream failure left one inference
  without authoritative usage (PARTIAL/STOP). That residual is a native-emission
  gap; arithmetic cannot fill it.

The current default delivery launches no in-product reviewer or other model
process: the owner reviews the diff (`task-completion.md`), and `gh` makes no
model calls. An ideate drain does start executor sessions, but rp-d1 measures
direct requests. The planned "in-product reviewer usage" has no process to
count on this path.

## Exact prerequisite

The prerequisite is a new delivery apparatus. No new accounting code is needed:

1. A cell whose `origin` is the throwaway private GitHub repository, with a
   transport invariant that permits exactly that remote and its pushes.
2. No injected delivery instruction (drop `local-delivery.txt`).
3. `gh` in a pinned image, plus a GitHub credential limited to that one
   repository and expiring after the run.
4. A done-check binding the independently verified source to the actual
   merged PR. This is separate from token accounting.

These are edits to inherited runner code and one new credential decision. Both
need the owner's approval before rp-d1 can be registered.
