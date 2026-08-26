# Package evidence must be self-contained

## Observed failure

Run `rs-20260826T132929Z-c65aab72cbc8` reached BUILD_GATE finding
`BGATE-0001`: `bash scripts/lint-skills.sh` failed because Check 10e copies and
audits benchmark evidence named by `package.json`, but 32 of those files are
ignored run-local files absent from Git. The same command exits 0 in the owner
workspace only because those ignored files happen to exist there.

The first bounded repair run (`rs-20260826T140719Z-cf93bf283586`) then exposed
the next hidden dependency: the packaged frontier regression test copies four
raw `l2_risk_probes/result.json` files that are also absent from a fresh
checkout and from the npm package allowlist.

## Violated invariant

Every file that `package.json` promises to publish, and every input used to
prove that package subset, must be present in a fresh checkout. Package lint
must not depend on an ignored local-results cache.

## Required change

Track the exact 36 already-produced evidence files listed in
`evidence.sha256`. Source bytes are staged for this run under
`.devlyn/package-evidence-source/`; copy them without editing their content.
Add the four raw result paths to `package.json` and to Check 10e's npm-pack
required-file assertion, so the shipped frontier regression test has the same
inputs as a source checkout. Do not change benchmark measurements,
`.gitignore`, docs, or runtime code.

The ignored `results/` parent remains correct for new ephemeral runs. These 32
files are explicit curated exceptions because `package.json` already names
them as shipped evidence.

## Authorized implementation surface

Only the 36 `benchmark/auto-resolve/results/**` paths listed in
`evidence.sha256`, plus `package.json` and `scripts/lint-skills.sh`. Normal
`.devlyn` evidence is exempt. No other tracked path may change.

## Acceptance

- Every manifest path is tracked and byte-identical to its recorded SHA-256.
- The four raw `result.json` paths are present in the npm dry-run file list.
- `bash scripts/lint-skills.sh` exits 0 from this isolated checkout.
- `npm pack --dry-run` therefore validates the package from tracked inputs,
  without owner-workspace ignored files.
- The worktree contains no unrelated generated files.

Pure-addition citation: the top-level files are already an explicit
`package.json` deliverable, and the four raw files are required by the shipped
frontier regression test. BUILD_GATE `BGATE-0001` and run
`rs-20260826T140719Z-cf93bf283586` proved both sets are missing from a fresh
checkout.
