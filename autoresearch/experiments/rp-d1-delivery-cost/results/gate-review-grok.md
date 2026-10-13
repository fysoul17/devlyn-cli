I'll review the 0254/0255 accounting path against the rp-d1 gate as a read-only check, starting from the handoff and the experiment runners it names.The 0254/0255 path cannot count the planned rp-d1 observations for both engines. Stop before any live run.

## 1. Gate by engine

**Claude: FAIL.** 0255 admits only Claude arms A/B/S and sends Codex elsewhere (`autoresearch/experiments/0255/runner.py:83-87`). On that Claude branch, 0254 can certify one successful owner plus same-model, first-level, foreground, noninteractive Agent children whose terminal stop is `end_turn` or `tool_use` (`0254/audit.py:14-16`, `72-76`, `166-167`, `313-324`). A separate `claude -p` or `codex-monitored.sh`, or `python … peer.py --engine`, is recorded as an independent launch and the whole cost becomes UNKNOWN (`0255/runner.py:71-73`, `120-126`; recognizers at `0234/diagnostics.py:47-64` and `0242/policy.py:15-41`). UNKNOWN is raised before the delivery check. 0254 itself says a MATCH is not a delivery result (`0254/README.md:43-45`). 0255 has not run a live owner (`0255/README.md:6-7`).

The inherited cell cannot host the required GitHub delivery either:

- The prompt always appends "Do not publish" (`0237/runner.py:70-73`, `0237/local-delivery.txt:1`).
- `origin` is a local bare repo, "without a GitHub transport" (`0233/prepare.py:65-66`, `125`).
- After the container exits, `origin` must still be exactly `/harness/mirror.git` and the mirror's objects must be unchanged (`0233/run_cell.py:136-148`). A push to that mirror, or retargeting `origin` at GitHub, STOPs the cell.
- The delivery checker accepts only a local descendant commit (`0237/delivery.py:1`, `38`).
- The image installs git, node, `claude`, and `codex`, and does not install `gh` (`0232/Dockerfile:2-9`).
- Credentials mounted into the cell are Claude `claude.env` and Codex `auth.json` only. HOME is the per-cell `/home/participant`. Outbound network is on (`--network bridge`) (`0251/cell.py:27-45`).
- `task-complete.py` publishes only when the remote is one `github.com` repository (`config/skills/_shared/task-complete.py:173-175`). With this origin, task-completion's own rule is the local-only route (`config/skills/_shared/task-completion.md:18-19`).

**Codex: FAIL.** `config == 'codex'` returns `super().run` (`0255/runner.py:84-85`), which is `0238.Runner.run`. That calls `0234/record_usage.py` and `0238/claude-accounting-v1.py`, then raises unless completeness is COMPLETE, before `delivery.check` (`0238/runner.py:140-172`). 0254 is not invoked. 0255 says this Codex test mocks the old trace accounting and does not claim a Codex parser (`0255/README.md:14`, `58-60`). In that trace path, an inference with `usage is None` is skipped and a session with no traced inferences is a named gap, so the whole total is PARTIAL or UNKNOWN (`0234/record_usage.py:61-71`, `305`). That is the 0248 Codex S STOP: one inference had no authoritative usage, whole tokens stayed null (`iterations/0237-minimal-solo-harness.md:12`; `0248/results/screen-conclusion.md:18`, `30`). 0252 stays closed with UNKNOWN whole cost (`0252/results/closure-v1.md:1-7`; `0254/README.md:5`). The same cell, prompt, remote, missing `gh`, and local-commit checker apply.

## 2. Minimal prerequisites

**Configuration/registration only.** A frozen runtime, tasks file, arm S (or A/B), image digest, and account hash are what `0255/runner.py` already requires, and it creates none (`0255/README.md:50-52`). That does not make the gate pass. Network is already bridge. A token stuffed into `claude.env` would be injected by the existing `--env-file`, and the origin, the "Do not publish" prompt, the mirror seal, and the absence of `gh` would remain.

**Requires new accounting code.** Codex. 0254 reads Claude API bodies under `home/.claude/api-bodies` and Claude `modelUsage` (`0254/audit.py:1`, `15-16`). Nothing in this chain captures Codex terminal bodies. Closing the missing-inference hole so every Codex child is fully counted needs a new reconciler. The handoff forbids building one, so this is a stop. Counting a second `claude -p`, `codex-monitored.sh`, or `peer.py --engine` process, or a nested, background, or other-model child, is also new accounting: 0255 currently forces UNKNOWN on purpose. Default delivery does not launch those.

**Apparatus changes, neither of the two buckets.** These are required before either engine can emit the observation the auditor would have to count. They are edits to inherited runner code, not a registration file and not a new receipt auditor:

- Point the cell's remote at the throwaway GitHub repo at prepare time, and change `harness_unchanged` so that remote and a real push are legal.
- Stop prepending `local-delivery.txt`.
- Put `gh` on the image PATH and mount GitHub credentials.
- Leave `0237/delivery.py` as the local-commit check. Token accounting does not read it. Proof of the merged PR stays a separate done-check.

## 3. Why the gate question is mis-posed

"The 0254/0255 path" is Claude-only by the runner's first branch. Codex never reaches it, so "both engines" fails from the source as written.

"Count a live GitHub delivery" joins two checks this code keeps apart. 0254 certifies receipt identity, and `0237/delivery.py` certifies a local commit. A merged PR is neither input.

Default delivery does not spawn the independent CLI that 0255 refuses. `task-completion.md:138-147` has the owner review the diff; the helper does not launch a model. `devlyn-ideate` adds no reviewer quota (`config/skills/devlyn-ideate/SKILL.md:6`). A drain does start `claude -p` or `codex-monitored.sh` (`SKILL.md:107-116`), and that child is told not to push; review files are optional and "no particular engine" is required (`references/loop.md:111`). `gh` does not match `launch_engine`. The cell already is the owner CLI (`0233/prepare.py:138-140`). The prediction's "in-product reviewer" is not a process this default path creates.

GATE: FAIL
