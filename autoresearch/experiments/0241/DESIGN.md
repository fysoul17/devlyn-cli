# 0241: bind peer configuration and capture provenance

Prospective repair of 0240's failed operational validation, 2026-10-10 UTC /
2026-10-11 KST. No old run is regraded, no product pair is admitted, and the
stopped 0238/0240 sequences remain stopped. Guides, root trigger, task semantics,
models, effort, owner capability, resource limits and watchdogs remain unchanged.

Two independently observed defects require correction before more native work.

1. In 0240 s01-h-codex, fresh and resumed peer argv include
   `features.multi_agent=false`, but actual initial request tool definitions still
   expose `collaboration.spawn_agent` and its companion tools. No child happened
   to run; that does not satisfy the registered capability restriction. The pinned
   CLI's network-disabled, credential-free `debug prompt-input` diagnostic shows
   that `agents.enabled=false` removes the multi-agent instruction blocks while
   the feature flag leaves them unchanged. The renderer contains no tool
   definitions. Replace only the peer flag; actual fresh/resume native catalogs
   must still demonstrate tool removal. This does not restrict the outer owner.
2. The owner wrote ordinary witness metadata to `peer-check.json`. The inherited
   collector interpreted its filename as evidence of a Claude result and marked
   it unreadable, including the custody copy. Actual helper receipts identify
   Codex captures; there are no Claude sessions. Expected model captures must
   be grounded in receipts or observed native launch/dispatch records. A filename
   alone cannot establish that a model ran. Preserve content-based discovery of
   valid native envelopes and all session/identity/missing-usage checks.

**No workaround:** repair the selecting configuration and capture classification,
not the owner's filenames, saved verdict or genuine accounting gaps. Do not
discard errors after collection, treat interrupted inference as free, or bypass
the inherited STOP guard. A declared capture that is absent, malformed or missing
its required native accounting remains an explicit failure. Valid unregistered
native sessions/results remain visible and require attribution.

**No overengineering / Best practice:** use the documented current setting and
one prospective discovery module on the runner's already shared evidence object.
Reuse the inherited runner, usage recorder, terminal reconciliation, peer policy,
evaluator and delivery checks. Avoid a replacement framework or global CLI
configuration change. New files and input identities preserve frozen history.

**No guesswork:** fixture controls must distinguish ordinary similarly named JSON
from declared captures, retain native interrupted/malformed/unregistered cases,
and demonstrate shared wiring into identity, policy and both accounting layers.
Offline replay may diagnose retained evidence into new output only; it cannot
replace an old verdict or license efficacy. Register and freeze any new native
sequence only after implementation review, source/package integrity, targeted
installation checks and comparison of reused evaluator inputs.

The source and local delivery observed in 0240 s01 remain useful protocol facts;
its raw STOP/PARTIAL and failed capability gate are preserved. Research cost is
retained separately from future task-efficiency comparisons. No performance gain
follows from either repair by itself.

Evidence: `../0240/results/s01-integrity-audit.json`,
`../0240/results/s01-artifact-accounting-audit.md`,
`../0240/results/config-probe-v1.json`, and
`../0240/results/config-repair-review-v1.md`.
The current setting is documented in the
[official configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference).
