#!/usr/bin/env python3
"""iter-0082 v2 collector contract — frozen 2026-07-27, written BEFORE the code.

Two tiers, both required by the frozen bar:

1. SYNTHETIC NEGATIVES, applied **path-invariantly**. A negative is not a payload;
   it is a payload x every ingress path (plain stream / envelope / envelope whose
   text is preceded by narration, which is the only way recovery fires). v1 died
   because it tested N6 as a plain stream only and recovery accepted it.

2. REAL-CAPTURE CORPUS. Replaces the unsatisfiable N9 with exact bytes of real
   judge captures and their hand-verified expected collections (manifest.json).
   Losslessness is claimed for shape class W1 only; the fence-wrapped-FINDING
   class has no surviving real capture and is reported uncovered, never synthesised.

Plus a non-regression sweep over the git-TRACKED judge captures (61 — not the 125
on disk; 64 of those are untracked and cannot be part of a bar that must stay
reproducible from a clean clone).
"""
import hashlib
import json
import pathlib
import runpy
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[3]
COLLECTOR = REPO / "config/skills/_shared/collect-codex-findings.py"

CRIT = '{"id":"c","severity":"CRITICAL","message":"real bug"}'
HIGH = '{"id":"real","severity":"HIGH"}'
INFO = '{"id":"i","severity":"INFO"}'
NW = '# SUMMARY {"verdict":"NEEDS_WORK"}'
PASS = '# SUMMARY {"verdict":"PASS"}'

# bare verdict / JSONL+verdict acceptance per SKILL.md pair-JUDGE contract, batch B 2026-08-18
INTENTIONAL_ACCEPTANCE_OVERRIDES = {
    "benchmark/ceiling/results/nodeg-20260720a/FS1-schedule-max-runs/A1/devlyn-snapshot/runs/rs-20260720T040421Z-4402cc885dcc/claude-judge.stdout": {"exit": 0, "findings_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", "verdict": "PASS"},
    "benchmark/ceiling/results/nodeg-20260720a/FS1-schedule-max-runs/A1/devlyn-snapshot/runs/rs-20260720T044950Z-db5f081dc14f/claude-judge.stdout": {"exit": 0, "findings_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", "verdict": "PASS"},
    "benchmark/ceiling/results/nodeg-20260720a/FS1-schedule-max-runs/A1/devlyn-snapshot/runs/rs-20260720T044950Z-db5f081dc14f/verify2.primary-judge.raw.stdout": {"exit": 0, "findings_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", "verdict": "PASS"},
    "benchmark/ceiling/results/nodeg-20260720d/DR-byte-preservation-f7-out-of-scope-trap/A1/devlyn-snapshot/codex-judge.stdout": {"exit": 0, "findings_sha256": "8c0e9aba10c18772907ca2ba1eccea35d3d580b6e8765f8254b6d9da44104cab", "verdict": "PASS_WITH_ISSUES"},
    "benchmark/ceiling/results/nodeg-20260720e/FS1-schedule-max-runs/A1/devlyn-snapshot/runs/rs-20260720T140815Z-068baf0da60c/codex-judge.stdout": {"exit": 0, "findings_sha256": "3f49be4f392d1ea9129255a9f82a901f07d8163bed9dac7dd7dedadc3fabb969", "verdict": "NEEDS_WORK"},
    "benchmark/ceiling/results/nodeg-20260721e/DR-atomic-state-f11-batch-import/A1/devlyn-snapshot/runs/rs-20260721T065728Z-3138278bd76a/claude-judge.stdout": {"exit": 0, "findings_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", "verdict": "PASS"},
    "benchmark/ceiling/results/nodeg-20260721e/DR-shape-compound-rules-f25-cart/A1/devlyn-snapshot/verify.judge.raw.stdout": {"exit": 0, "findings_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", "verdict": "PASS"},
}
TERMINAL_VERDICT_REQUIRED_OVERRIDES_2026_08_18 = {
    "benchmark/ceiling/results/iter0078a2-probe-a/DR-auth-signature-f12-webhook/A1/devlyn-snapshot/runs/rs-20260722T102122Z-68dfad3ca202/codex-primary-judge.round2.stdout": {
        "expected": {"exit": 1, "findings_sha256": None, "verdict": None},
        "rationale": "terminal-verdict required per user ruling 2026-08-18",
    },
    "benchmark/ceiling/results/nodeg-20260719g/DR-shape-compound-rules-f25-cart/A1/devlyn-snapshot/runs/rs-20260719T103916Z-60b9f2c446f0/codex-judge.stdout": {
        "expected": {"exit": 1, "findings_sha256": None, "verdict": None},
        "rationale": "terminal-verdict required per user ruling 2026-08-18",
    },
    "benchmark/ceiling/results/nodeg-20260720a/FS1-schedule-max-runs/A1/devlyn-snapshot/runs/rs-20260720T040421Z-4402cc885dcc/verify.primary-judge.raw.stdout": {
        "expected": {"exit": 1, "findings_sha256": None, "verdict": None},
        "rationale": "terminal-verdict required per user ruling 2026-08-18",
    },
    "benchmark/ceiling/results/nodeg-20260721e/DR-auth-signature-f12-webhook/A1/devlyn-snapshot/runs/rs-20260721T072845Z-400f808ec06b/codex-judge.stdout": {
        "expected": {"exit": 1, "findings_sha256": None, "verdict": None},
        "rationale": "terminal-verdict required per user ruling 2026-08-18",
    },
}
LEGACY_OBJECT_VERDICTS = frozenset({
    "env-weld-0081-run1.json", "env-weld-0081-run2.json", "env-weld-0081-run3.json",
    "env-weld-0081-run4.json", "env-weld-0081-run5.json", "env-weld-0081-run6.json",
    "env-weld-mc6chain.json", "env-weld-mc6smoke.json",
})
LEGACY_COMMENTED_OUTPUTS = frozenset({
    "benchmark/ceiling/results/nodeg-hook-20260722c/DR-atomic-state-f11-batch-import/A1/devlyn-snapshot/runs/rs-20260722T155851Z-5069eee5b1d7/claude-judge.stdout",
})


