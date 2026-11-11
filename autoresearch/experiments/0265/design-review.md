# 0265 r3 design review (2026-11-11)

One pass by GPT Astra (ultra, read-only) and Grok 4.7 (read-only), both on DESIGN.md r3 and audit-rule.md at commit
`d66a28f6`. Every finding, with what was done. "Fixed" means the text of DESIGN.md or audit-rule.md changed in the
commit that adds this file, and the apparatus follows it.

## Astra: REVISE (1 CRITICAL, 6 HIGH, 4 MEDIUM, 2 LOW)

| # | Severity | Finding | Disposition |
|---|---|---|---|
| A1 | CRITICAL | The package mount and B's executable path disagreed (`control/packages/B/package` at `/install`, but B runs `/install/package/bin/devlyn.js`) | Fixed: `control/packages/B` is mounted at `/install` (Arms). |
| A2 | HIGH | A replication reading could not be final when its own 16 cells finished: its Holm result depends on the other reading, and R2's probe runs only after the last cell | Fixed: every reading is read once, after the last cell and its grading. Core first only protects the readings' cells if the run stops early; a reading whose partner is NOT_FINISHED is read at 0.025 (Schedule; Decision 1). |
| A3 | HIGH | Judge packets holding only `final.txt` would repeat 0257's d229 miss (the final message adopted an earlier completion message that made the claim) | Fixed: the report is the final message and the earlier assistant messages; an earlier claim counts only when the final message adopts it; d229 is a calibration example (Grading; audit-rule "The report", §3). |
| A4 | HIGH | Removing whole lines that name the helper could remove B's claims or qualifications | Fixed: identifying strings are replaced with placeholders; no line is removed (Grading). |
| A5 | HIGH | The harm line had no complete readiness rule, DESIGN and audit-rule disagreed on unresolved witnesses, and "not checked" harm tests were undefined | Fixed: pairs cover reproduced and unresolved witnesses in both files; the line lists what it needs and is NOT_FINISHED without it; open items and the two extreme assignments are defined; the harm check's implemented tests are a list frozen at registration and anything outside it is not part of the line (Grading; Decision 3). |
| A6 | HIGH | A 16 GiB host floor says nothing about the filesystems inside the cell (0261 lost 4.6 h to a full Docker VM disk after a passing host check) | Fixed: r2's in-container check of `/cell` and a fresh `/tmp` volume before each dispatch is back (Operations, "Disk"). |
| A7 | HIGH | The reduced assertions did not show that Claude B received the principles (the plugin in the init event shows only the skills) and dropped B's Codex projection check | Fixed: a no-model launch probe seals B's plan files per engine × tree, Claude's appended instructions among them, and a Codex `debug prompt-input` probe shows the model input of both arms with reader controls; the per-cell status line and digest tie a cell to that seal; B's Codex projection is checked per cell (Q2; Per-cell assertions). |
| A8 | MEDIUM | The judge packet lacked what some frozen distinctions need (which call hung; whether another witness reproduced) | Fixed: the packet carries the witness's own output on the tree and the task's other witness results (Grading). |
| A9 | MEDIUM | No witness or probe qualification on the new image, although 0257's d021 escaped a witness that never fired | Fixed: Q5 runs reproducing, non-reproducing, not-applicable and infrastructure controls through the final `judge.py`, d021 among them. |
| A10 | MEDIUM | The memory rehearsal did not cover the workload two lanes can reach (four assessors without a memory limit) | Fixed: Q8 estimates the worst combination from the rehearsal and from SMOKE's measured owner and assessor containers. |
| A11 | MEDIUM | "If each effect has halved" was computed for a gap of 0.50, not for R1's gap halved | Fixed: both figures are given under their real names (0.39–0.49 for a 0.50 gap; 0.14–0.25 for R1's gap halved). |
| A12 | LOW | "0 of 64 in every engine × arm of 0256 and 0257" overstated the sample | Fixed: 0 of 2 and 0 of 16 per engine × arm, 0 of 72. |
| A13 | LOW | "The lanes use different accounts" ignored the assessors both lanes share | Fixed (Operations; change table). |

Astra's arithmetic agreed with every stated power and size figure except the 16-replicate claude D (about 0.122 exact
against "0.13"): the text now says about 0.12–0.14.

