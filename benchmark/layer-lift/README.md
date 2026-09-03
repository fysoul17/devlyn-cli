# Layer-lift operator recipe

1. Derive and verify the registered quick panel. Its fixed base is L0 ×4,
   L1 ×1, L2 ×1 with one lane and materiality δ = 6/20.

   ```sh
   python3 benchmark/layer-lift/run-lift-panel.py --derive-panel
   ```

2. Freeze before any model run, in this order: finalize every registered
   parameter; write `apparatus_sha256` from the normalized runner, scorer,
   README, panel, and `claude-isolation.py` bytes; replace both `TBD-FREEZE`
   constants with the final SHA-256 of `registered-params.json`; then re-seal
   `scripts.sha256` and require this to pass.

   ```sh
   shasum -a 256 -c benchmark/layer-lift/scripts.sha256
   ```

3. Run the one-task smoke gate (one rep in each arm).

   ```sh
   python3 benchmark/layer-lift/run-lift-panel.py run --model claude-opus-5 --panel quick --out /private/tmp/lift-smoke --run-id lift-smoke --smoke --task EQ3-AF2
   ```

   Continue only after every `SMOKE-CONJUNCT` and `SMOKE-0113` line is `PASS`.

4. Start the serial operator drain. It self-detaches, waits until the account
   has no active supported CLI session, five-hour use is at most 10%, and KST
   is outside the quiet window; it then runs the separate smoke directory,
   drains one task per window, replaces infrastructure-invalid rows through
   attempts 2 and 3, and scores. Top-ups remain an operator decision.

   ```sh
   python3 benchmark/layer-lift/drain-quick.py --model claude-opus-5 --out /private/tmp/lift-quick --run-id lift-quick
   ```

   Stop it with `kill -TERM "$(cat /private/tmp/lift-quick/drain.pid)"`.
   After `drain.done`, run the exact `NEEDS_TOPUP` command if present;
   otherwise retain the single `LIFT-0113:` token in `drain.log`.
