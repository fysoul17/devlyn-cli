# Core harness improvement — 0202 adopted; 3.2.0 release

2026-09-21 KST. User explicitly authorized main merge, branch/worktree cleanup
and npm release after reviewing the source-only verification limits. Root direct;
**no resolve, including controls**. PR80 merged as `ca33b00`; release target3.2.0.
Retained checkout: `/Users/aipalm/.local/share/nx01/core-continuation-20260912`.
Candidate branch `candidate/0202-owner-run-harness` is merged and cleaned.
Read [0202](iterations/0202-owner-run-candidate.md) for implemented behavior and
[0201](iterations/0201-harness-transformation-plan.md) for the finite product plan.

0125 BUILD removal has been ported (separate checkpoint2a2622e). Owner PLAN and
command-only CLEANUP are implemented; code/doc cleanup stays inside selected
IMPLEMENT. Independent VERIFY, scope, engine pins and failure evidence remain.
Evidence/status: `.devlyn/0202/FINAL.md`; completion receipt
`.git/devlyn-completion/0f83292ed2e8bf465628e33f/receipt.json`.

Next: actual candidate invocation conformance, including selected-worker cleanup
and repair→BUILD→fresh VERIFY. Fixture tests are not a model trace. Then register
0201's A/B/C tasks, whole-call/usage/time budgets and measurement before running
comparisons; the24/48 ceilings are not an automatic spending authorization.
Do not replace this milestone with open-ended small-defect research.

0200/0199/0198 are closed;0187 NO-GO, exposed0197–0200 tasks, A16 and frozen
results stay unchanged. Both0198 branch witnesses remain required for future R1
validation. Mission1, untouched confirmation and field gate15 remain OPEN.
Adoption is user-authorized; live-call conformance and comparative effectiveness
remain unproven and must not be claimed from fixture/CI results. Preserve
original checkout WIP and all source/Git/restart evidence. Installer PR73 is OPEN;
the installer worktree hosts the current live session and must remain until it
yields. Release status/evidence: `.devlyn/release-3.2.0/FINAL.md`.
