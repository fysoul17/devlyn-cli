Read-only review of 0257 amendment 2 in this worktree (devlyn-cli). The diff is in .devlyn/amend2.diff; read autoresearch/experiments/0257/{driver.py,amendment-2.md,amendment-1.md,DESIGN.md,test_apparatus.py,run_cell.py} as needed.

Context: a registered A-vs-B experiment driver dispatches cells one at a time on the host Claude login. The owner waived the registered window reserve (used + 2x estimate <= 85/70 caps) because the run held for hours while other accounts were free; an owner app switches the host login automatically when the current account has <=5% left. Amendment 2: dispatch while each window's used < 95 (no estimate); cells that hit a limit mid-run remain quota faults (archived and redispatched); caps 95/95 registered via the existing --amend-caps path. estimates/delta/FLOORS/panel were removed as unused.

Check: correctness of driver.py ready()/fits()/split-wait after the change; anything removed that was still needed (including the removed "incomplete Claude account pair" check); whether the change can bias A vs B or corrupt verdicts; whether quota faults mid-run are really archived/redispatched rather than counted; whether amendment-2.md is accurate and the operator steps are safe. Do not edit files.

Answer: verdict SHIP or FIX, then findings with severity (HIGH/MEDIUM/LOW), file:line, and a concrete failure scenario. Be brief.
