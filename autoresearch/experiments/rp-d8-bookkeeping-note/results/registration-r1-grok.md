# registration-r1 — grok

I'll review the registration against the frozen design and the apparatus, read-only. First I'll load the registration, DESIGN, and the files those hashes point at.Registration is loaded. Next I’ll compare it to the frozen DESIGN and recompute every listed input hash at the apparatus commit.The design text and the code pins are in place. I’ll recompute the input hashes at the apparatus commit and check the worktree, candidate, and decision text against them.The branch tip is the registration commit on top of `cd6ede46`. I’ll hash every listed input at that commit and compare the decision text before judging.The registration matches the frozen design and the code pins on the identities that can be checked by reading. One measurement in `registration.md` is stronger than the recorded evidence, so the registration should be corrected before exposure.

## Findings

1. **MEDIUM** — `registration.md` states an offline result the tree does not record. The apparatus paragraph says `rp-d8 460, rp-d7 325, rp-d6 277, rp-d4 268 (+18 subtests), rp-d5 195`. The later summary in `VALIDATION.md` (itself an `inputs` file) is `rp-d8: 366` with the same 325 / 277 / 268+18 / 195 figures. No other file in the experiment records 460. **Fix:** cite that recorded 366 summary, or add the raw pytest line that shows 460 and point the sentence at it.

2. **LOW** — `registration.md` says rounds 1–3 were REVISE. `results/apparatus-r3-verification.json` records Astra REVISE and Grok SHIP. Round 4 is both SHIP, which matches `apparatus-r4-astra.md` and `apparatus-r4-grok.md`. **Fix:** say rounds 1–2 were both REVISE, round 3 was Astra REVISE and Grok SHIP, and round 4 was both SHIP.

3. **LOW** — the engine sentence lists Codex as `g01`, `g02`, and `smoke-codex`. DESIGN’s spare pair and `schedule.py` `smoke_slots(2)` also include `smoke2-codex` at effort `high`, and the repository list already has it. **Fix:** add `smoke2-codex` to that parenthetical.

## What matches

The prediction quote and the eight decision rules are the same text as `DESIGN.md`. The schedule `m01`–`m16` matches DESIGN’s pair table and `schedule.py`: pairs 1–8, Z0 on 1, 2, 4, 5, 7, 8, BV on 3 and 6, orders XY, YX, XY, XY, YX, YX, XY, YX, every measured slot Claude at effort `high`.

Guards `g01`–`g08` match DESIGN and `prepare.py` `SUFFIXES`: `g01`/`g02` Codex with setup `null`; `g03`–`g05`, `g07`, `g08` use those exact suffix strings; `g06` is setup `no GitHub origin` and is not a prompt suffix. Tasks and engines match the table. There are 27 repository names, `fysoul17/rpd8-20261019a-<slot>`, covering `m01`–`m16`, `g01`–`g05`, `g07`, `g08`, and the four smoke names. `g06` is absent. That is the allowlist in `prepare.py`.

`pack.py` pins the same candidate `e22dbaf3b7d4a458768c86e7ec8ff85e0f8bdb8c`, blob `de7f9882dc8c3df1cb2b0a621c9c7fa794b01866`, design commit `7c5dcdf2fca05f8d17d9e7fb3bc340461f8713c1`, single shipped path `config/skills/_shared/task-completion.md`, and X `sha256` `799c6091…ca61` with the registered `sha512-` integrity. Y’s `candidate_commit` and `candidate_blobs` use those pins. The worktree copy and the `.agents` mirror both contain DESIGN’s bookkeeping sentence, and the four deleted sentences are absent. The branch tip `d0693f8d` is the child of `apparatus_commit` `cd6ede46` (`rp-d8: registration (before exposure)`).

P1 `2387ddde…cf2e` is `prepare.py`’s `P1_SHA256`. The models-cache id `8597e51f…0a49` is the rp-d6/rp-d7 frozen id. CLI versions match those registrations. The image id is a `sha256:` plus 64 hex digits. Token-gate rows match DESIGN’s counts (4867→4864, 2979→2974, 14309→14276). Roots are marked identical at 11 and 4284 bytes. `passed: true` is the result `rendered_gate.py` requires for those rows. Both `arms_sha256` fields are the same value. `registration.md` and `registration.json` contain no token, VPN hostname, or IP. “Cloudflare WARP” is DESIGN’s disclosed exception.

The listed `inputs` digests were not recomputed here, so this review does not certify them against `cd6ede46`. Recompute each path with `git cat-file blob cd6ede4612839e489066f76aaf419c33d9f03d28:<path>` before exposure, and confirm the diff from that commit is only the two registration files.

VERDICT: REVISE
