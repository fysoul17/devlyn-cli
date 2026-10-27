Read-only design question for devlyn-cli research. Do not edit any file. Answer independently; another reviewer answers the same question in parallel.

## Goal (owner, 2026-10-27)
Reduce Claude's false completions: a final report that makes a specific mechanism or guarantee claim which an ordinary trigger falsifies on the cell's own tree (judgment line "0233 m24"). Codex shows almost none; Claude shows them in every arm, including bare (no devlyn package).

## Evidence (repository /Users/aipalm/Documents/GitHub/devlyn-cli; read `git show origin/main:<path>` — the checkout itself is behind origin/main)
- `autoresearch/DECISIONS.md`, entries for 0233–0236 and 0256–0260.
- `autoresearch/experiments/0257/RESULT.md` (bare vs package: false completions B 10 vs A 12, all D4 timeout-bound claims and I0185 first-install cleanup), `0259/RESULT.md` + `0259/erratum-1.md`, `0260/RESULT.md` (F10: twelve process-boundary claims across both arms, plus non-object JSON and a dropped final `--`).
- Owner reports and end trees (without node_modules/.git) for every cell of 0256–0260: `/Users/aipalm/.local/share/nx01/archive/reports-0256-0260/<experiment>/<cell>/final.txt` and `.../snapshot/`. Examples: 0260 `c012-F10-claude-B-r6` and `c007-F10-claude-C-r4` (false completions: "One server process per file" / "One server process only" while the queue is per `createApp` instance), `c005-F10-claude-B-r3` (judged coverage because it says "per-app queue", though it also says "within one Node process").
- The canonical principles text: `CLAUDE.md` (same block ships in AGENTS.md and `config/skills/_shared/runtime-principles.md`).

## Owner constraints (binding)
- Harness ladder: instruction-only first; one mechanism at a time; keep it only if it improves wall time, quality, efficiency or tokens and worsens none; tokens must not increase.
- Owner preferred one appended sentence over a rewrite (2026-10-08). Already rejected: 0235's sentence appended to the definition of done (D4 false completions persisted), 0236's findings-repair turn (cost), 0234's pair method (no gain at 2.3–3.5× input). One-rule deletion ablations 0258–0260 moved nothing.

## Answer (under 600 words)
1. Root cause: why does Claude write claims broader than what it exercised? Cite cells.
2. One candidate: exact wording and exact location, and the predicted effect on false completions, completions and tokens. Say whether it changes the code defect or only the report's claim, and whether that difference matters to the user.
3. Measurement sketch: arms, tasks (F10, D4, others?), replicates, primary endpoint, guards (completion, tokens), and how to tell a real improvement from a wording-only change in what the audit counts (e.g. also count witnessed defects regardless of wording).
4. The main risk that would make the result uninterpretable.
End with one line: `PROPOSAL: <one-sentence summary>`.
