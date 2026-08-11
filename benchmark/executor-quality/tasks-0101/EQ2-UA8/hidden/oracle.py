#!/usr/bin/env python3
import json
import pathlib
import subprocess
import sys


workdir = pathlib.Path(sys.argv[1])
runner = r'''import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

const root = process.argv[1];
const load = async (name) => import(pathToFileURL(resolve(root, name)).href);
const { EligibilityRoll } = await load("eligibility-roll.js");
const { tabulateBatch } = await load("intake.js");
const { Poll } = await load("poll.js");
const { PrecinctTally } = await load("precinct-tally.js");
const { RejectionLog } = await load("rejection-log.js");
const { rankRejections } = await load("rejection-policy.js");

function ballot(ballotId, voterId, choices, precinctId = "north") {
  return { ballotId, precinctId, voterId, choices };
}

function setup({ maxChoices = 1, openPrecinctIds = ["north"] } = {}) {
  return {
    poll: new Poll({
      candidateIds: ["red", "blue"],
      eligibilityRoll: new EligibilityRoll({ north: ["v1", "v2"] }),
      maxChoices,
      openPrecinctIds,
    }),
    tally: new PrecinctTally(),
    rejectionLog: new RejectionLog(),
  };
}

function acceptedReplayDoesNotRetally() {
  const state = setup();
  const delivery = ballot("a-one", "v1", ["red"]);
  const outcomes = tabulateBatch(
    state.poll,
    state.tally,
    state.rejectionLog,
    [delivery, delivery],
  );
  return outcomes.map(({ status }) => status).join(",") === "accepted,duplicate"
    && JSON.stringify(state.tally.totalsFor("north")) === '{"red":1}'
    && state.tally.processedCount === 1
    && state.rejectionLog.entriesFor("north").length === 0;
}

function rejectedReplayDoesNotRelog() {
  const state = setup();
  const delivery = ballot("a-two", "outside", ["red"]);
  const outcomes = tabulateBatch(
    state.poll,
    state.tally,
    state.rejectionLog,
    [delivery, delivery],
  );
  return outcomes.map(({ status }) => status).join(",") === "rejected,duplicate"
    && outcomes[0].reason === "ineligible"
    && outcomes[1].reason === "ineligible"
    && state.rejectionLog.entriesFor("north").length === 1
    && JSON.stringify(state.tally.totalsFor("north")) === "{}";
}

function distinctReasonsUsePollPriority() {
  const ranked = rankRejections([
    { arrivalIndex: 0, reason: "unknown_choice" },
    { arrivalIndex: 1, reason: "overvote" },
    { arrivalIndex: 2, reason: "poll_closed" },
    { arrivalIndex: 3, reason: "ineligible" },
  ]);
  return ranked.map(({ reason }) => reason).join(",")
    === "poll_closed,ineligible,overvote,unknown_choice";
}

function sameReasonUsesArrivalTieBreak() {
  const ranked = rankRejections([
    { arrivalIndex: 5, reason: "unknown_choice" },
    { arrivalIndex: 2, reason: "overvote" },
    { arrivalIndex: 1, reason: "unknown_choice" },
  ]);
  return ranked.map(({ arrivalIndex }) => arrivalIndex).join(",") === "2,1,5";
}

function batchKeepsTallyAndLedgerConsistent() {
  const state = setup({ maxChoices: 2 });
  const outcomes = tabulateBatch(
    state.poll,
    state.tally,
    state.rejectionLog,
    [
      ballot("mix-batch", "v1", ["red", "blue", "ghost"]),
      ballot("counted-between", "v2", ["red"]),
      ballot("mix-batch", "outside", ["blue"]),
    ],
  );
  const entries = state.rejectionLog.entriesFor("north");
  return outcomes.map(({ status }) => status).join(",")
      === "rejected,accepted,duplicate"
    && outcomes[0] !== outcomes[2]
    && outcomes[0].reason === "overvote"
    && outcomes[2].reason === "overvote"
    && entries.length === 1
    && entries[0].reason === "overvote"
    && state.tally.processedCount === 2
    && JSON.stringify(state.tally.totalsFor("north")) === '{"red":1}';
}

process.stdout.write(JSON.stringify([
  acceptedReplayDoesNotRetally(),
  rejectedReplayDoesNotRelog(),
  distinctReasonsUsePollPriority(),
  sameReasonUsesArrivalTieBreak(),
  batchKeepsTallyAndLedgerConsistent(),
]));
'''
invariant = "Within a poll, each ballot identifier must be finalized once in the precinct tally across accepted and rejected deliveries, rejection reasons rank poll-closed before ineligible before overvote before unknown-choice with earlier arrival breaking same-reason ties, and when changed duplicate deliveries would each fail differently the first delivery's ranked reason must remain the precinct ledger's sole error with neither a second log append nor a duplicate tally effect while other ballots in the batch accumulate exactly once."


completed = subprocess.run(
    ["node", "--input-type=module", "--eval", runner, str(workdir)],
    text=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    check=False,
    timeout=10,
)
if completed.returncode == 0:
    checks = json.loads(completed.stdout)
else:
    checks = [False, False, False, False, False]

identifiers = ["axis1-a", "axis1-b", "axis2-a", "axis2-b", "interaction"]
print(json.dumps({"manifestations": [
    {"id": identifier, "invariant": invariant, "passed": passed}
    for identifier, passed in zip(identifiers, checks, strict=True)
]}))
