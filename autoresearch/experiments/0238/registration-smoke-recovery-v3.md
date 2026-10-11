# 0238 native transport after observed DNS recovery

2026-10-10, prospective before s01-h-claude-v3. This adds a fresh transport
attempt after an observed infrastructure failure; it does not replace or regrade
s01-h-claude-v2. The v2 owner exited nonzero after 1327.9404953750054 seconds.
The fresh peer and later owner requests both report getaddrinfo EAI_AGAIN for
api.anthropic.com. The peer produced no genuine native model response. Preserve
STOP, unverified peer evidence, and the 1,852,747 input / 74,086 output lower
bounds; unbound error requests leave whole usage UNKNOWN/PARTIAL.

The predeclared, unauthenticated connectivity probe at 14:07:07 UTC passed DNS
and HTTPS in the same image, bridge, security and resource configuration. No
resolver, authentication, prompt, source, launcher or resource setting changed.
The precise historical failing DNS hop is unknown. Current recovery supports a
fresh transport attempt, not a claim that the previous attempt passed.

Keep runtime-smoke-v2.json and all 75 execution inputs and 17 selected artifacts
from freeze-smoke-v2.json unchanged. Bind this addendum and the diagnosis/recovery
evidence in freeze-smoke-v3.json before dispatch. Use the following serial order:

1. s01-h-claude-v3: S2, H, Claude (new recovery attempt).
2. s02-h-codex-v2: S2, H, Codex (still unstarted).
3. s03-p-claude-v2: S2, P, Claude (still unstarted).
4. s04-p-codex-v2: S2, P, Codex (still unstarted).

Every original registration-smoke.md acceptance and stop rule remains in force,
including fresh/resumed identity, source stability, local delivery, full native
accounting, clean teardown and preflight account/lifetime verification. The same
watchdogs apply. No independent study calls or heavy checks during a native owner.
On another failure, stop for its named diagnosis; recovery retries are never an
automatic loop until a favorable result. This remains forced transport evidence,
not pair efficacy, automatic activation, or a product admission.
