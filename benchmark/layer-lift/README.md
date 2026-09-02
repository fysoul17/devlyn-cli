# Layer-lift operator recipe

1. Derive and verify the registered quick panel.

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

4. Start the quick panel detached. Keep the account quiet and outside
   23:00–01:00 KST.

   ```sh
   python3 benchmark/layer-lift/run-lift-panel.py run --model claude-opus-5 --panel quick --out /private/tmp/lift-quick --run-id lift-quick --attempt 1 --detach
   ```

   At a window boundary: `kill -TERM "$(cat /private/tmp/lift-quick/driver.pid)"`;
   when the account is quiet again, rerun step 4 with `--resume`.

5. Replace only infrastructure-invalid rows, at most twice.

   ```sh
   python3 benchmark/layer-lift/run-lift-panel.py run --model claude-opus-5 --panel quick --out /private/tmp/lift-quick --run-id lift-quick --attempt 2 --detach
   python3 benchmark/layer-lift/run-lift-panel.py run --model claude-opus-5 --panel quick --out /private/tmp/lift-quick --run-id lift-quick --attempt 3 --detach
   ```

6. Score the frozen rows.

   ```sh
   python3 benchmark/layer-lift/score-lift.py score --rows /private/tmp/lift-quick/rows.jsonl --params benchmark/layer-lift/registered-params.json --out /private/tmp/lift-quick/verdict.json
   ```

7. If the scorer prints `NEEDS_TOPUP`, run that exact command and score again.
   Stop on `PANEL_SATURATED`; otherwise retain the single `LIFT-0113:` token.
