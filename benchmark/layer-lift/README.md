# Layer-lift operator recipe

1. Derive and verify the registered quick panel. Its fixed base is L0 ×4,
   L1 ×1, L2 ×1 with one lane and materiality δ = 6/20.

   ```sh
   python3 benchmark/layer-lift/run-lift-panel.py --derive-panel
   ```

2. A16 freeze before any model run: finish code/tests/README; update only `apparatus_sha256` in parameters from the normalized runner, scorer,
   README, panel, and `claude-isolation.py` bytes; replace both parameter-pin
   constants with the final SHA-256 of `registered-params.json`; then re-seal
   `scripts.sha256` (seven existing targets; drain remains unsealed) and require this to pass.

   ```sh
   shasum -a 256 -c benchmark/layer-lift/scripts.sha256
   ```

3. Run the one-task smoke gate (one rep in each arm).

   ```sh
   python3 benchmark/layer-lift/run-lift-panel.py run --model claude-opus-5 --panel quick --out /private/tmp/lift-smoke --run-id lift-smoke --smoke --task EQ3-AF2
   ```

   Continue only after every `SMOKE-CONJUNCT` and `SMOKE-0113` line is `PASS`.
   A retained product failure with `pair_judge_ran=false` cannot pass actual-pair smoke.

4. Start the serial operator drain. It self-detaches, waits until the account
   has no active supported CLI session, five-hour use is at most 10%, and KST
   is outside 23:00–01:00. Both process gates recognize Claude `-p`, Codex `exec`,
   and plain or version-suffixed Grok with `-p` or `--prompt-file`; the runner
   independently blocks active root state. It then runs the separate smoke directory,
   drains one task per window, replaces infrastructure-invalid rows through
   attempts 2 and 3, and scores. Top-ups remain an operator decision.

   ```sh
   python3 benchmark/layer-lift/drain-quick.py --model claude-opus-5 --out /private/tmp/lift-quick --run-id lift-quick
   ```

   Stop it with `kill -TERM "$(cat /private/tmp/lift-quick/drain.pid)"`.
   After `drain.done`, run the exact `NEEDS_TOPUP` command if present;
   otherwise retain the single `LIFT-0113:` token in `drain.log`.

A16 retains A15's same isolated launcher/fresh homes/frozen environment in every
arm. L0 stays goal-only, unstaged, with exactly
`--allowedTools Read,Grep,Glob,Edit,Write,Bash`; existing `--tools-csv` callers
keep their semantics. The driver alone bounds launcher/auth preparation and
execution at 1800/3600 seconds and cleans ordinary process groups; explicit
session escapes are unproven. Bounded expiry is TIMEOUT with unknown usage:
absent metadata is allowed, present malformed/wrong identity is infrastructure.
Captured streams are preserved when available; launcher buffering can leave them empty.

Canonical unopened BLOCKED or mechanical-blocker skips retain `f_ship=1` and
cannot be retried. L2 records `pair_judge_ran=false` only for established
not-run, with empty pair identity and zero Codex usage; executed judges keep
exact evidence checks. Completed non-timeout stdout uses the frozen source
collector: max(summary/finding ranks), or BLOCKED on collector rejection or
invalid UTF-8. Claimed pair rank must be at least that rank; binding output
(NEEDS_WORK/BLOCKED) cannot accompany overall PASS/PASS_WITH_ISSUES. Truthful
nonshipping emission BLOCKED is retained/nonretryable; missing captures, I/O
failure and wrong identity remain infrastructure. Pair/driver TIMEOUT allows
incomplete stdout without relaxing capture/identity or unknown-usage rules.
Exact `BLOCKED:claude-unavailable` and
`BLOCKED:codex-unavailable` stay infrastructure. Stale prior-round captures
beside a final skip still reject; A15 does not add per-round provenance.

Token anchors divide exact mean output tokens per BASE run, summing models
within each run; wall anchors stay medians. Raw token totals remain diagnostics,
top-ups never change anchors, and unknown TIMEOUT usage stays INCONCLUSIVE.
Preserve pre-A15 artifacts as noncomparable, with unchanged staged product,
seats, panel, reps and thresholds. Actual operational status and collection
identity live in [HANDOFF](../../autoresearch/HANDOFF.md).
No measured runtime lift follows from A16.
