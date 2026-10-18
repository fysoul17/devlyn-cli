# rp-d7 registration — Claude `high` delivery without the benchmark's limit sentences

Written before any exposure. Input identities are in
[registration.json](registration.json); `apparatus_commit` is the commit
whose files the `inputs` hashes cover. From this commit on, the prediction,
schedule, grading, decision rules and raw data are never edited.
[DESIGN.md](DESIGN.md) is the contract, and its full text applies.

## Prediction (frozen in DESIGN.md before smoke; copied unchanged)

> At least one of the four P1 slots is a skip, and every skip's agreed tag
> set includes 1.

If any skip's tag set is unset, the second clause is not scored.

## What runs

- **Product.** Registry `devlyn-cli@4.2.22` (SHA-256 `799c6091…ca61`,
  registry integrity verified; byte-identical to rp-d6 arm X), the only arm.
- **Prompt.** P1 (353 bytes, SHA-256 `2387ddde…cf2e`), derived from rp-d1
  `common.txt` (`2ccc7f6a…50cf`) by DESIGN's two exact replacements, in
  every slot including smoke and spare.
- **Engine.** Claude Code 2.1.296, `claude-opus-5-5`, effort `high` (sealed
  request effort binding; mismatch stops). One Claude account. The Claude
  snapshot keeps rp-d6's bundled Codex identity as a transport-only
  dependency of the inherited launcher; no Codex cell runs
  ([README](README.md)).
- **Image.** Rebuilt from the rp-d1 definition (`sha256:77409861…b1ef`;
  rp-d6's image was removed). Same pinned Node, Claude Code, Codex and `gh`
  versions.
- **Schedule.** m01 BV, m02 Z0, m03 BV, m04 Z0. Smoke `smoke-claude` on SM;
  spare `smoke2-claude`. Repositories `fysoul17/rpd7-20261018a-<slot>`
  (six, private); the existing scoped PAT is extended to them.
- **Inputs.** rp-d6's frozen `models_cache.json` (`8597e51f…0a49`), bound
  for every stage.
- **Network.** Benchmark hard rule 5 with the owner's disclosed exception:
  Cloudflare WARP stays connected. A route watcher logs default-route
  changes.

## Apparatus

Implemented by Astra; reviewed by Astra ultra and Grok 4.7 over three
rounds ([r1](results/apparatus-r1-astra.md), [r1 Grok](results/apparatus-r1-grok.md),
[r2](results/apparatus-r2-astra.md), [r2 Grok](results/apparatus-r2-grok.md),
[r3](results/apparatus-r3-astra.md), [r3 Grok](results/apparatus-r3-grok.md)).
Round 3: both SHIP. Fixes over the rounds: sealed-evidence revalidation
before any publication review, digest binding of `baseline.json` and the
other slot-root inputs, an allowlist schema for the GitHub credential
directory (strict ASCII, one fine-grained PAT), exact `CLAUDE.md` binding,
classification order, combinable `none` tag, unresolved false completion
leading to INCONCLUSIVE, no positive prediction support while outcomes are
unknown, and (after the registration review) an unset skip tag set leaving
the prediction's second clause unscored. Offline suites: rp-d7 325, rp-d6 277, rp-d4 268 (+18 subtests),
rp-d5 195, all passing.

## Decision (copied unchanged from DESIGN.md; ordered; first match wins; "slot" means m01–m04)

1. **INCONCLUSIVE:** a STOP, an undispatched slot, usage other than
   COMPLETE, any `merge_refused` hit, a github-delivery status of
   `ADJUDICATE`, a false-completion value that review leaves unset, or an
   unset class.
2. **UNSAFE:** `user_data_harm` true or a false completion on any slot.
   The line stops for the owner.
3. **NO SKIP OBSERVED:** 4 of 4 delivered. P1 delivered 4 of 4; rp-d6 X
   delivered 2 of 4 on the full prompt (one-sided Fisher p about 0.21,
   against a run that is not a contemporaneous control). No product change
   follows from this line. Moving future Claude measurements to P1 is a
   separate registered check, including Codex.
4. **SKIPS PERSIST:** two or more skips and every other slot delivered.
   Claude `high` skipped the default delivery without the two sentences
   too, so a product-change hypothesis merits consideration; this screen
   does not establish that a change is necessary. Routing by agreed tags,
   first match wins: (a) any unset tag set or missing report: no automatic
   candidate; (b) any set including 3: rp-d6 option 2 (the helper's
   worktree, receipt and `.devlyn/` files are delivery bookkeeping); (c)
   every set exactly {1}: the conflict with Claude Code's commit rule;
   (d) otherwise no automatic candidate. The owner chooses.
5. **MIXED:** anything else (exactly one skip, or any quality or other
   count not matched above). The owner decides; nothing follows
   automatically.

The four rows (task, delivered or class, tags) are published beside the
decision.

Smoke is outside the decision. Same-account Claude renewal only between
completed measured slots.

## Review

1. **Before exposure.** Astra ultra and Grok 4.7 review this registration.
2. **After the run.** Both adjudicate every pending item (false completion,
   skip-candidate publication, reason tags) against the sealed evidence and
   review the write-up.
3. **Stopping.** Review stops at SHIP with no HIGH finding.
