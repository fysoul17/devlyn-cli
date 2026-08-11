import { BatchReject } from "./errors.js";
import { makeIssue, makePick, makeWaveResult } from "./models.js";
import { ShortageReporter } from "./shortage_reporter.js";

function issueReason(store, row) {
  if (!Number.isInteger(row.quantity) || row.quantity <= 0) {
    return "invalid";
  }
  return store.problemFor(row);
}

export function executePickWave(
  store,
  waveId,
  rows,
  { failCommit = false, reporter = new ShortageReporter() } = {},
) {
  const issues = [];
  const picks = [];
  for (const [arrivalIndex, row] of rows.entries()) {
    const reason = issueReason(store, row);
    if (reason !== null) {
      issues.push(makeIssue(arrivalIndex, row, reason));
      continue;
    }
    store.take(row);
    picks.push(makePick(row));
  }

  store.commitWave(waveId, { fail: failCommit });
  if (issues.length > 0) {
    const ordered = reporter.recordRejectedWave(waveId, issues, store);
    throw new BatchReject(ordered);
  }
  return makeWaveResult(waveId, picks);
}
