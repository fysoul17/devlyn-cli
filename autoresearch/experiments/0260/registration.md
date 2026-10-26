# 0260 registration — Saint-Exupéry ablation on claude

Registered after SMOKE qualification; no measured cell has run. [DESIGN.md](DESIGN.md) is frozen (r3) and
authoritative; this file adds the frozen identities.

## Prediction (copied unchanged from DESIGN.md)

1. P1: C has more JSON-400 F10 trees than B, and P1 is Holm-rejected. Scored when P1 is ready.
2. B's own P1 count is at most 3 of 16. Scored when P1 is ready.
3. P2: C has fewer reproducing D3 trees than B (direction only). Scored when P2 is ready.

## Identities

| Item | Value |
|---|---|
| Image | `devlyn-0256`, ID `sha256:25d47afd9a3a34752ae396f2701caff046d1201cd990a0b5b21d67697423bc88` (0257's) |
| Package B | `devlyn-cli@4.2.24`, tree sha256 `d024f9b48252f943bc537e2c8e7db36715dea0b6baa285a111e43bffe2114fee` (0257's) |
| Package C | B with DESIGN's two ordered edits (Saint-Exupéry bullet deleted, "Two discipline rules") in `AGENTS.md`, `CLAUDE.md`, `config/skills/_shared/runtime-principles.md`; tree sha256 `088ca842937d213b0d2392a6ff58c81adf97530f4df387d3b7224908676ad4ef`; `diff -r` B C shows exactly those three files, each with line 21 changed and line 25 deleted |
| Control manifest | sha256 `c3b6f916fc55bafc5b17f87a93c5d2efe65a07806a1227b991940d6b7353ddbb` (0257's control plus C) |
| Instruction seal | `instructions.seal.json` sha256 `9b8236ae518e85ad0492b45cffa3fe14afbef09b01417bfe6c947e4ef5a306f5`: installer files per arm (B `AGENTS.md` `11a85ab7…`, equal to 0257–0259; C `dc39bea7…`; `runtime-principles.md` B `6c615346…`, C `1c08fa57…` in both skill directories; `CLAUDE.md` `336cc4fb…` in both), Claude forms from SMOKE B and C (`AGENTS.md` 4,112 and 3,794 characters, differing only by the edit), qualification PASS |
| D3 witness | `results/witnesses/d3-parseoptions-override.js` sha256 `5e706105f608b888ff04fdff530855b84d4c994a466b320640957efa70e14c61` (0258's) |
| F10 probe | `results/witnesses/f-malformed-json.js` sha256 `6bcba20346013972696cd856e99545df48334f7cb777e49ab2defdc3c98979cb` (0257's) |
| Schedule | `cells.tsv` sha256 `d1176888abd03b2ce21cda06a0bfc018fa25170ff2500d7da08c24a92b4f8d32` (64 cells, 0258's order) |
| Caps | seven-day 95%, five-hour 95% from the first dispatch |
| Deadline | 2026-11-09T22:01:05Z: 14 days after the first SMOKE dispatch (2026-10-26T22:01:05Z) |
| Venue | any logged-in owner Claude account (0257 amendment 1); SMOKE ran on `25813bedb87d` / `e44a78e9700b` |
| Apparatus | `autoresearch/experiments/0260/` at the registration commit |

## Qualification

- **Tests:** `python3 -m pytest -q autoresearch/experiments/0260`: 48 passed, 36 subtests; 0259's suite still 36
  passed and 0258's 27, each run separately.
- **Reviews:** Astra ultra and Grok 4.7, read-only ([results/](results/)).
  - Design round 1: Astra SHIP (one LOW), Grok REVISE (one MEDIUM, four LOW), applied in DESIGN r2.
  - Code round 1 (also checking DESIGN r2): Grok SHIP (two LOW); Astra REVISE with two HIGH in `judge.py`: a
    completed attempt could be lost when a later create failed or a cleanup failed. Fixed under
    `results/fix-r1-contract.md`.
  - Round 2: Grok SHIP; Astra REVISE with one HIGH: `docker start -a` exits 1 when Docker cannot start a container,
    so a generic witness would read that as a reproduced defect. Fixed under `results/fix-r2-contract.md`, with
    DESIGN r3 stating the start rule.
  - Round 3: both SHIP, no findings.
- **Witness in the cell image** (no network, cap-drop ALL, uid 501, read-only), twice each on 0257 trees: d241 and
  d049 exit 1 (`P0258-WITNESS bypass`), d002 and d017 exit 0 (`P0258-WITNESS public`). Through the final `judge.py`
  (`docker create` / `docker start -a` / state check): d241 `[1, 1]`, d002 `[0, 0]`, no container left. Not data.
- **Probe:** the final `judge.py qualify-probe` classifies 0256 c01 as `json_error_400` and c02 as `html_400`. Not
  data.
- **Docker:** a bind mount from `/Users` ran normally on 2026-10-27 before SMOKE, so `NX01_0260_JUDGE_SCRATCH` is not
  set.
- **SMOKE** (outside every sum):

| Cell | Owner | Seconds | Teardown | Identity | Usage | Scope | Verdict |
|---|---|---:|---|---|---|---|---|
| smoke-claude-B | EXITED_0 | 68 | CLEAN | MATCH | COMPLETE | none | PRODUCT_INCOMPLETE |
| smoke-claude-C | EXITED_0 | 44 | CLEAN | MATCH | COMPLETE | none | PRODUCT_INCOMPLETE |

  PRODUCT_INCOMPLETE is SMOKE's expected verdict, as in 0256–0259. `instructions.py seal-forms` then recorded
  qualification PASS over both cells.

The runtime root is `~/.local/share/nx01/0260-live`. Measured cells run from a detached checkout of the registration
merge, on mains power (0259 amendment 1 came from a sleep on battery).
