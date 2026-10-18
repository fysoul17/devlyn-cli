# rp-d6 design — Claude's default delivery at effort `high`

DRAFT for design review (round 0). Product candidate; research run first.

## Why

devlyn's promise is that a request reaches a merged PR without the user
asking for delivery. In rp-d5's smoke (Claude Opus 5.5, effort `high`,
4.2.22) Claude implemented and verified the change, then declined the
default PR and merge as "an external repository" publication the request
"didn't ask for", and left the change uncommitted. The sealed request body
carries both Claude Code's "Commit or push only when the user asks" and
devlyn's managed-block sentence "deliver completed, verified requests with
changes by project policy (default PR and merge)". At effort `max` Claude
delivered in rp-d1 (3 of 4; o08 stopped at a local commit, also reading
publication as not allowed) and in both rp-d4 guards. The owner's everyday
setting is `high`. One `high` observation gives no rate.

Why-chain: Claude skipped delivery → it weighed the system prompt's
"only when the user asks" against devlyn's default → devlyn's sentence
states a policy, not that the user has already asked → nothing tells the
model that the installed policy *is* the user's standing request. The
violated invariant: the authorization exists (the user installed devlyn and
chose the default) but is not stated as authorization.

## Question

Under 4.2.22, how often does Claude at effort `high` finish the default
delivery with no delivery instruction, and does one sentence that states
the policy as the user's standing request raise that rate without making
Codex, Claude `max` behaviour or cost worse?

## Candidate (one rung, instruction only)

The managed block's Delivery bullet (CLAUDE.md and AGENTS.md templates,
byte-identical) states that the project policy is the user's standing
request to commit, push, open the PR and merge, so delivery does not wait
to be asked; explicit limits still win. Exact wording is chosen in design
review under the token gate: the whole managed block, Claude
`count_tokens` and o200k proxy, must not increase against 4.2.22, so the
added words are paid for inside the same block. `task-completion.md` is
unchanged. Installer fingerprints for the new block are added as the
release process requires.

## Arms

- **X:** registry `devlyn-cli@4.2.22`, verified (SHA-256, registry SHA-512).
- **Y:** X with only the managed-block template files (and the installer's
  fingerprint data for them) replaced by the candidate commit; the pack
  check confirms the tree differs by exactly those paths.
- Prompt: rp-d1 `common.txt` unchanged in every slot (no delivery
  instruction; no publishing limit).

## Schedule

Claude Code 2.1.296, `claude-opus-5-5`, effort `high` (per-slot override of
the inherited `max` pin, bound by every sealed request body's
`output_config.effort`). Tasks BV and Z0, two pairs each, interleaved:

| Pair | Task | Order |
|---|---|---|
| 1 | BV | X, Y |
| 2 | BV | Y, X |
| 3 | Z0 | X, Y |
| 4 | Z0 | Y, X |

Eight measured slots `m01`–`m08`, never replaced. Guards after them, Y only:
`g01` Codex BV and `g02` Codex Z0 (Codex 0.162.1, `gpt-6-sol`, `high`;
Codex delivered in every graded rp-d1..rp-d4 slot but rp-d3 m08), and
`g03` Claude BV at effort `max`.

**Smoke.** One Claude `high` Y cell and one Codex Y cell on SM. Delivery is
the measured outcome, so smoke qualifies the apparatus, not delivery:
owner exit 0, release and effort binding, reconciled accounting, archive
and 404. A smoke that does not deliver is recorded and still qualifies.
One spare pair; a failed spare stops the run.

## Grading

Delivery is graded mechanically as in rp-d1: scope and regression checks,
exactly one correctly merged PR from the delivered commit, preserved user
files, and no `merge_refused` (structure-free byte scan of every sealed
transcript, as in rp-d4). A `LOCAL_ONLY` or uncommitted result fails
delivery. Reports are not graded. Primary: **Claude `high` delivery passes
per arm**. Also per arm: owner wall, input and output over every dispatched
attempt, divided by delivery passes (0232 §6).

## Prediction (frozen before smoke)

> Y raises Claude `high` delivery from X to at least 3/4, with no guard
> failing.

## Decision (ordered; first match wins)

Attribution needs every slot dispatched and graded; otherwise
INCONCLUSIVE. A STOP overrides every branch.

1. **NO PROBLEM:** X ≥ 3/4. The skip is rare at this size; no adoption.
2. **REJECT:** Y ≤ X. No adoption.
3. **ADOPT** (patch release): Y ≥ 3/4 and Y > X; all three guards deliver;
   the token gate passed; cost per delivery pass by 0232 §6 (S_Y = 0
   fails; S_X = 0 < S_Y passes by dominance; otherwise Y's wall, input and
   output per pass each ≤ X's, with a strict improvement in passes or one
   cost).
4. **HOLD:** every ADOPT condition except cost. No adoption; owner decides.
5. **MIXED:** anything else. No adoption.

## Apparatus

Reuse rp-d4 (two-arm pack, Codex and Claude cells, Claude snapshot and
6300 s floor, token scans, `merge_refused` byte scan, spare registry) and
rp-d5 (per-slot Claude effort and its binding). Changes from both: the
spare binding uses the stage's frozen `models_cache.json` copy, not the
host file (rp-d5's spare was refused when the host file changed); smoke
qualification does not require delivery. Fresh run ID, private
repositories, the existing scoped PAT extended to them, benchmark hard rule
5 with the owner's disclosed exception (Cloudflare WARP kept connected),
route watcher, image prune guard.

## Interpretation limits

Four slots per arm on two tasks, one model and effort. 3/4 against 0/4 is
a routing gate (paired one-sided p ≈ 0.06–0.25 depending on discordant
pairs), not proof. The prompt carries no delivery instruction by design;
behaviour under a user's explicit "just fix it, don't push" is governed by
"explicit limits win" and is not tested here.
