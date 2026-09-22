# 0211 — repair startup and continue the approved comparison

2026-09-22. User: “계속 해 … 해결하고 진행해”. Root direct, no resolve.
The0210 failed attempt remains immutable. This instruction authorizes fixing
its pre-dispatch setup and a fresh capability attempt; the already approved
observational contract remains effective without another approval request.
Public tasks, order, models, candidate and observed targets remain0206/0210.

The violated invariant was configuration validity before model dispatch.
Delete the reserved `model_providers.openai` override. Use the supported custom
ID `observed-openai` with the same OpenAI name, native authentication, implicit
auth-selected endpoint, Responses/WebSocket capabilities and version headers.
Only retry settings differ from the built-in: request and stream retries are0.
Pinned codex-client `run_with_retry` uses `0..=max_attempts`, so0 still makes
one initial request; the previous native loopback also completed with both0.
The unchanged adapter mounts the private existing auth files read-only at
`/home/participant/.codex/auth.json` and `/credentials/claude.json`; credentials
are excluded from evidence. The config control intentionally mounts no auth.
There is no proxy, credential endpoint override or engine patch. All arms use
the same [configuration](codex.toml). Codex0.155.1 provider source confirms the
OpenAI name selects its native backend capabilities and auth selects its URL.

Prediction before inference: the old config fails on its reserved provider ID;
the corrected config loads in the pinned Linux image without credentials or
network. CLI `features list` exercises bootstrap loading, not inference or a
full strict-config launch. Unsupported strict flags on inspection subcommands
are retained setup-control failures, not evidence that a config loaded.
The actual capability run retains `exec --strict-config`.

Reuse0210's unchanged image, accounting/teardown controls and one-cell adapter.
The fresh capability attempt requires one Astra/high owner, exactly one native
child, one Fable5.1/medium review and independent function/unit checks. Keep
600s/20,000 OUTPUT/400,000 cache-inclusive INPUT/3 invocation observed targets.
Record every setup attempt; no model result is replaced. Any actual-call usage,
identity, lineage, budget or teardown failure stops collection as approved.
No public task starts before this capability check and the complete launch seal.

Shared Docker VM file handles affect conservative disposable-file cleanup;
they are not the startup error and do not gate the user's continued execution.
Preserve0210 evidence and unrelated work; do not stop the shared VM.
