# 0234 apparatus: pair reasoning on 4.2.0's misses

This apparatus copies 0233's sealed cell, locator, assessor, usage and checker machinery. It measures A (native), B (4.2.0), H (B plus a same-engine peer) and P (B plus a cross-engine peer). The only scored candidate is P. No code here dispatches a model during generation, calibration or unit tests. The experiment has not been run.

## Frozen packages and routes

The package procedure is 0233's history-aware clone, `scripts/update-instruction-templates.js`, then `npm pack --ignore-scripts` with Node 20/npm 10 and a temp npm cache. `control.py` checks the exact archive SHA-256 before mounting an installing arm. A has no package. Every arm receives the identical `0232/common.txt` native prompt and caller contract. Each task/configuration runs from its own sealed repository and private home.

| Arm | Commit | Packed SHA-256 |
|---|---|---|
| B | `dd4957775337e597f39838fa73acd5c7ec4a5699` | `6f03f5ac2895eaccc22ff12d1644a0fc623baca1eec7d00e877ce3254d33352d` |
| H | `335d27130c270e9c947558eb2f9c28a528776e32` | `f48ee18c5174d4c737489ca1fb14b8c27f9e09af42219a3fac56381ee22bd695` |
| P | `04712dad0e9f2efcc90aa85b7d5add8f76786fa9` | `54c513afbac15a87fa7bd19028769cb8a1cc43ae9c989fbfb3e6aeb08f8f8591` |

For every arm and configuration, the cell home sets Codex's CLI default to `gpt-6-astra`/high and Claude's CLI default to `claude-opus-5-5`/high. Codex's native child default remains `gpt-6-sol`/high. The owner's route remains Claude Opus/high or Codex Astra/high. H uses the owner engine and exact owner model/effort; P uses the other engine's default. Both CLIs' credentials and executable environment are mounted as in 0232's I arm. Peer route, session model and effort are reported and never turn into a STOP. Native owner and child identity rules retain their STOP behavior. In SMOKE, inspect `diagnostics.peer.turns` for three successful, awaited turns with the same id, registered model/effort, counted usage, and `teardown: CLEAN`.

## Tasks, participant source and requests

Pool order is `I0185`, `F16`, `F23`, `F25`, `F10`, `F11`. I0185's same 0233 source is copied into `sources/I0185` because the original external `.devlyn/0185/inputs/install` path does not exist in this checkout; its seven registered source hashes match. F10/F11 and E1/E2 reuse 0233 requests and reference overlays. All F16/F23/F25 arms receive one identical request: the fixture's `task.txt`, then its `## Requirements` section verbatim, ending before `## Constraints`. This declared adaptation includes the requirements graded by the fixture verifiers, and excludes their solo-headroom hypotheses and evaluator notes. F23 `remaining` was narrowed: its request does not say whether exhausted lots remain as zero-quantity rows. Both rows accept that choice while validating every row's schema, sort order, and exact positive inventory. The `priority-rollback` row grades accepted/rejected records, status, and stderr, matching the original verifier's scope. Original and adapted hashes are SHA-256 of UTF-8 request bytes:

| Task | Original | Adapted |
|---|---|---|
| F16 | `7c69228d11d3fd73d9278b96b8e29e365064013e339211eb3c4be4986d7e867c` | `cbaf501126934d2579aeb5f40a724f808bee3da361d133dd5ec3c81c0a88e69a` |
| F23 | `bb59a46ad92e43bcf31d07e0d7b22d595bcfe9da8a5e849672bb9c519fd05448` | `3f4c34c5909832e1f1d05fb005723cd04625a0c7dbd55a50a4f2142b2e11c6d2` |
| F25 | `df3150677be12630580a09c9b42c04c3bd85f41f95c3d32af38aac4f7d4db22e` | `07df8ba152902fc44a42a24d45aec2095d8494166a83223c07b342e75a2ba453` |

Each new fixture source is `fixtures/test-repo`, its participant setup data where present (`data/pricing.json` for F16, `data/catalog.json` for F25), and 0233's vendored locked dependencies. Evaluator scripts are excluded. The 0233 copied F10/F11/E1/E2 source trees on this checkout lack the ignored `node_modules/qs/dist/qs.js` that their 0233 hash manifest listed; the file is also absent from 0233's checked-out source. Their 0234 source hashes seal the actual copied bytes. This missing distribution artifact is not used by the public commands; changing the source seal to the physical tree makes preparation reproducible. `vendor-manifest.json` retains the 0233 package lock provenance.

S2 uses a tiny Python starter and requests a percentage discount before rounded tax, with half-up rounding at both steps. Its purpose is pair activation and route/teardown observation; product success is not a SMOKE gate. E1 and E2 are unchanged tripwires. Expected pair applicability is yes for I0185/F16/F23/F25/F10/F11/S2 and no for E1/E2.

## Hidden rows and calibration

`fixture_oracle.js` independently reimplements the fixture verifiers' inputs and expected records using `isDeepStrictEqual`, fresh writable copies and one process per row. F16 rows: `exact-success`, `stock-error`, `pricing-source`, `shipping-base`, `coupon-min`. F23: `priority-rollback`, `single-warehouse-fefo`. F25: `exact-success`, `stock-error`, `catalog-source`, `shipping-bases`, `coupon-min`. `shipping-base` distinguishes F16 subtotal from subtotal after coupon; F25 `shipping-bases` probes both subtotal versus after-line and after-line versus after-coupon. Coupon-minimum rows verify the stated eligibility bases. The public check for each is the fixture's `node --test tests/cli.test.js`. References are source overlays only and never enter a participant mount.

