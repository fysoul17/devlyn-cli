I’ll verify the frozen contract, registration hashes, and staged smoke evidence read-only, with parallel checks for contract drift and cell qualification. I’ll avoid the credential files and leave unchanged apparatus code out of scope.
hook: PreToolUse
hook: PreToolUse Completed
exec
/bin/zsh -lc "pwd && git status --short && git branch --show-current && git rev-parse HEAD && git show --stat --oneline 9b409492 && git diff 21699994 HEAD -- '*.py'" in /Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d2-rerun
 succeeded in 153ms:
/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d2-rerun
research/rp-d2-rerun
9b4094921b634e20e8fe495cbad99b02551cb31b
9b409492 research(rp-d2): register unchanged rerun 20261015a before exposure (smoke attempt 1 qualified)
 .../rp-d2-report-lines/registration-20261015a.json | 227 +++++++++++++++++++++
 .../experiments/rp-d2-report-lines/registration.md |  37 ++++
 2 files changed, 264 insertions(+)

hook: PostToolUse
hook: PostToolUse
hook: PostToolUse Completed
hook: PostToolUse Completed
hook: PreToolUse
hook: PreToolUse Completed
hook: PostToolUse
hook: PostToolUse
hook: PostToolUse Completed
hook: PostToolUse Completed
2026-10-15T14:29:46.553930Z ERROR codex_rmcp_client::oauth::refresh_transaction: error=failed to refresh OAuth tokens for server notion: OAuth refresh token was rejected: Server returned error response: invalid_grant: OAuth grant revoked
2026-10-15T14:29:47.174619Z ERROR rmcp::transport::worker: worker quit with fatal: Transport channel closed, when AuthRequired(AuthRequiredError { www_authenticate_header: "Bearer resource_metadata=\"https://mcp.context7.com/.well-known/oauth-protected-resource/mcp\"" })
[codex-monitored] heartbeat: elapsed=30s
hook: PreToolUse
hook: PreToolUse Completed
hook: PostToolUse
hook: PostToolUse
hook: PostToolUse Completed
hook: PostToolUse Completed
2026-10-15T14:29:54.167897Z ERROR codex_rmcp_client::oauth::refresh_transaction: error=failed to refresh OAuth tokens for server notion: OAuth refresh token was rejected: Server returned error response: invalid_grant: OAuth grant revoked
2026-10-15T14:29:54.697627Z ERROR rmcp::transport::worker: worker quit with fatal: Transport channel closed, when AuthRequired(AuthRequiredError { www_authenticate_header: "Bearer resource_metadata=\"https://mcp.context7.com/.well-known/oauth-protected-resource/mcp\"" })
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc 'cat /Users/aipalm/.local/share/nx01/rp-d2-rerun-live/notes/make-registration.py && cat /Users/aipalm/.local/share/nx01/rp-d2-rerun-live/notes/route-watch.log && cat autoresearch/experiments/rp-d2-report-lines/registration.json' in /Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d2-rerun
 succeeded in 0ms:
import hashlib, json, subprocess, importlib.util
from pathlib import Path
L = Path.home()/'.local/share/nx01/rp-d2-rerun-live'; W = Path.cwd()
d = W/'autoresearch/experiments/rp-d2-report-lines'; p1 = W/'autoresearch/experiments/rp-d1-delivery-cost'
h = lambda f: hashlib.sha256(Path(f).read_bytes()).hexdigest()
rt = json.loads((L/'stage/runtime-measured.json').read_text())
spec = importlib.util.spec_from_file_location('r', d/'runner.py'); r = importlib.util.module_from_spec(spec); spec.loader.exec_module(r)
so = L/'stage/smoke-output'
reg = dict(schema='rp-d2-registration-v1',
  apparatus_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
  run_id=rt['run_id'], phase='measured', supersedes_run_id='20261014a',
  schedule=[dict(slot=s, task=t, engine=e, arm=r.arm_for(s)) for s,t,e in r.SCHEDULE],
  repositories=[f"fysoul17/rpd2-{rt['run_id']}-{s}" for s,_,_ in r.SCHEDULE],
  releases={a: {k: v for k, v in rt['releases'][a].items() if k != 'tarball'} for a in ('X','Y')},
  image=rt['image'], cli=dict(claude='2.1.296', codex='0.162.1', gh='2.83.2'),
  routes=json.loads((p1/'tasks.json').read_text())['routes'],
  account=rt['account'], codex_account=rt['codex_account'], auth_manifest_sha256=rt['auth_manifest_sha256'],
  smoke_account=rt['smoke_account'], smoke_codex_account=rt['smoke_codex_account'],
  runtime_sha256=h(L/'stage/runtime-measured.json'),
  smoke=dict(attempt=1, verdicts={c: h(so/f'verdict-{c}.json') for c in ('smoke-claude-X','smoke-claude-Y','smoke-codex-X','smoke-codex-Y')},
             schedule_sha256=h(so/'rp-schedule.json')),
  inputs={str(f.relative_to(W)): h(f) for f in sorted(list(d.glob('*.py')) + [d/'DESIGN.md', d/'README.md'] + [p1/n for n in ('common.txt','tasks.json','oracle.py','runner.py','prepare.py','cell.py','github.py','summarize.py','reevaluate.py','Dockerfile','build.sh')])},
  live_inputs={k: h(v) for k, v in {'arms.json': L/'arms/arms.json', 'X.tgz': L/'arms/X.tgz', 'Y.tgz': L/'arms/Y.tgz',
      'control.manifest.json': L/'stage/control.manifest.json', 'models_cache.json': L/'stage/models_cache.json',
      'model-auth manifest.json': L/'model-auth-1/manifest.json'}.items()},
  watchdog_seconds=dict(owner=5400, evaluator_or_review=600))
(d/'registration-20261015a.json').write_text(json.dumps(reg, indent=1) + '\n')
print(reg['apparatus_commit'][:8], reg['account'], reg['codex_account'], reg['runtime_sha256'][:12], len(reg['inputs']))
2026-10-15T04:39:00Z default-route interface: en0
2026-10-15T07:54:45Z default-route interface: none
2026-10-15T09:28:08Z default-route interface: en0
2026-10-15T09:33:01Z default-route interface: utun4
2026-10-15T09:38:32Z default-route interface: en0
{
 "schema": "rp-d2-registration-v1",
 "apparatus_commit": "21699994b1257ccaccfae3129a68529e0c6040f9",
 "run_id": "20261014a",
 "phase": "measured",
 "schedule": [
  {
   "slot": "m01",
   "task": "BV",
   "engine": "claude",
   "arm": "X"
  },
  {
   "slot": "m02",
   "task": "BV",
   "engine": "claude",
   "arm": "Y"
  },
  {
   "slot": "m03",
   "task": "BV",
   "engine": "codex",
   "arm": "Y"
  },
  {
   "slot": "m04",
   "task": "BV",
   "engine": "codex",
   "arm": "X"
  },
  {
   "slot": "m05",
   "task": "Z0",
   "engine": "codex",
   "arm": "X"
  },
  {
   "slot": "m06",
   "task": "Z0",
   "engine": "codex",
   "arm": "Y"
  },
  {
   "slot": "m07",
   "task": "Z0",
   "engine": "claude",
   "arm": "Y"
  },
  {
   "slot": "m08",
   "task": "Z0",
   "engine": "claude",
   "arm": "X"
  },
  {
   "slot": "m09",
   "task": "Z0",
   "engine": "claude",
   "arm": "X"
  },
  {
   "slot": "m10",
   "task": "Z0",
   "engine": "claude",
   "arm": "Y"
  },
  {
   "slot": "m11",
   "task": "Z0",
   "engine": "codex",
   "arm": "Y"
  },
  {
   "slot": "m12",
   "task": "Z0",
   "engine": "codex",
   "arm": "X"
  },
  {
   "slot": "m13",
   "task": "BV",
   "engine": "codex",
   "arm": "X"
  },
  {
   "slot": "m14",
   "task": "BV",
   "engine": "codex",
   "arm": "Y"
  },
  {
   "slot": "m15",
   "task": "BV",
   "engine": "claude",
   "arm": "Y"
  },
  {
   "slot": "m16",
   "task": "BV",
   "engine": "claude",
   "arm": "X"
  }
 ],
 "repositories": [
  "fysoul17/rpd2-20261014a-m01",
  "fysoul17/rpd2-20261014a-m02",
  "fysoul17/rpd2-20261014a-m03",
  "fysoul17/rpd2-20261014a-m04",
  "fysoul17/rpd2-20261014a-m05",
  "fysoul17/rpd2-20261014a-m06",
  "fysoul17/rpd2-20261014a-m07",
  "fysoul17/rpd2-20261014a-m08",
  "fysoul17/rpd2-20261014a-m09",
  "fysoul17/rpd2-20261014a-m10",
  "fysoul17/rpd2-20261014a-m11",
  "fysoul17/rpd2-20261014a-m12",
  "fysoul17/rpd2-20261014a-m13",
  "fysoul17/rpd2-20261014a-m14",
  "fysoul17/rpd2-20261014a-m15",
  "fysoul17/rpd2-20261014a-m16"
 ],
 "releases": {
  "X": {
   "integrity": "sha512-yud5j6xq791XQlg6eVy8WkWTB/Ee7X0pn/Orbt0db4NvAKatEq577wyTT1Wo/x0FRKFRoXax1q+xxns97UXekw==",
   "manifest_sha256": "cd68caa4bcb0d64df14faa0c8647479ef532b6d84889aac096728b57f08cb2f5",
   "sha256": "7b22cce865d99e1400f9c0b0bff41c1b9ae3645b132cbb868ec01cadc973393e",
   "source": {
    "registry": "devlyn-cli@4.2.18"
   },
   "version": "4.2.18"
  },
  "Y": {
   "integrity": "sha512-eOKh4//n1WyIGfYBWLxs+7sTKgozAv5skd9MTJL9eA8qRrJ7Pz92UF7rV38smKDBLWMdAGn5YBV/TRMdURgUMg==",
   "manifest_sha256": "4141d0da1a6250d3af6c7614ef482726aa5d01619e941887438b17c0ad8996d7",
   "sha256": "c45bc13aec01f625a6687a9697854e705b3eb201fc2b0f1e01626e9f8dcaf603",
   "source": {
    "candidate_commit": "a623b382e655e893f6b39b96199ef8675afdde05",
    "registry": "devlyn-cli@4.2.18"
   },
   "version": "4.2.18"
  }
 },
 "image": "sha256:b55cbb940b6f7d21ca67e7ee39f221966b525c334608766eff31347571564eb0",
 "cli": {
  "claude": "2.1.296",
  "codex": "0.162.1",
  "gh": "2.83.2"
 },
 "routes": {
  "claude": {
   "owner": {
    "effort": "max",
    "engine": "claude",
    "model": "claude-opus-5-5"
   }
  },
  "codex": {
   "owner": {
    "child_effort": "high",
    "child_model": "gpt-6-sol",
    "effort": "high",
    "engine": "codex",
    "model": "gpt-6-sol"
   }
  }
 },
 "account": [
  "02b266ea50d2",
  "531f8e153d6b"
 ],
 "codex_account": "65ad276127a5",
 "auth_manifest_sha256": "9841482c834e99af9f58546fe95e7f7d10bdea336a7f5542b13a2e6ba34c3e3a",
 "smoke_account": [
  "cc43a4e02ede",
  "2905f4abf05b"
 ],
 "smoke_codex_account": "65ad276127a5",
 "runtime_sha256": "dfca27ffaf58b563ecd484644ff10b541f6cca38b998e0c794cf10a1fa30f075",
 "void_runtime_sha256": "513ec8521ec68bcccd1a357be4f8fd9c3663adcde724d531fb28d98f53dcc785",
 "smoke": {
  "attempt": 2,
  "verdicts": {
   "smoke2-claude-X": "c594e01b6382cdb7ee22db49ca0a15cfdf1db503bee10016248f1d93a4bbca6c",
   "smoke2-claude-Y": "572501ad8032b2b0a72492e3401cad9393cd07fb401e7504866484be0f5648af",
   "smoke2-codex-X": "300b1ba76f78e790b5af7afc7b4d92e834fe38ba2596533127afd2697eb3be8b",
   "smoke2-codex-Y": "5c2092ec903e00fc7ed41cd961a33b23a9d2f2075cf05a394fb101428b047db6"
  },
  "schedule_sha256": "8a4a225e6bd07556ab7687ef1bc7be8a8e81e5dfefffa7031fa3aeb2849beaf3",
  "stopped_attempt_1_schedule_sha256": "427adc72521099e30278f35d4739a4cfbfae9bc8dc01f8b7f23f319f9c972bbc"
 },
 "inputs": {
  "autoresearch/experiments/rp-d1-delivery-cost/Dockerfile": "6b9131a724e90aa381bb0e59411d31cdcff15a85a36a738df9f8f13278930b89",
  "autoresearch/experiments/rp-d1-delivery-cost/build.sh": "aefbfa7f764399804b3e8931a03afa1ac18c64aa2c168a199eb4e0c3869e582e",
  "autoresearch/experiments/rp-d1-delivery-cost/cell.py": "2a0f07a972fdfbab0d4c53039025507bda437d73c8f5e95163795c0e512d8678",
  "autoresearch/experiments/rp-d1-delivery-cost/common.txt": "2ccc7f6a11891f6270685c09ada44cc4376bbedb047f8a0864f950b415bf50cf",
  "autoresearch/experiments/rp-d1-delivery-cost/github.py": "64537542ff976cb280c4dcfb9e2bf65fddeef56684e034c5fea3304ae0d2aca9",
  "autoresearch/experiments/rp-d1-delivery-cost/oracle.py": "4c2d454662fd3c299dfac136bbff01d439ccd23af5b331d13b2e42cf44dab959",
  "autoresearch/experiments/rp-d1-delivery-cost/prepare.py": "6531b2958d81bbf4baff52fd118b61f43a05c26400569c4e2eb955947e5feb77",
  "autoresearch/experiments/rp-d1-delivery-cost/reevaluate.py": "4d122ddceedbeff80dbac9f93fb86ba8ac87b2fbc0b3037da7d8fdbde776e128",
  "autoresearch/experiments/rp-d1-delivery-cost/runner.py": "337af3003f76ec0407abf341752613c6bf87b094d47ffd7217d8f42ac115e811",
  "autoresearch/experiments/rp-d1-delivery-cost/summarize.py": "eb223d5222d6d50ee4c791a40dd49f26af0271c792ae799fb2cb484205e99be1",
  "autoresearch/experiments/rp-d1-delivery-cost/tasks.json": "12f4ef121cc0544ab1ffe42caf4cf5cc17d6df096cc1d2dcdd2565732c4f7ef7",
  "autoresearch/experiments/rp-d2-report-lines/DESIGN.md": "e623d7a8c8a39063c317813f50d083ebdbc0bdc37378e7159b51a09245022ddc",
  "autoresearch/experiments/rp-d2-report-lines/README.md": "3aa1ea55eee7889f9133b78244a9d48c72fafa5c6a6b4cb06e10cc918aded9ab",
  "autoresearch/experiments/rp-d2-report-lines/pack.py": "302f9f48c4bb3a3cb4a3c4d99d26f89e7ef6f3118f3b165fa574191f527b5aff",
  "autoresearch/experiments/rp-d2-report-lines/prepare.py": "43bffb00427388c1b2fc0f013cd1adf56130e979b2fb7f1d8bdd7ad1665aba76",
  "autoresearch/experiments/rp-d2-report-lines/reevaluate.py": "feb4129fa21ab55d81448d579ecd6a0be6e31a566308fe7f4d8c3422ab23ec44",
  "autoresearch/experiments/rp-d2-report-lines/runner.py": "6008e540d586ec9707fbe98016a558346241c398016a806e66f791ac4e1674a3",
  "autoresearch/experiments/rp-d2-report-lines/stage.py": "b4703ffae17e66242f0531e49c7656dd41faf74ddfcb68a954b3e14d242290e8",
  "autoresearch/experiments/rp-d2-report-lines/summarize.py": "92878ec0ea1225c8c25d2a8e2771eb75b788674b7200ee32cb866a64cfbdf4d2",
  "autoresearch/experiments/rp-d2-report-lines/test_rpd2_pack.py": "065553d0908a6555038b409526b88748b3a892bbbd4c973a174ebdb709421e7f",
  "autoresearch/experiments/rp-d2-report-lines/test_rpd2_runner.py": "6759792ed3b291f08e9c1171262f2b838b4ced4d3c6bbd26ad9235c985022cd1",
  "autoresearch/experiments/rp-d2-report-lines/test_rpd2_summary.py": "2e572d4cdb11b796f4be18d3f58f8501d8201172f2248f277d9e22d5eb599914",
  "autoresearch/experiments/rp-d2-report-lines/token_gate.py": "ec59c4f604fac2145cf9fa397b7ef0fe28493095839a5248fa962a5ff5cca7e7"
 },
 "live_inputs": {
  "arms.json": "60a97ad511ae2e2ce366a9b7905fb8c25c3bfaf718c12e24d822dde6d3236caa",
  "X.tgz": "7b22cce865d99e1400f9c0b0bff41c1b9ae3645b132cbb868ec01cadc973393e",
  "Y.tgz": "c45bc13aec01f625a6687a9697854e705b3eb201fc2b0f1e01626e9f8dcaf603",
  "control.manifest.json": "499d0476ec6fbfd1de222eef450ae0bdd3df25a7cbda0125ab441faf707e6db5",
  "models_cache.json": "0371c1bc63b4b9c8b7594484c072628543fb34e036174d64181a0fb43937ebeb",
  "model-auth manifest.json": "9841482c834e99af9f58546fe95e7f7d10bdea336a7f5542b13a2e6ba34c3e3a"
 },
 "watchdog_seconds": {
  "owner": 5400,
  "evaluator_or_review": 600
 }
}

