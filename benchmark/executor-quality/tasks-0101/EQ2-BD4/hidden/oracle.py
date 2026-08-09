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

function throwingLegRestoresNonReadyParcel() {
  const manifest = new ShipmentState({ box: parcel("customs", "inspection_hold", 7) });
  const journal = new TrackingJournal();
  const beforeManifest = manifest.view();
  const beforeJournal = journal.view();
  const outcome = runShipmentBatch(manifest, journal, {
    id: "failed-held",
    legs: [leg("scan-r1", "box", "release-dock", "released", true)],
  });
  return !outcome.ok
    && same(manifest.view(), beforeManifest)
    && same(journal.view(), beforeJournal);
}

function rollbackRestoresSeveralWorkflowStates() {
  const manifest = new ShipmentState({
    first: parcel("north-yard", "delayed", 2),
    second: parcel("south-hub", "loaded", 4),
  });
  const prior = [{
    eventId: "older-scan",
    parcelId: "archived",
    from: "yard",
    to: "dock",
    fromState: "received",
    state: "received",
  }];
  const journal = new TrackingJournal({ entries: prior, completed: ["older-batch"] });
  const beforeManifest = manifest.view();
  const beforeJournal = journal.view();
  const outcome = runShipmentBatch(manifest, journal, {
    id: "failed-history",
    legs: [
      leg("scan-r2", "first", "central", "in_transit"),
      leg("scan-r3", "second", "transfer", "transferring"),
      leg("scan-r4", "first", "airport", "loaded", true),
    ],
  });
  return !outcome.ok
    && same(outcome.applied, ["scan-r2", "scan-r3"])
    && same(manifest.view(), beforeManifest)
    && same(journal.view(), beforeJournal);
}

function completedBatchShortCircuitsUnknownParcel() {
  const manifest = new ShipmentState({ box: parcel("dock") });
  const journal = new TrackingJournal({ completed: ["already-published"] });
  const beforeManifest = manifest.view();
  const beforeJournal = journal.view();
  const outcome = runShipmentBatch(manifest, journal, {
    id: "already-published",
    legs: [leg("scan-i1", "missing", "hub", "in_transit", true)],
  });
  return outcome.ok
    && outcome.skipped
    && same(manifest.view(), beforeManifest)
    && same(journal.view(), beforeJournal);
}

function oldEventCanInterleaveWithNewEvent() {
  const prior = [{
    eventId: "scan-old",
    parcelId: "first",
    from: "dock",
    to: "hub",
    fromState: "ready",
    state: "in_transit",
  }];
  const manifest = new ShipmentState({
    first: parcel("hub", "in_transit", 1),
    second: parcel("warehouse", "packed", 3),
  });
  const journal = new TrackingJournal({ entries: prior, completed: ["prior-batch"] });
  const outcome = runShipmentBatch(manifest, journal, {
    id: "mixed-events",
    legs: [
      leg("scan-old", "first", "airport", "loaded"),
      leg("scan-new", "second", "dock", "ready"),
      leg("scan-old", "first", "aircraft", "departed"),
    ],
  });
  return outcome.ok
    && same(outcome.applied, ["scan-new"])
    && same(outcome.skippedEvents, ["scan-old", "scan-old"])
    && same(manifest.view(), {
      first: parcel("hub", "in_transit", 1),
      second: parcel("dock", "ready", 4),
    })
    && same(journal.view().entries, [
      ...prior,
      {
        eventId: "scan-new",
        parcelId: "second",
        from: "warehouse",
        to: "dock",
        fromState: "packed",
        state: "ready",
      },
    ]);
}

function replannedRoutePublishesFreshReplayOrigins() {
  const manifest = new ShipmentState({ box: parcel("customs", "exception_hold", 3) });
  const prior = [{
    eventId: "scan-prior",
    parcelId: "archived",
    from: "port",
    to: "customs",
    fromState: "arrived",
    state: "inspection_hold",
  }];
  const journal = new TrackingJournal({ entries: prior, completed: ["prior-route"] });
  const beforeManifest = manifest.view();
  const beforeJournal = journal.view();
  const batch = {
    id: "replanned-batch",
    legs: [
      leg("scan-x1", "box", "gateway", "in_transit"),
      leg("scan-x2", "box", "aircraft", "loaded", true),
    ],
  };
  const first = runShipmentBatch(manifest, journal, batch);
  const rolledBack = same(manifest.view(), beforeManifest)
    && same(journal.view(), beforeJournal);
  batch.legs[0].to = "sorter";
  batch.legs[0].state = "sorting";
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
      ...prior,
      {
        eventId: "scan-x1",
        parcelId: "box",
        from: "customs",
        to: "sorter",
        fromState: "exception_hold",
        state: "sorting",
      },
      {
        eventId: "scan-x2",
        parcelId: "box",
        from: "sorter",
        to: "aircraft",
        fromState: "sorting",
        state: "loaded",
      },
    ]);
}

process.stdout.write(JSON.stringify([
  throwingLegRestoresNonReadyParcel(),
  rollbackRestoresSeveralWorkflowStates(),
  completedBatchShortCircuitsUnknownParcel(),
  oldEventCanInterleaveWithNewEvent(),
  replannedRoutePublishesFreshReplayOrigins(),
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
