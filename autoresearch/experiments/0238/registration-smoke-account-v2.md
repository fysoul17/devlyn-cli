# 0238 native transport account binding addendum

2026-10-10, before any 0238 inference. The user explicitly chose to switch
accounts and then confirmed the new login. The profile check confirms a different
account and 21,008 seconds of remaining token lifetime, above the unchanged 6,300
second requirement. Keep old account fingerprints, runtime, freeze and the
not-dispatched rejection intact. No completed or attempted model cell is replaced.

Use the new private runtime `staged-v1/runtime-smoke-v2.json`, SHA256
636fca16d1394b6490ed68d2581377ca2844e9b1e8e28f3191625f5d001d98cf.
Only account fingerprints and new auth/scratch/output directories differ from
runtime-smoke.json. All package, task, source, control, prompt, model, effort,
tool, watchdog, init, quota, identity and accounting conditions remain fixed.
The actual selected-runtime controls still apply: their checked inputs and
evaluator are identical. Their results are retained, not rerun or relabeled.

Replace the unstarted transport identities with this prospective serial order:

1. s01-h-claude-v2: S2, H, Claude.
2. s02-h-codex-v2: S2, H, Codex.
3. s03-p-claude-v2: S2, P, Claude.
4. s04-p-codex-v2: S2, P, Codex.

All acceptance and stop rules in registration-smoke.md apply. Bind the new
runtime and this addendum in freeze-smoke-v2.json before dispatch. Authentication
still checks the selected account before every call. This explicit pre-inference
account selection does not pool previous-account results into a new comparison.
