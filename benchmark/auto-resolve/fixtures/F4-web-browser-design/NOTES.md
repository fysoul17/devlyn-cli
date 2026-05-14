# F4 — Notes

## Purpose

Exercises the browser-validate phase of the pipeline (Phase 1.5). Catches
web-UI-only regressions that unit tests can't see and that server/integration
tests won't surface.

## Failure modes detected

- **Italic via Unicode.** Arms may reach for Unicode italic characters
  (`𝑖𝑡𝑎𝑙𝑖𝑐`) instead of CSS. Spec explicitly forbids this because it breaks
  screen readers.
- **CDN link.** Linking to Google Fonts or an external CSS cuts the bench
  and breaks offline / air-gapped runs — disqualifier.
- **Breaking Greet.** Careless refactors rewire the Greet button's handler
  by mistake. Pipeline's Phase 1.5 browser-validate + dedicated spec test
  catches it.
- **Accessibility drift.** Missing/incorrect `aria-label` on button.

## Pipeline exercise

- Phase 1.5 BROWSER VALIDATE is the primary gate (web file changes trigger it).
- Phase 3 CRITIC design checks the DOM structure and event-handler wiring.

## Caveats

- Playwright requires browser binaries installed locally. If the runner
  machine lacks them, the browser test commands will fail. The suite
  runner can still scoring for diff + grep checks, but the Playwright
  command will show exit ≠ 0.
- The bench runner sets `BROWSER_METADATA` so future versions can wire
  stricter browser-required gating; today the fixture only checks file
  presence in verification.

## Current status

Rejected as pair-lift evidence. `20260512-f4-web-headroom` measured bare 70 /
solo_claude 92, with a +22 solo-over-bare margin, but failed headroom because
bare exceeded 60, solo exceeded 80, and bare carried judge/result/verify
disqualifiers. Rework the fixture or verifier before spending a pair arm on it.

## Rotation trigger

When both `bare` and `solo_claude` consistently produce correct output AND
include accessible markup without pipeline intervention, rotate to a harder UI
task (e.g., a form with validation states).
