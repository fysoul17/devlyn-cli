#!/usr/bin/env python3
"""iter-0076 Stage A gate (iii) validator — format validity + false-N/A."""
import importlib.util
import json
import pathlib
import sys

S = pathlib.Path(__file__).parent
spec = importlib.util.spec_from_file_location(
    "spw", "/Users/aipalm/Documents/GitHub/devlyn-cli/config/skills/_shared/state-phase-write.py")
spw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(spw)
ROW_RE = spw.SURFACE_ROW_RE

EXPECT = {"fs1": {"UVR-STALE": "FIRED", "PATH-TEST": "N/A"},
          "f23": {"UVR-STALE": "N/A", "PATH-TEST": "FIRED"}}

rows_out = []
valid = 0
false_na = 0
over_fired = 0
total = 0
for task in ("fs1", "f23"):
    for i in range(1, 7):
        total += 1
        rec = {"draw": f"{task}-{i}", "format_valid": False, "dispositions": {},
               "false_na": [], "over_fired": [], "notes": []}
        rows_out.append(rec)
        p = S / f"draw-{task}-{i}.json"
        try:
            wrapper = json.loads(p.read_text(encoding="utf-8"))
            result = wrapper["result"]
        except Exception as e:
            rec["notes"].append(f"wrapper unreadable: {e}")
            continue
        lines = result.splitlines()
        found = {}
        malformed = []
        for idx, line in enumerate(lines):
            if "UVR-STALE:" not in line and "PATH-TEST:" not in line:
                continue
            m = ROW_RE.fullmatch(line)
            if m is None:
                malformed.append(line)
                continue
            ob = m.group("obligation")
            if ob in found:
                malformed.append(f"duplicate {ob}")
                continue
            status = "FIRED" if m.group("fired") else "N/A"
            evidence = m.group("fired_evidence") or m.group("na_evidence")
            path = m.group("fired_path") or m.group("na_path")
            if status == "N/A" and evidence is None:
                malformed.append(f"{ob} N/A no evidence")
                continue
            work = S / f"work-{task}-{i}"
            cited = work / path
            raw_line = m.group("fired_line") or m.group("na_line")
            if not cited.is_file():
                malformed.append(f"{ob} cites missing file {path}")
                continue
            if raw_line is not None and int(raw_line) > len(
                    cited.read_text(encoding="utf-8", errors="replace").splitlines()):
                malformed.append(f"{ob} cites absent line {path}:{raw_line}")
                continue
            found[ob] = (status, idx)
        pass_idx = [i2 for i2, l in enumerate(lines) if l.strip() == "PASS"]
        shape_ok = (not malformed and set(found) == {"UVR-STALE", "PATH-TEST"}
                    and len(pass_idx) == 1
                    and pass_idx[0] > max(v[1] for v in found.values()))
        rec["format_valid"] = shape_ok
        if malformed:
            rec["notes"].extend(malformed[:3])
        if not pass_idx:
            rec["notes"].append("no PASS line")
        for ob, (status, _) in found.items():
            rec["dispositions"][ob] = status
            exp = EXPECT[task][ob]
            if exp == "FIRED" and status == "N/A":
                rec["false_na"].append(ob)
            if exp == "N/A" and status == "FIRED":
                rec["over_fired"].append(ob)
        if shape_ok:
            valid += 1
        false_na += len(rec["false_na"])
        over_fired += len(rec["over_fired"])

report = {
    "total_draws": total,
    "format_valid": valid,
    "format_validity_ratio": round(valid / total, 3) if total else None,
    "false_na_events": false_na,
    "over_fired_events": over_fired,
    "gate_format": valid / total >= 0.9 if total else False,
    "gate_false_na": false_na == 0,
    "gate_pass": (valid / total >= 0.9 and false_na == 0) if total else False,
    "draws": rows_out,
}
out = S / "probe-report.json"
out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps({k: report[k] for k in report if k != "draws"}, indent=1))
for r in rows_out:
    print(r["draw"], "valid=" + str(r["format_valid"]), r["dispositions"],
          ("FALSE_NA:" + ",".join(r["false_na"])) if r["false_na"] else "",
          ("notes:" + "; ".join(r["notes"][:2])) if r["notes"] else "")
sys.exit(0 if report["gate_pass"] else 1)
