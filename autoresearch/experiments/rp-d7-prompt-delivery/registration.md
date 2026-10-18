# rp-d7 registration — Claude `high` delivery without the benchmark's limit sentences

Written before any exposure. Input identities are in
[registration.json](registration.json); `apparatus_commit` is the commit
whose files the `inputs` hashes cover. From this commit on, the prediction,
schedule, grading, decision rules and raw data are never edited.
[DESIGN.md](DESIGN.md) is the contract, and its full text applies.

## Prediction (frozen in DESIGN.md before smoke)

> At least one of the four P1 slots is a skip, and every skip's agreed tag
> set includes 1.

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
leading to INCONCLUSIVE, and no prediction score while outcomes are
unknown. Offline suites: rp-d7 325, rp-d6 277, rp-d4 268 (+18 subtests),
rp-d5 195, all passing.

## Decision and stopping

As in DESIGN.md "Decision", in order: INCONCLUSIVE, UNSAFE, NO SKIP
OBSERVED, SKIPS PERSIST (routing (a)–(d)), MIXED. Smoke is outside the
decision. Same-account Claude renewal only between completed measured
slots.

## Review

1. **Before exposure.** Astra ultra and Grok 4.7 review this registration.
2. **After the run.** Both adjudicate every pending item (false completion,
   skip-candidate publication, reason tags) against the sealed evidence and
   review the write-up.
3. **Stopping.** Review stops at SHIP with no HIGH finding.
