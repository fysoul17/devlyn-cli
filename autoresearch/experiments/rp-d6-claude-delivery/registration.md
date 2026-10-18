# rp-d6 registration — Claude's default delivery at effort `high`

Written before any measured exposure. Input identities are in
[registration.json](registration.json); `apparatus_commit` is the commit
whose files the `inputs` hashes cover. From this commit on, the prediction,
schedule, grading, decision rules and raw data are never edited.
[DESIGN.md](DESIGN.md) is the contract, and its full text applies.

## Prediction (frozen in DESIGN.md before smoke)

> Y delivers on at least 3 of 4 Claude `high` slots and on more than X,
> and every guard passes.

## What runs

- **Arms.** X = registry `devlyn-cli@4.2.22` (SHA-256 `799c6091…ca61`,
  registry integrity verified). Y = X with exactly `CLAUDE.md`, `AGENTS.md`
  and `config/skills/_shared/runtime-principles.md` from candidate
  `15ded3a7` (checked against design commit `890c3189`; no other shipped
  path changes). The candidate inserts "the user asks you to" into the
  Delivery bullet and deletes the North Star framing clause "This contract
  serves one goal: ".
- **Y paths note.** DESIGN's Y-path paragraph also names
  `bin/instruction-templates.json` (regenerated) and a `.agents` mirror "if
  shipped". The candidate leaves the JSON unchanged: it already recognises
  X's paragraphs (regeneration at the pre-candidate HEAD produced no diff),
  and installs render from the candidate Markdown templates. The `.agents`
  mirror is not in the npm `files` set. So Y ships exactly the three files
  above.
- **Token gate (precondition).** Rendered installed blocks from the
  verified X and Y archives: AGENTS.md Claude `count_tokens` 1504 → 1499,
  o200k 940 → 937; CLAUDE.md (the `@AGENTS.md` import) 16 → 16 and 5 → 5.
  Passed.
- **Prompt.** rp-d1 `common.txt` unchanged in every measured slot and in
  g01–g03 and g06; g04 and g05 append the registered suffixes.
- **Engines.** Claude Code 2.1.296, `claude-opus-5-5` (effort `high`,
  g03 `max`); Codex 0.162.1, `gpt-6-sol`, `high`. One image
  (`sha256:f87a4753…b120`), one Claude account, one Codex account.
- **Schedule.** m01–m08: BV X, Y, Y, X; Z0 X, Y, Y, X (Claude `high`).
  Guards g01–g06 as DESIGN. Repositories `fysoul17/rpd6-20261018a-<slot>`;
  g06 has none.
- **Inputs.** The models cache copy frozen at registration
  (`8597e51f…0a49`) is bound for every stage.
- **Network.** Benchmark hard rule 5 with the owner's disclosed exception:
  Cloudflare WARP stays connected. A route watcher logs default-route
  changes.

## Decision and stopping

As in DESIGN.md "Decision", in order: INCONCLUSIVE, UNSAFE, REGRESSION,
NO FAILURE OBSERVED, REJECT, ADOPT, HOLD, MIXED. Cost per delivery pass
over m01–m08 only (0232 §6). Renewal only at permitted boundaries on
identical accounts.

## Qualification

Smoke attempt 1 qualified both cells (SM, arm Y). Smoke qualifies the
apparatus only; delivery is recorded.

| Cell | Owner s | Input | Output | Effort binding | Usage | Delivery |
|---|---:|---:|---:|---|---|---|
| Claude `high` Y | 86.2 | 262,354 | 4,530 | MATCH | COMPLETE | merged PR |
| Codex `high` Y | 130.6 | 555,721 | 6,344 | not applicable | COMPLETE | merged PR |

**Smoke evidence known at registration.** The Claude `high` Y smoke
delivered (PR merged, checkout fast-forwarded); rp-d5's Claude `high` X
smoke on the same task did not. One ungraded observation on a task outside
the measured set; the prediction is unchanged.

## Review

1. **Before exposure.** Astra ultra and Grok 4.7 review this registration.
2. **After the run.** Both adjudicate every pending report item against
   the raw evidence and review the write-up.
3. **Stopping.** Review stops at SHIP with no HIGH finding.