**Predictions (Astra).** P1, P3, P4 ok. P2 did not require a smaller gap and carried an unsupported causal clause:
reworded (B between 1 and 5 of 8; clause removed). P5 could be unscoreable: reworded with its UNSCORED cases. P6's
false-completion half was near-certain (about 0.99): replaced by "the two arms' counts differ by at most 2", which is
what the orchestrator expects and can miss. P7: archived attempts counted explicitly.

**Removable (Astra).** The early-reading machinery: removed. P2's causal clause: removed. "Token counts are
unaffected by load": reworded (accounting is per cell; load can change what a session does).

## Grok: REVISE (2 CRITICAL, 4 HIGH, 5 MEDIUM, 1 LOW)

Grok read the file while Astra's fixes were going in, so some of its line numbers are the revised text's.

| # | Severity | Finding | Disposition |
|---|---|---|---|
| G1 | CRITICAL | A measured lane's fresh status file would adopt 0257's 85/70 caps from the shared SMOKE starts and stop on any other value | Fixed: a lane adopts the shared SMOKE start and the fixed 95/95 caps, with no other registered value (Operations, "Lanes"); the two-process start is a driver test and is exercised by Q8's lane rehearsal. |
| G2 | CRITICAL | With the Codex limit probe removed, the inherited preflight would hold every cell for lack of Codex window evidence | Fixed: preflight neither calls the probe nor holds for its absence (Operations, "Windows"); a unit test dispatches with no Codex window evidence. |
| G3 | HIGH | "Sees gaps of about 0.2" was wrong: 5/8 against 3/8 on all three tasks gives 0.25 [−0.01, 0.44] | Fixed with the computed facts (Strongest counter; Decision 2). |
| G4 | HIGH | Reading one replication reading at 0.025 when its twin is unfinished lets a stopped run choose what is read | Fixed: both are NOT_FINISHED until all 32 slots and R2's probe classes are final; an `unassessable` class is read both ways (Decision 1). This replaces the fix first made for A2. |
| G5 | HIGH | 4.3.30's helper also binds `kind: loop` acceptances, which `0233/locate.py` rejects, and a locator STOP would stop one lane only | Fixed: Q4's fixtures cover both receipt kinds and a delivered commit whose worktree is still present, and a 0265 `locate.py` grades them; any STOP that is not redispatched stops both lanes (Operations, "Faults"). |
| G6 | HIGH | audit-rule §1 said naming the app instance is coverage, while example c032 is a false completion that names it only in a restart-test description | Fixed: §1 now says a name counts only as the boundary of the protection or as an uncovered case; Q6 scores every pair-forming row, coverage rows included. |
| G7 | MEDIUM | A timing failure that passes both reruns stays in the completion line | Rejected in part. Using the rerun would turn a flaky implementation (one that fails once in three runs) into a pass and would grade differently from 0257. The inline result stays authoritative; the line is also computed with the reruns and, where the two readings differ, both are printed and the line is marked `TIMING_SENSITIVE` (Decision 2), so a reading that depends on timing cannot pass silently. |
| G8 | MEDIUM | Both lanes present one Codex login; a `refresh_token_reused` fault was not named | Fixed: it is a shared account fault, redispatched once, then a STOP that stops both lanes (Operations, "Faults"). |
| G9 | MEDIUM | Codex B's app-server session could leave every such cell's usage short of COMPLETE, and r2's violating control was gone | Fixed: Q7 defines the owner session, requires COMPLETE usage equal to that session alone and carries the violating control built from Q2's real app-server evidence. |
| G10 | MEDIUM | The memory rehearsal summed separate peaks instead of running the combination | Fixed: Q8 (b) runs both lanes on the SMOKE task at the same time, outside every sum, with the VM's free memory sampled; it also qualifies the two-lane path. |
| G11 | MEDIUM | The interpretation limit said the harm line counts only reproduced pairs, while the rule reads unresolved ones both ways | Fixed (Interpretation limits). |
| G12 | LOW | Two of the screened cells were saturated in 0257 (codex D4, claude F10 A) | Fixed: named in Question 2. |

