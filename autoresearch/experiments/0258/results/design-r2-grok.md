I'll review the round-2 design against both round-1 findings and the 0257 background, read-only. First I'm loading the draft, the two reviews, and the prior experiment context.The round-1 package, seal, probe-rerun, safety-flag, and cap edits are in the draft. Three holes are still open.

### MEDIUM — The witness drops the value `_parseCommand` reads

**Exact text:** DESIGN.md lines 69–70, “defines a subclass whose `parseOptions(args)` replaces the operand `p0258-before` with `p0258-after` and calls `super.parseOptions`”. Qualification, lines 151–152: “exit 0 on d002 and d017 (B, public path)”.

**Evidence:** On the public path the caller uses the return value. `d002` `lib/command.js:1574–1581` and `d017` `lib/command.js:1572–1578` do `const parsed = this.parseOptions(unknown)` and then read `parsed.operands`. `parseOptions` returns `{operands, unknown}` and leaves `this.args` to that caller (`d002` `lib/command.js:1784` and `:1581`). A method that calls `super.parseOptions` and yields `undefined` throws on `parsed.operands`, and the witness maps a throw to exit 2. The bypass path calls `this._parseOptions` (`d241:1571`, `d049:1566`), so d241 and d049 can still exit 1 while d002 and d017 exit 2. `this.args` is the flat operand list. A variadic argument wraps `this.processedArgs` only, so the stated `['p0258-after']` / `['p0258-before']` checks are the right ones once the return is kept. This is a source trace; the four trees were not executed.

**Fix:** The override returns `super.parseOptions` of the rewritten argv. Keep the qualification exits: 0 on d002 and d017, 1 on d241 and d049.

### MEDIUM — “Holm-rejected” has no value when P2 has no p

**Exact text:** Line 76, “P1 and P2 form a two-test Holm family at α = 0.05.” Line 91, “CLAUSE_IMPLICATED: P1 is Holm-rejected.” Line 94, “P2_UNRESOLVED: P1 is ready and not rejected, and P2 is not ready.” Line 103, `P1:<C>/<B>(<p>,<adj>)`. Lines 106–108, predictions “scored only when the tests are ready” and prediction 1, “P1 is Holm-rejected.”

**Evidence:** `0257/decide.py:67–74` rejects when the monotone adjusted p is ≤ 0.05. With two tests, P1’s adjusted p is `2p` when P1 is smaller, and an exact P1 p in `(0.025, 0.05]` is still rejected when P2 is smaller and ≤ 0.025. An unresolved P2 supplies no second p, so those count pairs have two legal headlines. Line 77 sets `p = 1` only for an observed non-adverse direction. Line 104 prints `P2:NOT_READY`. An exact P1 p ≤ 0.025 is rejected for every possible second p. An exact p > 0.05 is rejected for none.

**Fix:** Keep the family size at 2 when P2 is unresolved. P1 is Holm-rejected only when its exact one-sided p ≤ 0.025, and the token’s adjusted value is `min(1, 2p)`. When `0.025 < p ≤ 0.05`, P1 is not rejected and the headline is `P2_UNRESOLVED`, with the raw p printed. Score prediction 1 when P1 is ready, under that rule. Score prediction 3 when P2 is ready.

### MEDIUM — Claude dispatch still waits on a live Codex call

**Exact text:** Lines 115–117, “Unchanged from 0257: … fault rules”, and line 129, “`run_cell.py`: the claude-only seal (no Codex form required) and the arm’s own package digest.”

**Evidence:** `run_cell.py:145–154` always calls `codex_limits`. That function (`99–112`) runs `codex exec` (`-m gpt-6-astra`, prompt `Reply OK.`) and reads Codex `used_percent`. A window at 100, an empty reading, or a failed check blocks dispatch (`150–154`) and `run` returns 3 (`249–252`). `driver.py:425–428` sleeps 60 seconds and retries the same cell. The 95/95 Claude caps are a separate check (`driver.py:264`). A full Codex window, or a Codex auth or model failure, holds every B and C cell until the 14-day deadline.

**Fix:** In the `run_cell.py` change, preflight reads the Claude windows only. Hold on the 95/95 Claude caps and on missing Claude limit evidence. Drop the Codex exec from this experiment’s preflight.

VERDICT: REVISE
