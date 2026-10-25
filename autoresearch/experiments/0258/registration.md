# 0258 registration — one-clause ablation on claude

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
| Package C | B minus the clause in `AGENTS.md`, `CLAUDE.md`, `config/skills/_shared/runtime-principles.md`; tree sha256 `c5c27dd06b23bfa7729059ce754079f6e9b3fb601fb964a7d656cadac807e5d2`; `diff -r` B C shows exactly those three lines |
| Control manifest | sha256 `b5e3b954f593e263ded4deab19472ea4c5834b50649eb23694b79710281ba801` (0257's control plus C) |
| Instruction seal | `instructions.seal.json` sha256 `e93cd014b848ab4d845e67c954b1e8db6bb7abc53176e69d05afeabcdae5749d`: installer files per arm (B `AGENTS.md` `11a85ab7…`, equal to 0257; C `a9bae4b3…`; `runtime-principles.md` B `6c615346…`, C `8e13cf46…` in both skill directories), Claude forms from SMOKE B and C (`AGENTS.md` 4,112 and 4,051 characters, differing only by the clause), qualification PASS |
| D3 witness | `results/witnesses/d3-parseoptions-override.js` sha256 `5e706105f608b888ff04fdff530855b84d4c994a466b320640957efa70e14c61` |
| F10 probe | `results/witnesses/f-malformed-json.js` sha256 `6bcba20346013972696cd856e99545df48334f7cb777e49ab2defdc3c98979cb` (0257's) |
| Schedule | `cells.tsv` sha256 `d1176888abd03b2ce21cda06a0bfc018fa25170ff2500d7da08c24a92b4f8d32` (64 cells) |
| Caps | seven-day 95%, five-hour 95% from the first dispatch |
| Deadline | 2026-11-08T01:19:17Z: 14 days after the first SMOKE dispatch (2026-10-25T01:19:17Z) |
| Venue | any logged-in owner Claude account (0257 amendment 1); SMOKE ran on `44e06b9de5c4` / `16b7ef0cf7cf` |
| Apparatus | `autoresearch/experiments/0258/` at the registration commit |

## Qualification

- **Tests:** `python3 -m pytest -q autoresearch/experiments/0258`: 27 passed, 5 subtests; 0257's suite still 63 passed.
- **Code review:** Astra ultra and Grok 4.7, two read-only rounds ([results/](results/) `code-r*`); round-2 MEDIUM
  findings fixed under `results/fix-r2-contract.md` with regression tests, without a third round.
- **Witness in the cell image** (no network, cap-drop ALL, uid 501, read-only), twice each on 0257 trees: d241 and
  d049 exit 1 (`P0258-WITNESS bypass`), d002 and d017 exit 0 (`P0258-WITNESS public`). Not data.
- **Probe:** `judge.py qualify-probe` classifies 0256 c01 as `json_error_400` and c02 as `html_400`. Not data.
- **SMOKE** (outside every sum):

| Cell | Owner | Seconds | Teardown | Identity | Usage | Scope | Verdict |
|---|---|---:|---|---|---|---|---|
| smoke-claude-B | EXITED_0 | 65 | CLEAN | MATCH | COMPLETE | none | PRODUCT_INCOMPLETE |
| smoke-claude-C | EXITED_0 | 62 | CLEAN | MATCH | COMPLETE | none | PRODUCT_INCOMPLETE |

  PRODUCT_INCOMPLETE is SMOKE's expected verdict, as in 0256 and 0257. `instructions.py seal-forms` then recorded
  qualification PASS over both cells.

The runtime root is `~/.local/share/nx01/0258-live`. Measured cells run from a detached checkout of the registration
merge.
