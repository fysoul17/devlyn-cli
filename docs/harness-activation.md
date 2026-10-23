# Engine activation contract (CLI-3)

`activation --plan --release-root <absolute release> --context-file <absolute file|-> --json`
is read-only. `-` reads UTF-8 JSON from stdin. APP-2 invokes this after finalizing
the account environment and reading effective owner configuration, before saving
launch provenance. Arguments are native argv elements, never shell fragments.
The app retains its permission flags, PTY/monitor wrapper and prompt transport.

The result envelope is `{schemaVersion:1,ok:true,data:ActivationPlan}`; failure is
`{schemaVersion:1,ok:false,error:Reason}` with diagnostics on stderr. Exit codes:
0 success, 1 operational failure, 2 invalid context/arguments, 3 conflict.
Partial/unavailable channel coverage is a successful plan, not a launch claim.

```ts
type EngineId = "claude" | "codex" | "grok" | "omp" | "antigravity" | "cursor"
  | "opencode" | "kimi" | "copilot" | "qwen";
type Coverage = "configured" | "partial" | "unavailable" | "disabled";
type ReleaseRef = {
  package: "devlyn-cli"; version: string; digest: string; root: string;
};
type Reason = { code: string; params: Record<string, string | number | boolean> };
type ChannelStatus = { state: Coverage; mechanism: string | null; reasons: Reason[] };
type EngineStatus = {
  engine: EngineId; version: string | null; accountRef: string | null;
  overall: Coverage;
  principles: ChannelStatus; skills: ChannelStatus; hide: ChannelStatus;
  invocation: { kind: "slash" | "dollar" | "read-file"; text: string } | null;
  executor: { supported: boolean; reasons: Reason[] };
  inheritedDevlyn: string[];
};
type ActivationContext = {
  schemaVersion: 1;
  engine: EngineId;
  version: string | null;              // normalized CLI version, no product prefix
  launchMode: "fresh" | "resume" | "fork";
  cwd: string;                        // absolute
  runDir: string;                     // absolute, app-owned per-run directory
  projectChoice: "default" | "devlyn" | "none";
  committedBlockApplies: boolean;     // verified native applicability, not file presence
  initialPrompt: { text: string; transport: "argv" | "stdin" } | null;
  accountRef?: string | null;          // opaque account ID; never credentials
  accountHome?: string;               // Codex: existing absolute CODEX_HOME
  skillRoots?: string[];              // extra effective discovery roots, absolute
  effectiveConfig: EffectiveConfig | null;
  recordedRelease?: ReleaseRef | null;
};
type ActivationPlan = {
  schemaVersion: 1;
  release: ReleaseRef | null;
  engineArgs: string[];
  envPatch: Record<string, string | null>;
  prompt: { text: string; transport: "argv" | "stdin" } | null;
  files: Array<{ relativePath: string; utf8: string; sha256: string }>;
  machineSync: { engine: "codex"; accountHome: string } | null;
  channels: EngineStatus;
};
```

`effectiveConfig` is the following engine-specific object. Missing optional
values mean unset; `null` for the whole object means the config read failed.
Unknown top-level context/config keys are refused, so callers cannot accidentally
serialize the entire environment or a complete app-server response. The caller
must exclude credentials from nested effective values too.

```ts
type EffectiveConfig =
  // claude, omp and qwen: read append files into text before planning.
  | { appendSystemPrompt?: string | null; pluginDirs?: string[] } // claude: effective enabled/launch plugin roots, absolute
  | { appendSystemPrompt?: string | null } // qwen
  | { // codex: values from config/read using final cwd, profile and owner overrides
      developer_instructions?: string | null;
      skills?: { config?: Array<{ path: string; enabled: boolean }> } | null;
      marketplaces?: Record<string, { source_type: string; source: string }> | null;
      plugins?: Record<string, { enabled: boolean }> | null;
    }
  | { rules?: string | null } // grok
  | { // omp: effective skills subtree, including other owner skill settings
      appendSystemPrompt?: string | null;
      skills?: {
        customDirectories?: string[]; ignoredSkills?: string[];
        enableSkillCommands?: boolean; [key: string]: unknown;
      } | null;
    }
  | { inlineConfig?: string | null } // opencode: OPENCODE_CONFIG_CONTENT JSON text
  | { ownerAgent: boolean } // kimi: explicit owner-selected agent/profile?
  | { skillsDirs?: string | null } // copilot: effective COPILOT_SKILLS_DIRS
  | Record<string, never>; // antigravity, cursor
```

