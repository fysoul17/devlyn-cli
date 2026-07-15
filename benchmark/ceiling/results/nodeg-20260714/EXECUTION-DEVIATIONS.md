# nodeg-20260714 execution deviations (honest record)

Runner-sha freeze: e94ad57 throughout. Three-phase execution due to two
environment hazards, NOT treatment changes.

## Phase 1 (2026-07-14 ~14:00-16:20) — attempts, partial
F7 (14:40), F25 (15:27), FS1 (16:18) completed on Claude Code **2.1.208**.
F23/F11/F12/F26 hit sonnet usage-limit `api_error` (6s exits, empty
patches). Their empty-patch A1 dirs preserved as
`A1-apierror-usage-limit-20260714T1620`. A stray judge pass over the empty
F11/F26 patches was quarantined as `nodeg-judge-STALE-...apierror-empty-patch-judge`.

## Phase 2 (2026-07-14 ~18:30-21:10, after usage reset) — 4 rows re-run
F26 (19:08), F11 (19:38), F12 (20:18), F23 (21:06) completed on Claude Code
**2.1.209** (CLI auto-updated from 2.1.208 between 16:18 and 19:08).
F25 arm recorded exit 1 but objective resolved=True (transcript truncation,
patch valid) — KEEP. Judge phase then fail-closed at the A-arm CLI identity
guard (nodeg-cell.py:837): A attempts spanned 2.1.208 (3) + 2.1.209 (4).

## Phase 3 (2026-07-15 ~09:00) — CLI homogenization
The identity guard is load-bearing (iter-0068 confound regime; NOT weakened).
Minimal fix: re-run the 3 minority (2.1.208) rows F7/F25/FS1 on 2.1.209,
**pinned** via `CEILING_TEST_CLAUDE_BIN=/Users/aipalm/.local/share/claude/versions/2.1.209`
so mid-run auto-update cannot re-drift. Their phase-1 A1 + reused judge dirs
quarantined as `...-STALE-20260714-cli-2.1.208-preupdate`. All 7 A attempts
now attest 2.1.209; judge runs fresh on all 7.

## Lesson (recorded as pyx correction)
Long multi-hour ceiling/nodeg cohorts are vulnerable to (a) harness
background-task kills — run detached (nohup+disown, launchd-parented), and
(b) Claude Code CLI auto-update mid-cohort → identity-drift fail-closed —
pin CEILING_TEST_CLAUDE_BIN to a versioned binary from the FIRST launch.

## Phase 3 note — F25 re-run timed out (objective preserved)
F25 on the 2.1.209 re-run hit the 3600s wall cap (exit 124, timed_out=True)
vs 2801s in phase 1. Objective resolved=True (patch.diff 9290 bytes valid —
work completed, process did not exit before the cap). Wall for F25 is thus
CENSORED at 3602s (true elapsed ≥ cap); F25 already exceeded the 3.0 wall
cap in the frozen baseline, so the row's wall PASS/FAIL is unchanged.
Likely fix-loop-round variance across the two runs, not a CLI regression;
recorded, not tuned.

## Post-verdict cleanup (2026-07-15)
After the verdict committed, the local diagnostic quarantine husks
(`A1-STALE-20260714-cli-2.1.208-preupdate`, `A1-apierror-usage-limit-20260714T1620`,
`nodeg-judge-STALE-*`) and dangling `A1/latest` symlinks were pruned to keep
the benchmark tree clean. The retained, committed evidence is the canonical
2.1.209 A1 trail (patch.diff / timing.json / objective.json / isolation),
the fresh judge dirs, nodeg-verdict.json, deviations.json, and this record.
