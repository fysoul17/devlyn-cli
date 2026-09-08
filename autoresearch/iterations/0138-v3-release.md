# 0138 — devlyn-cli 3.0.0 release

The user explicitly requested version alignment to 3.0.0, publication, commits/push, main integration and cleanup of task branches. This supersedes the earlier no-publication boundary for this release.

## Result — 2026-09-08

- Signed tag `v3.0.0` pins `1209c2acf8173c30b5dedc1970ff82db061771c0`; signature verification passed. Main and tag were pushed atomically, fast-forwarding origin/main from 59f8835. No merge commit or release branch was needed.
- [Publish workflow 34241364317](https://github.com/fysoul17/devlyn-cli/actions/runs/34241364317) succeeded through the existing npm OIDC route. Registry publication time: `2026-09-08T14:55:20.039Z`; `latest=3.0.0` and registry `gitHead` matches the tag.
- [GitHub release](https://github.com/fysoul17/devlyn-cli/releases/tag/v3.0.0) is public, stable and contains the installation command and scoped release notes.
- All product version carriers already derived from `package.json` 3.0.0, so no product edit was required. Independent schema, lockfile, dependency and historical versions remain unchanged.

## Verification and retained limits

Verification-only run `rs-20260908T144515Z-9fbb49e90ead` completed canonical PASS and archive: actual package check, Node syntax and full `scripts/lint-skills.sh` each exited 0; native read-only Codex primary and Claude pair each returned PASS with zero findings. Existing tests were unchanged. Finish gate exited 0; final report was rendered and bound before completion/archive. The corrected process-evidence CLI precheck and its original argument-order failure are retained.

The published tarball has 513 members and is byte-identical to the locally verified package, SHA256 `25e6bc8455794014064a7e9dd12c3930fc9095f213d1956fc3de0874c6d9b648`. All member paths, modes and bytes match; required assets are present and internal state is excluded. Its extracted help and a fresh-directory/fresh-cache registry `npx` invocation both exited 0 with `v3.0.0`.

The initial repository-local npm execution instead resolved the existing global `/Users/aipalm/.nvm/versions/node/v20.19.0/bin/devlyn` and displayed 1.9.1. Its original output is retained; the independent clean-directory check establishes published-package behavior. No global installation was changed.

Root evidence: `.devlyn/release-3.0.0-r0/`; canonical archive: `.devlyn/runs/rs-20260908T144515Z-9fbb49e90ead/`. Durable 109-file copy, with every copied byte hash checked: `~/.local/share/nx01/releases/3.0.0/20260908T145756Z-dxki_2rl/`, manifest SHA256 `7ef944ace988fc1bd82df4254e4780b70cfcc686f7308884340420def8f71f45`.

No branch/worktree was created by this release. Preexisting research branches/worktrees, including 0125 and 0128 candidates, retain their separate outcomes. This release does not complete broader Mission 1 comparisons or relabel 0137's original failures and reporting handoff.