hook: PostToolUse
hook: PostToolUse
exec
/bin/zsh -lc 'git show 9b409492 -- autoresearch/experiments/rp-d2-report-lines/registration.md && cat autoresearch/experiments/rp-d2-report-lines/registration-20261015a.json' in /Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d2-rerun
 succeeded in 0ms:
commit 9b4094921b634e20e8fe495cbad99b02551cb31b
Author: Terry K <fysoul17@hotmail.com>
Date:   Thu Oct 15 23:29:05 2026 +0900

    research(rp-d2): register unchanged rerun 20261015a before exposure (smoke attempt 1 qualified)

diff --git a/autoresearch/experiments/rp-d2-report-lines/registration.md b/autoresearch/experiments/rp-d2-report-lines/registration.md
index fd00d8b1..708a9a71 100644
--- a/autoresearch/experiments/rp-d2-report-lines/registration.md
+++ b/autoresearch/experiments/rp-d2-report-lines/registration.md
@@ -147,3 +147,40 @@ event the same way:
 4. **Write-up.** If Y is not adopted, the write-up reverts the paragraph
    before merge. The prompt ablation recorded in DESIGN.md is then the next
    candidate.
+
+## Rerun 20261015a (registered 2026-10-15, before exposure)
+
+Run 20261014a closed INCONCLUSIVE ([results](results.md)). The owner chose
+candidate 3 there: an unchanged rerun after the drop diagnosis. Everything
+above applies unchanged to run 20261015a: the prediction, the arms, the
+schedule, the grading, the cost and adoption rules, STOP and renewal. Its
+identities are in
+[registration-20261015a.json](registration-20261015a.json).
+
+- **Unchanged inputs.** The apparatus files, DESIGN.md, README.md, both arm
+  tarballs, `arms.json`, the control manifest, the image, the CLI versions and
+  the routes hash identically to [registration.json](registration.json).
+  `apparatus_commit` is the current main; no apparatus code changed since the
+  first registration.
+- **New per-run inputs.** The run ID, the 24 repositories, the GitHub PAT
+  (selected repositories only, Contents and Pull requests write), the model
+  auth snapshot and the Codex models cache. The cache is copied from the host
+  at staging, so its `fetched_at` differs. The Claude account pair is
+  `45eff57aaa45`/`b6b7768fd228` for smoke and measured; the Codex account is
+  unchanged.
+- **Network.** [Benchmark hard rule 5](../../../benchmark/README.md) applies:
+  the host network is held fixed for the whole run. A watcher logs every change
+  of the host's default-route interface. A change during a cell is reported
+  with that cell; it does not change any rule above.
+- **Smoke attempt 1 qualified all four cells.** No stream retry or API error
+  was recorded.
+
+| Cell | Owner s | Input | Output | Usage | Delivery | Repository |
+|---|---:|---:|---:|---|---|---|
+| Claude X | 572.4 | 2,519,890 | 59,060 | COMPLETE | passed | archived, deleted (404) |
+| Claude Y | 758.5 | 3,140,290 | 78,545 | COMPLETE | passed | archived, deleted (404) |
+| Codex X | 175.0 | 514,105 | 6,903 | COMPLETE | passed | archived, deleted (404) |
+| Codex Y | 131.8 | 381,285 | 5,889 | COMPLETE | passed | archived, deleted (404) |
+
+The run 20261014a smoke and measured records stay as they are and are never
+pooled with this run.
{
 "schema": "rp-d2-registration-v1",
 "apparatus_commit": "f5661c8170362970e0e21e4d7a2d2958aa9dfc1c",
 "run_id": "20261015a",
 "phase": "measured",
 "supersedes_run_id": "20261014a",
 "schedule": [
  {
   "slot": "m01",
   "task": "BV",
   "engine": "claude",
   "arm": "X"
  },
  {
   "slot": "m02",
   "task": "BV",
   "engine": "claude",
   "arm": "Y"
  },
  {
   "slot": "m03",
   "task": "BV",
   "engine": "codex",
   "arm": "Y"
  },
  {
   "slot": "m04",
   "task": "BV",
   "engine": "codex",
   "arm": "X"
  },
  {
   "slot": "m05",
   "task": "Z0",
   "engine": "codex",
   "arm": "X"
  },
  {
   "slot": "m06",
   "task": "Z0",
   "engine": "codex",
   "arm": "Y"
  },
  {
   "slot": "m07",
   "task": "Z0",
   "engine": "claude",
   "arm": "Y"
  },
  {
   "slot": "m08",
   "task": "Z0",
   "engine": "claude",
   "arm": "X"
  },
  {
   "slot": "m09",
   "task": "Z0",
   "engine": "claude",
   "arm": "X"
  },
  {
   "slot": "m10",
   "task": "Z0",
   "engine": "claude",
   "arm": "Y"
  },
  {
   "slot": "m11",
   "task": "Z0",
   "engine": "codex",
   "arm": "Y"
  },
  {
   "slot": "m12",
   "task": "Z0",
   "engine": "codex",
   "arm": "X"
  },
  {
   "slot": "m13",
   "task": "BV",
   "engine": "codex",
   "arm": "X"
  },
  {
   "slot": "m14",
   "task": "BV",
   "engine": "codex",
   "arm": "Y"
  },
  {
   "slot": "m15",
   "task": "BV",
   "engine": "claude",
   "arm": "Y"
  },
  {
   "slot": "m16",
   "task": "BV",
   "engine": "claude",
   "arm": "X"
  }
 ],
 "repositories": [
  "fysoul17/rpd2-20261015a-m01",
  "fysoul17/rpd2-20261015a-m02",
  "fysoul17/rpd2-20261015a-m03",
  "fysoul17/rpd2-20261015a-m04",
  "fysoul17/rpd2-20261015a-m05",
  "fysoul17/rpd2-20261015a-m06",
  "fysoul17/rpd2-20261015a-m07",
  "fysoul17/rpd2-20261015a-m08",
  "fysoul17/rpd2-20261015a-m09",
  "fysoul17/rpd2-20261015a-m10",
  "fysoul17/rpd2-20261015a-m11",
  "fysoul17/rpd2-20261015a-m12",
  "fysoul17/rpd2-20261015a-m13",
  "fysoul17/rpd2-20261015a-m14",
  "fysoul17/rpd2-20261015a-m15",
  "fysoul17/rpd2-20261015a-m16"
 ],
 "releases": {
  "X": {
   "integrity": "sha512-yud5j6xq791XQlg6eVy8WkWTB/Ee7X0pn/Orbt0db4NvAKatEq577wyTT1Wo/x0FRKFRoXax1q+xxns97UXekw==",
   "manifest_sha256": "cd68caa4bcb0d64df14faa0c8647479ef532b6d84889aac096728b57f08cb2f5",
   "sha256": "7b22cce865d99e1400f9c0b0bff41c1b9ae3645b132cbb868ec01cadc973393e",
   "source": {
    "registry": "devlyn-cli@4.2.18"
   },
   "version": "4.2.18"
  },
  "Y": {
   "integrity": "sha512-eOKh4//n1WyIGfYBWLxs+7sTKgozAv5skd9MTJL9eA8qRrJ7Pz92UF7rV38smKDBLWMdAGn5YBV/TRMdURgUMg==",
   "manifest_sha256": "4141d0da1a6250d3af6c7614ef482726aa5d01619e941887438b17c0ad8996d7",
   "sha256": "c45bc13aec01f625a6687a9697854e705b3eb201fc2b0f1e01626e9f8dcaf603",
   "source": {
    "candidate_commit": "a623b382e655e893f6b39b96199ef8675afdde05",
    "registry": "devlyn-cli@4.2.18"
   },
   "version": "4.2.18"
  }
 },
 "image": "sha256:b55cbb940b6f7d21ca67e7ee39f221966b525c334608766eff31347571564eb0",
 "cli": {
  "claude": "2.1.296",
  "codex": "0.162.1",
  "gh": "2.83.2"
 },
 "routes": {
  "claude": {
   "owner": {
    "effort": "max",
    "engine": "claude",
    "model": "claude-opus-5-5"
   }
  },
  "codex": {
   "owner": {
    "child_effort": "high",
    "child_model": "gpt-6-sol",
    "effort": "high",
    "engine": "codex",
    "model": "gpt-6-sol"
   }
  }
 },
 "account": [
  "45eff57aaa45",
  "b6b7768fd228"
 ],
 "codex_account": "65ad276127a5",
 "auth_manifest_sha256": "cd4fa3d350d13ad685c1c7f906e54060344e32f3e28cc6ea51401c6dfbf7aff5",
 "smoke_account": [
  "45eff57aaa45",
  "b6b7768fd228"
 ],
 "smoke_codex_account": "65ad276127a5",
 "runtime_sha256": "090f29f18fdd2bfde490f7d509087da4c593fd69b219ba5065f9f0ecbdf76b92",
 "smoke": {
  "attempt": 1,
  "verdicts": {
   "smoke-claude-X": "6a224081735324eccbcc5d18aed6865240f72e6d41c586992a6933f34dc4c0bc",
   "smoke-claude-Y": "b05561fbe9e73e5f12342f410f4093ba49c8a8164383becbb056c45b22de265a",
   "smoke-codex-X": "7a51ed653d5a9295a61bacc815304f14e99156c8e0861d2079f7928a9f451696",
   "smoke-codex-Y": "1701339b54a20da4de27201368503c36cffaca2799f89cdc21b1e3bdb8e7b10a"
  },
  "schedule_sha256": "e605cc00829d1396335dd5d4a885070d42a97678c5734c8cfc1839c243fe7cf8"
 },
 "inputs": {
  "autoresearch/experiments/rp-d1-delivery-cost/Dockerfile": "6b9131a724e90aa381bb0e59411d31cdcff15a85a36a738df9f8f13278930b89",
  "autoresearch/experiments/rp-d1-delivery-cost/build.sh": "aefbfa7f764399804b3e8931a03afa1ac18c64aa2c168a199eb4e0c3869e582e",
  "autoresearch/experiments/rp-d1-delivery-cost/cell.py": "2a0f07a972fdfbab0d4c53039025507bda437d73c8f5e95163795c0e512d8678",
  "autoresearch/experiments/rp-d1-delivery-cost/common.txt": "2ccc7f6a11891f6270685c09ada44cc4376bbedb047f8a0864f950b415bf50cf",
  "autoresearch/experiments/rp-d1-delivery-cost/github.py": "64537542ff976cb280c4dcfb9e2bf65fddeef56684e034c5fea3304ae0d2aca9",
  "autoresearch/experiments/rp-d1-delivery-cost/oracle.py": "4c2d454662fd3c299dfac136bbff01d439ccd23af5b331d13b2e42cf44dab959",
  "autoresearch/experiments/rp-d1-delivery-cost/prepare.py": "6531b2958d81bbf4baff52fd118b61f43a05c26400569c4e2eb955947e5feb77",
  "autoresearch/experiments/rp-d1-delivery-cost/reevaluate.py": "4d122ddceedbeff80dbac9f93fb86ba8ac87b2fbc0b3037da7d8fdbde776e128",
  "autoresearch/experiments/rp-d1-delivery-cost/runner.py": "337af3003f76ec0407abf341752613c6bf87b094d47ffd7217d8f42ac115e811",
  "autoresearch/experiments/rp-d1-delivery-cost/summarize.py": "eb223d5222d6d50ee4c791a40dd49f26af0271c792ae799fb2cb484205e99be1",
  "autoresearch/experiments/rp-d1-delivery-cost/tasks.json": "12f4ef121cc0544ab1ffe42caf4cf5cc17d6df096cc1d2dcdd2565732c4f7ef7",
  "autoresearch/experiments/rp-d2-report-lines/DESIGN.md": "e623d7a8c8a39063c317813f50d083ebdbc0bdc37378e7159b51a09245022ddc",
  "autoresearch/experiments/rp-d2-report-lines/README.md": "3aa1ea55eee7889f9133b78244a9d48c72fafa5c6a6b4cb06e10cc918aded9ab",
  "autoresearch/experiments/rp-d2-report-lines/pack.py": "302f9f48c4bb3a3cb4a3c4d99d26f89e7ef6f3118f3b165fa574191f527b5aff",
  "autoresearch/experiments/rp-d2-report-lines/prepare.py": "43bffb00427388c1b2fc0f013cd1adf56130e979b2fb7f1d8bdd7ad1665aba76",
  "autoresearch/experiments/rp-d2-report-lines/reevaluate.py": "feb4129fa21ab55d81448d579ecd6a0be6e31a566308fe7f4d8c3422ab23ec44",
  "autoresearch/experiments/rp-d2-report-lines/runner.py": "6008e540d586ec9707fbe98016a558346241c398016a806e66f791ac4e1674a3",
  "autoresearch/experiments/rp-d2-report-lines/stage.py": "b4703ffae17e66242f0531e49c7656dd41faf74ddfcb68a954b3e14d242290e8",
  "autoresearch/experiments/rp-d2-report-lines/summarize.py": "92878ec0ea1225c8c25d2a8e2771eb75b788674b7200ee32cb866a64cfbdf4d2",
  "autoresearch/experiments/rp-d2-report-lines/test_rpd2_pack.py": "065553d0908a6555038b409526b88748b3a892bbbd4c973a174ebdb709421e7f",
  "autoresearch/experiments/rp-d2-report-lines/test_rpd2_runner.py": "6759792ed3b291f08e9c1171262f2b838b4ced4d3c6bbd26ad9235c985022cd1",
  "autoresearch/experiments/rp-d2-report-lines/test_rpd2_summary.py": "2e572d4cdb11b796f4be18d3f58f8501d8201172f2248f277d9e22d5eb599914",
  "autoresearch/experiments/rp-d2-report-lines/token_gate.py": "ec59c4f604fac2145cf9fa397b7ef0fe28493095839a5248fa962a5ff5cca7e7"
 },
 "live_inputs": {
  "arms.json": "60a97ad511ae2e2ce366a9b7905fb8c25c3bfaf718c12e24d822dde6d3236caa",
  "X.tgz": "7b22cce865d99e1400f9c0b0bff41c1b9ae3645b132cbb868ec01cadc973393e",
  "Y.tgz": "c45bc13aec01f625a6687a9697854e705b3eb201fc2b0f1e01626e9f8dcaf603",
  "control.manifest.json": "499d0476ec6fbfd1de222eef450ae0bdd3df25a7cbda0125ab441faf707e6db5",
  "models_cache.json": "e5ad6ad98d3b82fb9a95602cf0b6d024aa1c562f9057a81bd68c80551b89c88c",
  "model-auth manifest.json": "cd4fa3d350d13ad685c1c7f906e54060344e32f3e28cc6ea51401c6dfbf7aff5"
 },
 "watchdog_seconds": {
  "owner": 5400,
  "evaluator_or_review": 600
 }
}