The returned segment replaces the recipe's existing append/config segment in
the launch command. Supply effective append text (not a filename or the already
activated harness text). Preserve all other argv. For example, OMP receives one
merged append argument and a skills overlay; the app retains other owner config
flags. Codex table overrides preserve owner plugins/marketplaces; they do not
write config.toml. `prompt:null` leaves the original task untouched. A non-null
prompt replaces the already requested task and retains its transport.

The app writes each `files` entry exclusively under `runDir`, checks its SHA-256,
and retains these bytes/hashes with session provenance. It performs `machineSync`
before launch, then splices `engineArgs` inside the monitored inner command and
applies `envPatch` to that process. A sync conflict is not successful activation.
No new task/model turn is created for an empty terminal.

Fresh selection uses the supplied release root. On resume/fork, `recordedRelease`
is mandatory: a reference selects and verifies that exact release (even if the
project choice is now None); explicit null preserves a disabled session; omission
returns partial legacy coverage without injecting anything. APP-2 retains the
recorded principles source when setting `committedBlockApplies`. This contract
does not claim behavioral resume/child propagation qualification.

None emits no managed activation. Codex can still return targeted hide overrides
for fingerprint-proven ordinary skills or marker-and-content-proven registered
plugins. Owner skills/plugins are preserved. `inheritedDevlyn` contains proven
skill file paths and proven `devlyn@marketplace` registration keys. Other engines
report inherited content and partial hide without broad disable flags.

`status --project <absolute> --engine <id> --context-file <absolute> --json`
returns the same `EngineStatus` in `data.engines[0]`; context engine/CWD must match
the request. Status without context retains CLI-1's pure inspection surface.

## Codex projection

```text
machine sync --release-root <absolute> --engine codex --account-home <absolute> --json
```

```ts
type MachineSyncResult = {
  release: ReleaseRef; projectionRoot: string; created: boolean; markerSha256: string;
};
// <account-home>/plugins/cache/devlyn-harness-v<VERSION-WITH-DASHES>/devlyn/<version>/
// .devlyn-harness-projection.json — exact CLI-2 resolver contract:
type ProjectionMarker = {
  schemaVersion: 1;
  release: ReleaseRef;
  source: "native/codex/plugins/devlyn";
};
```

Sync verifies the release, publishes a regular copy of its native Codex plugin,
and verifies every file/mode plus the marker on retries. Modified/unmarked cache
entries, extra files/directories, links and hardlinks are conflicts. Account-home
aliases resolve physically; cache descendants cannot be links. A temporary
exclusive publication lock prevents simultaneous writers; an interrupted lock is
an explicit conflict requiring inspection. No persistent registration or owner
config is written. The marker plus `DEVLYN_HARNESS_ROOT` resolve execution back
to the verified release, never to a cache-local queue implementation.

## Qualification and reasons

Capability floors live beside CLI-1's single engine list in `bin/engines.js`.
Floors are the examined versions, not historical introduction claims. A newer
release of the examined major (a newer Cursor build) is taken as compatible; a
new major is refused with `engine-version-unsupported`. Configured means prepared delivery,
not a model obeyed instructions. Only the existing Claude/Codex executor adapters
are supported. OMP explicitly declares `executor: no`.

Channel reason codes: `principles-task-only`, `principles-unavailable`,
`skills-catalog`, `skills-unavailable`, `engine-version-unsupported`,
`name-collision`, `config-unreadable`. New code: **`executor-unqualified`** with
`{engine}`; none of the channel codes describes an unqualified executor.
Existing CLI-1 release/argument/operational error codes remain unchanged.

The catalog names the verified release's `config/skills/_shared` absolutely and
supersedes the defaults' installed-folder references. Claude's single per-run
append file contains existing append text, immutable defaults (unless native
project principles apply), and this catalog. OMP/Qwen/Grok merge owner append
text; OpenCode preserves inline keys/instruction entries. Copilot principles
remain unavailable; Kimi cannot replace an owner agent or a resumed profile;
Cursor/Antigravity remain partial with task-only delivery.

Tests: `python3 scripts/test-harness-activation.py --codex-probe` packs/extracts
and tests the actual release. Set `TMPDIR` to the supplied scratch directory.
The optional native probe uses only `codex debug prompt-input` under isolated
HOME/CODEX_HOME. Windows path/TOML/argv fixtures also run on macOS; those results
do not establish native Windows runtime qualification.

The app sets `DEVLYN_NODE` to the absolute executable path of the Node runtime it
selected, both for CLI calls and in every harness session's environment. Python
release verification runs devlyn-cli on that runtime; project and engine commands
keep the session's own Node lookup. An unset variable uses the normal Node lookup;
an empty, relative, missing, non-file or non-executable override fails explicitly
instead of falling back to PATH.
