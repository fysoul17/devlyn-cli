import assert from "node:assert/strict";
import test from "node:test";

import { BallotBox } from "../ballot-box.js";
import { EligibilityRoll } from "../eligibility-roll.js";
import { receiveBallot } from "../intake.js";
import { Poll } from "../poll.js";
import { RejectionLog } from "../rejection-log.js";

function makeBallot(receiptId, voterId, choices) {
  return { receiptId, voterId, choices };
}

test("an exact retransmission deposits one accepted ballot", () => {
  const poll = new Poll({
    candidateIds: ["red"],
    eligibilityRoll: new EligibilityRoll(["v1"]),
  });
  const ballotBox = new BallotBox();
  const rejectionLog = new RejectionLog();
  const ballot = makeBallot("r1", "v1", ["red"]);

  const first = receiveBallot(poll, ballotBox, rejectionLog, ballot);
  const second = receiveBallot(poll, ballotBox, rejectionLog, ballot);

  assert.equal(second, first);
  assert.equal(ballotBox.ballots.length, 1);
  assert.equal(rejectionLog.entries.length, 0);
});

test("poll validation reports every ballot problem", () => {
  const poll = new Poll({
    candidateIds: ["red", "blue"],
    eligibilityRoll: new EligibilityRoll(["v1"]),
    maxChoices: 1,
    open: false,
  });
  const ballot = makeBallot("r2", "outside", ["red", "ghost"]);

  assert.deepEqual(
    poll.rejectionsFor(ballot).map(({ reason }) => reason),
    ["unknown_choice", "overvote", "ineligible", "poll_closed"],
  );
});
