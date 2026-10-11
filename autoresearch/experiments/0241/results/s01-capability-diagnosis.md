# 0241 s01 capability diagnosis

The native peer requests retain **both the collaboration catalog and the multi-agent instruction blocks** despite `agents.enabled=false`. The earlier debug probe did not reproduce the preserved owner's explicit `features.multi_agent_v2.enabled=true` setting. A new credential-free, network-disabled contrast reproduces that instruction-path interaction. It does not establish a native tool-removal fix.

Evidence and raw offline outputs are in `s01-capability-diagnosis.json`. No frozen input, earlier report, raw cell or verdict was changed. The only new execution was three `debug prompt-input` diagnostics in the same pinned image, with `--network none`, no mounted host directories or credentials, and a recorded prediction before execution. No model, authentication or native task call was made. The OpenAI Docs skill was consulted; this task's explicit no-network boundary takes precedence over its documentation-search workflow.

## Native observations

Cell: `/Users/aipalm/.local/share/nx01/0241-live/staged-v3/out-smoke/s01-h-codex`.

- Owner session: `01a12676-3aef-7851-9c9c-d81351b81b33`, trace `0f390e28-098f-4e39-b88e-b8499104856c`.
- Fresh peer: trace `ced8172e-3322-4da9-b60f-efaab0f96c75`, started at `1791646805734` ms, matching review1's attempt at `1791646805682159883` ns.
- Resume: trace `98c940a2-1a92-4c6c-b015-e6c9498b27b0`, started at `1791646878447` ms, matching review2's attempt at `1791646878395845889` ns.
- Both peer turns use session `01a12678-aede-7d52-bae3-84b3b6e297c6`. Timestamp and receipt binding corrects the fresh/resume labels supplied in the diagnostic handoff.

Both attempt receipts include literal `-c agents.enabled=false`. Both native session-configuration payloads show `gpt-6-astra`, effort `max`, approval policy `never`, read-only file permissions and restricted network. Thus other peer overrides visibly take effect; there is no evidence that all CLI overrides were ignored. The session-configuration payload does not expose the effective agents configuration, so it cannot independently prove precedence for that setting.

Each peer trace's `payloads/4.json` is linked from its `inference_started` event as an `inference_request`, not a printed example or copied answer. Its `input` contains an `additional_tools` developer item with six collaboration definitions: `followup_task`, `interrupt_agent`, `list_agents`, `send_message`, `spawn_agent`, `wait_agent`. The owner also has these six definitions. The peer initial requests also retain `<multi_agent_role>` and `<multi_agent_mode>` messages with the same text hashes as the owner's respective blocks. They advertise five concurrency slots. The retained home config contains:

```toml
[features.multi_agent_v2]
enabled = true
expose_spawn_agent_model_overrides = false
[agents]
default_subagent_model = "gpt-6-sol"
default_subagent_reasoning_effort = "high"
max_concurrent_threads_per_session = 4
```

The native request proves these tools were **advertised to the model**. It does not prove a tool handler would accept a spawn request, nor that a remote server inserted the catalog. No retained event identifies the assembly layer that selected those definitions. Calling them server-injected or asserting successful callable capability would exceed the evidence.

Both helper completions report `EXITED`, exit code 0 and `source_unchanged=true`. The fresh peer has two inferences and three `exec_command` inspections; the resume has one inference and no tool invocation. Each peer trace contains one root `thread_started` event, and neither contains a child thread or collaboration invocation. These are positive observations of a completed single-peer workflow, not proof of hard capability removal.

## Why the previous probe was insufficient

The retained 0240 default and legacy-flag debug captures include both multi-agent instruction blocks; its `agents.enabled=false` capture omits them. All three omit tool catalogs. That experiment used an unmounted, empty home and did not set the explicit multi-agent-v2 feature present in native owner/peer runs. Its prompt-level observation was correct but insufficiently representative. Native 0240 and 0241 initial request catalogs both expose the same six collaboration functions.

The new prospective prediction and raw results are preserved in the companion JSON. Same image: `sha256:0f472bb41685b7daa5923d51d31983f4b3c70053dd773fdf712bd0dcd6d87998`. Same debug command and model argument; only these configuration contrasts differ:

| Offline overrides | Role blocks | Mode blocks | Tool catalog | Exit |
| --- | ---: | ---: | --- | ---: |
| `agents.enabled=false` | 0 | 0 | Not emitted | 0 |
| `features.multi_agent_v2.enabled=true`, `agents.enabled=false` | 1 | 1 | Not emitted | 0 |
| `features.multi_agent_v2.enabled=false`, `agents.enabled=false` | 0 | 0 | Not emitted | 0 |

This establishes a causal interaction in the pinned **debug instruction renderer**: explicit v2 enablement restores the blocks despite the agents override. Together with the retained native configuration, it explains why extrapolating the earlier empty-home prompt result was unsound. It does not prove the internal precedence mechanism or establish that the same v2 override removes native tool definitions. No statement that “native instructions are disabled but tools remain” is supported: the native instructions remained too.

## The invariant needs to remain explicit

Three different claims must stay separate:

1. The peer did not delegate in this observed run — supported by retained native traces.
2. The model was not offered collaboration tools — contradicted by the actual request.
3. The runtime could not execute any delegation — untested; catalog presence alone does not settle handler enforcement.

Under **No guesswork**, neither two successful no-child turns nor renderer instruction removal establishes claim 2 or 3. The registered 0241 hard-catalog-removal criterion therefore remains unsatisfied. Under **No workaround**, old outcomes cannot be regraded by substituting observed compliance for the registered criterion.

For future design, the user's single independent reviewer objective does not logically require absent tool definitions if the intended guarantee is behavioral compliance with an auditable no-delegation protocol. If the guarantee instead is that delegation is technically impossible, it requires an enforced capability boundary, and catalog inspection alone is weaker than an execution-denial guarantee. Those are distinct prospective designs; this diagnosis chooses neither. **No overengineering** calls for deciding which guarantee is actually needed before spending further native runs on incidental configuration names.

Hard removal is not proven impossible or unsupported on this CLI. The available evidence leaves a specific untested configuration interaction; the renderer result is a lead, not permission to change treatment or run another task. Conversely, documentation or renderer output alone must not be sold as native proof.

## Raw outcome remains separate

The raw verdict remains `STOP`, usage `PARTIAL`, reason `ValueError: peer model identity/evidence UNVERIFIED`; its SHA-256 is `86e879e57de68761b8b11393deabe3c6d3f0e46890e3b826d6b328ceea8696e6`. The receipt-matching issue underlying that recorded STOP is under separate investigation. The catalog failure is independently observed and is not presented as the code path that emitted this raw STOP.

No new treatment, admission, efficacy claim or retrospective regrade follows from this diagnosis.
