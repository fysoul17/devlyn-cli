# 0212 — compact input worked; stale account snapshot stopped execution

Root direct, no resolve. The user approved a fresh24-cell observational screen
with the same numerical targets and reduced review input. Source was sealed at
175cdb7. Fable5.1 and Grok4.7 accepted the final packet implementation; five
packet tests and seven native-accounting tests passed. Restoring the old
assessor duration-line filter makes the new evidence-preservation test fail.

The new D1/repetition1/A reached independent review with a42,748-byte packet.
Its65 variadic regressions passed; the full suite reported1,416 passed,2 failed,
1 skipped. Both color-environment failures also reproduced with the original
detector. The cell was not externally assessed or completed.

Fable returned HTTP429 after1.82s: five_hour rejected, modelUsage empty.
The controller stopped the entire screen and removed the private container at
138.53s. Last observed native usage was183,035 cache-inclusive INPUT and3,441
OUTPUT. No numerical target breach was observed. Terminal all-attempt usage is
UNKNOWN, not zero. Raw classes are UNKNOWN and INFRA_INVALID. This screen has
1 attempted,23 NOT_RUN and0 external assessments. The prior0211 stopped attempt
and377 original evidence files remain byte-identical; two public attempts total.

## Corrected cause

The initial report incorrectly generalized that rejection to the user's current
account. On2026-09-22 at14:23UTC, read-only OAuth profile and usage calls showed
that the frozen container credential and the current macOS login belonged to
**different accounts and organizations**. The frozen account's five-hour usage
was100%; the current account's was33%. Different token bytes alone would not
prove this; both profile responses returned200 and their identity fingerprints
differed. The old account's reset time does not describe the current account.

The root cause was continued reuse of0210's credential snapshot after the active
login changed. A separate0600 credential snapshot of the current login is now
prepared in owned private scratch; old credentials and failed-run evidence are
preserved. No API keys, OAuth tokens or personal account identifiers are included
in this report. Fable is not inherently unavailable; Opus substitution is not
required to fix this routing error.

Before the next launch, compare the selected current-login and frozen snapshot
account/organization identities and usage, bind that snapshot to both participant
review and assessment, and seal the identity fingerprints with the runtime.
Do not silently rotate accounts or change models within a screen. The stopped
screen remains stopped; no result may be replaced or selectively excluded.

Evidence: `.devlyn/0212/launch-seal.json`, `screen-stop.json`, `stop-guards.json`,
`auth-diagnosis.json`, `auth-repair.json`, `packet-regression-controls.json` and
`cells/01-D1-1-A/`. No comparative quality, efficiency or adoption conclusion.
