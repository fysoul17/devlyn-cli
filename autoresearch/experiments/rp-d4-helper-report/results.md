# rp-d4 results — the helper states cleanup

**Outcome: MIXED under the registered rule. Y is not adopted; the product is
unchanged.** Codex named cleanup in 2 of 4 Y reports and 0 of 4 X reports.
The registered gate needed 3 of 4.

The run used the frozen [registration](registration.md) (both reviewers
SHIP), the [contract](DESIGN.md) and [registration.json](registration.json).
All ten slots ran with no STOP, no `merge_refused`, no connection drop and no
default-route change, and every delivery passed. Evidence:
[results/measured](results/measured/), with `summary.json` from the
registered summarizer and both reviewers' report reviews.

## What happened

| Slot | Arm | Task | Delivery | Cleanup (Astra / Grok) | Reconciliation (Astra / Grok) | Owner s | Input | Output |
|---|---|---|---|---|---|---:|---:|---:|
| m01 | X | BV | passed | MISSING / MISSING | MISSING / AMBIGUOUS | 118.2 | 764,671 | 6,082 |
| m02 | Y | BV | passed | **SUPPORTED** (both) | SUPPORTED (both) | 92.2 | 377,382 | 4,846 |
| m03 | Y | BV | passed | MISSING / MISSING | MISSING / AMBIGUOUS | 115.0 | 463,515 | 5,332 |
| m04 | X | BV | passed | MISSING / MISSING | MISSING / AMBIGUOUS | 118.2 | 667,454 | 5,605 |
| m05 | X | Z0 | passed | MISSING / MISSING | MISSING / AMBIGUOUS | 91.9 | 385,330 | 4,439 |
| m06 | Y | Z0 | passed | MISSING / MISSING | MISSING / AMBIGUOUS | 91.7 | 409,973 | 5,003 |
| m07 | Y | Z0 | passed | **SUPPORTED** (both) | SUPPORTED (both) | 126.9 | 330,245 | 5,277 |
| m08 | X | Z0 | passed | MISSING / MISSING | MISSING / AMBIGUOUS | 184.2 | 447,298 | 5,160 |
| g01 | Y (Claude) | BV | passed | SUPPORTED (both) | SUPPORTED (both) | 423.2 | 1,458,953 | 36,686 |
| g02 | Y (Claude) | Z0 | passed | SUPPORTED (both) | SUPPORTED (both) | 447.5 | 1,616,305 | 39,814 |

- **Cleanup (primary):** X 0/4, Y 2/4. m07 quoted the helper's sentence
  verbatim ("Cleanup: Removed the task worktree; deleted the local task
  branch; deleted the remote task branch; emptied the task scratch."). m02
  paraphrased it ("Delivery cleanup removed the task worktree and branches and
  emptied its scratch directory."). m03 and m06 omitted it, as did the Y
  smoke report.
- **Other categories:** verification and merge 4/4 in both arms;
  reconciliation X 0/4, Y 2/4. The two reports that named cleanup also named
  reconciliation ("fast-forwarded"). The two reviewers agreed on every
  SUPPORTED finding. No category was FALSE.
- **Success (all four categories):** X 0/4, Y 2/4. These are the first
  graded Codex successes across rp-d1, the rp-d2 rerun, rp-d3 and rp-d4.
- **Cost:** X used 2,264,753 input and 21,286 output tokens over 512.6 s;
  Y used 1,581,115 and 20,458 over 425.8 s. Y passed the cost gate by
  dominance over the zero-success control (0232 §6). It also used fewer raw
  tokens and less time, but four slots per arm cannot resolve that.
- **Claude guard:** both Y reports passed all four categories. g02 quoted
  the helper's sentence; g01 described the same state in its own words.

## Decision

Branches in order: no INCONCLUSIVE precondition held; X cleanup 0/4 is not
BASELINE MOVED; Y cleanup 2/4 is not REJECT (≤ 1/4); ADOPT failed only on
the primary condition (Y cleanup ≥ 3/4). Every other ADOPT condition held:
no Y FALSE, no category lost ground, Y successes ≥ X successes, cost by
dominance with strict improvement, both guards passed. The failing condition
is not cost or strict improvement, so the result is **MIXED**, not HOLD. A
paired 2-of-4 against 0-of-4 is not distinguishable from noise at this size
(two favourable discordant pairs, one-sided exact p = 0.25).

## Reading

The helper's sentence is reachable: in half the Y reports Codex carried it,
and those reports were complete in all four categories for the first time.
In the other half Codex kept its usual changed/verified/merged shape and
ignored both the instruction and the sentence in front of it, as it did in
the Y smoke. The mechanism moves Codex but does not settle its report, and
this rung does not meet the bar the owner set.

`config/skills/_shared/task-complete.py` and `task-completion.md` are
unchanged on main; 4.2.22 stays the release.

## Next candidates, for the owner

1. **Confirm this candidate at a larger size.** The same Y against X with
   more pairs (for example eight per arm) would resolve whether 2/4 is a
   real lift. This is the cheapest next step, and nothing about the
   candidate changes.
2. **Stop here.** Accept that Codex's report omits cleanup at roughly this
   rate; the helper already performs and records cleanup correctly whatever
   the report says.

## Cleanup

Done after this write-up merges:

- all 14 `rpd4-20261017a-*` repositories deleted (the ten measured and two
  smoke repositories after archiving, the two unused spare repositories
  empty) and verified 404;
- the measurement image, the live directory (stage, archives, auth
  snapshots, GitHub credential files), the route and image watchers, the
  worktree and the branch removed.

The owner deletes the fine-grained PAT `rpd4-aa`, which was pasted in chat.
