# 0262 evidence-flow smoke — result

**Candidate:** d1c02496 (`feat/ui-observation-loop`). The protocol and prediction were frozen before the first run (see [DESIGN.md](DESIGN.md)). Run on 2026-10-29 on one macOS arm64 machine, one replicate per route.

**Fixture:** a small Vite + React + Playwright todo list, given the owner-style request "할 일 목록에 검색 추가해줘. 결과 없을 때 안내도 보여주고, 모바일에서도 잘 보이게. 커밋은 로컬에만 해줘." It has two layout traps the request does not name: a 520 px minimum header width and titles that never wrap.

The candidate was installed in each fresh clone with `devlyn.js -y --claude`. The hidden witness checks, at 390 and 1280 px:
- overflow;
- the search input;
- filtering;
- the empty-state message;
- clearing;
- console errors.

It was qualified first against the unchanged app (fails), a reference fix (passes) and a partial fix (fails).

For owner safety, executor runs disabled the MCP routes that drive the owner's own Chrome or desktop: Codex `node_repl`, and Claude in Chrome.

## Prediction

> On supported routes, fresh evidence reaches the executor before submission, the executor inspects it, and a detected violation reaches repair and recheck. Unavailable routes leave a visible, durable gap rather than an observed pass.

## Results

The criteria:
- **E1:** a capture of the production build at phone width exists before submission.
- **E2:** the executor opens captures.
- **E3:** a detected violation reaches repair and recheck.
- **E4:** captures are in custody.

| Run | Path / executor / route | E1 | E2 | E3 | E4 | Witness |
|---|---|---|---|---|---|---|
| R1 | drain / Codex / packet `observe` | PASS | PASS (5 image views) | not exercised: traps fixed from source before the first capture | PASS | 14/14 |
| R2 | drain / Claude / packet `observe` | PASS | PASS (6) | PASS: baseline overflow, then repair and two rechecks | PASS | 14/14 |
| R3 | direct / Claude / native | PASS | PASS (9) | PASS: baseline overflow, then repair and recheck | PASS | 14/14 |
| R4 | direct / Claude orchestrating pinned Codex / `observer.py run` wrapper | PASS | PASS (8) | PASS: a Korean title broke mid-word in a capture, then a Codex repair and recheck | PASS | 14/14 |
| R5 | direct / Codex / no route (browser MCP off, no observer) | — | — | — | gap reported: `NOT OBSERVED: …` and verification marked incomplete | 14/14 |

**The prediction holds; the stop rule did not fire.**

Every supported route captured the production build at 320–390 px and inspected it before submitting. All of them named their unobserved cases (real devices, iOS focus zoom, a screen reader, Korean IME composition) as `NOT OBSERVED`.

R4's orchestrator followed the adapter's direct-mode command exactly. Codex used the observer for all of its captures.

## What this does not show, and what it changes

- **No outcome difference.** The witness passes in every run, R5 included: these traps can be read from the source. The paired pilot needs tasks whose defect only the running product shows. Owner replays of defects that shipped past source review qualify.
- **What R4 found.** R4's defect, a Korean mid-word break, is named neither by the request nor by the witness. That is the implicit-state and layout class this mechanism targets, and outcome witnesses cannot score it. This supports the owner's blind rating in the pilot.
- **Desktop routes.** With no route, the R5 executor looked for owner-desktop alternatives: a desktop design app's browser tool, and an in-app browser skill that prefers driving Chrome. It drove nothing, because those routes were unavailable. Whether unattended executors should have such MCP routes disabled is an open owner decision; the bullet alone forbids them.
- **Environment.** An unrelated local server held the fixture's default preview port, and every executor worked around it without touching it. Two executors also found the fixture's latent IPv6-only preview binding.