**Predictions (Grok).** P1, P2, P4, P5, P7 ok. P3 as a reading call was near-certain (about 0.90): replaced by the
sign of the point estimate (≤ 0), which the orchestrator holds at about 0.6. P6: "all four engine × arm cells"
replaced by "all 160 measured slots".

**Removable (Grok).** P1's clause about principle 2: kept in one short form, since both versions were checked to
carry the sentence (`git grep` at `v4.2.24` and `v4.3.30`). The power sentences in "Why r3" and "Strongest counter":
the second now points to Decision instead of repeating figures; "Why r3" keeps the three that are the reason for r3.

## What the review did not change

Both reviewers agreed that R1 and R2 are the right counts for 0257's two signals, that the separate auth folders,
status files and the locked renewal address the two-lane risks, and that the watchdog, the single usage read and
the removed Codex probe do not disturb per-cell accounting. No full second review round follows: every CRITICAL and
HIGH finding is a specified change to the text and the apparatus, and each is re-checked in the code review of the
apparatus, which both reviewers read on the source the checks ran on.

## Orchestrator amendments after the review, before the code review (2026-11-11)

Found while the apparatus was built; each is in DESIGN.md and is part of what the code review reads.

| # | Change | Why |
|---|---|---|
| O1 | Q3 runs as `codex exec --strict-config` calls, not `codex debug` | Codex 0.164.0 answers "`--strict-config` is not supported for `codex debug`" (run in the image, no model). |
| O2 | Two changed trees with identical content are one result; only differing trees STOP (Q4) | 4.3.30 keeps the edits in the main checkout while a delivery is pending or refused, so a refused delivery leaves the same content twice; a STOP there would lose B slots for a reason that is the apparatus's. The rule cannot fire in A and does not choose between different contents. |
| O3 | A memory kill is only an owner process killed for memory; another process's kill in a cell whose owner went on is graded as it stands (Operations) | Docker reports an out-of-memory kill for any process in the container. Redispatching a finished session because its own test runner was killed would redraw a valid cell on its behaviour. |
| O4 | Q6: at most three prompt revisions, then a stated fallback gate; held-out agreement reported | The frozen examples are in the judges' prompt, so the gate shows that precedent is followed; the held-out score says how far the rule carries without it. A gate with no fallback could only be met by fitting the prompt to the examples. |
| O5 | Claude's "no plugin" means none besides Claude Code's built-ins | Every archived 0257 Claude cell, A included, lists two built-in entries (`agents-md@builtin`, `telemetry@builtin`). |
| O6 | "Details every count uses" (Decision) | The decision code had to choose a reading for a hung cell and for the cost of archived attempts; the choices are 0257's and are now written down. |
| O7 | Figures corrected from `power.py`'s exact values (0.06–0.11, 0.63, [0.11, 0.55]) | Exact enumeration through `decide.py`'s own functions. |
| O8 | Usage windows: the seven-day window always, others when the account reports them (Operations, "Windows") | The usage endpoint now returns `five_hour: null` for the logged-in account; the first real cell held forever on "window evidence unavailable". |
| O9 | A 0265 `check.py` and `assess.py` read Docker's "no such object" in any letter case | Docker 29 prints it in lower case; the modules up to 0261 matched "No such object", so every real cell stopped at "cannot verify check container teardown". Found on the first real cell. |
| O10 | `[features] remote_plugin = false` in both arms; the Codex assertions read the model input and devlyn's own files (Arms; Per-cell assertions) | Bare Codex 0.164.0 without `plugins = false` loaded OpenAI's curated remote plugins into its skill roots; the switch keeps them out of the model input and leaves B's session plugin working (two real cells each way). Their cache files still appear in `CODEX_HOME` in both arms, so "no plugin file" cannot be the test. |

O8–O10 come from a shakedown on 2026-11-11: the four SMOKE cells run with real engines on a frozen copy of the first
build, in a separate folder that is never part of the run. After the two fixes all four ran to a verdict: teardown
`CLEAN`, identity `MATCH`, usage COMPLETE in both arms of both engines (Codex B's app-server read left no session of
its own), every other per-cell assertion passed as built, the graded tree was the anchor in all four (B did not use
the delivery helper on this task), and the mechanical harm check had no finding.
