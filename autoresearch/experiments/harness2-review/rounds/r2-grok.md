I'll review the round-2 synthesis against the three round-1 analyses and the files Astra cites, without editing anything.Astra's correction is the load-bearing claim. I'll check the installer, the 0233 writeup, and `prepare.py` against the synthesis before judging the plan.Astra's package correction is true. The plan still misstates the 0233 result, Figure 7, and the round-1 consensus, and steps 1–2 add work the evidence does not justify.

## 1. Misstatements

Verified. `0233` arm A is no install; B and C run that arm's `bin/devlyn.js` (`autoresearch/experiments/0233/prepare.py:53-62`, `:112-113`). B is the 4.2.0 package, and C is B plus one Quick Start line and `failure-paths.md` (`autoresearch/iterations/0233-installed-baseline-and-failure-paths.md:38-42`). The live template is the repo-root `CLAUDE.md` / `AGENTS.md` (`bin/instructions.js:223-225`). `bin/instruction-templates.json` is the legacy migration corpus (`bin/instructions.js:5`, `:299-302`).

The synthesis then goes past the record:

- "All three" do not make the base remeasure the first action (`r2-synthesis.md:5`). Root's first step is a playbook section (`root-independent.md:15`); the remeasure is item 5 (`:19`). Grok's session action is the admission rule; the remeasure is the next registration and is not run (`r1-grok.out:31-33`). Only Astra puts the instruction-only design first (`r1-astra.out:70`).
- Root does not concede form-first in round 1. `root-independent.md:15` still says skill, helper, or hook before prose. The Table 6 warning is Astra's (`r1-astra.out:65`). Grok uses Table 6 to rank the prompt group as the weakest component (`r1-grok.out:15`).
- Figure 7 is a joint ablation: no reference executions, no candidate probes, and no library. Code 73.4→63.2 and Web 69.9→65.0 (`paper/plain.txt:1241-1243`). `r2-synthesis.md:5` keeps one cause and one number.
- The 9/12 and 7/12 figures pool development and confirmation. The registration says panels are never pooled (`0233-installed-baseline-and-failure-paths.md:96`). The gating panel is n=8: Claude bare 4/8, package 2/8; Codex bare 5/8, package 6/8 (`:169-173`). Both package-vs-bare comparisons failed (`:166`). Quality failures decided that, including false completion.
- The hook is not an agreed open design (`r2-synthesis.md:7`). Grok says blocked runs fail the token rule and the hook is a rule change (`r1-grok.out:17`, `:33`). Root calls the always-on token cost zero (`root-independent.md:16`). rp-d8's skips cited unrequested publication (`autoresearch/HANDOFF.md:3`; `r1-astra.out:27`). `--dangerously-bypass-hook-trust` is real (`harness2/substrate/codex.py:167`). "Codex 0.163 reports `hooks stable true`" is not in the round-1 record. The only 0.163 string is the reviewer banner (`r1-astra.err:4`). The installer does remove the retired Stop hook (`bin/devlyn.js:890-903`).
- `0255` accounts for Claude solo arms. Codex uses the inherited runner (`autoresearch/experiments/0255/README.md:3-14`). Step 2 treats that path as shared (`r2-synthesis.md:11`).

## 2. Step 1 is accretion

The retired failure mode is Sections 2–4: `benchmark/auto-resolve/scripts/run-suite.sh` (`autoresearch/playbooks/iteration-loop.md:93-97`), `report.md` / `judge.json` (`:106-127`), and the suite-margin ship gate (`:134-138`). Replacing PROPOSE/ANALYZE with five new rules leaves those commands in place and adds doctrine. No guesswork and No overengineering already require a pre-stated prediction and the smallest change. Rule (e)'s hook clause also answers owner decision B inside a playbook.

Delete the retired runner, report paths, and suite-margin gate. Do not insert the five rules. KEEP_BASE, the contrast, and the confounded verdict belong in the next registration's own decision rule.

## 3. Step 2 is not the smallest decisive measurement

Bare versus the current installed package is the coherent replay. Both are real install states. Block-only is not. The block says the skills are installed beside it and tells the agent to follow `devlyn-ideate`, `task-completion.md`, `devlyn-engines`, and each `SKILL.md` (`CLAUDE.md:3`, `:29-33`). Those files are absent in a block-only cell, so a completion drop is confounded with dangling pointers (`r1-astra.out:17`). `runtime-principles.md` is the inverse document: principles for a context without the block, and it has no Quick Start.

D3/D4/B5 plus an E1 "guard" drops I0185, the task whose witnessed defects failed Codex (`0233-installed-baseline-and-failure-paths.md:179`). E1 was a one-replicate tripwire outside the sum (`:96`, `:146`).

A +3 count bar at n=8 is the bar rp-d8 missed by +2 (`autoresearch/experiments/rp-d8-bookkeeping-note/registration.md:67`; `HANDOFF.md:3`, sign test p=0.25). The gating Codex gap is +1/8. No replicate count puts an expected +1/8 over a +3 bar. The pooled Codex +3/12 is about +2 at n=8, which is the margin that just failed. A normal approximation under the pooled rates gives roughly a 0.3 chance Codex clears +3 and a 0.4 chance Claude clears −3 at n=8, joint about one in eight. n=24 is the first size where both pooled tails are likely, and that spends confirmation tasks the rule forbids pooling. The decisive 0233 fact is the quality fail, so the replay keeps D3, D4, I0185, and B5, two replicates, the false-completion and witness rule, and E1 outside the sum.

PR+merge is not a shared endpoint. Bare does not open a PR. `0233` used a local origin and graded `LOCAL_ONLY` (`0233-installed-baseline-and-failure-paths.md:86`).

## 4. Owner list

Keep one spend decision: whether to run that two-arm quality replay, and the shared local endpoint that makes bare and package the same graded outcome.

Reframe B. The owner either changes the token rule so a blocked run may spend tokens, or the hook stays closed. 4.2.23 adopted per-delivery cost for a prose edit (`registration.md:69`). It does not price hook retries.

Drop C and the block-only payload from this session. An agent can leave rp-d4 unscheduled; the owner decides only whether a below-threshold helper change ships. An agent also keeps `CLAUDE.md` identical to `AGENTS.md`, does not pool panels, and does not reopen the definition-of-done line (`autoresearch/iterations/0235-definition-of-done.md:82`).

## 5. Missed lever

The repeated false completion is a mechanical check, which is harness2's script lever: check the deliverable, because a successful write does not show it works (`harness2/core/prompts.py:355-356`, `:364-365`). `0233` d09 and d36 were false completions (`0233-installed-baseline-and-failure-paths.md:177-181`). In `0235`, both amended D4 cells claimed a FIFO bound while `read` ran on the main thread before the helper (`0235-definition-of-done.md:82-91`). That line of prose is closed. A delivery Stop hook addresses a different failure, the 15–76% helper bypass. Record the d09 moment. Do not add a checker in this session.

Required changes: correct the five evidence points above; delete the retired playbook runner and ship gate and add no five-rule text; draft two arms, bare versus the current package, on D3/D4/I0185/B5 with the quality rule, E1 outside the sum, and a shared local endpoint; ask the owner only to authorize that replay and, separately, whether the token rule may price a blocked run.

REVISE
