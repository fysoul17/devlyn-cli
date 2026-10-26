# 0259 registration — No-overengineering ablation on claude

Registered after SMOKE qualification; no measured cell has run. [DESIGN.md](DESIGN.md) is frozen (r2) and
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
| Package C | B with DESIGN's ordered edit (rule 2 deleted, "Six rules", rules renumbered 2–6) in `AGENTS.md`, `CLAUDE.md`, `config/skills/_shared/runtime-principles.md`; tree sha256 `cdb777034417a95cba1a044540ed2ad6bfd0ac9698ab197ea4e46899093fb7b1`; `diff -r` B C shows exactly those three files, each with lines 11 and 14–19 changed |
| Control manifest | sha256 `aa409052a2eaccf0b8c59d288438877a951b16f816654c727e75b85e2021912e` (0257's control plus C) |
| Instruction seal | `instructions.seal.json` sha256 `13e211ecd05510354f87172f54063119e1413ff51aa8590c94fd5ab0cf3baf46`: installer files per arm (B `AGENTS.md` `11a85ab7…`, equal to 0257 and 0258; C `dd013cfb…`; `runtime-principles.md` B `6c615346…`, C `c8a4c6dc…` in both skill directories), Claude forms from SMOKE B and C (`AGENTS.md` 4,112 and 3,815 characters, differing only by the edit), qualification PASS |
| D3 witness | `results/witnesses/d3-parseoptions-override.js` sha256 `5e706105f608b888ff04fdff530855b84d4c994a466b320640957efa70e14c61` (0258's) |
| F10 probe | `results/witnesses/f-malformed-json.js` sha256 `6bcba20346013972696cd856e99545df48334f7cb777e49ab2defdc3c98979cb` (0257's) |
| Schedule | `cells.tsv` sha256 `d1176888abd03b2ce21cda06a0bfc018fa25170ff2500d7da08c24a92b4f8d32` (64 cells, 0258's order) |
| Caps | seven-day 95%, five-hour 95% from the first dispatch |
| Deadline | 2026-11-09T02:52:58Z: 14 days after the first SMOKE dispatch (2026-10-26T02:52:58Z) |
| Venue | any logged-in owner Claude account (0257 amendment 1); SMOKE ran on `44e06b9de5c4` / `16b7ef0cf7cf` |
| Apparatus | `autoresearch/experiments/0259/` at the registration commit |

## Qualification

- **Tests:** `python3 -m pytest -q autoresearch/experiments/0259`: 32 passed, 33 subtests; 0258's suite still 27
  passed.
- **Reviews:** Astra ultra and Grok 4.7, read-only ([results/](results/)). Design round 1: Astra SHIP (three LOW),
  Grok REVISE (one MEDIUM: renumber instead of leaving a gap), applied in DESIGN r2. Code round 1 (also checking
  DESIGN r2): Grok SHIP; Astra REVISE with one HIGH inherited from 0258, that final SMOKE attempts were not required
  in the audit before a decision, fixed under `results/fix-r2-contract.md` with a regression test. Round 2: both SHIP,
  no findings.
- **Witness in the cell image** (no network, cap-drop ALL, uid 501, read-only), twice each on 0257 trees: d241 and
  d049 exit 1 (`P0258-WITNESS bypass`), d002 and d017 exit 0 (`P0258-WITNESS public`). Not data.
- **Probe:** `judge.py qualify-probe` classifies 0256 c01 as `json_error_400` and c02 as `html_400`. Not data.
- **SMOKE** (outside every sum):

| Cell | Owner | Seconds | Teardown | Identity | Usage | Scope | Verdict |
|---|---|---:|---|---|---|---|---|
| smoke-claude-B | EXITED_0 | 65 | CLEAN | MATCH | COMPLETE | none | PRODUCT_INCOMPLETE |
| smoke-claude-C | EXITED_0 | 55 | CLEAN | MATCH | COMPLETE | none | PRODUCT_INCOMPLETE |

  PRODUCT_INCOMPLETE is SMOKE's expected verdict, as in 0256–0258. `instructions.py seal-forms` then recorded
  qualification PASS over both cells.

The runtime root is `~/.local/share/nx01/0259-live`. Measured cells run from a detached checkout of the registration
merge.
