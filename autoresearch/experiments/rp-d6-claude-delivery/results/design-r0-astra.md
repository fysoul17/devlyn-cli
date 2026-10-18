The managed-block clarification is the right first rung under **No workaround / No overengineering**. Claude’s smoke report postpones reading `task-completion.md` until the user requests delivery, so changing only that reference may never reach the refusal decision. Removing default delivery would contradict the owner’s decision.

The draft needs these revisions:

1. **HIGH — ADOPT can accept harmful or regressive outcomes.**  
   [DESIGN.md:100](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d6/autoresearch/experiments/rp-d6-claude-delivery/DESIGN.md:100) permits Y=3/4 even if its fourth run damages user files. Aggregation also hides task regression: X succeeds twice on BV and never on Z0; Y succeeds once on BV and twice on Z0.

   Add the independent [0232 §6 requirements](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d6/autoresearch/iterations/0232-harness-ladder.md:148): no false completion, scope violation, user-data harm or severe regression; no decrease in any task’s completion count or check/oracle-row pass count. Evaluate safety failures before favorable outcome labels. Report-completeness scoring can remain excluded, but retain a narrow false-completion check. **Worldclass / Production ready.**

2. **MEDIUM — Stronger authorization needs boundary guards.**  
   The owner authorizes default PR+merge; another confirmation is unnecessary. However, “standing request” must remain **default/implicit delivery**, preserving [task-completion.md:11](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d6/config/skills/_shared/task-completion.md:11):

   - “Don’t push” prevents publication; “just edit” prevents delivery.
   - Bare “commit” stays local; a PR request stops at the PR.
   - No GitHub origin means implicit delivery uses `LOCAL_ONLY`; it does not authorize creating a remote.
   - Authentication/network failures do not activate that fallback.

   Add bounded Claude-high Y guards for no-push, bare commit and missing origin before adoption. Current unrestricted Y guards do not test these boundaries. Preserve project-policy precedence in the wording.

3. **MEDIUM — `NO PROBLEM` overstates four observations and masks possible improvement.**  
   [DESIGN.md:98](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d6/autoresearch/experiments/rp-d6-claude-delivery/DESIGN.md:98) calls a 1/4 observed failure rate “rare” and prevents considering X=3/4, Y=4/4.

   Prefer **NO FAILURE OBSERVED: X=4/4**, allowing 3→4 through the normal gates. Alternatively, retain ≥3/4 as a conservative routing choice, name it **BASELINE ABOVE TARGET**, and delete the rarity claim.

   Correct the statistical example: **3/4 versus 0/4 gives paired one-sided exact p=0.125**, without pairing-dependent variation. Some currently eligible patterns give p=0.5. Publish paired outcomes and retain the small-sample routing interpretation.

4. **MEDIUM — Separate the cost populations and narrow the guard claim.**  
   [DESIGN.md:85](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d6/autoresearch/experiments/rp-d6-claude-delivery/DESIGN.md:85) should explicitly sum each arm’s **four measured Claude-high slots**, including failures, children, repairs, retries and resumed sessions. Divide by that arm’s delivery passes. Report smoke and guards separately.

   The three independent cost inequalities and zero-success dominance rule correctly follow §6. `Y>X` already supplies strict improvement. UNKNOWN accounting must remain STOP.

   Y-only Codex and Claude-max guards establish observed delivery outcomes, not comparative behavior or cost nonregression. Narrow the question accordingly.

5. **MEDIUM — The root cause is plausible, not established.**  
   The evidence establishes that both instructions arrived and Claude reported missing authorization. It does not establish the internal weighing asserted in [DESIGN.md:19](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d6/autoresearch/experiments/rp-d6-claude-delivery/DESIGN.md:19).

   Label the why-chain a hypothesis. Also distinguish o08: it interpreted the apparatus prompt’s Git/upstream restrictions as publication limits. Keeping `common.txt` unchanged preserves attribution, but results apply to that known ambiguous prompt. Do not simultaneously delete its wording and change the product treatment. **No guesswork.**

The remaining measurement choices are sound: verified 4.2.22 control, narrowly patched Y, counterbalanced pairs, Claude-high primary, no replacement of measured slots, and smoke qualifying apparatus rather than selecting for successful delivery. The frozen-cache spare binding addresses rp-d5’s actual staging failure.

Concrete candidate wording:

> - Delivery — direct work edits this checkout. Standing user request: deliver completed, verified requests with changes by project policy (default: commit, push, PR, merge), per `_shared/task-completion.md` in `.claude/skills/` or `.agents/skills/` (project, else `~`). Explicit limits win; commit alone stays local. Isolate before editing with concurrent writers; on unexplained changes, pause writes until safe or isolated. Ideate drains deliver every task.

Fund it by deleting only redundant framing: remove “This contract serves one goal:” and capitalize “Any”; remove “Seven rules govern every change.” Both obligations remain stated elsewhere.

**Token-gate status: unverified.** That complete template changes from **4,049 to 3,997 bytes**, but bytes do not prove token savings. Claude counting was unavailable because credential lookup failed; the local o200k vocabulary was unavailable. Before freezing, count both complete **rendered installed blocks**, including the precedence sentence and hash markers added by [managedBlock()](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d6/bin/instructions.js:16). Require both actual counts ≤ baseline; do not substitute template-only or byte counts.

VERDICT: REVISE