hook: PostToolUse Completed
hook: PostToolUse Completed
hook: PostToolUse
hook: PostToolUse
hook: PostToolUse Completed
hook: PostToolUse Completed
exec
/bin/zsh -lc "rg --files -g AGENTS.md -g DESIGN.md -g '*registration*' -g '*result*' autoresearch && cat /Users/aipalm/.local/share/nx01/rp-d2-rerun-live/stage/runtime-measured.json && cat /Users/aipalm/.local/share/nx01/rp-d2-rerun-live/arms/arms.json" in /Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d2-rerun
 succeeded in 0ms:
autoresearch/iterations/0130-verdict-behavior-registration.md
autoresearch/iterations/0128-plan-reference-registration.md
autoresearch/iterations/0206-abc-registration.md
autoresearch/experiments/0229/r2/result.json
autoresearch/experiments/rp-d2-report-lines/DESIGN.md
autoresearch/experiments/rp-d2-report-lines/registration.md
autoresearch/experiments/rp-d2-report-lines/results.md
autoresearch/experiments/0243/DESIGN.md
autoresearch/experiments/0243/registration-draft.md
autoresearch/experiments/0233/DESIGN.md
autoresearch/experiments/0218/DESIGN.md
autoresearch/experiments/rp-d2-report-lines/registration.json
autoresearch/experiments/rp-d2-report-lines/registration-20261015a.json
autoresearch/experiments/rp-d2-report-lines/results/registration-r1-review-astra.md
autoresearch/experiments/rp-d2-report-lines/results/registration-r2-review-grok.md
autoresearch/experiments/rp-d2-report-lines/results/registration-r2-review-astra.md
autoresearch/experiments/rp-d2-report-lines/results/registration-r1-review-grok.md
autoresearch/experiments/0229/r3/result.json
autoresearch/experiments/rp-d1-delivery-cost/DESIGN.md
autoresearch/experiments/0229/evidence/result.json
autoresearch/experiments/rp-d1-delivery-cost/results/registration-r1-review-astra.md
autoresearch/experiments/rp-d1-delivery-cost/results/registration-r2-review-grok.md
autoresearch/experiments/rp-d1-delivery-cost/results/registration-r2-review-astra.md
autoresearch/experiments/rp-d1-delivery-cost/results/results-review-prompt.md
autoresearch/experiments/rp-d1-delivery-cost/results/results-review-astra.md
autoresearch/experiments/rp-d1-delivery-cost/results/registration-r1-review-grok.md
autoresearch/experiments/0216/DESIGN.md
autoresearch/experiments/0253/registration.json
autoresearch/experiments/0242/DESIGN.md
autoresearch/experiments/0220/DESIGN.md
autoresearch/experiments/0242/registration-smoke.md
autoresearch/experiments/0224/DESIGN.md
autoresearch/experiments/0252/registration-review-v1.md
autoresearch/experiments/0252/registration.md
autoresearch/experiments/0243/results/registration-review-v1.md
autoresearch/experiments/0243/results/registration-review-final-v1.md
autoresearch/experiments/0243/registration-v1.md
autoresearch/experiments/0223/DESIGN.md
autoresearch/experiments/rp-d1-delivery-cost/results/results-review-grok.md
autoresearch/experiments/rp-d1-delivery-cost/registration.json
autoresearch/experiments/0245/registration-smoke.md
autoresearch/experiments/0219/DESIGN.md
autoresearch/experiments/0228/r2/result.json
autoresearch/experiments/0210/preflight_result.py
autoresearch/experiments/0255/results/compatibility-v3-result.json
autoresearch/experiments/0255/results/compatibility-v2-result.json
autoresearch/experiments/0255/results/tests-v2-result.json
autoresearch/experiments/0255/results/tests-v1-result.json
autoresearch/experiments/0255/results/compatibility-v1-result.json
autoresearch/experiments/0215/DESIGN.md
autoresearch/experiments/0238/registration-smoke.md
autoresearch/experiments/0238/registration-smoke-account-v2.md
autoresearch/experiments/0238/registration-proposal.md
autoresearch/experiments/rp-d1-delivery-cost/registration.md
autoresearch/experiments/rp-d1-delivery-cost/results.md
autoresearch/experiments/0245/results/s01-native-result-summary.json
autoresearch/experiments/0244/DESIGN.md
autoresearch/experiments/0249/registration-proposal-v2.md
autoresearch/experiments/0244/fixtures/fresh-native-result.json
autoresearch/experiments/0244/fixtures/fresh-result-metadata.json
autoresearch/experiments/0244/registration-smoke.md
autoresearch/experiments/0237/results/account-registration.json
autoresearch/experiments/0237/results/confirmation-registration-freeze.json
autoresearch/experiments/0234/DESIGN.md
autoresearch/experiments/0237/results/cleanup-zombie-proposal-evidence/probe-root-results.json
autoresearch/experiments/0237/results/cleanup-zombie-proposal-evidence/probe-proposed-root-results.json
autoresearch/experiments/0237/results/cleanup-zombie-proposal-evidence/probe-proposed-results.json
autoresearch/experiments/0237/results/cleanup-zombie-proposal-evidence/probe-results.json
autoresearch/experiments/0236/DESIGN.md
autoresearch/experiments/0226/evidence/result.json
autoresearch/experiments/0238/results/s01-v2-connectivity-result.json
autoresearch/experiments/0238/registration-smoke-recovery-v3.md
autoresearch/experiments/0237/confirmation-registration.md
autoresearch/experiments/0254/results/compatibility-v2-result.json
autoresearch/experiments/0254/results/tests-v2-result.json
autoresearch/experiments/0254/results/tests-v1-result.json
autoresearch/experiments/0254/results/compatibility-v1-result.json
autoresearch/experiments/0239/results/import-dedup-result-v1.json
autoresearch/experiments/0239/results/selected-runtime-result.json
autoresearch/experiments/0247/registration-smoke.md
autoresearch/experiments/0247/results/registration-review-v1.md
autoresearch/experiments/0247/results/s01-native-result-summary.json
autoresearch/experiments/0227/evidence/result.json
autoresearch/experiments/0246/registration-draft.md
autoresearch/experiments/0246/results/registration-review-v1.md
autoresearch/experiments/0246/results/d04-native-result-summary.json
autoresearch/experiments/0246/results/d03-native-result-summary.json
autoresearch/experiments/0246/results/d05-native-result-summary.json
autoresearch/experiments/0246/registration-v1.md
autoresearch/experiments/0241/DESIGN.md
autoresearch/experiments/0241/registration-smoke.md
autoresearch/experiments/0239/registration.md
autoresearch/experiments/0222/DESIGN.md
autoresearch/experiments/0248/registration-v2.md
autoresearch/experiments/0248/registration-draft.md
autoresearch/experiments/0249/registration-proposal.md
autoresearch/experiments/0249/registration-v2.md
autoresearch/experiments/0248/results/registration-review-v1.md
autoresearch/experiments/0248/results/d07-native-result-summary.json
autoresearch/experiments/0248/results/d06-native-result-summary.json
autoresearch/experiments/0248/results/d10-native-result-summary.json
autoresearch/experiments/0248/results/screen-results.json
autoresearch/experiments/0248/results/d08-native-result-summary.json
autoresearch/experiments/0248/results/d05-native-result-summary.json
autoresearch/experiments/0248/results/registration-review-v2.md
autoresearch/experiments/0248/results/d09-native-result-summary.json
autoresearch/experiments/0248/registration-v1.md
autoresearch/experiments/0249/registration-v1.md
autoresearch/experiments/0237/confirmation/history/revision-1/audit-reproduction/raw-results.json
autoresearch/experiments/0249/results/registration-review-v2.md
autoresearch/experiments/0240/DESIGN.md
autoresearch/experiments/0249/results/fixture-review-v1-evidence/nonfinite-result.json
autoresearch/experiments/0249/results/registration-review-v1.md
autoresearch/experiments/0240/registration-smoke.md
autoresearch/experiments/0249/results/fixture-review-v2-evidence/result.json
autoresearch/experiments/0250/registration.md
autoresearch/experiments/0250/results/registration-review-v1.md
autoresearch/experiments/0250/results/d02-launch-result-v1.json
autoresearch/experiments/0250/results/d01-launch-result-v1.json
autoresearch/experiments/0232/DESIGN.md
autoresearch/experiments/0232/results/adjudication/release-variant-results.json
autoresearch/experiments/0235/DESIGN.md
{
  "account": [
    "45eff57aaa45",
    "b6b7768fd228"
  ],
  "arms_file": "/Users/aipalm/.local/share/nx01/rp-d2-rerun-live/stage/arms/arms.json",
  "auth": "/Users/aipalm/.local/share/nx01/rp-d2-rerun-live/model-auth-1",
  "auth_manifest_sha256": "cd4fa3d350d13ad685c1c7f906e54060344e32f3e28cc6ea51401c6dfbf7aff5",
  "boot_catalogs": {
    "claude": {
      "X": {
        "mcp_servers": [],
        "plugins": [
          {
            "name": "cc-plugin-agents-md",
            "path": "builtin",
            "source": "cc-plugin-agents-md@builtin"
          },
          {
            "name": "cc-plugin-plugin-authoring",
            "path": "builtin",
            "source": "cc-plugin-plugin-authoring@builtin"
          },
          {
            "name": "cc-plugin-telemetry",
            "path": "builtin",
            "source": "cc-plugin-telemetry@builtin"
          }
        ],
        "skills": [
          "batch",
          "claude-api",
          "code-review",
          "dataviz",
          "debug",
          "deep-research",
          "design",
          "design-sync",
          "devlyn-engines",
          "devlyn-ideate",
          "doctor",
          "fewer-permission-prompts",
          "loop",
          "plugin-authoring",
          "run",
          "run-skill-generator",
          "schedule",
          "simplify",
          "update-config",
          "verify",
          "workflow-authoring"
        ]
      },
      "Y": {
        "mcp_servers": [],
        "plugins": [
          {
            "name": "cc-plugin-agents-md",
            "path": "builtin",
            "source": "cc-plugin-agents-md@builtin"
          },
          {
            "name": "cc-plugin-plugin-authoring",
            "path": "builtin",
            "source": "cc-plugin-plugin-authoring@builtin"
          },
          {
            "name": "cc-plugin-telemetry",
            "path": "builtin",
            "source": "cc-plugin-telemetry@builtin"
          }
        ],
        "skills": [
          "batch",
          "claude-api",
          "code-review",
          "dataviz",
          "debug",
          "deep-research",
          "design",
          "design-sync",
          "devlyn-engines",
          "devlyn-ideate",
          "doctor",
          "fewer-permission-prompts",
          "loop",
          "plugin-authoring",
          "run",
          "run-skill-generator",
          "schedule",
          "simplify",
          "update-config",
          "verify",
          "workflow-authoring"
        ]
      }
    }
  },
  "codex_account": "65ad276127a5",
  "control": "/Users/aipalm/.local/share/nx01/rp-d2-rerun-live/stage/control",
  "github_auth": "/Users/aipalm/.local/share/nx01/rp-d2-rerun-live/github-auth",
  "image": "sha256:b55cbb940b6f7d21ca67e7ee39f221966b525c334608766eff31347571564eb0",
  "models_cache": "/Users/aipalm/.local/share/nx01/rp-d2-rerun-live/stage/models_cache.json",
  "models_cache_sha256": "e5ad6ad98d3b82fb9a95602cf0b6d024aa1c562f9057a81bd68c80551b89c88c",
  "output": "/Users/aipalm/.local/share/nx01/rp-d2-rerun-live/stage/output",
  "phase": "measured",
  "releases": {
    "X": {
      "integrity": "sha512-yud5j6xq791XQlg6eVy8WkWTB/Ee7X0pn/Orbt0db4NvAKatEq577wyTT1Wo/x0FRKFRoXax1q+xxns97UXekw==",
      "manifest_sha256": "cd68caa4bcb0d64df14faa0c8647479ef532b6d84889aac096728b57f08cb2f5",
      "sha256": "7b22cce865d99e1400f9c0b0bff41c1b9ae3645b132cbb868ec01cadc973393e",
      "source": {
        "registry": "devlyn-cli@4.2.18"
      },
      "tarball": "/Users/aipalm/.local/share/nx01/rp-d2-rerun-live/stage/arms/X.tgz",
      "version": "4.2.18"
    },
    "Y": {
      "integrity": "sha512-eOKh4//n1WyIGfYBWLxs+7sTKgozAv5skd9MTJL9eA8qRrJ7Pz92UF7rV38smKDBLWMdAGn5YBV/TRMdURgUMg==",
      "manifest_sha256": "4141d0da1a6250d3af6c7614ef482726aa5d01619e941887438b17c0ad8996d7",
      "sha256": "c45bc13aec01f625a6687a9697854e705b3eb201fc2b0f1e01626e9f8dcaf603",
      "source": {
        "candidate_commit": "a623b382e655e893f6b39b96199ef8675afdde05",
        "registry": "devlyn-cli@4.2.18"
      },
      "tarball": "/Users/aipalm/.local/share/nx01/rp-d2-rerun-live/stage/arms/Y.tgz",
      "version": "4.2.18"
    }
  },
  "run_id": "20261015a",
  "scratch": "/Users/aipalm/.local/share/nx01/rp-d2-rerun-live/stage/scratch",
  "smoke_account": [
    "45eff57aaa45",
    "b6b7768fd228"
  ],
  "smoke_attempt": 1,
  "smoke_codex_account": "65ad276127a5",
  "smoke_output": "/Users/aipalm/.local/share/nx01/rp-d2-rerun-live/stage/smoke-output",
  "source_root": "/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d2-rerun",
  "sources": "/Users/aipalm/.local/share/nx01/rp-d2-rerun-live/stage/sources",
  "tasks_file": "/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d2-rerun/autoresearch/experiments/rp-d1-delivery-cost/tasks.json"
}
{
  "X": {
    "integrity": "sha512-yud5j6xq791XQlg6eVy8WkWTB/Ee7X0pn/Orbt0db4NvAKatEq577wyTT1Wo/x0FRKFRoXax1q+xxns97UXekw==",
    "manifest_sha256": "cd68caa4bcb0d64df14faa0c8647479ef532b6d84889aac096728b57f08cb2f5",
    "sha256": "7b22cce865d99e1400f9c0b0bff41c1b9ae3645b132cbb868ec01cadc973393e",
    "source": {
      "registry": "devlyn-cli@4.2.18"
    },
    "tarball": "X.tgz",
    "version": "4.2.18"
  },
  "Y": {
    "integrity": "sha512-eOKh4//n1WyIGfYBWLxs+7sTKgozAv5skd9MTJL9eA8qRrJ7Pz92UF7rV38smKDBLWMdAGn5YBV/TRMdURgUMg==",
    "manifest_sha256": "4141d0da1a6250d3af6c7614ef482726aa5d01619e941887438b17c0ad8996d7",
    "sha256": "c45bc13aec01f625a6687a9697854e705b3eb201fc2b0f1e01626e9f8dcaf603",
    "source": {
      "candidate_commit": "a623b382e655e893f6b39b96199ef8675afdde05",
      "registry": "devlyn-cli@4.2.18"
    },
    "tarball": "Y.tgz",
    "version": "4.2.18"
  }
}

