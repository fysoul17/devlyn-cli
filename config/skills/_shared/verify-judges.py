#!/usr/bin/env python3
"""Run both VERIFY judges concurrently from one input snapshot, then merge.

This is the owner's only VERIFY command after MECHANICAL. It claims the round
by exclusively creating the dispatch record, renders both prompts from the same
snapshot, starts both judge runners before waiting on either, retains role
evidence for each successful runner, and ends with the one merge call that
collects, validates and writes the VERIFY verdict. It never writes state.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import runpy
import shutil
import signal
import subprocess
import sys
import time

sys.dont_write_bytecode = True
SHARED = pathlib.Path(__file__).resolve().parent
PLATFORM = runpy.run_path(str(SHARED / "platform-support.py"))
ROLE = runpy.run_path(str(SHARED / "role-config.py"))
RENDER = runpy.run_path(str(SHARED / "phase-prompt-render.py"))
EVIDENCE = runpy.run_path(str(SHARED / "judge-role-evidence.py"))
MERGE = runpy.run_path(str(SHARED / "verify-merge-findings.py"))
ROLES = ("primary_judge", "pair_judge")
BUDGET_SECONDS = 600
DEFAULT_EFFORT = {("codex", "primary_judge"): "high", ("codex", "pair_judge"): "medium",
                  ("claude", "primary_judge"): None, ("claude", "pair_judge"): "medium"}
# Inherited dispatch/evidence settings from an enclosing run must not reach a judge;
# CLAUDECODE would make the nested Claude CLI refuse to start.
SCRUBBED_PREFIXES = ("DEVLYN_INVOCATION_", "DEVLYN_VERIFY_", "CODEX_MONITORED_")
SCRUBBED_NAMES = {"DEVLYN_CODEX_PROMPT_FILE", "CLAUDECODE"}
HEARTBEAT_SECONDS = 30
TEARDOWN_GRACE_SECONDS = 15


class Blocked(Exception):
    pass


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def decide(state: dict, resolution: dict, role: str, mechanical_blocker: bool) -> dict:
    entry = resolution["roles"][role]
    engine = entry["engine"]
    decision = {"engine": engine, "model_requested": entry["model_requested"],
                "effort_requested": entry["effort_requested"], "decision": "skip", "reason": None}
    if mechanical_blocker:
        return {**decision, "reason": "mechanical_blocker"}
    if role == "pair_judge" and entry.get("skipped_reason"):
        if entry["skipped_reason"] == "auto_pair_other_engine_unavailable" and state.get("pair_verify") is True:
            other = "codex" if resolution["roles"]["primary_judge"]["engine"] == "claude" else "claude"
            return {**decision, "decision": "blocked",
                    "reason": f"BLOCKED:{other}-unavailable: --pair-verify requires an OTHER-engine judge; install and authenticate {other}"}
        return {**decision, "reason": entry["skipped_reason"]}
    if engine not in {"claude", "codex"}:
        return {**decision, "decision": "blocked", "reason": f"BLOCKED:judge-route-unsupported:{engine}"}
    try:
        ROLE["native_version"](engine)
        ROLE["options"](entry, role)
    except ValueError as exc:
        automatic = (role == "pair_judge" and entry.get("source") == "default"
                     and state.get("pair_verify") is not True
                     and str(exc).startswith(f"BLOCKED:{engine}-unavailable"))
        if automatic:
            return {**decision, "reason": "auto_pair_other_engine_unavailable"}
        return {**decision, "decision": "blocked", "reason": str(exc)}
    return {**decision, "decision": "dispatch", "channel": ROLE["channel"](engine, role),
            "effort": entry["effort_requested"] or DEFAULT_EFFORT[(engine, role)],
            "stem": f"{engine}-judge.r{state['phases']['verify']['round']}"}


def launch_argv(devlyn: pathlib.Path, entry: dict) -> tuple[list[str], dict[str, str]]:
    prompt = str(devlyn / (entry["stem"] + ".prompt"))
    model, effort = entry["model_requested"], entry["effort"]
    if entry["engine"] == "codex":
        # Resolve Bash through PATH: a bare name on Windows can start System32's WSL launcher.
        argv = [shutil.which("bash") or "bash", str(SHARED / "codex-monitored.sh"), "-C", str(devlyn.parent),
                "-s", "read-only"]
        argv += ["-m", model] if model else []
        argv += ["-c", f"model_reasoning_effort={effort}", "-"]
        return argv, {"DEVLYN_CODEX_PROMPT_FILE": prompt, "CODEX_MONITORED_ISOLATED": "1",
                      "CODEX_MONITORED_TIMEOUT_SEC": str(BUDGET_SECONDS)}
    argv = [sys.executable, str(SHARED / "run-bounded.py"), str(BUDGET_SECONDS), "--stdin-file", prompt,
            "--record-transport", "--", "claude", "-p", "--permission-mode", "dontAsk",
            "--tools", "Read,Grep,Glob", "--allowedTools", "Read,Grep,Glob", "--setting-sources", "project",
            "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}']
    argv += ["--model", model] if model else []
    argv += ["--effort", effort] if effort else []
    return argv + ["--output-format", "json", "--json-schema", EVIDENCE["JUDGE_SCHEMA_TEXT"]], {}


def write_new(path: pathlib.Path, raw: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(raw)


def launch(argv: list[str], cwd: pathlib.Path, env: dict[str, str], stdout, stderr) -> dict:
    """Start one runner that can be torn down with its whole process tree."""
    if os.name == "nt":
        # Git Bash execs the Codex dispatcher as a separate native process, so only a job
        # enclosing the runner reaches every descendant.
        job = PLATFORM["_WindowsJob"]()
        try:
            return {"proc": job.start(argv, subprocess.DEVNULL, cwd=cwd, env=env, stdout=stdout, stderr=stderr),
                    "job": job, "code": None}
        except BaseException:
            job.terminate()  # A launch that failed after the target started still owns it.
            raise
    return {"proc": subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                                     start_new_session=True), "job": None, "code": None}


def poll(runner: dict) -> int | None:
    """The runner's exit status, kept once known (a finished Windows job closes the process handle)."""
    if runner["code"] is None:
        runner["code"] = runner["proc"].poll()
    return runner["code"]


def end_job(runner: dict) -> None:
    """Terminate a Windows runner's job exactly once; a runner the job ended exits 1."""
    job, runner["job"] = runner["job"], None
    if job is not None:
        code = poll(runner)
        try:
            job.terminate()
        finally:
            runner["code"] = 1 if code is None else code


