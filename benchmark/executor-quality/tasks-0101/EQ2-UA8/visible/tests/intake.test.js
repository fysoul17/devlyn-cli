import assert from "node:assert/strict";
import test from "node:test";

import { EligibilityRoll } from "../eligibility-roll.js";
import { tabulateBatch } from "../intake.js";
import { Poll } from "../poll.js";
import { PrecinctTally } from "../precinct-tally.js";
import { RejectionLog } from "../rejection-log.js";

function makeBallot(ballotId, voterId, choices) {
  return { ballotId, precinctId: "north", voterId, choices };
}

function setup() {
  return {
    poll: new Poll({
      candidateIds: ["red", "blue"],
      eligibilityRoll: new EligibilityRoll({ north: ["v1", "v2"] }),
      openPrecinctIds: ["north"],
    }),
    tally: new PrecinctTally(),
    rejectionLog: new RejectionLog(),
  };
}

test("an accepted ballot contributes once to its precinct tally", () => {
  const state = setup();
  const ballot = makeBallot("b1", "v1", ["red"]);

  const outcomes = tabulateBatch(
    state.poll,
    state.tally,
    state.rejectionLog,
    [ballot, ballot],
  );

  assert.deepEqual(outcomes.map(({ status }) => status), ["accepted", "duplicate"]);
  assert.deepEqual(state.tally.totalsFor("north"), { red: 1 });
  assert.equal(state.rejectionLog.entriesFor("north").length, 0);
});

test("an exact rejected delivery creates one precinct log entry", () => {
  const poll = new Poll({
    candidateIds: ["red"],
    eligibilityRoll: new EligibilityRoll({ north: ["v1"] }),
    openPrecinctIds: ["north"],
  });
  const tally = new PrecinctTally();
  const rejectionLog = new RejectionLog();
  const ballot = makeBallot("b2", "outside", ["red"]);

  const outcomes = tabulateBatch(poll, tally, rejectionLog, [ballot, ballot]);

  assert.deepEqual(outcomes.map(({ status }) => status), ["rejected", "duplicate"]);
  assert.equal(rejectionLog.entriesFor("north").length, 1);
  assert.deepEqual(tally.totalsFor("north"), {});
});

test("poll validation reports every ballot problem", () => {
  const poll = new Poll({
    candidateIds: ["red", "blue"],
    eligibilityRoll: new EligibilityRoll({ north: ["v1"] }),
    openPrecinctIds: [],
    maxChoices: 1,
  });
  const ballot = makeBallot("b3", "outside", ["red", "ghost"]);

  assert.deepEqual(
    poll.rejectionsFor(ballot).map(({ reason }) => reason),
    ["unknown_choice", "overvote", "ineligible", "poll_closed"],
  );
});