| Task | Passing reference | Single-row failing references |
|---|---|---|
| F16 | `good` | `bad-exact-success` (tax after discount), `bad-stock-error-duplicate` (stock per line), `bad-pricing-source` (frozen pricing), `bad-shipping-base` (subtotal threshold), `bad-coupon-min` (early coupon) |
| F23 | `good`, `good-zero-rows` | `bad-priority-rollback` (tentative stock leaks to a later order), `bad-single-warehouse-fefo` (splits a single-warehouse line) |
| F25 | `good` | `bad-exact-success-promotion-order` (coupon before line discount), `bad-stock-error-duplicate` (stock per line), `bad-catalog-source` (frozen catalog), `bad-shipping-bases-subtotal`, `bad-shipping-bases-post-line`, `bad-coupon-min` |

Inherited 0233 references are copied with these registered expectations:

| Task | Passing references | Failing references (each fails its named row only) |
|---|---|---|
| F10 | `good`, `good-key-order`, `good-raw-item` | `bad-concurrent-posts`, `bad-concurrent-posts-counter-reset`, `bad-invalid-unchanged`, `bad-reads-use-store`, `bad-restart-persists` |
| F11 | `good` | `bad-invalid-body`, `bad-mid-batch-invalid-unchanged`, `bad-mid-batch-invalid-unchanged-qty`, `bad-valid-batch` |
| E1 | `good` | `bad-default-unchanged`, `bad-name-with-shout`, `bad-shout` |
| E2 | `good` | `bad-missing-key-exit-and-unchanged`, `bad-others-preserved`, `bad-set-get-unchanged`, `bad-unset-removes` |

The 17 new reference outcomes above were verified by host Node calibration. The 22 inherited reference outcomes are copied registered expectations, not fresh results. The full inherited calibration includes F10/F11 and E1/E2 server tests. This host's execution sandbox refuses local server binds (`listen EPERM`), and the Docker socket is unavailable, so the full `python3 calibrate.py` command cannot complete here. No evaluator result is inferred from that failure.

## Panels and decision

`generate_cells.py` writes all slots before a run: 4 S2 SMOKE, 12 B-only screening, 50 development, 72 confirmation and 8 easy rows. Every task/configuration's one screening cell determines eligibility from product incompleteness or any failed row. A screening `ADJUDICATE` status or `NOT_TRIGGERED` row stops gating until root records `screening-adjudication.json` in the output directory. That file maps each cell name to `{ "complete": true|false, "rows": { "row-id": "PASS"|"FAIL" } }`; `complete` is required for `ADJUDICATE`, and each `NOT_TRIGGERED` row needs a disposition. Per configuration, the first two eligible pool tasks enter development and the next two enter confirmation. All unselected slots receive `NOT_RUN` before preflight. Development has B/H/P once and A once, except I0185 A reuses both 0233 development A verdicts for that configuration. Their original verdict/check evidence and sealed period are retained in the 0234 verdict and decision table. Matched development comparisons use I0185 A replicate 1, the first reused 0233 A cell for that configuration in 0233 order. A replicate 2 and its period appear descriptively outside matched sums. The four required 0233 A verdict files were absent from the local 0233 output inspected during construction. `run_cell.py` returns an explicit not-dispatched record until `reuse_0233_output` points to completed evidence. Confirmation has A/B/P twice, with the second arm order reversed. Easy has B/P once. The `cells.tsv` rows freeze identities; after screening, `python3 generate_cells.py --dispatch-order <output>` gives the actual run order. Development arm order depends on eligible slot and configuration: Claude slot 1 `ABHP`, slot 2 `PHBA`; Codex slot 1 `HAPB`, slot 2 `BPAH`. This prevents pool-index gating from putting P last in both blocks. Confirmation rotates by task/configuration and reverses replicate 2; all six three-arm permutations occur. Easy alternates `BP`/`PB` by task plus configuration, so order is not confounded with configuration. Screening, SMOKE and easy are outside development and confirmation sums.

`decide.py` applies 0232 §6 per-success quality and resource dominance to each configuration and panel. Development reports P/B, P/A, H/B, P/H and B/A. Confirmation gates only P/B and P/A: a P-only quality failure, a failed comparison, or zero P successes against any A/B success yields FAIL; both PASS yields PASS; other nonempty panels are UNCONFIRMED; empty panels are NO_HEADROOM. P is admitted on confirmation PASS when development P/B is not FAIL. Beating B alone does not earn admission over A if B itself has not earned admission. Quality failures are evaluated before a zero-success `NO_CLAIM`. UNCONFIRMED gives P-unconfirmed. H never admits anything. The easy tripwire reports completion regression or a P raw wall/input/output total over 1.25 times B. Unknown usage remains unknown.

`diagnostics.json` records the pair guide as `read` only when the guide heading appears in a successful read's tool result. It reports peer tool returns, backgrounding, actual process/turn completions, engine/model/effort, session continuity, timing relative to the first edit, owner exit while a peer runs, turn count over three, and executable peer counterexamples found in transcripts and run on final source when parseable. Unparseable counterexamples are `unknown`. Diagnostics do not gate product grading or admission.