def each(runners: dict[str, dict], action) -> list[str]:
    """Apply `action` to every runner even when one of them fails; return the failures."""
    errors = []
    for role, runner in runners.items():
        try:
            action(runner)
        except (OSError, subprocess.SubprocessError) as exc:
            errors.append(f"{role}: {exc}")
    return errors


def teardown(runners: dict[str, dict]) -> list[str]:
    """Stop live runners: a POSIX runner tears down its own child tree on TERM; a Windows job ends all members."""
    live = {role: runner for role, runner in runners.items() if poll(runner) is None}

    def interrupt(runner):
        if runner["job"] is not None:
            end_job(runner)
            return
        try:
            os.killpg(runner["proc"].pid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            pass  # Already gone, or an unreaped leader (macOS reports EPERM); reap() collects it.

    deadline = time.monotonic() + TEARDOWN_GRACE_SECONDS

    def reap(runner):
        if runner["code"] is not None:
            return
        try:
            runner["code"] = runner["proc"].wait(timeout=max(0.0, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            try:
                os.killpg(runner["proc"].pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
            runner["code"] = runner["proc"].wait()

    return each(live, interrupt) + each(live, reap)


def supervise(runners: dict[str, dict], received: list[int]) -> list[str]:
    """Wait for every runner, tearing all down on a handled signal or a wedged runner; return cleanup failures."""
    errors: list[str] = []
    started = time.monotonic()
    next_heartbeat = started + HEARTBEAT_SECONDS
    while any(poll(runner) is None for runner in runners.values()):
        now = time.monotonic()
        # Runners bound their own children; this only catches a wedged runner.
        if received or now - started > BUDGET_SECONDS + 2 * TEARDOWN_GRACE_SECONDS:
            errors += teardown(runners)
            break
        if now >= next_heartbeat:
            running = ",".join(role for role, runner in runners.items() if poll(runner) is None)
            print(f"[verify-judges] heartbeat: elapsed={int(now - started)}s running={running}",
                  file=sys.stderr, flush=True)
            next_heartbeat = now + HEARTBEAT_SECONDS
        time.sleep(0.2)
    return errors + each(runners, end_job)  # Close each job; any straggling descendant ends with it.


def merge(devlyn: pathlib.Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SHARED / "verify-merge-findings.py"), "--devlyn-dir", str(devlyn),
                           "--write-state"], capture_output=True, text=True, encoding="utf-8")


def run(devlyn: pathlib.Path) -> int:
    devlyn = devlyn.resolve()
    with PLATFORM["file_lock"](devlyn / "pipeline.state.lock", blocking=True):
        try:
            state = ROLE["loads"]((devlyn / "pipeline.state.json").read_bytes())
            resolution = ROLE["snapshot"](state)
        except (OSError, ValueError) as exc:
            raise Blocked(f"verify-not-open: {exc}") from exc
    verify = (state.get("phases") or {}).get("verify")
    if (resolution is None or not isinstance(verify, dict) or not verify.get("started_at")
            or verify.get("completed_at") or type(verify.get("round")) is not int):
        raise Blocked("verify-not-open")
    _findings, mechanical = MERGE["mechanical_source"](devlyn)
    roles = {role: decide(state, resolution, role, MERGE["rank"](mechanical) >= 2) for role in ROLES}
    dispatched = [role for role in ROLES if roles[role]["decision"] == "dispatch"]
    snapshot, prompts = None, {}
    if dispatched:
        try:
            snapshot = RENDER["build_verify_snapshot"](devlyn, state)
        except SystemExit as exc:
            for role in dispatched:
                roles[role].update(decision="blocked", reason=str(exc))
            dispatched = []
    for role in dispatched:
        prompts[role] = RENDER["render_verify"](role, roles[role]["engine"], snapshot)
        roles[role]["prompt_sha256"] = sha256(prompts[role])
        roles[role]["argv"], roles[role]["environment"] = launch_argv(devlyn, roles[role])
    pair = roles["pair_judge"]
    trigger = ({"eligible": False, "reasons": [], "skipped_reason": pair["reason"]} if pair["decision"] == "skip"
               else {"eligible": True, "reasons": MERGE["outcome_independent_reasons"](devlyn), "skipped_reason": None})
    seal = devlyn / "source-seal.json"
    record = {"schema": 1, "run_id": state.get("run_id"), "round": verify["round"],
              "verify_started_at": verify["started_at"], "resolution_sha256": resolution["sha256"],
              "snapshot_sha256": sha256(snapshot) if snapshot is not None else None,
              # The merge refuses a MECHANICAL seal that changed after this dispatch decision.
              "source_seal_sha256": hashlib.sha256(seal.read_bytes()).hexdigest() if seal.is_file() else None,
              "pair_trigger": trigger, "roles": roles}
    # From the claim on, a signal is recorded and handled: launched runners are torn down
    # and the merge still runs.
    received: list[int] = []
    previous = {sig: signal.signal(sig, lambda signum, _frame: received.append(signum))
                for sig in (signal.SIGTERM, signal.SIGINT)}
    try:
        try:
            write_new(devlyn / f"verify-judge.r{verify['round']}.dispatch.json",
                      (json.dumps(record, indent=2, sort_keys=True) + "\n").encode("utf-8"))
            for role in dispatched:
                stem = roles[role]["stem"]
                write_new(devlyn / (stem + ".prompt"), prompts[role])
                write_new(devlyn / (stem + ".argv.json"), ROLE["encoded"](roles[role]["argv"]))
        except FileExistsError as exc:
            raise Blocked(f"verify-already-supervised: {exc.filename}") from exc
        environment = {key: value for key, value in os.environ.items()
                       if not key.startswith(SCRUBBED_PREFIXES) and key not in SCRUBBED_NAMES}
        runners: dict[str, dict] = {}
        errors: list[str] = []
        try:
            for role in dispatched:
                if received:
                    break
                entry = roles[role]
                capture = entry["stem"] + (".output.json" if entry["engine"] == "claude" else ".stdout")
                with (devlyn / capture).open("xb") as stdout, (devlyn / (entry["stem"] + ".stderr")).open("xb") as stderr:
                    runners[role] = launch(entry["argv"], devlyn.parent, {**environment, **entry["environment"]},
                                           stdout, stderr)
        except (OSError, subprocess.SubprocessError) as exc:  # Includes a failed launch's own cleanup timing out.
            print(f"[verify-judges] launch failed: {exc}", file=sys.stderr, flush=True)
            errors += teardown(runners)
        errors += supervise(runners, received)
        for error in errors:
            print(f"[verify-judges] cleanup failed: {error}", file=sys.stderr, flush=True)
        for role, runner in runners.items():
            if runner["code"] == 0:
                try:
                    EVIDENCE["retain"](devlyn, state, role, 0)
                except (OSError, ValueError, TypeError, KeyError) as exc:
                    print(f"[verify-judges] {role} evidence rejected: {exc}", file=sys.stderr, flush=True)
        merged = merge(devlyn)
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)
    sys.stdout.write(merged.stdout)
    sys.stderr.write(merged.stderr)
    if received:
        return 128 + received[0]
    return 0 if merged.returncode == 0 and not errors else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--devlyn-dir", type=pathlib.Path, default=pathlib.Path(".devlyn"))
    group.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    try:
        return run(args.devlyn_dir)
    except Blocked as exc:
        print(json.dumps({"verdict": "BLOCKED", "error": str(exc)}, sort_keys=True))
        return 1


STUB = r"""#!/usr/bin/env python3
import json, os, pathlib, sys, time
engine, args = pathlib.Path(sys.argv[0]).name, sys.argv[1:]
if args == ["--version"]:
    print("9.9.9")
    sys.exit(0)
if "CLAUDECODE" in os.environ or any(key.startswith("DEVLYN_INVOCATION_") for key in os.environ):
    sys.exit(9)
prompt = sys.stdin.read()
state = pathlib.Path(os.environ["STUB_DIR"])
(state / (engine + ".pid")).write_text(str(os.getpid()))
(state / (engine + ".argv")).write_text(json.dumps(args))
mode = os.environ.get("STUB_" + engine.upper(), "pass")
barrier = state / "barrier"
if os.environ.get("STUB_BARRIER"):
    (barrier / engine).touch()
    deadline = time.time() + 20
    while len(list(barrier.iterdir())) < 2 and time.time() < deadline:
        time.sleep(0.05)
    if len(list(barrier.iterdir())) < 2:
        sys.exit(3)
if mode == "sleep":
    time.sleep(120)
if mode in {"fail", "exit124"}:
    sys.exit(1 if mode == "fail" else 124)
option = lambda name, default: args[args.index(name) + 1] if name in args else default
finding = {"id": engine + "-1", "rule_id": "fixture.binding",
           "severity": {"high": "HIGH", "narrated": "LOW"}.get(mode, "CRITICAL"),
           "file": "app.py", "line": 1, "message": engine + " finding", "criterion_ref": "spec", "confidence": "high"}
text = {"pass": "PASS\n", "high": json.dumps(finding) + "\nNEEDS_WORK\n",
        "narrated": "I found no blocking issues, only one low-severity one.\n\n" + json.dumps(finding) + "\nPASS_WITH_ISSUES",
        "blocked": json.dumps(finding) + "\nBLOCKED\n", "garbage": "not a verdict\n"}[mode]
judgment = {"pass": {"findings": [], "verdict": "PASS"}, "high": {"findings": [finding], "verdict": "NEEDS_WORK"},
            "narrated": {"findings": [finding], "verdict": "PASS_WITH_ISSUES"},
            "blocked": {"findings": [finding], "verdict": "BLOCKED"}}.get(mode)
if engine == "codex":
    effort = next(arg.split("=", 1)[1] for arg in args if arg.startswith("model_reasoning_effort="))
    sys.stderr.write("OpenAI Codex v9.9.9\n--------\nworkdir: " + option("-C", "") + "\nmodel: "
                     + option("-m", "fixture-codex-default") + "\nsandbox: read-only\nreasoning effort: "
                     + effort + "\nsession id: fixture-codex\n--------\nuser\n" + prompt)
    sys.stdout.write(text)
else:
    envelope = {"type": "result", "subtype": "success", "is_error": False, "stop_reason": "end_turn",
                "session_id": "fixture-claude", "result": text, "modelUsage": {option("--model", "fixture-claude-default"): {}}}
    sys.stdout.write(json.dumps({**envelope, **({"structured_output": judgment} if judgment else {})}))
"""


def self_test() -> int:
    if os.name == "nt":
        print("SKIP verify-judges POSIX stub self-test; native Windows seats run in scripts/test-windows-portability.py")
        return 0
    import contextlib
    import io
    import tempfile

    def git(work, *args):
        return subprocess.run(["git", "-c", "user.name=fixture", "-c", "user.email=fixture@example.com", *args],
                              cwd=work, check=True, capture_output=True, text=True).stdout.strip()

    def loads(path):
        return ROLE["loads"](path.read_bytes())

    with tempfile.TemporaryDirectory(prefix="verify-judges-") as raw:
        root = pathlib.Path(raw).resolve()
        everything, claude_only = root / "bin", root / "bin-claude"
        for directory, engines in ((everything, ("claude", "codex")), (claude_only, ("claude",))):
            directory.mkdir()
            for engine in engines:
                (directory / engine).write_text(STUB, encoding="utf-8")
                (directory / engine).chmod(0o755)
        # Judges must resolve to the stubs, never an installed engine CLI.
        system = root / "sys-bin"
        system.mkdir()
        (system / "python3").symlink_to(sys.executable)
        isolated_path = os.pathsep.join([str(system), "/usr/bin", "/bin"])
        codex_home = root / "codex-home"
        codex_home.mkdir()
        (codex_home / "models_cache.json").write_text(json.dumps({"client_version": "9.9.9", "models": [
            {"slug": "fixture-codex-model", "supported_reasoning_levels": [{"effort": "medium"}, {"effort": "high"}]}]}))
        saved = dict(os.environ)

        def make_run(name, roles=None, *, pair_verify=False, no_pair=False):
            work = root / name
            devlyn = work / ".devlyn"
            devlyn.mkdir(parents=True)
            git(work, "init", "-q")
            (work / ".gitignore").write_text(".devlyn/\n")
            (work / "spec.md").write_text("# Spec\n\n## Requirements\n- app returns b\n")
            (work / "app.py").write_text("a\n")
            git(work, "add", ".")
            git(work, "commit", "-qm", "base")
            base = git(work, "rev-parse", "HEAD")
            (work / "app.py").write_text("b\n")
            git(work, "commit", "-qam", "change")
            if roles:
                (devlyn / "engines.json").write_bytes(ROLE["encoded"]({"roles": roles}))
            (devlyn / "plan.md").write_text('<!-- devlyn:authorized-surface -->\n## Files to touch\n```json\n'
                                            '{"authorized_surface": ["app.py"]}\n```\n')
            (devlyn / "verify-mechanical.findings.jsonl").write_text("")
            (devlyn / "spec-verify.results.json").write_text('{"commands": [], "process_evidence": null}\n')
            resolution = ROLE["resolve"](work, "claude", no_pair=no_pair, available=lambda engine: True)
            state = {"version": "3.0", "run_id": "rs-" + name, "engine": "claude", "mode": "spec",
                     "base_ref": {"sha": base}, "pair_verify": pair_verify,
                     "source": {"type": "spec", "spec_path": "spec.md",
                                "spec_sha256": sha256((work / "spec.md").read_bytes())},
                     "risk_profile": {"high_risk": False, "risk_probes_enabled": False,
                                      "pair_default_enabled": not no_pair, "reasons": []},
                     "rounds": {"global": 0, "max_rounds": 2}, "role_resolution": resolution,
                     "verify": {"coverage_failed": False, "pair_trigger": None},
                     "phases": {"verify": {"engine": resolution["roles"]["primary_judge"]["engine"], "round": 0,
                                           "started_at": "2026-09-27T00:00:00Z", "completed_at": None,
                                           "verdict": None, "sub_verdicts": None}}}
            (devlyn / "pipeline.state.json").write_bytes(ROLE["encoded"](state))
            return work

        def verify(work, *, path=everything, short=None, hold=False, **modes):
            stubs = work / "stubs"
            shutil.rmtree(stubs, ignore_errors=True)
            (stubs / "barrier").mkdir(parents=True)
            os.environ.clear()
            os.environ.update(saved, PATH=f"{path}{os.pathsep}{isolated_path}", CODEX_HOME=str(codex_home),
                              STUB_DIR=str(stubs), CLAUDECODE="1", DEVLYN_INVOCATION_RUN_ID="enclosing",
                              **{"STUB_" + key.upper(): value for key, value in modes.items()})
            original = launch_argv

            def shortened(devlyn, entry):
                # A two-second budget for one seat only; the other keeps its authenticated 600 s.
                argv, environment = original(devlyn, entry)
                if entry["engine"] != short:
                    return argv, environment
                return ([("2" if arg == str(BUDGET_SECONDS) else arg) for arg in argv],
                        {**environment, **({"CODEX_MONITORED_TIMEOUT_SEC": "2"} if environment else {})})
            globals()["launch_argv"] = shortened
            held_merge = merge
            if hold:  # Stop before the round's one merge so a test can alter what it will collect.
                globals()["merge"] = lambda devlyn: subprocess.CompletedProcess([], 0, "", "")
            output = io.StringIO()
            try:
                with contextlib.redirect_stdout(output):
                    code = main_for(work / ".devlyn")
            finally:
                globals()["launch_argv"] = original
                globals()["merge"] = held_merge
                os.environ.clear()
                os.environ.update(saved)
            text = output.getvalue()
            return code, (json.loads(text) if text.strip() else None), loads(work / ".devlyn/pipeline.state.json")

        def main_for(devlyn):
            try:
                return run(devlyn)
            except Blocked as exc:
                print(json.dumps({"verdict": "BLOCKED", "error": str(exc)}))
                return 1

        def merge_cli(work, relative=False):
            return subprocess.run([sys.executable, str(SHARED / "verify-merge-findings.py"), "--devlyn-dir",
                                   ".devlyn" if relative else str(work / ".devlyn"), "--write-state"],
                                  cwd=work, capture_output=True, text=True)

        def merged_ids(work):
            return [json.loads(line)["id"] for line in
                    (work / ".devlyn/verify-merged.findings.jsonl").read_text().splitlines() if line.strip()]

        def carriers(work, round_=0):
            devlyn = work / ".devlyn"
            return {engine: loads(devlyn / f"{engine}-judge.r{round_}.prompt.transport.json")
                    for engine in ("claude", "codex") if (devlyn / f"{engine}-judge.r{round_}.prompt.transport.json").exists()}

        # Default routes: both judges start before either finishes (the barrier
        # stub exits 3 when serial), and an enclosing CLAUDECODE/receipt env is scrubbed.
        work = make_run("default")
        code, summary, state = verify(work, barrier="1")
        verify_state = state["phases"]["verify"]
        assert code == 0 and summary["verdict"] == "PASS", summary
        assert verify_state["sub_verdicts"] == {"mechanical": "PASS", "judge": "PASS", "pair_judge": "PASS"}
        assert set(verify_state["role_evidence"]) == {"primary_judge", "pair_judge"}
        assert verify_state["pair_trigger"] == state["verify"]["pair_trigger"] == {
            "eligible": True, "reasons": ["pair.default"], "skipped_reason": None}
        assert all(type(value) is int for value in verify_state["judge_durations_ms"].values())
        spans = carriers(work)
        assert min(record["ended_at"] for record in spans.values()) > max(record["started_at"] for record in spans.values())
        claude_argv = json.loads((work / "stubs/claude.argv").read_text())
        codex_argv = json.loads((work / "stubs/codex.argv").read_text())
        assert "--effort" not in claude_argv and "--model" not in claude_argv and "--output-format" in claude_argv
        assert claude_argv[claude_argv.index("--json-schema") + 1] == EVIDENCE["JUDGE_SCHEMA_TEXT"]
        assert "model_reasoning_effort=medium" in codex_argv and "-m" not in codex_argv
        record = loads(work / ".devlyn/verify-judge.r0.dispatch.json")
        prompts = [(work / ".devlyn" / (record["roles"][role]["stem"] + ".prompt")).read_bytes() for role in ROLES]
        frames = [RENDER["prompt_frames"](prompt) for prompt in prompts]
        assert frames[0]["snapshot"] == frames[1]["snapshot"] and sha256(frames[0]["snapshot"]) == record["snapshot_sha256"]
        assert [frame["role"] for frame in frames] == [b"primary_judge", b"pair_judge"]
        assert record["roles"]["primary_judge"]["channel"] == "claude-CLI"
        # A second supervisor never reclaims the round, and a merged round is never merged again.
        code, summary, _ = verify(work)
        assert code == 1 and summary["error"].startswith("verify-already-supervised"), summary
        state_path = work / ".devlyn/pipeline.state.json"
        before = state_path.read_bytes()
        again = merge_cli(work)
        assert again.returncode == 1 and "verify-already-merged" in again.stderr and state_path.read_bytes() == before
        summary_path = work / ".devlyn/verify-merge.summary.json"
        published = summary_path.read_bytes()
        unlocked = subprocess.run([sys.executable, str(SHARED / "verify-merge-findings.py"), "--devlyn-dir", str(work / ".devlyn")],
                                  capture_output=True, text=True)
        assert unlocked.returncode == 2 and summary_path.read_bytes() == published, "merge published outside --write-state"

        # Before the round's one merge: findings files are regenerated outputs, a relative
        # directory works, and a tampered prompt blocks only its own seat.
        work = make_run("held")
        verify(work, hold=True)
        (work / ".devlyn/verify.findings.jsonl").write_text(json.dumps({"id": "forged", "severity": "HIGH"}) + "\n")
        prompt = work / ".devlyn/codex-judge.r0.prompt"
        prompt.write_bytes(prompt.read_bytes() + b"tamper")
        merged = merge_cli(work, relative=True)
        summary = json.loads(merged.stdout)
        assert summary["source_verdicts"]["judge"] == "PASS" and summary["source_verdicts"]["pair_judge"] == "BLOCKED", summary
        assert "forged" not in merged_ids(work) and "verify-judge-execution-incomplete" in merged_ids(work)
        assert "primary_judge" in loads(work / ".devlyn/pipeline.state.json")["phases"]["verify"]["role_evidence"]

        # A sealed round binds its MECHANICAL seal into the dispatch record: an unchanged seal
        # merges, a seal replaced after the dispatch decision never does.
        checker = runpy.run_path(str(SHARED / "spec-verify-check.py"))

        def sealed_run(name):
            work = make_run(name)
            (work / ".gitignore").write_text(".devlyn/\nstubs/\n")  # judge stubs write into the work tree
            git(work, "commit", "-qam", "ignore judge stubs")
            state_path = work / ".devlyn/pipeline.state.json"
            state = loads(state_path)
            state["phases"]["verify"]["pre_sha"] = git(work, "rev-parse", "HEAD")
            state_path.write_bytes(ROLE["encoded"](state))
            reseal(work)
            return work

        def reseal(work):
            current = loads(work / ".devlyn/pipeline.state.json")
            document, digest, problems = checker["source_snapshot"](work, work / ".devlyn", current)
            (work / ".devlyn/source-seal.json").write_text(json.dumps({
                "schema": 1, "run_id": current["run_id"], "round": 0, "snapshot": document, "digest": digest,
                "problems": problems, "seal": {"digest": digest, "head": document["head"]}}))

        work = sealed_run("sealed-ok")
        code, summary, sealed_state = verify(work)
        assert code == 0 and summary["verdict"] == "PASS", summary
        assert sealed_state["phases"]["verify"]["source_seal"]["sha256"] == sha256((work / ".devlyn/source-seal.json").read_bytes())
        work = sealed_run("sealed-replaced")
        verify(work, hold=True)
        assert loads(work / ".devlyn/verify-judge.r0.dispatch.json")["source_seal_sha256"] == sha256(
            (work / ".devlyn/source-seal.json").read_bytes())
        (work / "app.py").write_text("changed after the judges were dispatched\n")
        reseal(work)
        merged = merge_cli(work)
        assert json.loads(merged.stdout)["verdict"] == "BLOCKED", merged.stdout
        assert "verify-dispatch-invalid" in merged_ids(work), merged.stdout

        # A dispatch record that no longer matches the span is never published, checked before
        # any defect of the record itself; a seat whose names differ from the frozen selection is BLOCKED.
        work = make_run("drift")
        verify(work, hold=True)
        state_path, dispatch_path = work / ".devlyn/pipeline.state.json", work / ".devlyn/verify-judge.r0.dispatch.json"
        state, record = loads(state_path), loads(dispatch_path)
        drifted = json.loads(json.dumps(state))
        drifted["phases"]["verify"]["started_at"] = "2026-09-27T00:05:00Z"
        stale = {**record, "run_id": "another-run", "roles": {**record["roles"], "primary_judge": {
            **record["roles"]["primary_judge"], "decision": "skip"}}}
        for state_bytes, record_bytes in ((ROLE["encoded"](drifted), ROLE["encoded"](record)),
                                          (ROLE["encoded"](state), ROLE["encoded"](stale))):
            state_path.write_bytes(state_bytes)
            dispatch_path.write_bytes(record_bytes)
            merged = merge_cli(work)
            assert merged.returncode == 1 and "BLOCKED:verify-state-changed" in merged.stderr, merged.stderr
            assert state_path.read_bytes() == state_bytes
        state_path.write_bytes(ROLE["encoded"](state))
        record["roles"]["pair_judge"]["stem"] = "codex-judge.r9"
        dispatch_path.write_bytes(ROLE["encoded"](record))
        assert json.loads(merge_cli(work).stdout)["source_verdicts"]["pair_judge"] == "BLOCKED"

        # One seat's failure never hides the other's finding, in both orientations.
        for name, modes, kept, failed in (("primary-high", {"claude": "high", "codex": "fail"}, "claude-1", "pair_judge"),
                                           ("pair-high", {"claude": "fail", "codex": "high"}, "codex-1", "judge")):
            work = make_run(name)
            code, summary, _ = verify(work, **modes)
            assert summary["verdict"] == "BLOCKED" and summary["source_verdicts"][failed] == "BLOCKED", summary
            assert kept in merged_ids(work) and "verify-judge-exit-nonzero" in merged_ids(work)
        # An authenticated semantic BLOCKED floors its seat; a HIGH alone is NEEDS_WORK.
        work = make_run("semantic-blocked")
        _, summary, state = verify(work, codex="blocked")
        assert summary["source_verdicts"]["pair_judge"] == "BLOCKED" and "pair_judge" in state["phases"]["verify"]["role_evidence"]
        writer = runpy.run_path(str(SHARED / "state-phase-write.py"))
        state["phases"]["verify"]["completed_at"] = "2026-09-27T00:10:00Z"
        try:
            writer["do_spawn"](state, "implement", 1, "verify", None, None)
        except SystemExit as exc:
            assert str(exc) == "BLOCKED:repair-edge-invalid"
        else:
            raise AssertionError("BLOCKED VERIFY entered product repair")
        work = make_run("needs-work")
        _, summary, state = verify(work, claude="high")
        assert summary["verdict"] == "NEEDS_WORK" and state["phases"]["verify"]["verdict"] == "NEEDS_WORK"
        state["phases"]["verify"]["completed_at"] = "2026-09-27T00:10:00Z"
        writer["do_spawn"](state, "implement", 1, "verify", None, None)
        assert state["rounds"]["global"] == 1
        work = make_run("garbage")
        _, summary, _ = verify(work, codex="garbage")
        assert summary["source_verdicts"]["pair_judge"] == "BLOCKED" and "verify-judge-emission-contract-violated" in merged_ids(work)
        # 0227: a Claude seat answers only through structured output; prose without it BLOCKs that seat alone.
        work = make_run("claude-without-structured-output")
        _, summary, _ = verify(work, claude="garbage", codex="high")
        assert summary["source_verdicts"]["judge"] == "BLOCKED" and summary["source_verdicts"]["pair_judge"] == "NEEDS_WORK", summary
        assert {"codex-1", "verify-role-evidence-invalid"} <= set(merged_ids(work))
        # 0225: leading narrative carries no authority, so a narrated advisory review never hides the other seat's
        # binding finding behind a BLOCKED round; a Claude seat's prose stays outside its structured output, and a
        # malformed emission still BLOCKs its seat while the other seat's finding is kept.
        for name, modes, verdicts in (
                ("narrated-primary", {"claude": "narrated", "codex": "high"}, ("PASS_WITH_ISSUES", "NEEDS_WORK")),
                ("narrated-pair", {"claude": "high", "codex": "narrated"}, ("NEEDS_WORK", "PASS_WITH_ISSUES"))):
            work = make_run(name)
            _, summary, state = verify(work, **modes)
            assert summary["verdict"] == "NEEDS_WORK" and (
                summary["source_verdicts"]["judge"], summary["source_verdicts"]["pair_judge"]) == verdicts, summary
            assert {"claude-1", "codex-1"} <= set(merged_ids(work)) and set(state["phases"]["verify"]["role_evidence"]) == set(ROLES)
            if modes["claude"] == "narrated":  # the derived stdout renders structured_output; the prose is not in it
                envelope = json.loads((work / ".devlyn/claude-judge.r0.output.json").read_text())
                derived = (work / ".devlyn/claude-judge.r0.stdout").read_bytes()
                assert derived == EVIDENCE["structured_judgment"](envelope) and b"blocking issues" not in derived
        work = make_run("garbage-beside-high")
        _, summary, _ = verify(work, claude="high", codex="garbage")
        assert summary["verdict"] == "BLOCKED" and summary["source_verdicts"]["judge"] == "NEEDS_WORK", summary
        assert {"claude-1", "verify-judge-emission-contract-violated"} <= set(merged_ids(work))

        # Explicit profiles apply field by field; a model-only role keeps its default effort.
        work = make_run("profiles", {"primary_judge": {"engine": "claude", "model": "fixture-claude-model"},
                                     "pair_judge": {"engine": "codex", "model": "fixture-codex-model"}})
        _, summary, _ = verify(work)
        claude_argv = json.loads((work / "stubs/claude.argv").read_text())
        codex_argv = json.loads((work / "stubs/codex.argv").read_text())
        assert summary["verdict"] == "PASS", summary
        assert claude_argv[claude_argv.index("--model") + 1] == "fixture-claude-model" and "--effort" not in claude_argv
        assert codex_argv[codex_argv.index("-m") + 1] == "fixture-codex-model" and "model_reasoning_effort=medium" in codex_argv
        # A pinned pair may not be relabeled as an automatic unavailability skip.
        work = make_run("pinned-relabel", {"pair_judge": {"engine": "codex", "model": "fixture-codex-model"}})
        verify(work, hold=True)
        dispatch_path = work / ".devlyn/verify-judge.r0.dispatch.json"
        record = loads(dispatch_path)
        record["roles"]["pair_judge"].update(decision="skip", reason="auto_pair_other_engine_unavailable")
        record["pair_trigger"] = {"eligible": False, "reasons": [], "skipped_reason": "auto_pair_other_engine_unavailable"}
        dispatch_path.write_bytes(ROLE["encoded"](record))
        merged = merge_cli(work)
        assert json.loads(merged.stdout)["verdict"] == "BLOCKED" and "verify-dispatch-invalid" in merged_ids(work), merged.stdout
        work = make_run("codex-primary", {"primary_judge": {"engine": "codex", "model": "fixture-codex-model", "effort": "high"}})
        _, summary, _ = verify(work)
        codex_argv = json.loads((work / "stubs/codex.argv").read_text())
        claude_argv = json.loads((work / "stubs/claude.argv").read_text())
        assert summary["verdict"] == "PASS" and "model_reasoning_effort=high" in codex_argv, summary
        assert claude_argv[claude_argv.index("--effort") + 1] == "medium"

        # Routes: unsupported engines and explicit unavailability BLOCK; an
        # automatic pair without its engine is a reported solo skip.
        try:
            make_run("unsupported-freeze", {"pair_judge": {"engine": "grok"}})
        except ValueError as exc:
            assert "judge-route-unsupported:grok" in str(exc), exc
        else:
            raise AssertionError("a grok pair seat survived role freeze")
        # A state frozen before that rule still cannot launch an unscripted seat.
        work = make_run("unsupported")
        state_path = work / ".devlyn/pipeline.state.json"
        state = loads(state_path)
        resolution = {key: value for key, value in state["role_resolution"].items() if key != "sha256"}
        resolution["roles"]["pair_judge"]["engine"] = "grok"
        state["role_resolution"] = {**resolution, "sha256": ROLE["digest"](ROLE["encoded"](resolution))}
        state_path.write_bytes(ROLE["encoded"](state))
        _, summary, _ = verify(work)
        assert summary["source_verdicts"]["pair_judge"] == "BLOCKED" and "verify-judge-route-blocked" in merged_ids(work)
        work = make_run("auto-unavailable")
        _, summary, state = verify(work, path=claude_only)
        assert summary["verdict"] == "PASS" and summary["source_verdicts"]["pair_judge"] is None, summary
        assert state["phases"]["verify"]["pair_trigger"]["skipped_reason"] == "auto_pair_other_engine_unavailable"
        work = make_run("explicit-unavailable", pair_verify=True)
        _, summary, _ = verify(work, path=claude_only)
        assert summary["source_verdicts"]["pair_judge"] == "BLOCKED", summary
        # --pair-verify whose OTHER engine was already missing at freeze names that engine.
        work = make_run("explicit-missing-at-freeze", pair_verify=True)
        state = loads(work / ".devlyn/pipeline.state.json")
        state["role_resolution"] = ROLE["resolve"](work, "claude", available=lambda engine: engine == "claude")
        (work / ".devlyn/pipeline.state.json").write_bytes(ROLE["encoded"](state))
        _, summary, _ = verify(work, path=claude_only)
        record = loads(work / ".devlyn/verify-judge.r0.dispatch.json")
        assert record["roles"]["pair_judge"]["reason"].startswith("BLOCKED:codex-unavailable"), record["roles"]["pair_judge"]
        assert summary["source_verdicts"]["pair_judge"] == "BLOCKED", summary
        work = make_run("no-pair", no_pair=True)
        _, summary, state = verify(work)
        assert summary["verdict"] == "PASS" and state["phases"]["verify"]["pair_trigger"]["skipped_reason"] == "user_no_pair"
        assert not (work / "stubs/codex.argv").exists()

        # Invalid shared inputs and a binding MECHANICAL result launch no judge.
        work = make_run("bad-contract")
        (work / "spec.md").write_text("# Spec\n\nchanged after bootstrap\n")
        _, summary, _ = verify(work)
        assert summary["verdict"] == "BLOCKED" and not list((work / ".devlyn").glob("*.prompt")), summary
        record = loads(work / ".devlyn/verify-judge.r0.dispatch.json")
        assert record["roles"]["primary_judge"]["reason"].startswith("BLOCKED:verify-input-invalid:contract")
        # A dispatch record may not skip a seat MECHANICAL did not skip.
        work = make_run("forged-skip", no_pair=True)
        verify(work, hold=True)
        dispatch_path = work / ".devlyn/verify-judge.r0.dispatch.json"
        record = loads(dispatch_path)
        record["roles"]["primary_judge"].update(decision="skip", reason="mechanical_blocker")
        dispatch_path.write_bytes(ROLE["encoded"](record))
        merged = merge_cli(work)
        assert json.loads(merged.stdout)["verdict"] == "BLOCKED" and "verify-dispatch-invalid" in merged_ids(work), merged.stdout
        work = make_run("mechanical-blocker")
        (work / ".devlyn/verify-mechanical.findings.jsonl").write_text(json.dumps(
            {"id": "VERIFY-MECH-1", "severity": "CRITICAL", "message": "failed"}) + "\n")
        _, summary, state = verify(work)
        assert summary["source_verdicts"] == {"mechanical": "NEEDS_WORK", "judge": None, "pair_judge": None}, summary
        assert state["phases"]["verify"]["pair_trigger"]["skipped_reason"] == "mechanical_blocker"
        assert not (work / "stubs/claude.argv").exists()

        # Runner-authored outcomes. A real deadline on a budget other than the dispatched
        # 600 s bound is recorded as timed_out but can never earn the solo verdict.
        work = make_run("short-budget")
        _, summary, _ = verify(work, short="codex", codex="sleep")
        assert carriers(work)["codex"]["outcome"] == "timed_out" and summary["source_verdicts"]["pair_judge"] == "BLOCKED", summary

        def timed_out(work, engine, keep_capture=False):
            # What a runner writes when the 600 s deadline fires (the deadline itself is
            # exercised in invocation-receipt.py's self-test): no evidence, empty capture.
            devlyn = work / ".devlyn"
            carrier = devlyn / f"{engine}-judge.r0.prompt.transport.json"
            record = loads(carrier)
            record.update(outcome="timed_out", exit_code=124)
            carrier.write_bytes(ROLE["encoded"](record))
            if not keep_capture:
                (devlyn / f"{engine}-judge.r0{'.output.json' if engine == 'claude' else '.stdout'}").write_bytes(b"")
            derived = [f"{engine}-judge.r0.stdout"] if engine == "claude" else []  # Codex's capture is its stdout.
            for name in (f"{engine}-judge.r0.role-evidence.json", f"{engine}-judge.stdout", *derived):
                (devlyn / name).unlink(missing_ok=True)
            return json.loads(merge_cli(work).stdout)

        work = make_run("pair-timeout")
        verify(work, hold=True)
        summary = timed_out(work, "codex")
        assert summary["source_verdicts"]["pair_judge"] == "TIMEOUT" and summary["verdict"] == "PASS", summary
        assert summary["report_header_note"] == "solo verdict after pair TIMEOUT" and summary["pair_timeout"]["budget_seconds"] == 600
        assert "pair_judge" in loads(work / ".devlyn/pipeline.state.json")["phases"]["verify"]["executions"]
        # A timed-out seat whose recorded command is not the frozen read-only route is not a timeout.
        work = make_run("unauthorized-timeout")
        verify(work, hold=True)
        devlyn = work / ".devlyn"
        swap = lambda argv: ["not-claude" if arg == "claude" else arg for arg in argv]
        (devlyn / "claude-judge.r0.argv.json").write_bytes(ROLE["encoded"](swap(loads(devlyn / "claude-judge.r0.argv.json"))))
        carrier = loads(devlyn / "claude-judge.r0.prompt.transport.json")
        carrier.update(command=swap(carrier["command"]), argv=swap(carrier["argv"]))
        (devlyn / "claude-judge.r0.prompt.transport.json").write_bytes(ROLE["encoded"](carrier))
        record = loads(devlyn / "verify-judge.r0.dispatch.json")
        record["roles"]["primary_judge"]["argv"] = swap(record["roles"]["primary_judge"]["argv"])
        (devlyn / "verify-judge.r0.dispatch.json").write_bytes(ROLE["encoded"](record))
        summary = timed_out(work, "claude")
        merged = (work / ".devlyn/verify-merged.findings.jsonl").read_text()
        assert "Claude print-mode command missing" in merged and "verify-primary-timeout" not in merged_ids(work), merged
        # The actual executable must be the authorized command's own, not a substituted prefix.
        work = make_run("substituted-executable")
        verify(work, hold=True)
        carrier_path = work / ".devlyn/claude-judge.r0.prompt.transport.json"
        carrier = loads(carrier_path)
        carrier["argv"] = ["not-claude", *carrier["argv"][1:]]
        carrier_path.write_bytes(ROLE["encoded"](carrier))
        summary = timed_out(work, "claude")
        assert "actual executable differs" in (work / ".devlyn/verify-merged.findings.jsonl").read_text(), summary
        # A removed evidence file leaves a BLOCKED seat whose remaining artifacts are sealed.
        work = make_run("evidence-removed")
        verify(work, hold=True)
        (work / ".devlyn/claude-judge.r0.role-evidence.json").unlink()
        (work / ".devlyn/claude-judge.r0.stdout").write_text("NEEDS_WORK\n")
        summary = json.loads(merge_cli(work).stdout)
        assert summary["source_verdicts"]["judge"] == "BLOCKED" and "verify-role-evidence-invalid" in merged_ids(work), summary
        assert "primary_judge" in loads(work / ".devlyn/pipeline.state.json")["phases"]["verify"]["executions"]
        work = make_run("primary-timeout")
        verify(work, hold=True)
        summary = timed_out(work, "claude")
        assert summary["source_verdicts"]["judge"] == "BLOCKED" and "verify-primary-timeout" in merged_ids(work), summary
        # A timed-out Claude seat's envelope passes the same check as authentication: an unsuccessful envelope with
        # valid-looking structured output still BLOCKs the seat instead of counting as a solo TIMEOUT.
        for field, value in (("subtype", "error_max_structured_output_retries"), ("is_error", True), ("session_id", "")):
            work = make_run("pair-timeout-bad-envelope-" + field, {"primary_judge": {"engine": "codex"},
                                                                   "pair_judge": {"engine": "claude"}})
            verify(work, hold=True, claude="high")
            output = work / ".devlyn/claude-judge.r0.output.json"
            output.write_text(json.dumps({**json.loads(output.read_text()), field: value}))
            summary = timed_out(work, "claude", keep_capture=True)
            assert summary["source_verdicts"]["pair_judge"] == "BLOCKED", summary
            assert "verify-judge-emission-contract-violated" in merged_ids(work), merged_ids(work)
        # A Claude seat killed after writing its result envelope keeps what it found, narrated or not.
        for name, mode in (("primary-timeout-after-result", "high"), ("primary-timeout-narrated", "narrated")):
            work = make_run(name)
            verify(work, hold=True, claude=mode)
            summary = timed_out(work, "claude", keep_capture=True)
            ids = set(merged_ids(work))
            assert summary["source_verdicts"]["judge"] == "BLOCKED" and {"claude-1", "verify-primary-timeout"} <= ids, summary
            assert "verify-judge-emission-contract-violated" not in ids, ids
        work = make_run("own-124")
        _, summary, _ = verify(work, codex="exit124")
        assert carriers(work)["codex"]["outcome"] == "exited" and summary["source_verdicts"]["pair_judge"] == "BLOCKED"
        assert "verify-judge-exit-nonzero" in merged_ids(work)

        # A failed second launch tears the first runner down; nothing is left running.
        work = make_run("second-launch")
        original_argv = launch_argv
        globals()["launch_argv"] = lambda devlyn, entry: (
            (["definitely-missing-verify-judge-binary"], {}) if entry["engine"] == "codex" else original_argv(devlyn, entry))
        try:
            _, summary, _ = verify(work, claude="sleep")
        finally:
            globals()["launch_argv"] = original_argv
        # The torn-down runner either never started its judge or recorded the cancellation.
        assert summary["verdict"] == "BLOCKED" and carriers(work).get("claude", {"outcome": "cancelled"})["outcome"] == "cancelled", summary
        pid_file = work / "stubs/claude.pid"
        assert not pid_file.exists() or not process_alive(int(pid_file.read_text()))
        assert set(loads(work / ".devlyn/pipeline.state.json")["phases"]["verify"]["executions"]) == {"primary_judge", "pair_judge"}

        # A failed launch whose own cleanup times out still tears the first runner down and merges.
        work = make_run("launch-cleanup-timeout")
        original_launch = launch
        calls = []

        def failing_second_launch(argv, cwd, env, stdout, stderr):
            calls.append(argv)
            if len(calls) == 2:
                raise subprocess.TimeoutExpired(argv, 5)
            return original_launch(argv, cwd, env, stdout, stderr)
        globals()["launch"] = failing_second_launch
        try:
            _, summary, _ = verify(work, claude="sleep")
        finally:
            globals()["launch"] = original_launch
        assert summary["verdict"] == "BLOCKED", summary
        pid_file = work / "stubs/claude.pid"
        assert not pid_file.exists() or not process_alive(int(pid_file.read_text()))

        # A signal that lands while the runners are being launched still tears down, merges and exits 130.
        work = make_run("signal-during-launch")
        original_launch = launch

        def interrupted_launch(argv, cwd, env, stdout, stderr):
            started = original_launch(argv, cwd, env, stdout, stderr)
            os.kill(os.getpid(), signal.SIGINT)
            return started
        globals()["launch"] = interrupted_launch
        try:
            code, summary, _ = verify(work, claude="sleep", codex="sleep")
        finally:
            globals()["launch"] = original_launch
        assert code == 130 and summary["verdict"] == "BLOCKED", (code, summary)
        assert not (work / "stubs/codex.pid").exists(), "the second runner started after the signal"

        # A handled signal cancels both judges, records it, reaps them and still merges.
        if os.name != "nt":
            work = make_run("cancel")
            stubs = work / "stubs"
            (stubs / "barrier").mkdir(parents=True)
            env = {**saved, "PATH": f"{everything}{os.pathsep}{isolated_path}", "CODEX_HOME": str(codex_home),
                   "STUB_DIR": str(stubs), "STUB_CLAUDE": "sleep", "STUB_CODEX": "sleep"}
            proc = subprocess.Popen([sys.executable, str(pathlib.Path(__file__).resolve()), "--devlyn-dir",
                                     str(work / ".devlyn")], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            deadline = time.monotonic() + 30
            while not all((stubs / f"{engine}.pid").exists() for engine in ("claude", "codex")):
                assert time.monotonic() < deadline and proc.poll() is None, proc.communicate()
                time.sleep(0.1)
            time.sleep(0.5)
            proc.send_signal(signal.SIGTERM)
            out, err = proc.communicate(timeout=60)
            assert proc.returncode == 143, (proc.returncode, out, err)
            assert json.loads(out)["verdict"] == "BLOCKED"
            assert {record["outcome"] for record in carriers(work).values()} == {"cancelled"}, carriers(work)
            assert not any(process_alive(int((stubs / f"{engine}.pid").read_text())) for engine in ("claude", "codex"))
    print("PASS verify-judges self-test: concurrent seats, isolation, routes, inputs, outcomes, teardown")
    return 0


def process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


if __name__ == "__main__":
    PLATFORM["configure_utf8"]()
    raise SystemExit(main())
