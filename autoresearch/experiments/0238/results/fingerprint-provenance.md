# e389e1e7 fingerprint provenance — offline bounded audit

No shipped-release migration regression is established. The removed key identifies
an intermediate branch template, not a paragraph found in any local release tag.
Source, package archives, frozen controls and manifests were not changed.

## Provenance

- Key: `e389e1e77cc2da32214e95451b25b45402b1b586b26f5688bb373c492db3fcfb`.
- Introduced in both paragraph lists by `7e2eef0aaa74c0f5b0dcacd0ea1889c7efb3aeff`
  (2026-10-07 08:34 KST). Hashing its actual AGENTS.md / CLAUDE.md paragraphs
  with current `instructionParagraphs` identifies Quick Start's Delivery line:
  “direct work edits the current checkout. Only when the user asks to ship it
  (commit, PR or merge)…” without the later concurrency clause.
- All reachable root path-history scans covered 59 AGENTS commits / 55 distinct
  blobs and 86 CLAUDE commits / 84 distinct blobs. The matching paragraph version
  is the one introduced by 7e2eef0a; it is absent from the current first-parent
  path history (46 / 75 commits respectively) and every local release-tag root.
  Descendant commits before its replacement can naturally retain the same blob;
  this is not a claim that only one commit in the graph contains the text.
- `f4de6c0622d8122ba8eaacb6d38e1bb288ccee06` replaced it with the concurrency
  clause before PR #173 merged. First-parent merge `415e2d14` already contains
  that replacement. Tags v4.2.0 through v4.2.3 contain the later automatic-delivery
  wording; v4.1.0 predates this intermediate simplification.
- `6623c55b529d17d39bd2b14d6b68bc33ef9ed74d` commit message explicitly says its
  regeneration drops this PR #173 branch key, that it manually keeps the key,
  and that the release workflow would still drop it. `08132b628710b795200318da485f3ac3097e423f`
  explicitly repeats that preservation. Thus its presence in committed manifests
  was intentional historical coverage; its later disappearance is explained.

## Generator and migration behavior

`scripts/update-instruction-templates.js:12-21` clears paragraph sets and rebuilds
from HEAD's first-parent root-file history. `.github/workflows/publish.yml:33-34`
runs this before publishing (lines 46-56). Computing that exact set in memory at
HEAD removes only e389… from each file and adds nothing, matching the package diff.

The prospective prediction and raw local controls are retained as
`fingerprint-provenance-prediction.json` and `fingerprint-provenance-raw.json`.
Sixteen actual migration calls (two filenames × two manifest variants × four
inputs) all exited 0 and confirmed the prediction. Tagged v4.1.0/v4.2.0 legacy
sources and an intact managed 7e2eef0a source upgrade byte-identically with either
manifest. Only a deliberately edited managed 7e2eef0a block differs: regeneration
preserves the now-unrecognized delivery line as custom content; the committed
manifest recognizes/removes it. Both retain the explicit custom addition and
produce exactly one managed block. This follows `bin/instructions.js:253-255`
(edited blocks use paragraph recognition) versus its intact-body digest branch.
It demonstrates conditional branch-install behavior, not released-user exposure.

No cached registry devlyn-cli tarball was found in the inspected local npm cache;
registry bytes and publication history were not fetched. Git tags plus the actual
publish workflow support intermediate-source provenance, but do not prove that
no person ever installed or privately published that branch. No global monotonic
history change or manual package-key restoration is justified by this bounded
evidence alone. If branch-installed edited templates are explicitly supported,
this reproducible coverage difference can be considered separately from current
fresh-home experiments and tagged-release upgrades.
