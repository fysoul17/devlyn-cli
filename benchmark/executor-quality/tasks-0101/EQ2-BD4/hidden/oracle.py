#!/usr/bin/env python3
import json
import pathlib
import subprocess
import sys


workdir = pathlib.Path(sys.argv[1])
runner = r'''import { pathToFileURL } from "node:url";
const root = pathToFileURL(`${process.argv[1]}/`);
const { runShipmentBatch } = await import(new URL("shipment-batch.js", root));
const { ShipmentState } = await import(new URL("shipment-state.js", root));
const { TrackingJournal } = await import(new URL("tracking-journal.js", root));

const same = (left, right) => JSON.stringify(left) === JSON.stringify(right);
const parcel = (location, state = "ready", hops = 0) => ({ location, state, hops });
const leg = (eventId, parcelId, to, state, failAfterMove = false) => ({
  eventId,
  parcelId,
  to,
  state,
  failAfterMove,
});

function rollbackSingleMovedLeg() {
  const manifest = new ShipmentState({ box: parcel("dock") });
  const journal = new TrackingJournal();
  const beforeManifest = manifest.view();
  const beforeJournal = journal.view();
  const outcome = runShipmentBatch(manifest, journal, {
    id: "failed-single",
    legs: [leg("scan-r1", "box", "hub", "in_transit", true)],
  });
  return !outcome.ok
    && same(manifest.view(), beforeManifest)
    && same(journal.view(), beforeJournal);
}

function rollbackPreservesPriorHistory() {
  const manifest = new ShipmentState({
    first: parcel("north", "ready", 2),
    second: parcel("south", "ready", 4),
  });
  const prior = [{
    eventId: "older-scan",
    parcelId: "archived",
    from: "yard",
    to: "dock",
    fromState: "ready",
    state: "received",
  }];
  const journal = new TrackingJournal({ entries: prior, completed: ["older-batch"] });
  const beforeManifest = manifest.view();
  const beforeJournal = journal.view();
  const outcome = runShipmentBatch(manifest, journal, {
    id: "failed-history",
    legs: [
      leg("scan-r2", "first", "central", "in_transit"),
      leg("scan-r3", "second", "central", "in_transit", true),
    ],
  });
  return !outcome.ok
    && same(manifest.view(), beforeManifest)
    && same(journal.view(), beforeJournal);
}

function completedBatchRunsOnce() {
  const manifest = new ShipmentState({ box: parcel("dock") });
  const journal = new TrackingJournal();
  const batch = {
    id: "stable-batch",
    legs: [leg("scan-i1", "box", "hub", "in_transit")],
  };
  const first = runShipmentBatch(manifest, journal, batch);
  const afterManifest = manifest.view();
  const afterJournal = journal.view();
  const second = runShipmentBatch(manifest, journal, batch);
  return first.ok
    && second.ok
    && second.skipped
    && same(manifest.view(), afterManifest)
    && same(journal.view(), afterJournal);
}

function repeatedEventIsNotRepublished() {
  const manifest = new ShipmentState({ box: parcel("dock") });
  const journal = new TrackingJournal();
  const first = runShipmentBatch(manifest, journal, {
    id: "first-event-batch",
    legs: [leg("scan-i2", "box", "hub", "in_transit")],
  });
  const afterManifest = manifest.view();
  const second = runShipmentBatch(manifest, journal, {
    id: "second-event-batch",
    legs: [leg("scan-i2", "box", "airport", "loaded")],
  });
  return first.ok
    && second.ok
    && same(second.skippedEvents, ["scan-i2"])
    && same(manifest.view(), afterManifest)
    && journal.view().entries.length === 1;
}

function rollbackThenReplayFromHeldState() {
  const manifest = new ShipmentState({ box: parcel("customs", "exception_hold", 3) });
  const journal = new TrackingJournal();
  const beforeManifest = manifest.view();
  const beforeJournal = journal.view();
  const batch = {
    id: "recoverable-batch",
    legs: [
      leg("scan-x1", "box", "gateway", "in_transit"),
      leg("scan-x2", "box", "aircraft", "loaded", true),
    ],
  };
  const first = runShipmentBatch(manifest, journal, batch);
  const rolledBack = same(manifest.view(), beforeManifest)
    && same(journal.view(), beforeJournal);
  batch.legs[1].failAfterMove = false;
  const replay = runShipmentBatch(manifest, journal, batch);
  const replayAgain = runShipmentBatch(manifest, journal, batch);
  return !first.ok
    && rolledBack
    && replay.ok
    && !replay.skipped
    && replayAgain.skipped
    && same(replay.applied, ["scan-x1", "scan-x2"])
    && same(manifest.view(), { box: parcel("aircraft", "loaded", 5) })
    && same(journal.view().entries, [
      {
        eventId: "scan-x1",
        parcelId: "box",
        from: "customs",
        to: "gateway",
        fromState: "exception_hold",
        state: "in_transit",
      },
      {
        eventId: "scan-x2",
        parcelId: "box",
        from: "gateway",
        to: "aircraft",
        fromState: "in_transit",
        state: "loaded",
      },
    ]);
}

process.stdout.write(JSON.stringify([
  rollbackSingleMovedLeg(),
  rollbackPreservesPriorHistory(),
  completedBatchRunsOnce(),
  repeatedEventIsNotRepublished(),
  rollbackThenReplayFromHeldState(),
]));
'''
invariant = "Failed shipment batches restore parcel positions, workflow states, hop counts, and published tracking entries to their exact pre-batch values, successful batch and event identifiers take effect at most once, and replaying a batch after its first partially applied attempt rolls back begins from that clean state so each leg and its tracking event are applied exactly once."

completed = subprocess.run(
    [
        "node",
        "--input-type=module",
        "--eval",
        runner,
        str(workdir),
    ],
    text=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    check=False,
    timeout=10,
)
if completed.returncode != 0:
    raise SystemExit(completed.stderr)

passed = json.loads(completed.stdout)
ids = ["axis1-a", "axis1-b", "axis2-a", "axis2-b", "interaction"]
print(json.dumps({"manifestations": [
    {"id": identifier, "invariant": invariant, "passed": result}
    for identifier, result in zip(ids, passed, strict=True)
]}))
