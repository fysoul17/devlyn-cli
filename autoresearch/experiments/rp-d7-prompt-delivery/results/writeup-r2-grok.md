# rp-d7 write-up review r2 — Grok 4.7

I'll review the write-up against the round-1 findings and the measured evidence, without editing anything or running the experiment.Round-1 notes are in. I’ll check the rewritten claims against DESIGN and the measured files, including the new route-watch wording.Round 1 is fixed except the route-watcher aliveness claim. Astra’s four items and Grok’s causal, Stop-candidate, and rounding items match the evidence. Grok’s route fix does not: the unsupported clock times are gone, and a new unsupported process check replaces them.

**MEDIUM.** `results.md` says the route-watcher process was still running when checked at 12:18:48Z, and from that that no default-route change was logged across the run. `12:18:48Z` is not in `route-watch.log`, `rp-schedule.json`, the smoke schedule, the verdicts, the reviews, the census, or `repository-deletion.txt`. The log is change-only and its last line is `2026-10-18T11:05:09Z` returning to `en0`. A missing later line does not show the watcher was alive through the smoke PR (`11:47:44Z`), the latest m04 census time (`11:56:06Z`), or the deletion check (`12:07:31Z`). “Before exposure” is also not a recorded start time.

Fix: delete the 12:18:48Z sentence. Say the log’s last line is the 11:05:09Z return to `en0`, with no later line to show the watcher was still alive. Keep the four drops to `none` (08:32:32Z, 08:36:28Z, 10:25:54Z, 11:04:19Z), each returning to `en0`, and place them before the smoke PR.

**LOW.** “Reason 3 has now appeared in four skip reports (rp-d6 m05, m08, g06; rp-d7 m04)” counts g06 as a skip. In rp-d6, g06 is the failed no-origin guard. m05’s tag-3 phrase is “limited my edits”; the helper worktree and `.devlyn/` objection is m08 and g06.

Fix: “Tag 3 also covers rp-d6 m05 (“limited my edits”), m08, and the g06 guard; rp-d7 m04 is the fourth report.”

Checked against DESIGN’s ordered rules and the measured files: rule 5 is MIXED (one skip; rules 1–4 do not match). `final: false` and pending `m04:tags` are the summarizer’s response to an unset skip tag set. Astra’s tags are `1` and `3`; Grok’s are `1`, `3`, and `none` for the `base_sha` comparison; the frozen rule publishes that disagreement as unset. The prediction quote matches DESIGN; the first clause is true and the second is unscored. Displayed costs match the unrounded evidence under the stated rounding, including rp-d6’s 6,526.5. The three m04 quotations match `m04-final.txt`. Cleanup is past tense for six repositories at HTTP 404, with archive receipts on the five used slots, and future tense for credentials, snapshots, and the image. No secret, VPN hostname, or IP in the write-up or the rp-d7 handoff text.

VERDICT: REVISE
