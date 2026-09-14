# 0174 — apply the shipped entry policy to the active environment

2026-09-14. The current source already contained the0172 direct/full selection
policy, but the user's working checkout at `cb80904` still had the earlier
AGENTS/CLAUDE summaries. Four active core skill copies also had older descriptions.
Updating only the retained research checkout had not updated these loaded inputs.

Applied the already-shipped0172 entry delta to the active project's `AGENTS.md`
and `CLAUDE.md`, and the current resolve description to project `.agents`/`.claude`
and global `.codex`/`.agents` core copies. Preserved all phase bodies, helpers,
pins and personal configuration. The original dirty `.gitignore` and HANDOFF
remain byte-identical. The active project changes are a local application of
existing upstream source, not a commit of the user's unrelated WIP.

Native offline Codex rendering now includes the updated project entry and core
descriptions. Twelve legacy snapshot cards still appear in this active render;
they were not silently edited/deleted. This is not catalog-isolation proof.
The next matched comparison must isolate the catalog as documented in0173.

## Actual behavior checks

Codex requested gpt-6-astra/high and Claude requested/observed Opus5/medium
(effort is requested, not independently observed). Each read the actual fixture
instructions, code and callers before selecting a route. The user-style request
included an old BUILD_GATE failure and devlyn:resolve path as context.

| Check | Codex | Claude |
|---|---|---|
| Fix local git-report filename whitespace loss | DIRECT, completed | DIRECT, completed |
| Existing regression tests | PASS; original had2 assertion failures | PASS; original had2 assertion failures |
| Independent boundary cases | 8/8 | 8/8 |
| Discover tenant authorization change | FULL | FULL |
| Discover persisted edits deleted by "cache" cleanup | FULL | FULL |
| Explicit resolve for small edit | FULL | FULL |
| Queue drain | FULL | FULL |

Both fixes delete only `.strip()`; protected tests, instructions and risk-case
files are unchanged. No native pipeline/helper invocation occurred. The four
FULL cases were expressly inspection-only decisions; no full run is claimed.
The unchanged pipeline's existing actual full acceptance is0173. These checks
validate the applied behavior on bounded cases, not a before/after routing-rate,
speed improvement, broad risk recall or difficulty threshold. Native totals
118.939s/66.406s are diagnostic observations, not an engine comparison.

## Decision and custody

**No overengineering / Optimized:** no new router, classifier, phase or model layer.
The observed gap was applying the existing policy to the inputs actually loaded.
The installer intentionally preserves existing project instructions; this task
does not change that customer-data preservation contract. Native snapshots and
raw results are in `.devlyn/0174/`, with exact pre-application backups and hashes.
An initial root audit expected3 failures; the observed2 were preserved and the
audit expectation corrected. No native draw was retried or externally repaired.

The user subsequently requested a new-session difficulty-boundary study after
this task. [The prepared plan](../NEXT-SESSION-routing-boundary.md) is NOT RUN;
it defines task dimensions, a bounded exploratory stage, untouched confirmation,
common quality requirements, explicit catalog checks and honest cost coverage.
`.devlyn/0174-delivery/FINAL.md` records delivery/cleanup and supersedes pending
handoff language. Do not repeat0173 or describe this application as a new
upstream pipeline algorithm.