def merge_verdict(findings):
    """What the real merge makes of these collected findings."""
    merge = runpy.run_path(str(REPO / "config/skills/_shared/verify-merge-findings.py"))
    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        (root / "verify.pair.findings.jsonl").write_text(
            "".join(json.dumps(f) + "\n" for f in findings), encoding="utf-8"
        )
        merged, source_verdicts = merge["read_findings"](root)
        merge["write_outputs"](root, merged, source_verdicts)
        return source_verdicts["pair_judge"]


def collect(body, *, envelope=False, narrated=False, stop_reason="EndTurn"):
    """Run the collector over one stdout body. Returns (exit_code, findings, summary)."""
    payload = ("Narration that does not parse." + body) if narrated else body
    if envelope or narrated:
        payload = json.dumps(
            {"text": payload, "stopReason": stop_reason,
             "sessionId": "s", "requestId": "r"}
        )
    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        (root / "j.stdout").write_text(payload, encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(COLLECTOR), "--devlyn-dir", td,
             "--stdout-file", "j.stdout", "--summary-out", str(root / "s.json")],
            capture_output=True, text=True,
        )
        canonical = root / "verify.pair.findings.jsonl"
        findings = [json.loads(l) for l in canonical.open()] if canonical.exists() else []
        summary = json.loads((root / "s.json").read_text()) if (root / "s.json").exists() else None
        return proc.returncode, findings, summary


# --- Frozen negatives. Every one must reject on EVERY ingress path. -----------
# Ingress paths. `narrated` is the only one that reaches byte-forward recovery.
PATHS = [("plain", {}), ("envelope", {"envelope": True}), ("recovery", {"narrated": True})]
ALL_PATHS = [name for name, _ in PATHS]

