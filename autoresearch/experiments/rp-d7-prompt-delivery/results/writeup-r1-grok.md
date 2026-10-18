# rp-d7 write-up review r1 — Grok 4.7

I'll review the write-up against the design rules and the measured evidence only, without editing files or running anything.The write-up and summary are loaded. Next I’ll check the design rules, registration, and the measured evidence those numbers come from.The MIXED label, the prediction score, the m04 quotes, and the 3/4 versus 2/4 comparison follow the frozen rules and the measured files. Three places overclaim or cite times the evidence does not record.

**MEDIUM.** The route paragraph states times that are not in the measured evidence. `results.md` says smoke started at 11:46Z and the measured slots ended at 11:57Z. Neither timestamp appears in `route-watch.log`, `rp-schedule.json`, the verdicts, or the smoke schedule. The log is change-only and its last line is `2026-10-18T11:05:09Z` returning to `en0`, so a missing later line does not show that the watcher was still running through the deletion check. Recorded bounds that do exist: smoke PR created `2026-10-18T11:47:44Z`; latest measured repository timestamp in the m04 census is `2026-10-18T11:56:06Z`; deletion check `2026-10-18T12:07:31Z`. The drop lines in that window are `default-route interface: none` (08:32:32Z, 08:36:28Z, 10:25:54Z, 11:04:19Z), each returning to `en0`.

Fix: replace the 11:46Z / 11:57Z sentence with those recorded bounds, and say the log’s last line is the 11:05:09Z return to `en0`, with no later line to show the watcher was still alive. Call the earlier events drops to `none`.

**MEDIUM.** “Removing the two sentences did not remove the skip” treats the screen as a causal test. DESIGN says this run is a routing screen, not a causal test, and that the tags record stated rationales. P1 still had one skip (m04); rp-d6 X, an earlier run on the full prompt, had two. Fisher p = 0.5 is already labeled as not a contemporaneous control.

Fix: “A skip still occurred on P1 (1 of 4). rp-d6 X, earlier and on the full prompt, had 2 of 4.”

**MEDIUM.** The Stop candidate goes past the evidence. “Real direct requests rarely carry an allowed-file list” and “The residual skip needs a task contract like `caller.json`” are not measured. DESIGN kept `caller.json` in every request; m04’s report cited that contract. The screen does not show that the skip requires it, or how often real requests carry such a list.

Fix: “Stop. Claude `high` delivered 3/4 without the two sentences, and BV was 4/4 across rp-d6 X and this run on 4.2.22. The remaining report cited the task contract’s allowed files; a request without that contract was not run.”

**LOW.** Rounding is not stated, and the rp-d6 output-per-delivery cell does not match the reference. `summary.json` has `13053/2` = 6,526.5, and rp-d6 `results.md` prints 6,526.5. This write-up prints 6,527. The other displayed figures match half-up to 0.1 s or to the nearest integer (96.545… → 96.5; 322,506.666… → 322,507; 4,631.666… → 4,632; 289.636… → 289.6; slot seconds 93.9, 67.5, 93.0, 35.3; smoke 84.477… → 84.5).

Fix: state “owner seconds to 0.1 s; token averages to the nearest integer, exact halves kept” and print 6,526.5.

Checked and consistent with the evidence: rule 5 is MIXED (one skip; rules 1–4 do not match: no STOP, usage COMPLETE, no `merge_refused`, false completion false on every slot, not 4/4, fewer than two skips). `final: false` and pending `m04:tags` are the summarizer’s response to an unset skip tag set. Astra’s tags are `1` and `3`; Grok’s are `1`, `3`, and `none` for the `base_sha` comparison; the frozen rule publishes that disagreement as unset. The second prediction clause is unscored; the first is true. The three m04 quotations match `m04-final.txt`. Cleanup is past tense for six repositories at HTTP 404, with archive receipts on the five used slots, and future tense for credentials, snapshots, and the image. No secret, VPN hostname, or IP in the write-up or the rp-d7 handoff text.

VERDICT: REVISE
