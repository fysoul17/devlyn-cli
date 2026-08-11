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
const { BallotBox } = await load("ballot-box.js");
const { EligibilityRoll } = await load("eligibility-roll.js");
const { receiveBallot } = await load("intake.js");
const { Poll } = await load("poll.js");
const { RejectionLog } = await load("rejection-log.js");
const { rankRejections } = await load("rejection-policy.js");

function makeBallot(receiptId, voterId, choices) {
  return { receiptId, voterId, choices };
}

function setup({ voters = ["v1", "v2"], open = true, maxChoices = 1 } = {}) {
  return {
    poll: new Poll({
      candidateIds: ["red", "blue"],
      eligibilityRoll: new EligibilityRoll(voters),
      maxChoices,
      open,
    }),
    ballotBox: new BallotBox(),
    rejectionLog: new RejectionLog(),
  };
}

function exactAcceptedRetransmission() {
  const state = setup();
  const ballot = makeBallot("a1", "v1", ["red"]);
  const first = receiveBallot(state.poll, state.ballotBox, state.rejectionLog, ballot);
  const second = receiveBallot(state.poll, state.ballotBox, state.rejectionLog, ballot);
  return first === second
    && first.status === "accepted"
    && state.ballotBox.ballots.length === 1
    && state.rejectionLog.entries.length === 0;
}

function changedAcceptedEnvelopeKeepsFirst() {
  const state = setup();
  const first = receiveBallot(
    state.poll,
    state.ballotBox,
    state.rejectionLog,
    makeBallot("a2", "v1", ["red"]),
  );
  const second = receiveBallot(
    state.poll,
    state.ballotBox,
    state.rejectionLog,
    makeBallot("a2", "v2", ["blue"]),
  );
  return first === second
    && second.voterId === "v1"
    && state.ballotBox.ballots.length === 1
    && state.rejectionLog.entries.length === 0;
}

function distinctReasonsUsePollPriority() {
  const ranked = rankRejections([
    { arrivalIndex: 0, reason: "unknown_choice" },
    { arrivalIndex: 1, reason: "overvote" },
    { arrivalIndex: 2, reason: "poll_closed" },
  ]);
  return ranked.map(({ reason }) => reason).join(",") === "poll_closed,overvote,unknown_choice";
}

function equalReasonsKeepArrivalOrder() {
  const ranked = rankRejections([
    { arrivalIndex: 5, reason: "unknown_choice" },
    { arrivalIndex: 2, reason: "overvote" },
    { arrivalIndex: 1, reason: "unknown_choice" },
  ]);
  return ranked.map(({ arrivalIndex }) => arrivalIndex).join(",") === "2,1,5";
}

function changedRejectedEnvelopeKeepsFirst() {
  const state = setup({ maxChoices: 2 });
  const first = receiveBallot(
    state.poll,
    state.ballotBox,
    state.rejectionLog,
    makeBallot("mix", "v1", ["red", "blue", "ghost"]),
  );
  const second = receiveBallot(
    state.poll,
    state.ballotBox,
    state.rejectionLog,
    makeBallot("mix", "outside", ["red"]),
  );
  return first === second
    && first.reason === "overvote"
    && state.rejectionLog.entries.length === 1
    && state.ballotBox.ballots.length === 0;
}

process.stdout.write(JSON.stringify([
  exactAcceptedRetransmission(),
  changedAcceptedEnvelopeKeepsFirst(),
  distinctReasonsUsePollPriority(),
  equalReasonsKeepArrivalOrder(),
  changedRejectedEnvelopeKeepsFirst(),
]));
'''
invariant = "Ballot receipts must admit at most one accepted ballot or rejection record across changed duplicate envelopes, rejection reasons rank poll-closed before ineligible before overvote before unknown-choice with arrival order breaking equal-reason ties, and when duplicate envelopes would fail for different reasons the first envelope's ranked rejection must remain the only outcome without another log append or ballot-box side effect."


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
