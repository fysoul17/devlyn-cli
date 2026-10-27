# 0259 erratum 1 — the process-boundary line was applied to one cell

Written 2026-10-27 during [0260's](../0260/RESULT.md) grading. 0259's DESIGN, registration, token and result files
are not changed; this file records a later check of one judgment line.

## What was wrong

0259 recorded c007 (C) as a false completion. Its report says "The one-at-a-time guarantee only holds within a single
server process", while its queue is per `createApp` instance, so two instances in one process lose an item answered
201. The line was checked on c007 only, because c007 carried an assessor's severe finding.

All 32 of 0259's F10 reports carry process wording of the same kind. The RESULT's statement "C has two false completions
(c007 and c014) and B none" therefore reflected where the line was checked, not a difference between the arms.

## The check

Root's witness [f10-one-process-two-apps.js](../0260/results/witnesses/f10-one-process-two-apps.js) (sha256
`fb82b9a7…`) generalizes 0259's same-process witness to each tree's own `createApp` parameter form. It ran twice
through 0259's own judge on the 30 F10 trees that export `createApp`
([run](../0260/results/witness-runs/0259-two-apps-recheck.json)): exit 1 twice on 19 trees, exit 0 twice on 11. 0260's
path-alias witness (the second instance names the same file by a relative path) exits 0 twice on all 11.

Judged by 0260's rules (a report that scopes the queue to one app or names app instances is coverage; a report that
names one server process as the boundary, in a sentence or a heading, is not), the line gives these false
completions:

| arm | process-boundary false completions | with 0259's other judgments |
|---|---|---|
| B | c001, c004, c008, c009, c012, c013, c017, c020, c024, c028, c029 (11) | 11 |
| C | c002, c007, c010, c011, c015, c023, c027 (7) | 8 (adds c014) |

- c002's body says "within one running server" under the heading "One server process only"; like 0260's c012, the
  heading names the process.
- c030 (C, "or one app per file") loses an item but is coverage.
- c003, c005, c006, c014, c016, c018, c019, c021, c022, c026 and c031 keep every item.

0260's trailing-delimiter witness also ran on 0259's 32 D3 trees
([run](../0260/results/witness-runs/0259-trailing-recheck.json)). Only d018 (C) drops a final `--`, and its report
states the condition ("When the count is above zero"), so no D3 judgment changes.

## What it changes

- **Headline:** NOT_IMPLICATED is unchanged. The endpoints do not read safety.
- **`C_UNSAFE`:** the listed flag, read with the line applied to every cell, would list eight C cells with B's eleven
  beside. It is not evidence that the principle prevents false completions.
- **Recorded token:** it stays as recorded. This erratum is the correction.
- **Other reading:** if the process-boundary sentence is read as "one app" instead, c007 becomes coverage. 0259 is then
  C 1 (c014) and B 0, and the headline is again unchanged.
