#!/usr/bin/env python3
import json
import pathlib
import subprocess
import sys


workdir = pathlib.Path(sys.argv[1])
program = r'''
const path = require("node:path");
const { routeEscalations } = require(path.join(process.argv[1], "escalation.js"));

const roster = { api: ["ada", "bea"], billing: ["cy"] };
const ids = (items) => items.map(({ id }) => id);
const slots = (items) => items.map(({ slot }) => slot);

const firstOrder = routeEscalations([
  { id: "low", requester: "ada", service: "api", severity: "low" },
  { id: "urgent", requester: "bea", service: "api", severity: "critical" },
], roster);
const axis1a = JSON.stringify(ids(firstOrder)) === JSON.stringify(["urgent", "low"])
  && JSON.stringify(slots(firstOrder)) === JSON.stringify([1, 2]);

const tiedOrder = routeEscalations([
  { id: "first-high", requester: "ada", service: "api", severity: "high" },
  { id: "medium", requester: "cy", service: "billing", severity: "medium" },
  { id: "second-high", requester: "bea", service: "api", severity: "high" },
], roster);
const axis1b = JSON.stringify(ids(tiedOrder)) === JSON.stringify(["first-high", "second-high", "medium"])
  && JSON.stringify(slots(tiedOrder)) === JSON.stringify([1, 2, 3]);

const deniedOnly = routeEscalations([
  { id: "intruder", requester: "zo", service: "api", severity: "critical" },
], roster);
const axis2a = deniedOnly.length === 0;

const filtered = routeEscalations([
  { id: "allowed", requester: "cy", service: "billing", severity: "medium" },
  { id: "denied", requester: "ada", service: "billing", severity: "low" },
], roster);
const axis2b = JSON.stringify(ids(filtered)) === JSON.stringify(["allowed"]);

const composed = routeEscalations([
  { id: "allowed-low", requester: "ada", service: "api", severity: "low" },
  { id: "denied-critical", requester: "zo", service: "api", severity: "critical" },
  { id: "allowed-high", requester: "bea", service: "api", severity: "high" },
], roster, 2);
const interaction = JSON.stringify(ids(composed)) === JSON.stringify(["allowed-high", "allowed-low"])
  && JSON.stringify(slots(composed)) === JSON.stringify([1, 2]);

process.stdout.write(JSON.stringify({ axis1a, axis1b, axis2a, axis2b, interaction }));
'''
completed = subprocess.run(
    ["node", "-e", program, str(workdir)],
    cwd=workdir,
    text=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    check=False,
    timeout=20,
)
if completed.returncode != 0:
    raise RuntimeError(completed.stderr or completed.stdout)

checks = json.loads(completed.stdout)
invariant = "Ticket escalations are placed by descending severity with arrival order breaking ties, the on-call ACL rejects every requester not assigned to the ticket's service, and when privileged and unprivileged requests interleave the ACL decides authorization before severity placement so denied tickets never consume an ordered slot."

print(json.dumps({"manifestations": [
    {"id": "axis1-a", "invariant": invariant, "passed": checks["axis1a"]},
    {"id": "axis1-b", "invariant": invariant, "passed": checks["axis1b"]},
    {"id": "axis2-a", "invariant": invariant, "passed": checks["axis2a"]},
    {"id": "axis2-b", "invariant": invariant, "passed": checks["axis2b"]},
    {"id": "interaction", "invariant": invariant, "passed": checks["interaction"]},
]}))
