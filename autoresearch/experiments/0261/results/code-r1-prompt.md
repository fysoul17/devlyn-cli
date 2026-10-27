Read-only code review of a devlyn-cli research apparatus before any live run. Do not edit any file.

Worktree: /Users/aipalm/Documents/GitHub/.devlyn-worktrees/devlyn-cli/0261-registration. New, uncommitted folder `autoresearch/experiments/0261/` built from 0260's apparatus (`autoresearch/experiments/0260/`, committed). The frozen spec is `autoresearch/experiments/0261/DESIGN.md` (reviewed by you over three rounds; SHIP). The implementation brief: /private/tmp/claude-501/-Users-aipalm-Documents-GitHub-devlyn-cli/39734701-88f7-45dd-bd5a-f5397ef89eed/scratchpad/codex-0261-brief.md. README.md in 0261 lists every deviation from 0260.

Check that the code implements DESIGN exactly and safely, focusing on what decides the result:
- `control.py` edit (exact sentence, anchor once, refusals) and `instructions.py` package-diff/baseline checks (no `prior_runtime` reads remain; null hashes block).
- `generate_cells.py`/`cells.tsv` schedule (D4 then F10 per replicate, BC odd / CB even, 16 per arm).
- witnesses: applicability exit 3 and setup exit 2 added without changing reproduction logic (diff each against its origin file in 0256/0257/0260 `results/witnesses/`); `judge.py` limits (D4 300 s, F10 30 s), exit handling, pass agreement.
- `blind.py`: what enters a packet, redaction, exclusions (never `home/`, `auth/`, credentials), label-map write-once.
- `decide.py`: readiness (incl. COMPLETE usage, zero ΣB), one outcome per slot across attempts, P (one-sided Fisher), G1–G4 margins and per-task logic, G3 arithmetic R and the printed bound, headline order, flags, token, predictions, disputed-assignment enumeration.
Run `python3 -m pytest -q autoresearch/experiments/0261` if you can.

Report HIGH / MEDIUM / LOW with file:line and a concrete fix, under 600 words. End with exactly one line: `VERDICT: SHIP` or `VERDICT: REVISE`.
