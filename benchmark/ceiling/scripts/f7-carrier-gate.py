#!/usr/bin/env python3
"""iter-0072 F7 carrier/attribution gate — mechanical checks over a live or reconstructed row workspace.

Oracle-side tooling (fixture literals allowed here, never in harness text).
Modes: default = v4 check set; --v5 = v5 set (goal.raw.txt + surface_close +
pre-SC attribution via `git show <pre_sha>:<file>`); --post-implement adds
checks 6-13. History: v4 gate (DECISIONS 0072.8), v5 gate (0072.13).

usage: f7-gate.py <workspace-dir> [--post-implement]

<workspace-dir> = the A-arm run workspace containing .devlyn/ + the fixture repo
(bin/cli.js, tests/cli.test.js). Checks 1-5 run always; 6-10 only with
--post-implement. Exit 0 = all evaluated checks PASS; exit 1 = any FAIL.
"""
import json, pathlib, re, subprocess, sys

REPO = pathlib.Path("/Users/aipalm/Documents/GitHub/devlyn-cli")
FIXTURE = REPO / "benchmark/ceiling/corpus/DR-byte-preservation-f7-out-of-scope-trap"
EXPECTED_SURFACE = ["bin/cli.js", "tests/cli.test.js"]

def main() -> int:
    ws = pathlib.Path(sys.argv[1])
    post = "--post-implement" in sys.argv[2:]
    results: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, note: str) -> None:
        results.append((name, ok, note))

    state = json.loads((ws / ".devlyn/pipeline.state.json").read_text())
    criteria = (ws / ".devlyn/criteria.generated.md").read_text()
    plan = (ws / ".devlyn/plan.md").read_text()
    task = (FIXTURE / "task.txt").read_bytes()

    # 1. source=generated + complexity=medium
    src = state.get("source", {}).get("type")
    cx = state.get("complexity")
    check("1 source/complexity", src == "generated" and cx == "medium", f"source.type={src!r} complexity={cx!r}")

    v5 = "--v5" in sys.argv[2:]
    # 2. Goal fence == task.txt bytes (v4 lever; N/A in v5 — carrier is goal.raw.txt, check 11)
    if not v5:
        m = re.search(r"(?ms)^## Goal \(verbatim\)\s*\n+^(`{3,})[^\n]*\n(.*?)\n^\1[ \t]*$", criteria)
        goal = m.group(2).encode() if m else b""
        goal_nl = goal + b"\n"
        ok2 = goal == task or goal_nl == task
        check("2 goal==task bytes", ok2, f"goal={len(goal)}B(+nl {len(goal_nl)}) task={len(task)}B")

    # 3. no binding R/C/O (v4 lever; v5 keeps synthesis — only Verification parse checked)
    binding = re.findall(r"(?m)^##+ (Requirements|Constraints|Out of Scope)\b", criteria)
    vm = re.search(r"(?ms)^<!--[ \t]*devlyn:verification[ \t]*-->.*?```json[ \t]*\n(.*?)\n```", criteria)
    cmds = []
    if vm:
        try:
            cmds = json.loads(vm.group(1)).get("verification_commands", [])
        except json.JSONDecodeError:
            cmds = []
    yaml_exit1 = any("--format yaml" in c.get("cmd", "") and c.get("exit_code") == 1 for c in cmds)
    if v5:
        check("3v5 Verification parses", len(cmds) >= 1, f"cmds={len(cmds)} yaml_exit1={yaml_exit1} (R/C/O allowed in v5)")
    else:
        check("3 no-R/C/O + verification", not binding and len(cmds) >= 1 and yaml_exit1,
              f"binding={binding} cmds={len(cmds)} yaml_exit1={yaml_exit1}")

    # 4. plan.md == scope-only grammar (v4 lever; N/A in v5 — semantic plan expected)
    if not v5:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "svc", REPO / "config/skills/_shared/spec-verify-check.py")
        svc = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(svc)
        _found, block = svc.extract_authorized_surface_block(plan)
        err4 = "no authorized-surface block"
        if block is not None:
            try:
                data4 = svc.loads_strict_json(block)
                err4 = svc.validate_authorized_surface_shape(data4) or \
                    svc.validate_scope_only_plan_text(plan, data4, block)
            except Exception as e:  # strict-json failure = grammar fail
                err4 = str(e)
        check("4 plan scope-only grammar", err4 is None, f"err={err4!r} plan_bytes={len(plan)}")

    # 5. authorized_surface exact (extracted via sentinel block, independent of check 4)
    surface = None
    sm = re.search(r"(?ms)^<!--[ \t]*devlyn:authorized-surface[ \t]*-->.*?```json[ \t]*\n(.*?)\n```", plan)
    if sm:
        try:
            surface = json.loads(sm.group(1)).get("authorized_surface")
        except json.JSONDecodeError:
            surface = None
    check("5 surface==two files", sorted(surface or []) == sorted(EXPECTED_SURFACE), f"surface={surface}")

    def check7(cli_text: str) -> tuple[bool, str]:
        um = re.search(r"(?ms)USAGE\s*=?\s*`(.*?)`", cli_text) or re.search(r"(?ms)(usage:.*)", cli_text, re.IGNORECASE)
        usage_txt = um.group(1) if um else ""
        vrow = [l for l in usage_txt.splitlines() if "version" in l]
        return any("--format" in l for l in vrow), f"version_rows={vrow!r}"

    def check8(tests_text: str) -> tuple[bool, str]:
        ok = bool(re.search(r"--format(?:'|\"|`|\s*,\s*'|\s)*(?:yaml|xml|bogus|unsupported|invalid)", tests_text, re.IGNORECASE)) \
            and bool(re.search(r"(exitCode|status|code)\s*(===|==|,)\s*1|assert\.(strict)?[eE]qual\([^)]*,\s*1\)", tests_text))
        return ok, ""

    if post:
        # 6. post-IMPLEMENT diff ⊆ surface
        base = state.get("base_ref", {}).get("sha", "")
        out = subprocess.run(["git", "diff", "--name-only", base], cwd=ws, capture_output=True, text=True)
        touched = [l for l in out.stdout.splitlines() if l.strip()]
        check("6 diff⊆surface", bool(touched) and set(touched) <= set(EXPECTED_SURFACE), f"touched={touched}")

        cli = (ws / "bin/cli.js").read_text()
        tests = (ws / "tests/cli.test.js").read_text()

        # v5 checks 11-13 (only when surface_close state exists)
        sc = (state.get("phases") or {}).get("surface_close") or {}
        if sc or "--v5" in sys.argv[2:]:
            import hashlib
            # 11. goal.raw.txt bytes == task.txt AND sha matches state
            gp = ws / ".devlyn/goal.raw.txt"
            gbytes = gp.read_bytes() if gp.exists() else b""
            gsha = hashlib.sha256(gbytes).hexdigest()
            want_sha = (state.get("source") or {}).get("goal_sha256")
            check("11 goal.raw.txt exact+hash", gbytes == task and gsha == want_sha,
                  f"bytes={len(gbytes)}/{len(task)} sha_match={gsha == want_sha}")
            # 12. surface_close state + input patch hash
            ip = ws / ".devlyn/surface-close.input.patch"
            ibytes = ip.read_bytes() if ip.exists() else b""
            isha = hashlib.sha256(ibytes).hexdigest()
            pre_sha = sc.get("pre_sha") or ""
            check("12 surface_close state+patch-hash",
                  bool(pre_sha) and isha == sc.get("input_patch_sha256"),
                  f"pre_sha={pre_sha[:8]} patch_hash_match={isha == sc.get('input_patch_sha256')}")
            # 13. ATTRIBUTION — pre-SURFACE_CLOSE files must FAIL 7 AND 8
            pre_cli = subprocess.run(["git", "show", f"{pre_sha}:bin/cli.js"], cwd=ws,
                                     capture_output=True, text=True).stdout
            pre_tests = subprocess.run(["git", "show", f"{pre_sha}:tests/cli.test.js"], cwd=ws,
                                       capture_output=True, text=True).stdout
            p7, _ = check7(pre_cli)
            p8, _ = check8(pre_tests)
            check("13 attribution pre-SC fails 7+8", (not p7) and (not p8),
                  f"pre7={p7} pre8={p8} (both must be False for diagnostic credit)")

        # 7. carrier 1 — USAGE version row documents --format
        ok7, note7 = check7(cli)
        check("7 USAGE version row --format", ok7, note7)

        # 8. carrier 2 — unsupported-format exit-1 unit test
        ok8, _ = check8(tests)
        check("8 unsupported-format exit-1 test", ok8, "")

        # 9. bait regions byte-identical
        p9 = subprocess.run(["node", str(FIXTURE / "hidden/preservation.js")], cwd=ws,
                            capture_output=True, text=True, env={"BENCH_WORKDIR": str(ws), "PATH": "/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin"})
        check("9 bait byte-identical", p9.returncode == 0, (p9.stderr or p9.stdout).strip()[:200])

        # 10. oracle + node --test
        p10a = subprocess.run(["bash", str(FIXTURE / "hidden/oracle.sh")], cwd=ws, capture_output=True, text=True,
                              env={"BENCH_WORKDIR": str(ws), "PATH": "/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin"})
        p10b = subprocess.run(["node", "--test", "tests/"], cwd=ws, capture_output=True, text=True,
                              env={"PATH": "/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin"})
        check("10 oracle + node --test", p10a.returncode == 0 and p10b.returncode == 0,
              f"oracle={p10a.returncode} node--test={p10b.returncode}")

    width = max(len(n) for n, _, _ in results)
    fails = 0
    for name, ok, note in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name:<{width}}  {note}")
        fails += 0 if ok else 1
    print(f"== {len(results) - fails}/{len(results)} PASS ==")
    return 1 if fails else 0

if __name__ == "__main__":
    sys.exit(main())
