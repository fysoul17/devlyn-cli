# 0238 operational staging and native smoke proposal

Preparation only, 2026-10-10. No authenticated call, credential read or model
inference was run for this plan. The 0237 CF comparison is closed without
admission. The 0239 lifetime comparison is also closed without adoption: d01's
source/lifecycle passes remain, but interrupted inference leaves whole cost
UNKNOWN; no d02 or C rerun follows. The admitted guide stays B.

Completed preparation: the installer correction is accepted; v5 accounting guard
is SHIP; selected-packs-v2 and staged-v1 are created. Actual positive/no-op/deleted
controls and 12 helper bindings pass (selected-runtime-controls-v1 and corrected
selected-runtime-install-v2). Preserve the initial target-layout audit error.
An empty `.claude` tree is correct when only the Codex target was installed.
Preparation-packs-v1 and v4 remain historical. Native dispatch is governed by
../registration-smoke.md and ../STATUS.md; the commands below are the preparation
procedure, not instructions to recreate an existing destination.

## Concrete staging

`results/stage.py` accepts explicitly selected package archives, tasks and the
latest review manifest. It checks package/archive/helper/process-primitive
hashes, creates a fresh private destination, copies the existing public/oracle
control, adds both historical F23 JS dependencies and the new witness, extracts
B/S/H/P offline, and writes a complete control manifest and smoke runtime.
It never builds packages, reads credentials, contacts profile APIs or starts a
cell. Archive extraction uses Python's data filter. This script itself is a
separately reviewed operational script: apparatus-review-v4-followup.md verifies
dependency drift is rejected before destination creation. selected-stage-v1.json
records its actual use with the reviewed v5 manifest and selected archives.

From the allocated worktree, after root explicitly selects and freezes inputs:

```sh
python3 -B autoresearch/experiments/0238/results/stage.py \
  /Users/aipalm/.local/share/nx01/0238-live/staged-v1 \
  --packs /Users/aipalm/.local/share/nx01/0238-live/SELECTED-PACKS \
  --tasks /absolute/path/to/registered-smoke-tasks.json \
  --template-runtime /Users/aipalm/.local/share/nx01/0237-live/runtime-discovery-max-smoke.json \
  --review-manifest autoresearch/experiments/0238/results/SELECTED-REVIEW-MANIFEST.json
```

The template supplies only public paths and account fingerprints. New auth,
scratch and output directories start empty with private permissions. It pins
image `sha256:0f472bb41685b7daa5923d51d31983f4b3c70053dd773fdf712bd0dcd6d87998`,
uses the allocated worktree as source_root, and creates phase=smoke with empty
boot_catalogs. Each later phase gets a separate immutable tasks/runtime pair;
do not edit the smoke runtime into the measured runtime after a cell runs.

Required oracle destinations are `oracle/experiments/0234/oracle.js`, its
`fixture_oracle.js` sibling, and `oracle/experiments/0238/f23_precision.py`.
The first full-check probe omitted fixture_oracle.js and correctly exposed an
invalid staging setup; preserve that failure rather than calling it product
quality. Do not place oracle, gold or calibration overlays under public or
participant source. Before model dispatch, run separately named model-free
prepare/check cells against the selected staged runtime, using the positive,
no-op and deleted-product cases from full_check_probe.py. That historical probe
creates its own control tree and cannot certify the selected staged control.
H/P installation smoke must
check installed `_shared/peer.py` and sibling platform-support.py hashes against
the selected review/package manifest, not merely confirm archive membership.

## Smallest useful authenticated native sequence

Two short H owner cells are the minimum for helper mechanics: each real owner
launches its own CLI as an independent peer, once fresh and once resumed. Four
short cells additionally cover both cross-engine inherited environments used by
P. Recommended serial order is H/Claude, H/Codex, P/Claude, P/Codex; these are
operational tests, not efficacy observations. Preserve failed cells and give any
retry a new cell identity.

| Owner/arm | Peer root | Native work explicitly exercised |
| --- | --- | --- |
| Claude/H | Claude Opus 5.5 / max | Nested noninteractive new plus resume in actual owner tool environment |
| Codex/H | Astra / max | New plus resume; one permitted Sol/high native child in first peer turn |
| Claude/P | Astra / max | Cross-engine new plus resume; one permitted Sol/high native child |
| Codex/P | Claude Opus 5.5 / max | Cross-engine new plus resume with restricted Read/Grep/Glob |