hook: PostToolUse
hook: PostToolUse
hook: PostToolUse Completed
hook: PostToolUse Completed
The checkout is clean at `9b409492`, and no Python files changed since `21699994`. Under **No guesswork**, my next prediction is that every registered file hash will match the staged bytes, with differences from the first registration limited to the disclosed run-specific identities and evidence.
[codex-monitored] heartbeat: elapsed=60s
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PostToolUse
hook: PostToolUse
exec
/bin/zsh -lc 'cat autoresearch/experiments/rp-d2-report-lines/DESIGN.md && cat autoresearch/experiments/rp-d2-report-lines/registration.md && cat autoresearch/experiments/rp-d2-report-lines/README.md' in /Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d2-rerun
 succeeded in 0ms:
# rp-d2 design — report lines

rp-d1 ([results](../rp-d1-delivery-cost/results.md)) refuted its prediction on
report coverage alone: Codex merged a correct PR and cleaned up in 4/4 attempts,
but each final report said only "the local checkout is clean". Both reviewers
found cleanup MISSING and checkout reconciliation AMBIGUOUS. rp-d2 tests one
instruction-only change aimed at that gap. Design reviews:
[Astra](results/design-r0-astra.md) (SHIP) and
[Grok](results/design-r0-grok.md) (REVISE; every finding is resolved below).

## Mechanism

Only the reporting paragraph of
[task-completion.md](../../../config/skills/_shared/task-completion.md) changes,
in place. The paragraph is at line 203, the end of "Deliver and resume".

Control X (`7516ebc9`):

```text
Report verification, delivery and checkout reconciliation separately. A delivery
error does not rewrite an accepted product result; unperformed verification
must never be reported as accepted.
```

Candidate Y:

```text
Report verification, delivery, cleanup and checkout reconciliation separately. A
delivery error never changes an accepted product result; never report unperformed
verification as accepted.
```

- "cleanup" becomes a named report category.
- "checkout" stays. It separates the owner's reconciliation of the original
  checkout from the helper's `reconciled` allocation field
  (`task-completion.md:82`).
- "product result" stays. It is the term `devlyn-ideate` reports with.

**Token gate (tokens never increase).** The gate counts the whole file, before
and after, with [token_gate.py](token_gate.py). Claude uses Anthropic's
`count_tokens` for `claude-opus-5-5`. Codex uses `o200k_base` as a proxy,
because the `gpt-6-sol` tokenizer is not published.

| Wording | Claude | o200k |
|---|---:|---:|
| X (control) | 4,873 | 2,982 |
| Y (candidate) | 4,872 | 2,981 |
| Astra's draft ("Delivery errors do not rewrite …") | 4,875 | 2,979 |

The gate rejected two drafts. Astra's draft adds 2 Claude tokens. Grok's "as
four claims" adds 1 to 4 tokens on the paragraph in every arrangement tried.
`AGENTS.md`, `CLAUDE.md` and the prompt [common.txt](../rp-d1-delivery-cost/common.txt) are unchanged.

## Arms and artifacts

- **Control X** is the published `devlyn-cli@4.2.18` registry tarball, the
  artifact rp-d1 measured (SHA-256 `7b22cce8…393e`, registry integrity
  verified). Its `task-completion.md` must equal the `7516ebc9` blob.
- **Candidate Y** is X with that one file replaced by the candidate commit's
  blob, then repacked. Nothing is regenerated. A source pack would add a
  skill-history fingerprint and other publish-time differences.
- **Identity.** Both arms keep version `4.2.18`, so the version alone does not
  identify them. Each arm's identity is its tarball SHA-256 and SHA-512 plus
  its extracted file manifest.
- **Pre-registration check.** The two extracted trees must differ in exactly
  one file, `config/skills/_shared/task-completion.md`, and that file's diff
  must be exactly this paragraph.
- **The apparatus descends from rp-d1, with three changes:**
  1. two release records, each verified;
  2. a per-attempt arm, X or Y, that selects which package is installed;
  3. summaries grouped by arm and engine.

  Everything else is the rp-d1 apparatus as merged, including the corrected
  Git-mode evaluator, strict archive validation and the PAT scans. Both arms
  run on it.

## Schedule

There are 16 measured attempts: 2 arms × 2 engines × 2 tasks (BV, Z0) × 2
repetitions. They run serially, with no replay.

- **Pairs.** The rp-d1 order of task and engine becomes eight pairs:
  `BV/Claude, BV/Codex, Z0/Codex, Z0/Claude, Z0/Claude, Z0/Codex, BV/Codex, BV/Claude`.
  Odd pairs run X then Y; even pairs run Y then X.
- **Engines.**
  - Claude Code 2.1.296 runs `claude-opus-5-5` at effort `max`.
  - Codex 0.162.1 runs `gpt-6-sol` at effort `high`.
- **Frozen across arms:** the prompt, tasks, oracle, image, model cache,
  accounting and accounts.
- **Credentials.** They may be renewed, on the same account, only between
  pairs. An account change between arms invalidates the run.
- **Watchdogs.** These are the rp-d1 watchdogs. There is no token or cost
  budget.
- **Repositories.** There are 24 private repositories,
  `fysoul17/rpd2-<run>-<slot>`: 16 measured, 4 for smoke cells and 4 spare
  smoke cells. The owner makes one fine-grained PAT edit that selects all 24,
  with the rp-d1 permissions.
- **Smoke.** Each pairing of engine and arm runs one fresh smoke on SM. The
  spares allow one complete repeat. Measured attempts are never replaced.
- **Repository handling.** It follows rp-d1: check that the repository is
  empty, archive it, verify the archive, delete the repository, then confirm
  it returns 404. Raw evidence is kept until final adjudication.
- **UNKNOWN usage STOPs, as in rp-d1.** One proposed rule would have
  continued after an accounting-only UNKNOWN. It was implemented, reviewed
  (REVISE, both: [Astra](results/cont-r1-review-astra.md),
  [Grok](results/cont-r1-review-grok.md)), corrected, then withdrawn before
  exposure, for two reasons:
  - **The rule would not have applied to the real case.** The dropped-connection cell
    from smoke attempt 1 has its retry rows filtered out, but it still fails
    the unchanged 0254 audit, on two unindexed request bodies
    ([eligibility](results/cont-fix-real-eligibility.json)).
  - **A compared UNKNOWN cost row blocks adoption either way.** Continuing
    would add descriptive data only. It could not change the decision.

  The rp-d1 STOP rule is therefore kept, with no added code. A STOP makes the
  run inconclusive.

## Success and cost

Success per request is the rp-d1 registration's four conditions, unchanged:

1. scope and regression checks;
2. exactly one correctly merged PR;
3. preserved user files and sentinel;
4. a truthful verification, merge, cleanup and reconciliation report, with
   each claim supported by both reviewers.

A truthful `CLEANUP_PENDING` remains allowed. A missing or ambiguous claim
fails.

Every dispatched attempt counts, failures included. The cost metrics are owner
wall seconds, input tokens and output tokens, each divided by the number of
successes. Accounting is the rp-d1 accounting.

## Prediction

> On the same 4.2.18 tree, Y's paragraph raises Codex's success over X (BV/Z0,
> 2 repetitions each, paired and interleaved), and neither engine's quality or
> cost per success gets worse.

## Adoption rule

Adopt Y only if, for each engine, both of the following hold, and at least one
engine improves:

- **Quality.** Y's successes are at least X's.
- **Cost.** Y's wall, input and output per success are each no higher than
  X's. Cost is compared only when both arms of that engine have at least one
  success.

Two edge cases:

- **One arm has zero successes.** With 0 X successes and at least one Y
  success, the engine counts as a quality improvement, and its cost row is
  recorded as "no baseline", neither worse nor infinite. With 0 successes on
  both arms, the engine is unchanged. With 0 Y successes and at least one X
  success, the engine got worse.
- **UNKNOWN usage on a compared cost row.** Adoption is blocked.

Two repetitions support this task and model setting only. Extra artifact
differences, unequal repairs, a mid-pair account or model change, selective
retries, changed grading, missing usage or damaged evidence all void
attribution.

## Qualification and the pre-registration decision

All four repositories were archived, then deleted and confirmed 404.

- **Smoke attempt 1** stopped on its first cell, Claude X. The owner delivered
  correctly, but a dropped connection was retried (`api_error`/`api_retry`;
  the transcript names ECONNRESET). The 0254 accounting therefore returns UNKNOWN, by design.
- **Smoke attempt 2**, the spares, qualified all four cells. Every cell
  delivered, its usage was COMPLETE, and its report checklist was set to
  ADJUDICATE.
  - **Codex, both arms.** The report kept the rp-d1 shape: the merged PR, "the
    checkout is clean" and "Nothing remains unresolved." Y's wording was "PR #1
    merged, and the local checkout is clean."
  - **Codex Y read the new paragraph.** It ran `cat` on
    `task-completion.md`, and the output was not truncated.
  - **Claude, both arms.** The report named the merge, the fast-forward, the
    clean tree and the removal of the worktree and branch. Y also named the
    scratch area.

**Decision before registration.** The smoke evidence was put to Astra and Grok
([Astra](results/smoke-decision-astra.md), [Grok](results/smoke-decision-grok.md)).

- **Both reviewers.** Both proposed an accounting-only UNKNOWN continuation.
  It was later withdrawn; see Schedule.
- **Astra.** Register Y unchanged. One SM observation cannot establish no
  effect on BV/Z0.
- **Grok, dissenting.** The prompt's closing sentence ("Finish with what you
  changed, what you verified and anything unresolved") sets Codex's report
  shape. Grok would replace the arms with a prompt ablation.

**Resolution.** Y is measured as designed, because the owner chose a product
instruction fix. The prompt ablation is the registered next candidate if Y is
not adopted.

Interpretation is narrowed accordingly. rp-d2 measures whether Y improves
report coverage under this frozen prompt. A null result does not show that
the product's reporting rule is wrong in general. Delivery outcomes and report
outcomes are shown separately.

## Review

1. **Registration.** Astra ultra and Grok 4.7 approve it before exposure.
2. **Results.** After the run, both review the results against the raw
   evidence.
3. **Write-up.** If Y is not adopted, the write-up reverts the paragraph before
   merge.
# rp-d2 registration — report lines

This registration is written before any measured exposure. Its input
identities are in [registration.json](registration.json). That file's
`apparatus_commit` is the commit whose files the `inputs` hashes cover; this
registration commit follows it. From this commit on, the prediction, the
schedule, the grading and the raw data are never edited.

[DESIGN.md](DESIGN.md) is the contract. Its full text applies, including:

- the token gate;
- artifact identity;
- the adoption rule;
- the qualification record;
- Grok's recorded dissent.

## Prediction (frozen)

> On the same 4.2.18 tree, Y's paragraph raises Codex's success over X (BV/Z0,
> 2 repetitions each, paired and interleaved), and neither engine's quality or
> cost per success gets worse.

**Smoke evidence known at registration.** On SM, Codex Y read the new
paragraph in full, yet still reported only "PR #1 merged, and the local
checkout is clean. Nothing remains unresolved." This is one observation on an unrelated task. It lowers
expectations and leaves the prediction unchanged.

## What runs

- **Arms.**
  - X is the registry `devlyn-cli@4.2.18` tarball.
  - Y is the same archive with only the reporting paragraph of
    `task-completion.md` replaced.
  - Both are verified by SHA-256, SHA-512 and their extracted manifest.
  - Each attempt installs its own arm through the unchanged rp-d1 installer
    path.
- **Engines.**
  - Claude Code 2.1.296 runs `claude-opus-5-5` at effort `max`.
  - Codex 0.162.1 runs `gpt-6-sol` at effort `high`.
  - Native children use the owner's model.
- **Unchanged from rp-d1:**
  - the prompt [common.txt](../rp-d1-delivery-cost/common.txt);
  - the tasks and hidden oracle;
  - the image definition. The image itself was rebuilt, because the rp-d1
    image had been pruned. Its ID is in `registration.json`, and both arms
    use it.
- **Schedule.** Serial, with no replay:

  | Pair | Task / engine | Order | Slots |
  |---|---|---|---|
  | 1 | BV / Claude | X, Y | m01, m02 |
  | 2 | BV / Codex | Y, X | m03, m04 |
  | 3 | Z0 / Codex | X, Y | m05, m06 |
  | 4 | Z0 / Claude | Y, X | m07, m08 |
  | 5 | Z0 / Claude | X, Y | m09, m10 |
  | 6 | Z0 / Codex | Y, X | m11, m12 |
  | 7 | BV / Codex | X, Y | m13, m14 |
  | 8 | BV / Claude | Y, X | m15, m16 |

