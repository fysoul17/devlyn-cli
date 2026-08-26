# Package evidence must be self-contained

## Observed failure

Run `rs-20260826T132929Z-c65aab72cbc8` reached BUILD_GATE finding
`BGATE-0001`: `bash scripts/lint-skills.sh` failed because Check 10e copies and
audits benchmark evidence named by `package.json`, but 32 of those files are
ignored run-local files absent from Git. The same command exits 0 in the owner
workspace only because those ignored files happen to exist there.

## Violated invariant

Every file that `package.json` promises to publish, and every input used to
prove that package subset, must be present in a fresh checkout. Package lint
must not depend on an ignored local-results cache.

## Required change

Track the exact 32 already-produced evidence files listed in
`evidence.sha256`. Source bytes are staged for this run under
`.devlyn/package-evidence-source/`; copy them without editing their content.
Do not change the benchmark measurements, package allowlist, lint logic,
`.gitignore`, docs, or runtime code.

The ignored `results/` parent remains correct for new ephemeral runs. These 32
files are explicit curated exceptions because `package.json` already names
them as shipped evidence.

## Authorized implementation surface

Only the 32 `benchmark/auto-resolve/results/**` paths listed in
`evidence.sha256`. Normal `.devlyn` evidence is exempt. No other tracked path
may change.

## Acceptance

- Every manifest path is tracked and byte-identical to its recorded SHA-256.
- `bash scripts/lint-skills.sh` exits 0 from this isolated checkout.
- `npm pack --dry-run` therefore validates the package from tracked inputs,
  without owner-workspace ignored files.
- The worktree contains no unrelated generated files.

Pure-addition citation: the files are already an explicit `package.json`
deliverable and BUILD_GATE `BGATE-0001` proved they are missing from a fresh
checkout.