Use exact IDs from the registered routes, not these display names. The owner
continues to use its registered native-child policy. Ask the Codex peer to use
one native child for a tiny read-only fact check; do not permit that child to
become a substitute independent primary peer. Claude peers cannot spawn a
child under their registered three-tool capability.

Build a separate smoke-task JSON using the unchanged S2 source/schema/public
checks and a caller request that explicitly instructs the owner to exercise the
helper. S2 is cheap and already has verified source/delivery setup. After its
small implementation and checks, require two awaited helper turns over the
same stable source, original request first, with role header: read-only peer,
no implementation, delivery or recursive independent review. The resume asks
for the earlier fact and a short confirmation of the visible contract. Such
forced activation validates transport only; its cost and behavior cannot be
reported as automatic trigger efficacy. A/B/S and easy-negative efficacy cells
must retain their normal requests.

For the Claude/H startup observation, report only whether CLAUDECODE is present
before launching the peer; do not dump environment variables and do not remove
or change that marker. The pinned offline probe already showed no nested guard
refusal without credentials; the authenticated owner cell must now prove the
actual model, effort, native session persistence and resumed usage.

Freeze each smoke task, order and raw output destination before calls. Register
all four native primary/child routes in the normal task table, and use the
installed helper via the guide's path. The usual command is:

```sh
python3 -B autoresearch/experiments/0238/runner.py run \
  /absolute/path/to/runtime-smoke.json <fresh-cell-name> <smoke-task-id> H claude
```

Use each row's arm/config for subsequent calls. Do not call prepare first with
the same name: run deliberately rejects an existing cell. Separate model-free
prepare probes need separate names.

## Evidence required before comparison

Record whole owner wall and all root/child/peer/resume token usage; no peer cost
is a research-only subtraction. Every actual model/effort must match registered
native evidence; each resume must have its own native evidence, and every
attempt/capture must be retained. Require COMPLETE usage, clean teardown,
unchanged input/config seals, and an exact saved answer path. Wrong route,
missing usage or malformed telemetry stops registration. The reviewed v5
guard checks interrupted inference with no terminal usage carrier even
when the inherited recorder labels the aggregate COMPLETE. Preserve reported
lower bounds plus UNKNOWN residual; an accounting STOP is not a product-quality
failure. Fully accounted failed attempts and recovery remain visible and must
stay distinguishable. Retain the actual d01 negative evidence and successful
controls bound by the v5 review before native pair calls.

Check Codex native read-only/never-approve context, child ancestry and full trace
counters; check Claude native message effort/timestamps and every result
snapshot. Inspect actual Claude owner startup skills/plugins/MCP catalogs and
native request evidence for installed instructions; do not reuse old B catalog
expectations for modified H/P packages. These native smokes do not replace
phase=measured catalog expectations. Known capability asymmetry remains:
Claude has Read/Grep/Glob, Codex has native read-only tools/children.

## Supported authentication lifecycle

Runner.preflight calls the inherited snapshot_auth. It reads the host Claude
keychain privately, refuses less than **6300 seconds** of token lifetime,
copies host Claude/Codex authentication into the private auth directory, then
checks the Claude profile's account/organization fingerprints. Each cell mounts
an isolated Claude credential copy and the Codex auth snapshot; teardown removes
the per-cell credential directory. Never print keychain output or auth files.

If the margin actually blocks, retain the not-dispatched reason and use the
host CLI's normal supported login/refresh flow (interactive `/login`, or its
supported auth login command). Verify the installed help when selecting that
flow. If interactive sign-in is necessary, that is the concrete external step
requiring the user; do not fabricate refresh timestamps or silently switch
accounts. Rerun the same unchanged preflight after the normal login refresh;
if account fingerprints differ, stop and resolve the account mismatch. Never
lower MIN_TOKEN_SECONDS, edit expiresAt, use stale copied credentials, disable
the profile check or inject a substitute API key to pass the gate. A host auth
refresh is not a model test and has no product-quality verdict. This plan does
not perform it in anticipation of a hypothetical expiry.