- **Repositories.** Each slot uses its own empty private repository,
  `fysoul17/rpd2-20261014a-<slot>`. The rp-d1 lifecycle applies:
  1. a precheck that the remaining repositories are still empty;
  2. archive, then verify the archive;
  3. delete the repository and confirm it returns 404;
  4. PAT scans.
- **Watchdogs.** 5400 s per owner and 600 s per evaluator or review. There is
  no token or cost budget.
- **Credentials.** The model auth snapshot may be renewed only between pairs,
  and only on the same Claude account pair and the same Codex account digest.
  Every launch keeps the 6300-second lifetime floor.

## Success, cost and decision

- **Success per request.** These are the four rp-d1 conditions, graded by the
  unchanged rp-d1 code:
  1. requirements and scope;
  2. exactly one correctly merged PR;
  3. preserved user files and sentinel;
  4. a truthful verification, merge, cleanup and checkout reconciliation
     report, with each claim supported by both Astra ultra and Grok 4.7
     reading the raw evidence.
- **Cost.** Every dispatched attempt counts, and every number comes from
  [summarize.py](summarize.py). For each arm and engine it reports:
  - successes and attempts;
  - total wall, input and output;
  - cost per success.
- **Decision.** `summarize.py` applies the DESIGN.md adoption rule
  mechanically and prints ADOPT, REJECT or INCONCLUSIVE with the reason for
  each row.
- **STOP rule.** An instrumentation STOP is recorded as `NOT_ASSESSED`. That
  includes UNKNOWN usage, as in rp-d1. The remaining slots become `NOT_RUN`,
  and the run is inconclusive. No attempt is ever retried or replaced.

## Qualification

**Smoke attempt 1 stopped** on Claude X. Its delivery was correct, but its
usage was UNKNOWN after a dropped-connection retry
(`api_error`/`api_retry`; the transcript names ECONNRESET). The other three cells did not run.

**Smoke attempt 2**, the registered spares, qualified all four cells.

| Cell | Owner s | Input | Output | Usage | Done-check | Repository |
|---|---:|---:|---:|---|---|---|
| Claude X | 639.0 | 1,376,277 | 60,605 | COMPLETE | ADJUDICATE | archived, deleted (404) |
| Claude Y | 613.9 | 2,195,861 | 58,835 | COMPLETE | ADJUDICATE | archived, deleted (404) |
| Codex X | 165.2 | 353,955 | 5,607 | COMPLETE | ADJUDICATE | archived, deleted (404) |
| Codex Y | 173.2 | 470,647 | 5,878 | COMPLETE | ADJUDICATE | archived, deleted (404) |

The verdict hashes and both schedule hashes are in
[registration.json](registration.json). Smoke reports are not graded and are
never pooled with measured data.

## Freeze revision before exposure

The first registration review returned SHIP from Grok and REVISE from Astra,
which raised one MEDIUM ([Astra](results/registration-r1-review-astra.md),
[Grok](results/registration-r1-review-grok.md)): `summarize.py` let REJECT win
over a STOP. It now returns INCONCLUSIVE whenever a row is UNKNOWN, matching
the STOP rule above. Grok's three wording LOWs are corrected.

Before any measured slot ran, the snapshot crossed the 6300-second floor.
Meanwhile the host's Claude login had switched accounts, so the staged
credential could not be renewed on the same account. rp-d1 handled the same
event the same way:

- **Void runtime.** The first measured runtime, which never ran, is kept as
  `runtime-measured-void-account-switch.json`. Its hash is recorded in
  `void_runtime_sha256`.
- **Re-staged account.** The measured run was re-staged on the current Claude
  account pair. The Codex account is unchanged.
- **Recorded smoke accounts.** The smoke qualification accounts are recorded
  as `smoke_account` and `smoke_codex_account`. The apparatus checks the smoke
  verdicts against those recorded accounts.
- **Measured account freeze.** All 16 measured slots must use the one
  registered account pair and the one Codex account. Renewal is allowed only
  between pairs, only on the identical accounts.

[registration.json](registration.json) was regenerated for this commit.

## Review

1. **Before exposure.** Astra ultra and Grok 4.7 review this registration.
2. **After the run.** Both judge every report checklist and the results
   against the raw evidence.
3. **Stopping.** Review stops at SHIP with no HIGH finding, reading each
   reviewer's final verdict line.
4. **Write-up.** If Y is not adopted, the write-up reverts the paragraph
   before merge. The prompt ablation recorded in DESIGN.md is then the next
   candidate.

## Rerun 20261015a (registered 2026-10-15, before exposure)

Run 20261014a closed INCONCLUSIVE ([results](results.md)). The owner chose
candidate 3 there: an unchanged rerun after the drop diagnosis. Everything
above applies unchanged to run 20261015a: the prediction, the arms, the
schedule, the grading, the cost and adoption rules, STOP and renewal. Its
identities are in
[registration-20261015a.json](registration-20261015a.json).

- **Unchanged inputs.** The apparatus files, DESIGN.md, README.md, both arm
  tarballs, `arms.json`, the control manifest, the image, the CLI versions and
  the routes hash identically to [registration.json](registration.json).
  `apparatus_commit` is the current main; no apparatus code changed since the
  first registration.
- **New per-run inputs.** The run ID, the 24 repositories, the GitHub PAT
  (selected repositories only, Contents and Pull requests write), the model
  auth snapshot and the Codex models cache. The cache is copied from the host
  at staging, so its `fetched_at` differs. The Claude account pair is
  `45eff57aaa45`/`b6b7768fd228` for smoke and measured; the Codex account is
  unchanged.
- **Network.** [Benchmark hard rule 5](../../../benchmark/README.md) applies:
  the host network is held fixed for the whole run. A watcher logs every change
  of the host's default-route interface. A change during a cell is reported
  with that cell; it does not change any rule above.
- **Smoke attempt 1 qualified all four cells.** No stream retry or API error
  was recorded.

| Cell | Owner s | Input | Output | Usage | Delivery | Repository |
|---|---:|---:|---:|---|---|---|
| Claude X | 572.4 | 2,519,890 | 59,060 | COMPLETE | passed | archived, deleted (404) |
| Claude Y | 758.5 | 3,140,290 | 78,545 | COMPLETE | passed | archived, deleted (404) |
| Codex X | 175.0 | 514,105 | 6,903 | COMPLETE | passed | archived, deleted (404) |
| Codex Y | 131.8 | 381,285 | 5,889 | COMPLETE | passed | archived, deleted (404) |

The run 20261014a smoke and measured records stay as they are and are never
pooled with this run.
# rp-d2 — report lines

The authoritative contract is [DESIGN.md](DESIGN.md). The apparatus loads the
frozen rp-d1 and 0255/0251/0233 code by path. Its internal `B` route means
installed product; rp-d2 plans, baselines and verdicts bind the actual X/Y arm,
release hashes and manifest. Tasks, checks, grading, scans and delivery stay rp-d1.

From the repository root, set `d=autoresearch/experiments/rp-d2-report-lines`.
Keep all stage, auth, archive and build directories outside the repository.

1. Pack offline from the verified registry artifact into a new directory:
   `python3 "$d/pack.py" /path/devlyn-cli-4.2.18.tgz /path/arms --candidate a623b382e655e893f6b39b96199ef8675afdde05`.
   X is copied verbatim; Y changes only the registered paragraph. `arms.json`
   records both tarball identities and extracted file manifest digests.
2. Build the pinned image with `bash autoresearch/experiments/rp-d1-delivery-cost/build.sh /path/new-build-context`.
   Register its exact `sha256:...` image ID for both arms.
3. Create the 24 private repositories `fysoul17/rpd2-<run-id>-<slot>`:
   `m01`..`m16`, `smoke-<claude|codex>-<X|Y>` and
   `smoke2-<claude|codex>-<X|Y>`. Use rp-d1's merge policy and fine-grained PAT
   permissions. Provision its private read-only `hosts.yml` and `config.yml`
   separately from the model auth snapshot and output roots.
4. Stage smoke:
   `python3 "$d/stage.py" /path/stage --run-id RUN --arms /path/arms/arms.json --image sha256:IMAGE --auth /path/model-auth --github-auth /path/github-auth --phase smoke`.
   Run `python3 "$d/stage.py" --check /path/stage/runtime-smoke.json`, then
   `python3 "$d/runner.py" /path/stage/runtime-smoke.json smoke`.
   A complete repeat uses a fresh stage directory and `--smoke-attempt 2`.
   Preserve attempt 1; no third attempt is registered.
5. Stage measured with the same directory and arguments except `--phase measured`
   and optionally a new `--auth` snapshot: this freezes one Claude smoke catalog
   per arm, permits different Claude account/org and Codex identities from smoke,
   and records the smoke identities as `smoke_account` / `smoke_codex_account`.
   Runtime binds Codex
   by the 12-hex SHA-256 prefix of `codex.json`'s `tokens.account_id`.
   Check `runtime-measured.json` as above;
   all four selected smoke cells must have working delivery and archived
   deletion/404 receipts. Freeze inputs and obtain registration reviews before exposure.
6. Run `python3 "$d/runner.py" /path/stage/runtime-measured.json measured`.
   For renewal, use `--through-pair N` to return after complete pair N, then
   `python3 "$d/stage.py" --renew /path/stage/runtime-measured.json --auth /path/new-model-auth`.
   Check and resume using the printed new runtime path. Earlier runtimes and
   slots remain intact; only the auth snapshot may change, on the identical
   Claude account/org and Codex account. Mid-pair renewal and stopped-run recovery are refused.
   The inherited 6300-second credential lifetime floor applies at every launch.
7. Generate each review with
   `python3 "$d/summarize.py" /path/stage/output m01 --review-template`.
   Astra ultra and Grok 4.7 fill separate `<slot>.json` files against raw
   evidence. Then run
   `python3 "$d/summarize.py" /path/stage/output --review astra=/path/astra --review grok=/path/grok`.
   `summary.json` and the table give arm × engine costs and the mechanical
   ADOPT / REJECT / INCONCLUSIVE decision with row reasons.
8. If reevaluation is needed, run
   `python3 "$d/reevaluate.py" /path/stage/output /path/new-corrections`.
   The rp-d1 seal/archive checks and optional `--disclosed-change SLOT:cell/work/.git/index`
   apply unchanged. Regenerate reviews and summarize with `--checklists /path/new-corrections`;
   raw evidence remains untouched until final adjudication.

Offline verification (importlib collection avoids the three frozen fixtures'
identically named test modules; their source directories supply local imports):

```sh
p=autoresearch/experiments/rp-d1-delivery-cost
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
PYTHONPATH="$PWD/$p:$PWD/$d:$PWD/$p/fixtures/BV/src:$PWD/$p/fixtures/SM/src:$PWD/$p/fixtures/Z0/src" \
PYTEST_ADDOPTS='--import-mode=importlib -p no:cacheprovider' \
python3 -m pytest "$p" "$d" -q
```

Tests use synthetic tarballs/auth and mocked external boundaries, never real
credentials, models, Docker or GitHub.

hook: PostToolUse Completed
hook: PostToolUse Completed
hook: PostToolUse
hook: PostToolUse
hook: PostToolUse Completed
hook: PostToolUse Completed
exec
/bin/zsh -lc "cat autoresearch/experiments/rp-d2-report-lines/results.md && rg -n -A 9 -B 9 'network|Network|hard rule' benchmark/README.md && git log -6 --oneline" in /Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d2-rerun
 succeeded in 0ms:
# rp-d2 results — report lines

**Outcome: INCONCLUSIVE. Y is not adopted, and the paragraph is reverted.**

The registered schedule stopped at its first slot, under the registered STOP
rule. No arm comparison exists. The test used the frozen
[registration](registration.md) (commit `2c0fde6c`, both reviewers SHIP), the
[contract](DESIGN.md) and [registration.json](registration.json).

## What happened

| Slot | Arm | Engine / task | Status | Notes |
|---|---|---|---|---|
| m01 | X | Claude / BV | STOP (`NOT_ASSESSED`) | Owner exited 0 after 999.8 s. Identity MATCH. Repository archived, then deleted and confirmed 404. Usage UNKNOWN: one `api_error` (ECONNRESET) retry, so the 0254 gap is `error or retry outside scope`. |
| m02–m16 | — | — | NOT_RUN | earlier slot stopped the schedule |

- **No usage is reported for m01.** Its native aggregate was about 2.77M
  input-side tokens and 63.5k output, but those figures are observations, not
  counted usage.
- **m01 was never graded.** Its delivery and report were not assessed, as the
  STOP rule requires. Its final report claims a merged PR, a fast-forwarded
  checkout and the removal of the worktree and branches.
- **Evidence hashes.** The schedule file is `rp-schedule.json`, SHA-256
  `25d7541a…`. The m01 verdict is `verdict-m01.json`, `e3e3d083…`.
- **The image guard never had to restore the image.**

## Why it stopped (infrastructure, not product)

Both Claude cells that stopped today, m01 and smoke attempt 1 Claude X, did so
the same way:

- **Timing.** An `api_error` ECONNRESET came after a single request that had
  been silent for 150–180 s. In m01 that happened at 886 s of 987 s; in the
  smoke cell at 563 s of 879 s.
- **Smoke attempt 2.** Its Claude cells completed without a drop.
- **rp-d1, earlier the same date.** Its final freeze was at 01:15 KST, and
  the two drops came at 20:20 and 23:05 KST. It used the same image
  definition, CLI, model and effort; the image was rebuilt for rp-d2, with a
  different ID. Every rp-d1 Claude cell recorded COMPLETE usage, with no
  drop.

The cause is not established. One hypothesis is that something on the path
between the cell and the API resets long-silent streaming connections. The
path runs through the Docker bridge, the host network and upstream.

The 0254 accounting cannot count such a retry. The withdrawn continuation rule
(DESIGN.md, Schedule) would not have changed the outcome either. The real
case also fails the unchanged audit, on unindexed request bodies. In addition,
a compared UNKNOWN cost row blocks adoption.

## Diagnosis (added 2026-10-15, after merge)

The owner chose candidate 1. Host route changes made by a VPN client are the
likely cause. On the morning of 2026-10-15, failures followed each VPN change
within about a minute. For 2026-10-14 the match rests on timing alone. Docker is not needed
for a drop, because host sessions dropped as well. One retry remains
unexplained. The text above is unchanged. "Silent" there means no transcript
row was written; it does not mean the connection carried no bytes.

- **Host sessions outside Docker dropped the same way.** Host Claude Code
  transcripts record nine `api_error` ECONNRESET retries on 2026-10-14, from
  18:54 to 23:26 KST. Each came 82–160 s after the previous row. Three more
  followed on the morning of 2026-10-15, by 08:48 KST. From 2026-09-29 until
  18:54 KST on 2026-10-14 there were none, across about 600 requests that
  waited 80 s or more. Successful requests on the same evening waited up to
  1,020 s, so a fixed limit on total request time does not explain the drops.
  Transcript gaps do not measure idle time on the wire.
- **Codex dropped in the same morning window.** Three Codex streams failed with
  `Can't assign requested address` (EADDRNOTAVAIL), which fits a local
  address that is no longer available.
