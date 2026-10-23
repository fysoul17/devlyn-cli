Implement 0257 amendment 3 in this worktree (devlyn-cli). Work only under `autoresearch/experiments/0257/` (0233/0231/0256 modules are shared: read, don't edit). Do not commit. No Docker, models, credentials or runtime files.

## Owner decision (2026-10-23)

Asked "Docker가 꺼져서 망가진 칸은 버리고 다시 돌릴까요? (추천) — 사용량 한도에 걸린 칸처럼 따로 보관하고 그 칸만 처음부터 다시" the owner answered "추천대로".

## Observed failure

At 2026-10-23T09:34:17Z Docker Desktop quit (cause unknown, not an agent transcript) while cell d058-I0185-claude-A-r4 was running. Its verdict is:
status STOP, teardown FAILED, identity MATCH, owner_status EXITED_NONZERO, reason `teardown failed: Command '['docker', 'inspect', '<container id>']' returned non-zero exit status 1. Cannot connect to the Docker daemon at unix:///Users/aipalm/.docker/run/docker.sock. Is the docker daemon running?` (the teardown_error comes from 0233/cell.py's teardown). Under DESIGN §Operations that STOP stops the run. After Docker came back, the container (name `devlyn-0231-<hex>`) exists in state Exited (255). Earlier, the same day, Docker went down between cells (handled by PR #275's docker load hold).

## Rule (amendment 3)

A cell whose execution lost the Docker daemon is an infrastructure fault, handled like a quota fault: the attempt is archived as `.stop-N` and the cell is redispatched; only the final verdict is scored; archived attempts count toward attempts/usage and are covered by the post-run user-data-harm audit. Before archiving, the driver must prove teardown with Docker up: every container of that attempt is not running, then is removed (`docker rm`), and the removal is verified; record what was found and removed in a driver event. If a container of the attempt is still running, or cannot be identified, it is NOT a fault: stop the run as today (a real teardown failure).

Recognition: a STOP verdict whose teardown is FAILED and whose teardown_error/reason contains `Cannot connect to the Docker daemon` (this must match the existing d058 verdict, already on disk). Optionally also classify it in run_cell.py going forward with a reason prefix like `docker daemon lost during execution:`, but the driver must still accept the existing d058 form. Find where the container id/name of an attempt is recorded (verdict, owner record or cell output) and use that, not a guess; the id also appears in the reason text — prefer a structured record if one exists, and say what you used.

Placement: mirror the existing quota-fault archive path in `Driver.dispatch` (driver.py, "shared account fault during execution:"). Dispatch only reaches that path after `ready()` passed, which includes the image check, so Docker is up. Keep it the smallest change; no retries counters or new machinery beyond the teardown proof.

Check the harm latch: d058's identity is MATCH and the latch for STOP verdicts only looks at identity, so it must not latch; confirm, and make sure the archived attempt does not later latch on rerun.

Also in scope only if it is a few lines: Astra noted (existing) that Docker dying after preflight can make prepare.py's installer `docker run` raise through `dispatch()` and kill the driver. If there is a clean way to turn a Docker-daemon-unreachable exception during dispatch into the same archived infrastructure fault, do it; otherwise leave it and report.

Tests (test_apparatus.py): the d058-form verdict + exited container → teardown proven, archived to `.stop-1`, redispatched; a running container → stop; unidentifiable container → stop; non-Docker teardown failure → stop as before. Run `python3 -m pytest -q autoresearch/experiments/0257` and `python3 -m pytest -q autoresearch/experiments/0256`.

Docs: new `amendment-3.md` modelled on `amendment-2.md` (date, owner quote, observed failure, rule, why it does not bias A vs B — the fault depends on when Docker stops, not on the arm, and reruns are fresh; what stays; operator steps: none beyond relaunching the driver from an updated worktree). README.md: one mention next to amendments 1–2 and the driver row. DESIGN.md is frozen.

Report: files changed, what identifies the attempt's containers, test counts, anything left out.
