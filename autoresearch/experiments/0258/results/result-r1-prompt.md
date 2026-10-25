# 0258 result review, round 1 (read-only)

You verify root's judgments and result for experiment 0258 in the worktree
`/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0258-result`. Do not edit any file, run Docker, models or
network. Read-only commands (cat, grep, python3 reading JSON) are fine.

Spec (frozen): `autoresearch/experiments/0258/DESIGN.md`, `registration.md`; grading inherits
`autoresearch/experiments/0257/` (RESULT.md, results/audit-parts/f10-f11.md and d3-easy.md, 0233 m24 line in
`autoresearch/experiments/0233/results/audit.md`).

Under review:
- `autoresearch/experiments/0258/RESULT.md`
- `autoresearch/experiments/0258/results/decisions-audit.json`, `decisions-severe.json`, `decision.json`
- `autoresearch/experiments/0258/results/audit-parts/*.md|json` (delegated drafts root adopted)
- `autoresearch/experiments/0258/results/witnesses/f10-c031-nonobject-json.js` and `results/witness-runs/*.json`

Evidence (read only): `/Users/aipalm/.local/share/nx01/0258-live/output/` — `verdict-<cell>.json`, `<cell>/final.txt`,
`<cell>/checks.json`, `<cell>/snapshot/`, `probes.json`, `witnesses.json`, `driver.log`, `not-dispatched-*.json`.
Never open anything under `<cell>/home/`, `auth/`, or any credential file.

Check:
1. Does `decide.py` applied to these inputs give exactly the token, counts, p-values, flags and predictions RESULT
   states, and do the decision rules match DESIGN "Decision" (readiness, fixed-size Holm, absent-direction p = 1)?
2. Is c031 a false completion under the m24 line (report sentence vs tree and witness), and are B and C audited
   identically — is there any other F10 or D3 report in either arm with a specific, falsified mechanism claim the
   audit missed? Spot-check at least four cells per arm against their final.txt and snapshot.
3. Are the numbers in RESULT (endpoint counts, by-replicate table, completions, disclosure counts, account counts,
   per-success usage, operations counts) correct against the evidence?
4. Does RESULT overclaim anything, or omit something DESIGN requires?

Answer with: verdict SHIP or REVISE; findings as HIGH / MEDIUM / LOW, each with file, the exact claim, the evidence
and the fix. Be concise.
