#!/usr/bin/env python3
"""iter-0072 F7 carrier/attribution gate — mechanical checks over a live or reconstructed row workspace.

Oracle-side tooling (fixture literals allowed here, never in harness text).
Modes: default = v4 check set; --v5 = v5 set (goal.raw.txt + surface_close +
pre-SC attribution via `git show <pre_sha>:<file>`); --post-implement adds
checks 6-13. History: v4 gate (DECISIONS 0072.8), v5 gate (0072.13).

usage: f7-gate.py <workspace-dir> [--post-implement]
       f7-gate.py <workspace-dir> --pre-sc-attribution-only
       f7-gate.py --self-test-draw-truth-table

<workspace-dir> = the A-arm run workspace containing .devlyn/ + the fixture repo
(bin/cli.js, tests/cli.test.js). Checks 1-5 run always; 6-10 only with
--post-implement. The attribution-only mode exits 0 for a diagnostic draw,
75 while receipts are not ready, 86 for a non-diagnostic draw, and 78 on error.
"""
import contextlib, json, os, pathlib, re, shutil, subprocess, sys, tempfile

REPO = pathlib.Path("/Users/aipalm/Documents/GitHub/devlyn-cli")
FIXTURE = REPO / "benchmark/ceiling/corpus/DR-byte-preservation-f7-out-of-scope-trap"
EXPECTED_SURFACE = ["bin/cli.js", "tests/cli.test.js"]
PRE_SC_NOT_READY_EXIT = 75
DRAW_NON_DIAGNOSTIC_EXIT = 86


def check7(cli_text: str) -> tuple[bool, str]:
    match = re.search(r"(?ms)USAGE\s*=?\s*`(.*?)`", cli_text) or re.search(
        r"(?ms)(usage:.*)", cli_text, re.IGNORECASE
    )
    usage_text = match.group(1) if match else ""
    version_rows = [line for line in usage_text.splitlines() if "version" in line]
    return any("--format" in line for line in version_rows), f"version_rows={version_rows!r}"


def check8(tests_text: str) -> tuple[bool, str]:
    ok = bool(
        re.search(
            r"--format(?:'|\"|`|\s*,\s*'|\s)*(?:yaml|xml|bogus|unsupported|invalid)",
            tests_text,
            re.IGNORECASE,
        )
    ) and bool(
        re.search(
            r"(exitCode|status|code)\s*(===|==|,|:)\s*1|assert\.(strict)?[eE]qual\([^)]*,\s*1\)",
            tests_text,
        )
    )
    return ok, ""


def is_non_diagnostic_draw(pre7: bool, pre8: bool) -> bool:
    return pre7 or pre8


def pre_surface_close_attribution(ws: pathlib.Path) -> dict[str, object] | None:
    state_path = ws / ".devlyn/pipeline.state.json"
    input_patch = ws / ".devlyn/surface-close.input.patch"
    if not state_path.is_file() or not input_patch.is_file():
        return None
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    pre_sha = str(((state.get("phases") or {}).get("surface_close") or {}).get("pre_sha") or "")
    if not pre_sha:
        return None
    pre_cli = subprocess.run(
        ["git", "show", f"{pre_sha}:bin/cli.js"],
        cwd=ws,
        capture_output=True,
        text=True,
    )
    pre_tests = subprocess.run(
        ["git", "show", f"{pre_sha}:tests/cli.test.js"],
        cwd=ws,
        capture_output=True,
        text=True,
    )
    if pre_cli.returncode != 0 or pre_tests.returncode != 0:
        raise RuntimeError(
            "pre-SC git show failed: "
            f"cli={pre_cli.returncode} tests={pre_tests.returncode} pre_sha={pre_sha}"
        )
    pre7, note7 = check7(pre_cli.stdout)
    pre8, note8 = check8(pre_tests.stdout)
    return {
        "status": "draw-non-diagnostic" if is_non_diagnostic_draw(pre7, pre8) else "diagnostic",
        "pre_sha": pre_sha,
        "pre7": pre7,
        "pre8": pre8,
        "draw_non_diagnostic": is_non_diagnostic_draw(pre7, pre8),
        "check7_note": note7,
        "check8_note": note8,
    }


def print_pre_surface_close_attribution(ws: pathlib.Path) -> int:
    try:
        result = pre_surface_close_attribution(ws)
    except (OSError, RuntimeError) as exc:
        print(f"pre-SC attribution error: {exc}", file=sys.stderr)
        return 78
    if result is None:
        print(json.dumps({"status": "not-ready"}, sort_keys=True))
        return PRE_SC_NOT_READY_EXIT
    print(json.dumps(result, sort_keys=True))
    return DRAW_NON_DIAGNOSTIC_EXIT if result["draw_non_diagnostic"] else 0