# (id, payload, paths it applies to). Path-invariance is the default; the two
# exceptions are frozen that way in their own text and are NOT a weakening:
# N4 forbids a RECOVERED PASS — on a plain stream `INFO` + `PASS` is a legitimate
# advisory review that HEAD accepts and the tracked corpus contains, so applying
# N4 everywhere would regress real captures (that is the LOW/VJP-PASS regression
# v1's gate caught). N12 rejects comment prose on every path, including a
# commented-out example alongside a real finding.
NEGATIVES = [
    ("N1 dual-tab: two full contracts, tab-indented second",
     f"{INFO}\n{PASS}\n\t{CRIT}\n\t{NW}\n", ALL_PATHS),
    ("N2 one summary, trailing record after it",
     f"{INFO}\n{PASS}\n{CRIT}\n", ALL_PATHS),
    ("N3 CRITICAL with a PASS summary",
     f"{CRIT}\n{PASS}\n", ALL_PATHS),
    ("N4 recovered preamble + INFO + PASS (recovery may never yield PASS)",
     f"{INFO}\n{PASS}\n", ["recovery"]),
    ("N6 fence token welded to the contract start",
     f"```json{CRIT}\n{NW}\n", ALL_PATHS),
    ("N7 fenced decoy PASS contract, then a real NEEDS_WORK contract",
     f"```json\n{INFO}\n{PASS}\n```\n{CRIT}\n{NW}\n", ALL_PATHS),
    # v2 additions, all measured against the v1 patch (0082 § "v2 FROZEN").
    ("N10 severity-less summary carrying a verdict merge does not know",
     '```json\n# comment\n' + INFO + '\n{"verdict":"UNKNOWN"}\n```\n', ALL_PATHS),
    ("N11a fence token + trailing bytes, same line as the contract",
     f"```json trailing {CRIT}\n{NW}\n", ALL_PATHS),
    ("N11b fence token + trailing bytes, on its own line",
     f"```json trailing\n{CRIT}\n{NW}\n", ALL_PATHS),
    # Terminal verdicts are mandatory after findings on every ingress path;
    # N13's envelope path is the registered-envelope fixture.
    ("N13 findings then EOF", f"{HIGH}\n", ALL_PATHS),
    ("N14 findings then fence then EOF", f"{HIGH}\n```\n", ALL_PATHS),
]

# N12 is a rejection rule: a #-commented finding must fail collection.
COMMENTED = f'# example {{"id":"commented","severity":"CRITICAL"}}\n{HIGH}\n{NW}\n'

# --- Positive controls. Each must ACCEPT. -------------------------------------
POSITIVES = [
    ("legitimate single contract", f"{CRIT}\n{NW}\n", {}, 1, "NEEDS_WORK"),
    ("welded preamble recovered (the failure this iter exists for)",
     f"{CRIT}\n{NW}\n", {"narrated": True}, 1, "NEEDS_WORK"),
    ("many findings, one summary, order preserved",
     f"{CRIT}\n{HIGH}\n{NW}\n", {}, 2, "NEEDS_WORK"),
    # Guards the exact regression v1's gate caught: a real LOW/INFO advisory
    # alongside a PASS summary is legitimate and lives in the tracked corpus.
    ("advisory INFO finding with a PASS summary", f"{INFO}\n{PASS}\n", {}, 1, "PASS"),
]

FENCE_SHAPES = [
    ("paired", f"```json\n{CRIT}\n{NW}\n```\n"),
    ("opening-only", f"```json\n{CRIT}\n{NW}\n"),
    ("closing-only", f"{CRIT}\n{NW}\n```\n"),
]


