# Configuration repair review v1

**SHIP-for-testing: replace only the prospective Codex peer override with `-c agents.enabled=false` on fresh and resume.** No blocking HIGH in this proposed repair. This does not establish native tool removal or approve implementation/adoption. Owner configuration, primary model/effort, accounting and all STOP gates must remain unchanged.

The previous feature-metadata check was insufficient: a reported legacy feature value did not establish the effective request tool catalog. Parent reports both actual fresh/resume peer catalogs still exposed collaboration/spawn_agent despite features.multi_agent=false. Preserve that failed assumption and native result; do not reinterpret it as a passing single-peer transport.

Independently inspected all three network-disabled, credential-free debug-renderer captures and verified their hashes against config-probe-v1.json. Default and legacy retain multi_agent_role and spawn_agent developer-instruction text. The agents.enabled=false capture removes both. All commands exited0. This is direct evidence the pinned CLI recognizes a setting with the desired prompt-level effect, unlike the legacy feature override; it justifies the narrow replacement hypothesis under No guesswork and No workaround. No extra layer of prompt text or experimental preemption switch is warranted.

The renderer contains messages, not inference tool definitions. Consequently instruction removal does not prove collaboration tools are absent, does not establish execution/resume behavior, and does not guarantee absence of independently launched CLI processes. The official-reference description supplied by parent is corroborating context, not an independently verified source in this bounded review; the pinned offline capture is the operative evidence.

Before native validation, pin a new implementation/manifest and verify that argv changes only this key for both Codex peer paths; preserve owner capability and all historical bytes/results. Then inspect actual fresh and resumed request tool catalogs and captured thread/session ancestry under the new flag. Require complete native identity, usage, source stability, valid answers and teardown as before. No child call observed is insufficient if the spawning tool remains advertised. Keep the prior failed catalog check distinct and visible; do not pool it as equivalent treatment evidence. If the replacement still exposes delegation, stop and diagnose instead of adding speculative flags.

The reported witness-output filename accounting collision is outside this review; no judgment here changes its STOP outcome. No model/native/auth/test execution, source modification, or frozen-input mutation was performed.

## Checked hashes

- `/Users/aipalm/.local/share/nx01/0237-harness/autoresearch/experiments/0240/results/config-probe-v1.json`: `a15d05ede33bedad935be13033e58bee071ca6be6b41fe485987cc6b4618ddad`
- `/Users/aipalm/.local/share/nx01/0240-live/config-probe-v1/agents.json`: `f76a6336f275cd7604dade5a3b1e599509982f5eaa40c404c232b094cc0d1e0e`
- `/Users/aipalm/.local/share/nx01/0240-live/config-probe-v1/default.json`: `d12406149ae4b89bb1a691a110c4782046bb9acb2af4d4111da03953b481db00`
- `/Users/aipalm/.local/share/nx01/0240-live/config-probe-v1/legacy.json`: `2d1c6ae84fd64ca9ff41d459dd69d4cca9642d211b0036314c8a17cc961db5ef`
