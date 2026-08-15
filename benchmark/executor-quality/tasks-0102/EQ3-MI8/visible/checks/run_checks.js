"use strict";

const assert = require("node:assert/strict");
const { closeAssignment, openAssignment } = require("../desk/assignment_desk");
const { armAbortAtWindowClose } = require("../tide/tide_window_planner");
const { localCloseReceipt } = require("./local_receipts_test");
const { harborForDesk } = require("../support/fixtures");

const harbor = harborForDesk("D-18", "pilot-18", "berth-18");
assert.equal(openAssignment(harbor, harbor.request).opened, true);
assert.equal(armAbortAtWindowClose(harbor, harbor.request.assignmentId, { opensAt: 31, closesAt: 41 }).armed, true);
assert.equal(closeAssignment(harbor, harbor.request.assignmentId, 40).closed, false);
const first = closeAssignment(harbor, harbor.request.assignmentId, 41);
assert.equal(localCloseReceipt(first, harbor, harbor.request.pilotId), true);
const second = closeAssignment(harbor, harbor.request.assignmentId, 41);
assert.equal(second.closed, false);
assert.equal(second.alreadyClosed, true);
console.log("assignment desk checks passed");