- **This morning's logs pair VPN changes with failures.**
  - Cisco Secure Client brought up a full-tunnel VPN, with a VPN default
    route, at 08:22:55 KST.
  - A user-requested disconnect ended it at 08:29:10–08:29:12.
  - Codex streams then failed with EADDRNOTAVAIL at 08:29:59, 08:30:08 and
    08:31:20. A fourth, at 08:30:08, failed with `error decoding response
    body`.
  - A host Claude request that began at 08:28:09, inside the tunnel window,
    failed with ECONNRESET at 08:30:20.
  - The tunnel came up again at 08:46:38. A host Claude request failed with
    ECONNRESET at 08:47:47.
  - One more host retry came at 08:45:01. The system log from 08:44:30 to
    08:45:05 has no VPN, tunnel or route event. Its cause is not established.
- **Yesterday matches on timing (inferred).** The detailed agent log for
  2026-10-14 has rotated out, and only process stamps remain.
  - The Cisco Secure Client app started at 18:53:35 KST.
  - VPN agent helper processes appeared at 18:51–18:53, 19:49, 20:18, 23:02
    and 23:21.
  - The first host drop followed at 18:54:20. Smoke attempt 1 dropped at about
    20:20 and m01 at about 23:05, each about two minutes after a stamp.
- **Docker cells share the host's routes.** Docker Desktop opens container
  connections from the host, so a host route change can break them as well.

**Consequence.** A live run needs a fixed host network. No VPN may connect or
disconnect, and the host may not switch networks, while a cell runs.
[benchmark/README.md](../../../benchmark/README.md) now states this as a hard
rule. The rule avoids the likely trigger. It does not prove that every drop
goes away, and a drop during a cell still stops the run as registered.
Candidates 2 and 3 remain for the owner.

## Descriptive signal (not measured data)

In smoke attempt 2, on SM, one observation per cell:

- **Codex Y read the new paragraph in full, untruncated.** Its report still
  had the rp-d1 shape: "PR #1 merged, and the local checkout is clean. Nothing
  remains unresolved."
- **Claude reported cleanup and reconciliation in both arms.**

This is consistent with Grok's recorded dissent: the prompt's closing sentence
("Finish with what you changed, what you verified and anything unresolved")
may set Codex's report shape. It proves nothing about BV/Z0.

## Decision and next candidates

The registered write-up rule applies: Y is not adopted, and the
`task-completion.md` paragraph and its `.agents` mirror are reverted to
`7516ebc9`. No product file changes on main.

Next candidates, for the owner to choose:

1. **Diagnose the connection drops first.** Find out whether long-silent
   streams are reset in the cell network, for example with a timed idle-stream
   probe from the same image, before any Claude-inclusive rerun. Every Claude
   cost guardrail depends on COMPLETE usage.
2. **Grok's prompt ablation.** Hold the published paragraph fixed and drop the
   prompt's closing sentence in arm Y. This tests whether the report failures
   in rp-d1 belong to the prompt rather than the product.
3. **Rerun rp-d2 unchanged after (1).** This needs a new run ID, fresh
   repositories and a PAT edit.

## Cleanup

Cleanup is done after this write-up merges. The PR records each removal once
it is verified:

- the 18 never-used, empty `rpd2-20261014a-*` repositories: m02–m16 and the
  three attempt-1 smoke cells that did not run. The apparatus had already
  archived and deleted the other six, smoke-claude-X, the four smoke2 cells
  and m01, each confirmed 404;
- the measurement image and its saved copy;
- the live directory, `~/.local/share/nx01/rp-d2-live`;
- the worktree, after merge.