def main():
    failures = []

    # Tier 1a — negatives, path-invariant unless frozen otherwise.
    for name, body, paths in NEGATIVES:
        for path_name, kwargs in PATHS:
            if path_name not in paths:
                continue
            code, _, _ = collect(body, **kwargs)
            if code == 0:
                failures.append(f"  {name} [{path_name}]: ACCEPTED, must reject")

    # A non-SUMMARY comment is not pair-JUDGE output.
    for path_name, kwargs in PATHS:
        code, _, _ = collect(COMMENTED, **kwargs)
        if code == 0:
            failures.append(f"  N12 [{path_name}]: comment prose was accepted")

    # Tier 1b — fence shapes must behave IDENTICALLY, and must accept.
    fence = {label: collect(body)[0] for label, body in FENCE_SHAPES}
    if len(set(fence.values())) != 1:
        failures.append(f"  N5 fence shapes not uniform: {fence}")
    elif set(fence.values()) != {0}:
        failures.append(f"  N5 fence shapes uniform but rejecting: {fence}")

    # Tier 1c — positive controls.
    for name, body, kwargs, n_findings, verdict in POSITIVES:
        code, findings, summary = collect(body, **kwargs)
        if code != 0:
            failures.append(f"  positive '{name}': REJECTED, must accept")
        elif len(findings) != n_findings or (summary or {}).get("verdict") != verdict:
            failures.append(
                f"  positive '{name}': got {len(findings)} findings / "
                f"{(summary or {}).get('verdict')}, want {n_findings} / {verdict}"
            )

    # Tier 2 — the real-capture corpus.
    manifest = json.loads((HERE / "manifest.json").read_text())
    for row in manifest["captures"]:
        src = HERE / "corpus" / row["file"]
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            (root / "j.stdout").write_bytes(src.read_bytes())
            proc = subprocess.run(
                [sys.executable, str(COLLECTOR), "--devlyn-dir", td,
                 "--stdout-file", "j.stdout", "--summary-out", str(root / "s.json")],
                capture_output=True, text=True,
            )
            canonical = root / "verify.pair.findings.jsonl"
            got = [json.loads(l) for l in canonical.open()] if canonical.exists() else []
            summary = json.loads((root / "s.json").read_text()) if (root / "s.json").exists() else None
        want = {"exit": 1} if row["file"] in LEGACY_OBJECT_VERDICTS else row["expect"]
        if proc.returncode != want["exit"]:
            failures.append(f"  corpus {row['file']}: exit {proc.returncode}, want {want['exit']}")
            continue
        if want["exit"] != 0:
            continue
        want_sev = [f["severity"] for f in want["findings"]]
        got_sev = [str(f.get("severity") or "").upper() for f in got]
        if got_sev != want_sev:
            failures.append(f"  corpus {row['file']}: severities {got_sev}, want {want_sev}")
        if (summary or {}).get("verdict") != want["verdict"]:
            failures.append(
                f"  corpus {row['file']}: verdict {(summary or {}).get('verdict')}, want {want['verdict']}"
            )
        # v1's N8 carried a merge half: collecting is not enough, the run must
        # actually come back NEEDS_WORK. Written down rather than implied.
        merged = merge_verdict(got)
        if merged != want["verdict"]:
            failures.append(
                f"  corpus {row['file']}: merge returned {merged}, want {want['verdict']}"
            )

    # Tier 3 — C5: the git-tracked judge captures must collect exactly as they did
    # at HEAD before the change. The baseline was taken from the pre-change
    # collector, which is the only honest moment to take it.
    baseline = json.loads((HERE / "tracked-baseline.json").read_text())
    for rel, want in baseline["captures"].items():
        src = REPO / rel
        if not src.exists():
            failures.append(f"  tracked baseline: {rel} no longer exists")
            continue
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            (root / "j.stdout").write_bytes(src.read_bytes())
            proc = subprocess.run(
                [sys.executable, str(COLLECTOR), "--devlyn-dir", td,
                 "--stdout-file", "j.stdout", "--summary-out", str(root / "s.json")],
                capture_output=True, text=True,
            )
            canonical = root / "verify.pair.findings.jsonl"
            digest = hashlib.sha256(canonical.read_bytes()).hexdigest() if canonical.exists() else None
            summary = json.loads((root / "s.json").read_text()) if (root / "s.json").exists() else None
        got = {"exit": proc.returncode, "findings_sha256": digest,
               "verdict": (summary or {}).get("verdict")}
        if rel in LEGACY_COMMENTED_OUTPUTS:
            want = {"exit": 1, "findings_sha256": None, "verdict": None}
        else:
            terminal_verdict_override = TERMINAL_VERDICT_REQUIRED_OVERRIDES_2026_08_18.get(rel)
            want = (
                terminal_verdict_override["expected"]
                if terminal_verdict_override is not None
                else INTENTIONAL_ACCEPTANCE_OVERRIDES.get(rel, want)
            )
        if got != want:
            failures.append(f"  tracked regression {rel}: {got} != baseline {want}")

    if failures:
        print("collector contract FAIL:\n" + "\n".join(failures))
        return 1

    checks = (sum(len(paths) for _, _, paths in NEGATIVES) + len(PATHS) + len(FENCE_SHAPES)
              + len(POSITIVES) + len(manifest["captures"]) + len(baseline["captures"]))
    print(f"collector contract ✓ ({checks} checks: "
          f"{len(NEGATIVES)} negatives across ingress paths, N12 rejection x{len(PATHS)}, "
          f"{len(FENCE_SHAPES)} fence shapes, {len(POSITIVES)} positive controls, "
          f"{len(manifest['captures'])} real captures (W1 rows also replayed through the real merge), "
          f"{len(baseline['captures'])} tracked non-regression)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
