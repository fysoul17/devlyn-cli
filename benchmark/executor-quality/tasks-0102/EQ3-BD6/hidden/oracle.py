#!/usr/bin/env python3
"""Evaluate permit revocation manifestations without writing to the supplied fixture."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


RUNNER = r'''
const { makeFestival } = require("./support/fixtures");
const { revokePermit } = require("./issuer/permit_issuer");
const { activePermitIds } = require("./issuer/permit_registry");
const { creditMatches } = require("./finance/refund_register");

const festival = makeFestival();
const original = festival.permits.find((permit) => permit.pitchId !== null && permit.status === "active");
const revocationDay = original.setupDay + 3;
const orderedBeforeRevocation = festival.waitlist
  .filter((request) => request.kind === original.kind && request.status === "waiting")
  .map((request) => ({ permitId: request.permitId, sequence: request.sequence }))
  .sort((left, right) => left.sequence - right.sequence);
const expectedWinner = orderedBeforeRevocation[0];
const expectedLater = orderedBeforeRevocation[1];
const preservedCredit = { ...festival.creditEntries.find((entry) => entry.permitId !== original.id) };
const first = revokePermit(festival, original.id, revocationDay);
const afterFirstPlacementIds = festival.placements.map((placement) => placement.permitId);
const afterFirstCredits = festival.creditEntries.filter((entry) => entry.permitId === original.id);
const second = revokePermit(festival, original.id, revocationDay);
const targeted = festival.creditEntries.filter((entry) => entry.permitId === original.id);
const winner = festival.waitlist.find((request) => request.permitId === expectedWinner.permitId);
const later = festival.waitlist.find((request) => request.permitId === expectedLater.permitId);
const permit = festival.permits.find((item) => item.id === original.id);
const pitch = festival.pitches.find((item) => item.id === original.pitchId);
const oldCredit = festival.creditEntries.find((entry) => entry.permitId !== original.id);

console.log(JSON.stringify({
  localA: first.revoked === true && !activePermitIds(festival).includes(original.id),
  localB: first.revoked === true && second.revoked === false
    && second.permitId === original.id && second.revokedAt === revocationDay,
  remoteA: winner !== undefined && later !== undefined
    && pitch.occupiedBy === expectedWinner.permitId && winner.status === "placed" && later.status === "waiting"
    && winner.sequence === expectedWinner.sequence && later.sequence === expectedLater.sequence
    && expectedWinner.sequence < expectedLater.sequence && festival.placements.length === 1
    && festival.placements[0].permitId === expectedWinner.permitId && festival.placements[0].sourcePermitId === original.id,
  remoteB: revocationDay > original.setupDay && afterFirstCredits.length === 1
    && creditMatches(original, revocationDay, afterFirstCredits[0]),
  restore: second.revoked === false && permit !== undefined && permit.status === "revoked" && targeted.length === 1
    && creditMatches(original, revocationDay, targeted[0]) && festival.placements.length === 1
    && afterFirstPlacementIds.length === 1 && afterFirstPlacementIds[0] === festival.placements[0].permitId
    && oldCredit.amountCents === preservedCredit.amountCents && oldCredit.remainingDays === preservedCredit.remainingDays
    && pitch.occupiedBy === expectedWinner.permitId && winner.status === "placed" && later.status === "waiting",
}));
'''


def evaluate(workdir: Path) -> dict[str, bool]:
    result = subprocess.run(
        ["node", "-e", RUNNER], cwd=workdir, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=False, timeout=10,
    )
    if result.returncode:
        raise SystemExit(result.stderr or "node runner failed")
    values = json.loads(result.stdout)
    return {
        "local-a": bool(values["localA"]),
        "local-b": bool(values["localB"]),
        "remote-a": bool(values["remoteA"]),
        "remote-b": bool(values["remoteB"]),
        "restore": bool(values["restore"]),
    }


def main() -> None:
    values = evaluate(Path(sys.argv[1]))
    print(json.dumps({"manifestations": [
        {"id": role, "passed": values[role]}
        for role in ("local-a", "local-b", "remote-a", "remote-b", "restore")
    ]}, separators=(",", ":")))


if __name__ == "__main__":
    main()
