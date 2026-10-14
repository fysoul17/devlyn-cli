I'll review the registration against DESIGN.md and the staged smoke evidence, read-only, and check identities before judging whether exposure is safe.The registration text is in hand. Next I’ll check the staged verdicts, runtime identities, and the measured-stage rules against those files.Registration at `41aa890a` matches DESIGN.md and the staged attempt-2 evidence. Smoke attempt 2 meets the measured-stage gate for all four cells. Attempt 1 is a stopped run and is not the qualification set. No HIGH finding.

**Checked**

- Prediction text matches DESIGN.md. The schedule is the rp-d1 task/engine order with odd pairs X then Y and even pairs Y then X, the same order as `registration.json` and `runner.py`. Success, cost, adoption, and STOP/`NOT_RUN` match `summarize.py` and the withdrawn continuation (UNKNOWN still stops the run). Renewal stays between pairs, on the same Claude account pair and Codex digest, with the 6300-second floor.
- DESIGN.md records Grok’s dissent and the narrowed reading: this run tests Y under the frozen prompt; a null result does not indict the product rule in general; the prompt ablation is the next candidate if Y is not adopted. `registration.md` incorporates that text and the same next candidate.
- `registration.json` releases match `arms/arms.json` and `stage2/runtime-measured.json` (X `7b22cce8…393e`, Y `c45bc13a…f603`, candidate `a623b382`). Account `cc43a4e02ede` / `2905f4abf05b` and `codex_account` `65ad276127a5` match the runtime, `model-auth-1/manifest.json`, and all four attempt-2 verdicts. Image `sha256:b55cbb94…4eb0` matches `build/image.id`. Routes match `tasks.json`. Plans use `claude-opus-5-5` at `max` and `gpt-6-sol` at `high`, owner wall 5400 s. The cell home records Claude Code `2.1.296`.
- Registered smoke verdict hashes equal each cell’s `inherited_verdict_sha256` (`verdict-smoke2-*.json`). `stage2/output` is empty.
- Attempt 2, all four cells: `rp-verdict` status `ADJUDICATE`, usage `COMPLETE`, `github-delivery` status `ADJUDICATE`, archive present, repository `DELETED` with HTTP 404, and `merged: true` in the archive. Counts match the table (owner seconds 639.002, 613.917, 165.180, 173.208). Codex Y’s `cat` of `task-completion.md` returned the cleanup paragraph at 3610 tokens, under the 6000 cap.
- Attempt 1 is `STOP` on Claude X, usage `UNKNOWN` (`error or retry outside scope`, `api_retry`), delivery `NOT_ASSESSED`. The other three cells are `NOT_RUN`. Its schedule hash is recorded separately. The measured runtime’s `smoke_attempt` is 2, so those cells are not the predecessors `prior_deleted` requires for `m01`.

**LOW**

- `registration.md:23` quotes Codex Y as only “PR #1 merged, and the local checkout is clean”. `smoke2-codex-Y/final.txt` also ends with “Nothing remains unresolved”, which DESIGN.md:175–176 already records. The prediction is unchanged.
- DESIGN.md:179–180 says both Claude smoke reports named scratch removal. `smoke2-claude-X/final.txt` names the worktree and branch, not scratch. `smoke2-claude-Y/final.txt:20` does name scratch. The qualification gate is `ADJUDICATE` plus usage `COMPLETE`, not that sentence.
- DESIGN.md:170 and `registration.md:97` name ECONNRESET. The sealed attempt-1 stdout shows `api_retry` with `"error":"unknown"` and the usage gap `error or retry outside scope`. The STOP handling does not depend on that errno string.

Before `m01`, the staged manifest `expires_at_ms` `1791990062055` crosses the 6300-second floor at unix `1791983762` (about nine minutes after registration commit `1791983235`). If that floor has already passed, renew on the same accounts and resume from the new runtime path. Leave `registration.json` as it is. `renewal_allowed` accepts a measured runtime with zero completed slots.

VERDICT: SHIP