The owner deletes the fine-grained PAT (`rpd1-20261013a`, regenerated for
rp-d2) in the GitHub UI.
85-
86-**Output**: 7-axis behavior score, NOT a single PASS/FAIL. `summary_verdict ∈ {IMPROVED, MIXED, REGRESSED}`. Detail: [`instruction-sensitivity/README.md`](instruction-sensitivity/README.md) + [`instruction-sensitivity/RUBRIC.md`](instruction-sensitivity/RUBRIC.md).
87-
88-## Hard rules (every lane)
89-
90-1. **Commit-pinned only.** Working-tree benchmarks are log noise, not evidence. Pin baseline and candidate to specific SHAs.
91-2. **No silent fallbacks on engine unavailability.** Stop and report when an engine is unavailable; never substitute another.
92-3. **Don't mix lanes.** Each lane's fixtures answer its own question; running them in another lane's mode contaminates both signals.
93-4. **Results are evidence, not opinions.** Cite the run-id, the gate JSON path, and the exact verdict — never a paraphrase.
94:5. **Hold the host network fixed during live runs.** Do not connect or disconnect a VPN or switch networks while a cell runs. A route change can interrupt in-flight API streams on the host and in Docker cells (rp-d2 [diagnosis](../autoresearch/experiments/rp-d2-report-lines/results.md#diagnosis-added-2026-10-15-after-merge)).
9b409492 research(rp-d2): register unchanged rerun 20261015a before exposure (smoke attempt 1 qualified)
f5661c81 Merge pull request #237 from fysoul17/research/rp-d2-drop-diagnosis
85192e9d research(rp-d2): diagnosis review records (r1 both REVISE; r2 Grok SHIP, Astra REVISE wording applied)
3399ed03 research(rp-d2): diagnosis review r2 fix (likely cause, not confirmed)
dd312baa research(rp-d2): diagnosis wording wrap
bdac9c69 research(rp-d2): diagnosis review r1 fixes (causation scoped, Codex errors split, timeout claim narrowed)

hook: PostToolUse
hook: PostToolUse
hook: PostToolUse Completed
hook: PostToolUse Completed
[codex-monitored] heartbeat: elapsed=90s
hook: PreToolUse
hook: PreToolUse Completed
hook: PostToolUse
hook: PostToolUse
hook: PostToolUse Completed
hook: PostToolUse Completed
hook: PreToolUse
hook: PreToolUse Completed
exec
/bin/zsh -lc "python3 -B -c 'from pathlib import Path
import json, hashlib, base64, re
w=Path.cwd(); d=w/'\\''autoresearch/experiments/rp-d2-report-lines'\\''; l=Path('\\''/Users/aipalm/.local/share/nx01/rp-d2-rerun-live'\\''); s=l/'\\''stage'\\''
n=json.loads((d/'\\''registration-20261015a.json'\\'').read_text()); old=json.loads((d/'\\''registration.json'\\'').read_text()); rt=json.loads((s/'\\''runtime-measured.json'\\'').read_text()); arms=json.loads((l/'\\''arms/arms.json'\\'').read_text())
fails=[]; counts={}
def ck(label, ok):
 counts['\\''checked'\\'']=counts.get('\\''checked'\\'',0)+1
 if not ok: fails.append(label)
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
ck('\\''runtime_sha256'\\'',sha(s/'\\''runtime-measured.json'\\'')==n['\\''runtime_sha256'\\''])
for k in ['\\''run_id'\\'','\\''phase'\\'','\\''image'\\'','\\''account'\\'','\\''codex_account'\\'','\\''smoke_account'\\'','\\''smoke_codex_account'\\'','\\''auth_manifest_sha256'\\'']:
 ck('\\''runtime '\\''+k,rt[k]==n[k])
ck('\\''smoke attempt'\\'',rt['\\''smoke_attempt'\\'']==n['\\''smoke'\\'']['\\''attempt'\\'']==1)
ck('\\''smoke schedule hash'\\'',sha(s/'\\''smoke-output/rp-schedule.json'\\'')==n['\\''smoke'\\'']['\\''schedule_sha256'\\''])
for cell,h in n['\\''smoke'\\'']['\\''verdicts'\\''].items(): ck('\\''smoke verdict '\\''+cell,sha(s/'\\''smoke-output'\\''/('\\''verdict-'\\''+cell+'\\''.json'\\''))==h)
for path,h in n['\\''inputs'\\''].items(): ck('\\''input '\\''+path,sha(w/path)==h)
ck('\\''unchanged inputs'\\'',n['\\''inputs'\\'']==old['\\''inputs'\\''])
for k in ['\\''schema'\\'','\\''phase'\\'','\\''schedule'\\'','\\''releases'\\'','\\''image'\\'','\\''cli'\\'','\\''routes'\\'','\\''codex_account'\\'','\\''smoke_codex_account'\\'','\\''inputs'\\'','\\''watchdog_seconds'\\'']: ck('\\''unchanged '\\''+k,n[k]==old[k])
for k in ['\\''arms.json'\\'','\\''X.tgz'\\'','\\''Y.tgz'\\'','\\''control.manifest.json'\\'']: ck('\\''unchanged live input '\\''+k,n['\\''live_inputs'\\''][k]==old['\\''live_inputs'\\''][k])
paths={'\\''arms.json'\\'': l/'\\''arms/arms.json'\\'', '\\''X.tgz'\\'':l/'\\''arms/X.tgz'\\'','\\''Y.tgz'\\'':l/'\\''arms/Y.tgz'\\'','\\''control.manifest.json'\\'':s/'\\''control.manifest.json'\\'','\\''models_cache.json'\\'':s/'\\''models_cache.json'\\'','\\''model-auth manifest.json'\\'':l/'\\''model-auth-1/manifest.json'\\''}
for k,p in paths.items(): ck('\\''live hash '\\''+k,sha(p)==n['\\''live_inputs'\\''][k])
ck('\\''staged arms hash'\\'',sha(Path(rt['\\''arms_file'\\'']))==n['\\''live_inputs'\\'']['\\''arms.json'\\''])
for a in ['\\''X'\\'','\\''Y'\\'']:
 for label,v in [('\\''runtime'\\'',rt['\\''releases'\\''][a]),('\\''arms'\\'',arms[a])]:
  ck(label+'\\'' release '\\''+a,{k:v for k,v in v.items() if k"'!='"'\\''tarball'\\''}==n['\\''releases'\\''][a])
 p=Path(rt['\\''releases'\\''][a]['\\''tarball'\\'']); ck('\\''staged tarball '\\''+a,sha(p)==n['\\''releases'\\''][a]['\\''sha256'\\''])
 ck('\\''tarball integrity '\\''+a,'\\''sha512-'\\''+base64.b64encode(hashlib.sha512(p.read_bytes()).digest()).decode()==n['\\''releases'\\''][a]['\\''integrity'\\''])
ck('\\''runtime models hash'\\'',rt['\\''models_cache_sha256'\\'']==n['\\''live_inputs'\\'']['\\''models_cache.json'\\''])
ck('\\''routes'\\'',n['\\''routes'\\'']==json.loads((w/'\\''autoresearch/experiments/rp-d1-delivery-cost/tasks.json'\\'').read_text())['\\''routes'\\''])
ck('\\''repository identities'\\'',n['\\''repositories'\\'']==[f\"fysoul17/rpd2-{n['\\''run_id'\\'']}-{row['\\''slot'\\'']}\" for row in n['\\''schedule'\\'']])
print(json.dumps({'\\''checks'\\'':counts['\\''checked'\\''],'\\''failures'\\'':fails,'\\''runtime_actual'\\'':sha(s/'\\''runtime-measured.json'\\''),'\\''input_count'\\'':len(n['\\''inputs'\\'']),'\\''changed_top_level_fields'\\'':[k for k in sorted(set(n)|set(old)) if n.get(k)"'!=old.get(k)],'"'\\''changed_live_input_fields'\\'':[k for k in n['\\''live_inputs'\\''] if n['\\''live_inputs'\\''][k]"'!=old['"'\\''live_inputs'\\''].get(k)]},indent=2))
raw=(d/'\\''registration-20261015a.json'\\'').read_text()
patterns={'\\''github_pat'\\'':r'\\''(?:github_pat_|gh[pousr]_)[A-Za-z0-9_]{20,}'\\'', '\\''private_key'\\'':r'\\''-----BEGIN [A-Z ]*PRIVATE KEY-----'\\'','\\''jwt'\\'':r'\\''eyJ[A-Za-z0-9_-]{15,}\\.[A-Za-z0-9_-]{15,}\\.[A-Za-z0-9_-]{15,}'\\'','\\''api_key'\\'':r'\\''\\bsk-[A-Za-z0-9_-]{16,}'\\''}
print('\\''registration_secret_pattern_hits'\\'', {k:len(re.findall(v,raw)) for k,v in patterns.items()})
print('\\''safe stage top level'\\'',sorted(p.name for p in s.iterdir()))
out=Path(rt['\\''output'\\'']); print('\\''measured_output_exists'\\'',out.exists()); print('\\''measured_output_names'\\'',sorted(p.name for p in out.iterdir()) if out.exists() else [])
manifest=json.loads(paths['\\''model-auth manifest.json'\\''].read_text()); print('\\''auth_manifest_keys'\\'',sorted(manifest)); print('\\''control_manifest_type'\\'',type(json.loads(paths['\\''control.manifest.json'\\''].read_text())).__name__)
'" in /Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d2-rerun
 succeeded in 0ms:
{
  "checks": 72,
  "failures": [],
  "runtime_actual": "090f29f18fdd2bfde490f7d509087da4c593fd69b219ba5065f9f0ecbdf76b92",
  "input_count": 23,
  "changed_top_level_fields": [
    "account",
    "apparatus_commit",
    "auth_manifest_sha256",
    "live_inputs",
    "repositories",
    "run_id",
    "runtime_sha256",
    "smoke",
    "smoke_account",
    "supersedes_run_id",
    "void_runtime_sha256"
  ],
  "changed_live_input_fields": [
    "models_cache.json",
    "model-auth manifest.json"
  ]
}
registration_secret_pattern_hits {'github_pat': 0, 'private_key': 0, 'jwt': 0, 'api_key': 0}
safe stage top level ['arms', 'control', 'control.manifest.json', 'models_cache.json', 'output', 'runtime-measured.json', 'runtime-smoke.json', 'scratch', 'smoke-output', 'sources']
measured_output_exists True
measured_output_names []
auth_manifest_keys ['account', 'expires_at_ms', 'files', 'schema_version']
control_manifest_type dict

hook: PostToolUse
hook: PostToolUse
hook: PostToolUse Completed
hook: PostToolUse Completed
[codex-monitored] heartbeat: elapsed=120s
All 72 identity and hash checks passed, including the runtime, smoke verdicts and schedule, 23 apparatus inputs, staged arm tarballs, and SHA-512 integrity. The measured output directory is empty. The contract review found no outcome-driven rule changes; I’m finishing archive/deletion verification and checking the route log against the smoke timestamps.
hook: PreToolUse
hook: PreToolUse Completed
hook: PostToolUse
hook: PostToolUse
hook: PostToolUse Completed
hook: PostToolUse Completed
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "python3 -B -c 'from pathlib import Path; import json; p=Path(\"/Users/aipalm/.local/share/nx01/rp-d2-rerun-live/stage/control.manifest.json\"); v=json.loads(p.read_text()); print(\"control manifest keys\", list(v)[:15]); print(\"notes files\",sorted(p.name for p in Path(\"/Users/aipalm/.local/share/nx01/rp-d2-rerun-live/notes\").iterdir())); print(\"staged arm files\",sorted(p.name for p in Path(\"/Users/aipalm/.local/share/nx01/rp-d2-rerun-live/stage/arms\").iterdir()))'" in /Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d2-rerun
 succeeded in 0ms:
control manifest keys ['manifests']
notes files ['image-guard.sh', 'make-registration.py', 'resources.txt', 'route-watch.log', 'route-watch.sh']
staged arm files ['X.tgz', 'Y.tgz', 'arms.json']

hook: PostToolUse
hook: PostToolUse
hook: PostToolUse Completed
hook: PostToolUse Completed
exec
/bin/zsh -lc "rg -n 'manifest|smoke|def .*check|check_runtime' autoresearch/experiments/rp-d2-report-lines/pack.py autoresearch/experiments/rp-d2-report-lines/stage.py && cat /Users/aipalm/.local/share/nx01/rp-d2-rerun-live/model-auth-1/manifest.json && git diff 21699994 HEAD --stat && git status --short" in /Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d2-rerun
 succeeded in 143ms:
autoresearch/experiments/rp-d2-report-lines/pack.py:50:def manifest_digest(manifest):
autoresearch/experiments/rp-d2-report-lines/pack.py:51:    return digest(json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode())
autoresearch/experiments/rp-d2-report-lines/pack.py:54:def archive_manifest(path):
autoresearch/experiments/rp-d2-report-lines/pack.py:76:def tree_manifest(root):
autoresearch/experiments/rp-d2-report-lines/pack.py:105:    manifests = {arm: archive_manifest(path) for arm, path in paths.items()}
autoresearch/experiments/rp-d2-report-lines/pack.py:106:    x, y = manifests['X'], manifests['Y']
autoresearch/experiments/rp-d2-report-lines/pack.py:108:            'arm manifests must differ in exactly the reporting instruction')
autoresearch/experiments/rp-d2-report-lines/pack.py:125:    return manifests
autoresearch/experiments/rp-d2-report-lines/pack.py:161:    archive_manifest(source)
autoresearch/experiments/rp-d2-report-lines/pack.py:166:    manifests = verify_pair(paths)
autoresearch/experiments/rp-d2-report-lines/pack.py:170:                     manifest_sha256=manifest_digest(manifests[arm])) for arm, path in paths.items()}
autoresearch/experiments/rp-d2-report-lines/pack.py:191:    manifests = verify_pair(paths)
autoresearch/experiments/rp-d2-report-lines/pack.py:193:        require(manifest_digest(manifests[arm]) == arms[arm]['manifest_sha256'], arm + ': manifest digest mismatch')
autoresearch/experiments/rp-d2-report-lines/stage.py:20:def smoke_catalogs(output, attempt):
autoresearch/experiments/rp-d2-report-lines/stage.py:22:    for name, _, engine in runner.smoke_slots(attempt):
autoresearch/experiments/rp-d2-report-lines/stage.py:35:    runner.smoke_slots(args.smoke_attempt)
autoresearch/experiments/rp-d2-report-lines/stage.py:39:    smoke_output = (args.smoke_output or dest / 'smoke-output').resolve()
autoresearch/experiments/rp-d2-report-lines/stage.py:40:    require(smoke_output.is_relative_to(dest) and smoke_output != dest, 'smoke output must be under stage directory')
autoresearch/experiments/rp-d2-report-lines/stage.py:42:    roots = [Path(str(path.resolve()).casefold()) for path in (control, dest / 'output', smoke_output, dest / 'scratch')]
autoresearch/experiments/rp-d2-report-lines/stage.py:48:    manifest, manifest_hash = model_auth(args.auth)
autoresearch/experiments/rp-d2-report-lines/stage.py:49:    catalogs = smoke_catalogs(smoke_output, args.smoke_attempt) if phase == 'measured' else {}
autoresearch/experiments/rp-d2-report-lines/stage.py:52:    runtime = dict(run_id=args.run_id, phase=phase, smoke_attempt=args.smoke_attempt, releases=releases,
autoresearch/experiments/rp-d2-report-lines/stage.py:54:        smoke_output=str(smoke_output), scratch=str(dest / 'scratch'), sources=str(dest / 'sources'),
autoresearch/experiments/rp-d2-report-lines/stage.py:56:        account=manifest['account'], codex_account=runner.codex_account(args.auth),
autoresearch/experiments/rp-d2-report-lines/stage.py:57:        auth_manifest_sha256=manifest_hash, boot_catalogs=catalogs,
autoresearch/experiments/rp-d2-report-lines/stage.py:58:        tasks_file=str(runner.PRIOR / ('smoke-tasks.json' if phase == 'smoke' else 'tasks.json')),
autoresearch/experiments/rp-d2-report-lines/stage.py:60:    for output in (runtime['output'], runtime['smoke_output']):
autoresearch/experiments/rp-d2-report-lines/stage.py:64:        previous = read(dest / 'runtime-smoke.json')
autoresearch/experiments/rp-d2-report-lines/stage.py:65:        for key in ('run_id', 'image', 'releases', 'arms_file', 'control', 'models_cache', 'smoke_output',
autoresearch/experiments/rp-d2-report-lines/stage.py:66:                    'smoke_attempt', 'github_auth'):
autoresearch/experiments/rp-d2-report-lines/stage.py:67:            require(runtime[key] == previous[key], 'measured inputs differ from staged smoke: ' + key)
autoresearch/experiments/rp-d2-report-lines/stage.py:68:        runtime['smoke_account'] = previous['account']
autoresearch/experiments/rp-d2-report-lines/stage.py:69:        runtime['smoke_codex_account'] = previous['codex_account']
autoresearch/experiments/rp-d2-report-lines/stage.py:73:        require(phase == 'smoke', 'stage smoke before measurement')
autoresearch/experiments/rp-d2-report-lines/stage.py:92:        write(dest / 'control.manifest.json', dict(manifests={
autoresearch/experiments/rp-d2-report-lines/stage.py:95:    for key in ('output', 'smoke_output', 'scratch', 'sources'):
autoresearch/experiments/rp-d2-report-lines/stage.py:117:    manifest, manifest_hash = model_auth(auth_path)
autoresearch/experiments/rp-d2-report-lines/stage.py:118:    renewal_allowed(previous, manifest['account'], completed)
autoresearch/experiments/rp-d2-report-lines/stage.py:121:    auth.lifetime(manifest['expires_at_ms'])
autoresearch/experiments/rp-d2-report-lines/stage.py:122:    updated = dict(previous, auth=str(auth_path.absolute()), auth_manifest_sha256=manifest_hash,
autoresearch/experiments/rp-d2-report-lines/stage.py:124:    target = runtime_path.parent / ('runtime-measured-auth-' + manifest_hash + '.json')
autoresearch/experiments/rp-d2-report-lines/stage.py:130:def check(runtime_path):
autoresearch/experiments/rp-d2-report-lines/stage.py:133:    expected = runner.PRIOR / ('smoke-tasks.json' if runtime['phase'] == 'smoke' else 'tasks.json')
autoresearch/experiments/rp-d2-report-lines/stage.py:138:    manifest, manifest_hash = model_auth(Path(runtime['auth']))
autoresearch/experiments/rp-d2-report-lines/stage.py:139:    require(manifest_hash == runtime['auth_manifest_sha256'] and manifest['account'] == runtime['account'],
autoresearch/experiments/rp-d2-report-lines/stage.py:140:            'auth manifest/account binding mismatch')
autoresearch/experiments/rp-d2-report-lines/stage.py:141:    auth.lifetime(manifest['expires_at_ms'])
autoresearch/experiments/rp-d2-report-lines/stage.py:143:    for output in (original['output'], original['smoke_output']):
autoresearch/experiments/rp-d2-report-lines/stage.py:156:        require(runtime['boot_catalogs'] == smoke_catalogs(Path(runtime['smoke_output']), runtime['smoke_attempt']),
autoresearch/experiments/rp-d2-report-lines/stage.py:157:                'registered boot catalogs differ from smoke Claude cells')
autoresearch/experiments/rp-d2-report-lines/stage.py:176:    parser.add_argument('--phase', choices=('smoke', 'measured'))
autoresearch/experiments/rp-d2-report-lines/stage.py:177:    parser.add_argument('--smoke-output', type=Path)
autoresearch/experiments/rp-d2-report-lines/stage.py:178:    parser.add_argument('--smoke-attempt', type=int, default=1)
{
  "account": [
    "45eff57aaa45",
    "b6b7768fd228"
  ],
  "expires_at_ms": 1792085288002,
  "files": {
    "claude.env": "11b49d45aa4cf63040c8fa5d1343570f990cc822e90c883be6bf053d37ccce72",
    "codex.json": "ec7f5f27a477119c9faa3573c9f186b8ed901224bfc74c158ecfc1914b63b002"
  },
  "schema_version": 1
}
 .agents/skills/_shared/task-completion.md          |   6 +-
 autoresearch/HANDOFF.md                            |   4 +-
 .../rp-d2-report-lines/registration-20261015a.json | 227 +++++++++++++++++++++
 .../rp-d2-report-lines/registration.json           |  30 +--
 .../experiments/rp-d2-report-lines/registration.md |  64 ++++++
 .../experiments/rp-d2-report-lines/results.md      | 146 +++++++++++++
 .../results/diagnosis-r1-review-astra.md           |  11 +
 .../results/diagnosis-r1-review-grok.md            |  19 ++
 .../results/diagnosis-r2-review-astra.md           |   5 +
 .../results/diagnosis-r2-review-grok.md            |  17 ++
 .../results/registration-r2-review-astra.md        |   9 +
 .../results/registration-r2-review-grok.md         |  20 ++
 .../results/writeup-r1-review-astra.md             |   6 +
 .../results/writeup-r1-review-grok.md              |  11 +
 .../results/writeup-r2-review-astra.md             |   8 +
 .../results/writeup-r2-review-grok.md              |   9 +
 benchmark/README.md                                |   1 +
 config/skills/_shared/task-completion.md           |   6 +-
 18 files changed, 580 insertions(+), 19 deletions(-)

hook: PostToolUse
hook: PostToolUse
hook: PostToolUse Completed
hook: PostToolUse Completed
hook: PreToolUse
hook: PreToolUse Completed
hook: PostToolUse
hook: PostToolUse
hook: PostToolUse Completed
hook: PostToolUse Completed
hook: PreToolUse
hook: PreToolUse Completed
exec
/bin/zsh -lc "sed -n '45,82p' autoresearch/experiments/rp-d2-report-lines/pack.py && sed -n '130,162p' autoresearch/experiments/rp-d2-report-lines/stage.py && cat /Users/aipalm/.local/share/nx01/rp-d2-rerun-live/notes/route-watch.sh" in /Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d2-rerun
 succeeded in 0ms:
def identity(path):
    raw = Path(path).read_bytes()
    return dict(sha256=digest(raw), integrity='sha512-' + base64.b64encode(hashlib.sha512(raw).digest()).decode())


def manifest_digest(manifest):
    return digest(json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode())


def archive_manifest(path):
    result, names = {}, set()
    with tarfile.open(path, 'r:gz') as archive:
        for member in archive:
            name = Path(member.name)
            require(not name.is_absolute() and '..' not in name.parts and name.parts[0] == 'package',
                    'unsafe release archive path')
            require(member.name not in names, 'duplicate release archive member')
            names.add(member.name)
            require(member.isfile() or member.isdir() or member.issym(), 'unsupported release archive entry')
            if member.isdir():
                continue
            relative = str(name.relative_to('package'))
            require(relative != '.', 'release member must be inside package')
            result[relative] = (dict(type='link', target=member.linkname) if member.issym() else
                                dict(type='file', mode=member.mode, sha256=digest(archive.extractfile(member).read())))
    for name in result:
        require(not any(str(parent) in result for parent in Path(name).parents),
                'release entry has a non-directory ancestor')
    return result


def tree_manifest(root):
    result = {}
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            value = dict(type='link', target=str(path.readlink()))
        elif path.is_file():
            value = dict(type='file', mode=path.stat().st_mode & 0o7777, sha256=digest(path.read_bytes()))
def check(runtime_path):
    app = runner.Runner(runtime_path)
    runtime = app.runtime
    expected = runner.PRIOR / ('smoke-tasks.json' if runtime['phase'] == 'smoke' else 'tasks.json')
    require(app.tasks == read(expected) and read(runtime['tasks_file']) == app.tasks, 'phase requires frozen rp-d1 tasks')
    app.inputs()
    runner.prepare.verify_release(runtime)
    require(digest(Path(runtime['models_cache'])) == runtime['models_cache_sha256'], 'models cache changed')
    manifest, manifest_hash = model_auth(Path(runtime['auth']))
    require(manifest_hash == runtime['auth_manifest_sha256'] and manifest['account'] == runtime['account'],
            'auth manifest/account binding mismatch')
    auth.lifetime(manifest['expires_at_ms'])
    original = read(runtime_path)
    for output in (original['output'], original['smoke_output']):
        runner.cell.credential_directory(dict(runtime, output=output))
    hidden = Path(runtime['control']) / 'oracle/experiments/rp-d1-delivery-cost'
    require(digest(hidden / 'oracle.py') == digest(runner.PRIOR / 'oracle.py'), 'hidden oracle changed')
    for task in app.tasks['tasks']:
        for fixture in (Path(runtime['source_root']) / task['source_dir'], hidden / 'fixtures' / task['id']):
            require(app.packet.content(app.packet.tree(fixture)) == task['source_sha256'], 'registered source changed')
    require(all((Path(runtime['control']) / 'public' / name).is_dir() for name in ('python', 'autoresearch')),
            'public check mount missing')
    for name, _, config in app.slots():
        app.repository(name)
        app.boot_expectation(runner.arm_for(name), config)
    if runtime['phase'] == 'measured':
        require(runtime['boot_catalogs'] == smoke_catalogs(Path(runtime['smoke_output']), runtime['smoke_attempt']),
                'registered boot catalogs differ from smoke Claude cells')
    completed = app.completed_prefix()
    require(len(completed) < len(app.slots()), 'schedule already complete')
    name = app.slots()[len(completed)][0]
    app.prior_deleted(name)
    app.validate(name)
#!/bin/bash
# Log host default-route interface changes (attribution only; the apparatus does not read this).
L=~/.local/share/nx01/rp-d2-rerun-live; prev=""
while [ ! -f "$L/notes/run-finished" ]; do
  cur=$(route -n get default 2>/dev/null | awk '/interface:/{print $2}')
  if [ "$cur" != "$prev" ]; then echo "$(date -u +%FT%TZ) default-route interface: ${cur:-none}" >> "$L/notes/route-watch.log"; prev=$cur; fi
  sleep 5
done

hook: PostToolUse
hook: PostToolUse
hook: PostToolUse Completed
hook: PostToolUse Completed
[codex-monitored] heartbeat: elapsed=150s
hook: PreToolUse
hook: PreToolUse Completed
exec
/bin/zsh -lc "python3 -B -c 'from pathlib import Path
from datetime import datetime, timezone
import json,hashlib,tarfile
l=Path('\\''/Users/aipalm/.local/share/nx01/rp-d2-rerun-live'\\''); s=l/'\\''stage'\\''
n=json.loads(Path('\\''autoresearch/experiments/rp-d2-report-lines/registration-20261015a.json'\\'').read_text())
auth=json.loads((l/'\\''model-auth-1/manifest.json'\\'').read_text())
print('\\''auth_manifest_account_matches'\\'',auth['\\''account'\\'']==n['\\''account'\\''])
print('\\''auth_expiry_utc'\\'',datetime.fromtimestamp(auth['\\''expires_at_ms'\\'']/1000,timezone.utc).isoformat())
print('\\''auth_lifetime_seconds_at_review'\\'',round(auth['\\''expires_at_ms'\\'']/1000-datetime.now(timezone.utc).timestamp()))
manifests={}
for arm in ('\\''X'\\'','\\''Y'\\''):
 m={}
 with tarfile.open(s/'\\''arms'\\''/(arm+'\\''.tgz'\\''),'\\''r:gz'\\'') as t:
  for e in t:
   if e.isdir(): continue
   key=str(Path(e.name).relative_to('\\''package'\\''))
   m[key]=dict(type='\\''link'\\'',target=e.linkname) if e.issym() else dict(type='\\''file'\\'',mode=e.mode,sha256=hashlib.sha256(t.extractfile(e).read()).hexdigest())
 h=hashlib.sha256(json.dumps(m,sort_keys=True,separators=('\\'','\\'','\\'':'\\'')).encode()).hexdigest()
 print('\\''extracted_manifest'\\'',arm,'\\''entries'\\'',len(m),'\\''actual'\\'',h,'\\''matches'\\'',h==n['\\''releases'\\''][arm]['\\''manifest_sha256'\\''])
 manifests[arm]=m
print('\\''arm_manifest_differences'\\'',[k for k in sorted(set(manifests['\\''X'\\''])|set(manifests['\\''Y'\\''])) if manifests['\\''X'\\''].get(k)"'!=manifests['"'\\''Y'\\''].get(k)])
smoke=json.loads((s/'\\''runtime-smoke.json'\\'').read_text()); measured=json.loads((s/'\\''runtime-measured.json'\\'').read_text())
fixed=['\\''run_id'\\'','\\''image'\\'','\\''releases'\\'','\\''arms_file'\\'','\\''control'\\'','\\''models_cache'\\'','\\''models_cache_sha256'\\'','\\''smoke_output'\\'','\\''smoke_attempt'\\'','\\''github_auth'\\'','\\''account'\\'','\\''codex_account'\\'','\\''auth_manifest_sha256'\\'']
print('\\''smoke_measured_binding_mismatches'\\'',[k for k in fixed if smoke[k]"'!=measured[k]])
'"'" in /Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d2-rerun
 succeeded in 0ms:
auth_manifest_account_matches True
auth_expiry_utc 2026-10-15T17:28:08.002000+00:00
auth_lifetime_seconds_at_review 10567
extracted_manifest X entries 241 actual cd68caa4bcb0d64df14faa0c8647479ef532b6d84889aac096728b57f08cb2f5 matches True
extracted_manifest Y entries 241 actual 4141d0da1a6250d3af6c7614ef482726aa5d01619e941887438b17c0ad8996d7 matches True
arm_manifest_differences ['config/skills/_shared/task-completion.md']
smoke_measured_binding_mismatches []

hook: PostToolUse
hook: PostToolUse
hook: PostToolUse Completed
hook: PostToolUse Completed
hook: PreToolUse
hook: PreToolUse Completed
hook: PostToolUse
hook: PostToolUse
hook: PostToolUse Completed
hook: PostToolUse Completed
[codex-monitored] heartbeat: elapsed=180s
hook: PreToolUse
hook: PreToolUse Completed
exec
/bin/zsh -lc 'nl -ba autoresearch/experiments/rp-d2-report-lines/registration.md | tail -42 && nl -ba autoresearch/experiments/rp-d2-report-lines/registration-20261015a.json | tail -75' in /Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d2-rerun
 succeeded in 0ms:
   145	3. **Stopping.** Review stops at SHIP with no HIGH finding, reading each
   146	   reviewer's final verdict line.
   147	4. **Write-up.** If Y is not adopted, the write-up reverts the paragraph
   148	   before merge. The prompt ablation recorded in DESIGN.md is then the next
   149	   candidate.
   150	
   151	## Rerun 20261015a (registered 2026-10-15, before exposure)
   152	
   153	Run 20261014a closed INCONCLUSIVE ([results](results.md)). The owner chose
   154	candidate 3 there: an unchanged rerun after the drop diagnosis. Everything
   155	above applies unchanged to run 20261015a: the prediction, the arms, the
   156	schedule, the grading, the cost and adoption rules, STOP and renewal. Its
   157	identities are in
   158	[registration-20261015a.json](registration-20261015a.json).
   159	
   160	- **Unchanged inputs.** The apparatus files, DESIGN.md, README.md, both arm
   161	  tarballs, `arms.json`, the control manifest, the image, the CLI versions and
   162	  the routes hash identically to [registration.json](registration.json).
   163	  `apparatus_commit` is the current main; no apparatus code changed since the
   164	  first registration.
   165	- **New per-run inputs.** The run ID, the 24 repositories, the GitHub PAT
   166	  (selected repositories only, Contents and Pull requests write), the model
   167	  auth snapshot and the Codex models cache. The cache is copied from the host
   168	  at staging, so its `fetched_at` differs. The Claude account pair is
   169	  `45eff57aaa45`/`b6b7768fd228` for smoke and measured; the Codex account is
   170	  unchanged.
   171	- **Network.** [Benchmark hard rule 5](../../../benchmark/README.md) applies:
   172	  the host network is held fixed for the whole run. A watcher logs every change
   173	  of the host's default-route interface. A change during a cell is reported
   174	  with that cell; it does not change any rule above.
   175	- **Smoke attempt 1 qualified all four cells.** No stream retry or API error
   176	  was recorded.
   177	
   178	| Cell | Owner s | Input | Output | Usage | Delivery | Repository |
   179	|---|---:|---:|---:|---|---|---|
   180	| Claude X | 572.4 | 2,519,890 | 59,060 | COMPLETE | passed | archived, deleted (404) |
   181	| Claude Y | 758.5 | 3,140,290 | 78,545 | COMPLETE | passed | archived, deleted (404) |
   182	| Codex X | 175.0 | 514,105 | 6,903 | COMPLETE | passed | archived, deleted (404) |
   183	| Codex Y | 131.8 | 381,285 | 5,889 | COMPLETE | passed | archived, deleted (404) |
   184	
   185	The run 20261014a smoke and measured records stay as they are and are never
   186	pooled with this run.
   153	    "effort": "max",
   154	    "engine": "claude",
   155	    "model": "claude-opus-5-5"
   156	   }
   157	  },
   158	  "codex": {
   159	   "owner": {
   160	    "child_effort": "high",
   161	    "child_model": "gpt-6-sol",
   162	    "effort": "high",
   163	    "engine": "codex",
   164	    "model": "gpt-6-sol"
   165	   }
   166	  }
   167	 },
   168	 "account": [
   169	  "45eff57aaa45",
   170	  "b6b7768fd228"
   171	 ],
   172	 "codex_account": "65ad276127a5",
   173	 "auth_manifest_sha256": "cd4fa3d350d13ad685c1c7f906e54060344e32f3e28cc6ea51401c6dfbf7aff5",
   174	 "smoke_account": [
   175	  "45eff57aaa45",
   176	  "b6b7768fd228"
   177	 ],
   178	 "smoke_codex_account": "65ad276127a5",
   179	 "runtime_sha256": "090f29f18fdd2bfde490f7d509087da4c593fd69b219ba5065f9f0ecbdf76b92",
   180	 "smoke": {
   181	  "attempt": 1,
   182	  "verdicts": {
   183	   "smoke-claude-X": "6a224081735324eccbcc5d18aed6865240f72e6d41c586992a6933f34dc4c0bc",
   184	   "smoke-claude-Y": "b05561fbe9e73e5f12342f410f4093ba49c8a8164383becbb056c45b22de265a",
   185	   "smoke-codex-X": "7a51ed653d5a9295a61bacc815304f14e99156c8e0861d2079f7928a9f451696",
   186	   "smoke-codex-Y": "1701339b54a20da4de27201368503c36cffaca2799f89cdc21b1e3bdb8e7b10a"
   187	  },
   188	  "schedule_sha256": "e605cc00829d1396335dd5d4a885070d42a97678c5734c8cfc1839c243fe7cf8"
   189	 },
   190	 "inputs": {
   191	  "autoresearch/experiments/rp-d1-delivery-cost/Dockerfile": "6b9131a724e90aa381bb0e59411d31cdcff15a85a36a738df9f8f13278930b89",
   192	  "autoresearch/experiments/rp-d1-delivery-cost/build.sh": "aefbfa7f764399804b3e8931a03afa1ac18c64aa2c168a199eb4e0c3869e582e",
   193	  "autoresearch/experiments/rp-d1-delivery-cost/cell.py": "2a0f07a972fdfbab0d4c53039025507bda437d73c8f5e95163795c0e512d8678",
   194	  "autoresearch/experiments/rp-d1-delivery-cost/common.txt": "2ccc7f6a11891f6270685c09ada44cc4376bbedb047f8a0864f950b415bf50cf",
   195	  "autoresearch/experiments/rp-d1-delivery-cost/github.py": "64537542ff976cb280c4dcfb9e2bf65fddeef56684e034c5fea3304ae0d2aca9",
   196	  "autoresearch/experiments/rp-d1-delivery-cost/oracle.py": "4c2d454662fd3c299dfac136bbff01d439ccd23af5b331d13b2e42cf44dab959",
   197	  "autoresearch/experiments/rp-d1-delivery-cost/prepare.py": "6531b2958d81bbf4baff52fd118b61f43a05c26400569c4e2eb955947e5feb77",
   198	  "autoresearch/experiments/rp-d1-delivery-cost/reevaluate.py": "4d122ddceedbeff80dbac9f93fb86ba8ac87b2fbc0b3037da7d8fdbde776e128",
   199	  "autoresearch/experiments/rp-d1-delivery-cost/runner.py": "337af3003f76ec0407abf341752613c6bf87b094d47ffd7217d8f42ac115e811",
   200	  "autoresearch/experiments/rp-d1-delivery-cost/summarize.py": "eb223d5222d6d50ee4c791a40dd49f26af0271c792ae799fb2cb484205e99be1",
   201	  "autoresearch/experiments/rp-d1-delivery-cost/tasks.json": "12f4ef121cc0544ab1ffe42caf4cf5cc17d6df096cc1d2dcdd2565732c4f7ef7",
   202	  "autoresearch/experiments/rp-d2-report-lines/DESIGN.md": "e623d7a8c8a39063c317813f50d083ebdbc0bdc37378e7159b51a09245022ddc",
   203	  "autoresearch/experiments/rp-d2-report-lines/README.md": "3aa1ea55eee7889f9133b78244a9d48c72fafa5c6a6b4cb06e10cc918aded9ab",
   204	  "autoresearch/experiments/rp-d2-report-lines/pack.py": "302f9f48c4bb3a3cb4a3c4d99d26f89e7ef6f3118f3b165fa574191f527b5aff",
   205	  "autoresearch/experiments/rp-d2-report-lines/prepare.py": "43bffb00427388c1b2fc0f013cd1adf56130e979b2fb7f1d8bdd7ad1665aba76",
   206	  "autoresearch/experiments/rp-d2-report-lines/reevaluate.py": "feb4129fa21ab55d81448d579ecd6a0be6e31a566308fe7f4d8c3422ab23ec44",
   207	  "autoresearch/experiments/rp-d2-report-lines/runner.py": "6008e540d586ec9707fbe98016a558346241c398016a806e66f791ac4e1674a3",
   208	  "autoresearch/experiments/rp-d2-report-lines/stage.py": "b4703ffae17e66242f0531e49c7656dd41faf74ddfcb68a954b3e14d242290e8",
   209	  "autoresearch/experiments/rp-d2-report-lines/summarize.py": "92878ec0ea1225c8c25d2a8e2771eb75b788674b7200ee32cb866a64cfbdf4d2",
   210	  "autoresearch/experiments/rp-d2-report-lines/test_rpd2_pack.py": "065553d0908a6555038b409526b88748b3a892bbbd4c973a174ebdb709421e7f",
   211	  "autoresearch/experiments/rp-d2-report-lines/test_rpd2_runner.py": "6759792ed3b291f08e9c1171262f2b838b4ced4d3c6bbd26ad9235c985022cd1",
   212	  "autoresearch/experiments/rp-d2-report-lines/test_rpd2_summary.py": "2e572d4cdb11b796f4be18d3f58f8501d8201172f2248f277d9e22d5eb599914",
   213	  "autoresearch/experiments/rp-d2-report-lines/token_gate.py": "ec59c4f604fac2145cf9fa397b7ef0fe28493095839a5248fa962a5ff5cca7e7"
   214	 },
   215	 "live_inputs": {
   216	  "arms.json": "60a97ad511ae2e2ce366a9b7905fb8c25c3bfaf718c12e24d822dde6d3236caa",
   217	  "X.tgz": "7b22cce865d99e1400f9c0b0bff41c1b9ae3645b132cbb868ec01cadc973393e",
   218	  "Y.tgz": "c45bc13aec01f625a6687a9697854e705b3eb201fc2b0f1e01626e9f8dcaf603",
   219	  "control.manifest.json": "499d0476ec6fbfd1de222eef450ae0bdd3df25a7cbda0125ab441faf707e6db5",
   220	  "models_cache.json": "e5ad6ad98d3b82fb9a95602cf0b6d024aa1c562f9057a81bd68c80551b89c88c",
   221	  "model-auth manifest.json": "cd4fa3d350d13ad685c1c7f906e54060344e32f3e28cc6ea51401c6dfbf7aff5"
   222	 },
   223	 "watchdog_seconds": {
   224	  "owner": 5400,
   225	  "evaluator_or_review": 600
   226	 }
   227	}

hook: PostToolUse
hook: PostToolUse
hook: PostToolUse Completed
hook: PostToolUse Completed
hook: PreToolUse
hook: PreToolUse Completed
hook: PostToolUse
hook: PostToolUse
hook: PostToolUse Completed
hook: PostToolUse Completed
[codex-monitored] heartbeat: elapsed=210s
No findings requiring changes; no CRITICAL, HIGH, MEDIUM, or LOW issues.

- **Contract:** Frozen prediction, schedule, grading, cost/adoption, STOP, and renewal rules remain unchanged. No evidence of measured-outcome tuning. The prior instrumentation failure informed the disclosed diagnosis and rerun choice.
- **Registration:** All registered hashes match actual files. Runtime, smoke evidence, accounts, releases, tarball integrity, and extracted manifests agree. All 23 apparatus input hashes equal the original registration. No secrets found.
- **Qualification:** All four attempt-1 cells pass the apparatus’s smoke qualification predicate: delivery passed, usage COMPLETE, archives verified, deletion receipts confirm 404. Every table number matches its verdict, including wall-time rounding. No retry/error events or route changes overlap the smoke cells.
- **Exposure boundary:** Measured output is empty. No Python changes exist since `21699994`; unchanged apparatus code was not re-reviewed.

Credential files were not read; nothing was modified. No fixes are required before exposure.

VERDICT: SHIP