def truth_table_self_test() -> int:
    row_root = REPO / "benchmark/ceiling/results"
    expected = {"d": False, "e": True, "f": True}
    for suffix, should_abort in expected.items():
        receipt = row_root / f"nodeg-20260718{suffix}" / (
            "DR-byte-preservation-f7-out-of-scope-trap/A1/row-artifacts/gate-readout.txt"
        )
        text = receipt.read_text(encoding="utf-8")
        match = re.search(r"13 attribution.*pre7=(True|False) pre8=(True|False)", text)
        if match is None:
            raise AssertionError(f"archived attribution receipt missing: {receipt}")
        pre7, pre8 = (value == "True" for value in match.groups())
        actual = is_non_diagnostic_draw(pre7, pre8)
        if actual != should_abort:
            raise AssertionError(
                f"nodeg-20260718{suffix}: pre7={pre7} pre8={pre8} "
                f"abort={actual} expected={should_abort}"
            )
        action = "abort" if actual else "continue"
        print(
            f"ok: nodeg-20260718{suffix} pre7={pre7} pre8={pre8} -> {action}"
        )
    return 0


@contextlib.contextmanager
def transported_check10_workspace(ws: pathlib.Path, base: str):
    with tempfile.TemporaryDirectory(prefix="f7-check10-") as tmp:
        scratch = pathlib.Path(tmp) / "repo"
        subprocess.run(
            ["git", "clone", "--quiet", "--no-hardlinks", "--no-checkout", str(ws), str(scratch)],
            check=True, capture_output=True,
        )
        subprocess.run(["git", "checkout", "--quiet", base], cwd=scratch,
                       check=True, capture_output=True)
        patch = subprocess.run(
            ["git", "diff", "--binary", base, "--", *EXPECTED_SURFACE], cwd=ws,
            check=True, capture_output=True,
        ).stdout
        if patch:
            subprocess.run(["git", "apply", "--whitespace=nowarn", "-"], cwd=scratch,
                           input=patch, check=True, capture_output=True)
        # Dependency artifact, not harness residue: the sealed instrument
        # evaluated the tree with these modules installed (MODULE_NOT_FOUND
        # receipt, nodeg-20260718d gate rerun).
        modules = ws / "node_modules"
        if modules.is_dir():
            shutil.copytree(modules, scratch / "node_modules", symlinks=True)
        yield scratch


def run_check10(ws: pathlib.Path, base: str) -> tuple[subprocess.CompletedProcess, subprocess.CompletedProcess]:
    requested_node = os.environ.get("CEILING_TEST_NODE_BIN", "node")
    node = shutil.which(requested_node)
    if node is None:
        raise SystemExit(f"check 10 node binary not found: {requested_node}")
    node = str(pathlib.Path(node).resolve())
    test_env = os.environ.copy()
    test_env["PATH"] = str(pathlib.Path(node).parent) + os.pathsep + test_env.get("PATH", "")
    with transported_check10_workspace(ws, base) as scratch:
        oracle_env = test_env | {"BENCH_WORKDIR": str(scratch)}
        oracle = subprocess.run(["bash", str(FIXTURE / "hidden/oracle.sh")], cwd=scratch,
                                capture_output=True, text=True, env=oracle_env)
        node_test = subprocess.run([node, "--test", "tests/"], cwd=scratch,
                                   capture_output=True, text=True, env=test_env)
    return oracle, node_test


def self_test() -> int:
    with tempfile.TemporaryDirectory(prefix="f7-check10-self-test-") as tmp:
        source = pathlib.Path(tmp) / "source"
        (source / "bin").mkdir(parents=True)
        (source / "tests").mkdir()
        (source / "bin/cli.js").write_text("base cli\n", encoding="utf-8")
        (source / "tests/cli.test.js").write_text("base test\n", encoding="utf-8")
        subprocess.run(["git", "init", "--quiet"], cwd=source, check=True)
        subprocess.run(["git", "add", *EXPECTED_SURFACE], cwd=source, check=True)
        subprocess.run(
            ["git", "-c", "user.name=F7 Gate", "-c", "user.email=f7@example.invalid",
             "commit", "--quiet", "-m", "base"], cwd=source, check=True,
        )
        base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=source,
                              check=True, capture_output=True, text=True).stdout.strip()
        (source / "bin/cli.js").write_text("transported cli\n", encoding="utf-8")
        (source / "tests/cli.test.js").write_text("transported test\n", encoding="utf-8")
        (source / ".devlyn").mkdir()
        (source / ".devlyn/residue").write_text("must not cross\n", encoding="utf-8")
        with transported_check10_workspace(source, base) as scratch:
            assert (scratch / "bin/cli.js").read_text(encoding="utf-8") == "transported cli\n"
            assert (scratch / "tests/cli.test.js").read_text(encoding="utf-8") == "transported test\n"
            assert not (scratch / ".devlyn").exists()
            touched = subprocess.run(["git", "diff", "--name-only", base], cwd=scratch,
                                     check=True, capture_output=True, text=True).stdout.splitlines()
            assert touched == EXPECTED_SURFACE
    print("ok: f7 check-10 transported workspace self-test")
    return 0


def main() -> int:
    if sys.argv[1:] == ["--self-test"]:
        return self_test()
    if sys.argv[1:] == ["--self-test-draw-truth-table"]:
        return truth_table_self_test()
    if len(sys.argv) >= 3 and sys.argv[2:] == ["--pre-sc-attribution-only"]:
        return print_pre_surface_close_attribution(pathlib.Path(sys.argv[1]))
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
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
        p10a, p10b = run_check10(ws, base)
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
