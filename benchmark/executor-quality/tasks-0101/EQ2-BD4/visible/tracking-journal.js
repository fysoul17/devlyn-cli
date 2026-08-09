import { applyLeg } from "./leg-applier.js";

function clone(value) {
  return structuredClone(value);
}

export class TrackingJournal {
  #entries;
  #completed;
  #seenEvents;

  constructor({ entries = [], completed = [] } = {}) {
    this.#entries = clone(entries);
    this.#completed = new Set(completed);
    this.#seenEvents = new Set(entries.map((entry) => entry.eventId));
  }

  applyBatch(manifest, batchId, legs) {
    if (this.#completed.has(batchId)) {
      return { ok: true, skipped: true, applied: [], skippedEvents: [], error: null };
    }

    const receipts = [];
    const applied = [];
    const skippedEvents = [];
    try {
      for (const leg of legs) {
        if (this.#seenEvents.has(leg.eventId)) {
          skippedEvents.push(leg.eventId);
          continue;
        }
        const receipt = applyLeg(manifest, leg);
        receipts.push(receipt);
        applied.push(leg.eventId);
        this.#seenEvents.add(leg.eventId);
        this.#entries.push({
          eventId: leg.eventId,
          parcelId: leg.parcelId,
          from: receipt.from,
          to: leg.to,
          fromState: receipt.fromState,
          state: leg.state,
        });
      }
      this.#completed.add(batchId);
      return { ok: true, skipped: false, applied, skippedEvents, error: null };
    } catch (error) {
      for (const receipt of receipts.reverse()) {
        this.#seenEvents.delete(receipt.eventId);
        const index = this.#entries.findIndex((entry) => entry.eventId === receipt.eventId);
        this.#entries.splice(index, 1);
        if (receipt.before === undefined) {
          manifest.legacyRewind(receipt.parcelId, receipt.from);
        } else {
          manifest.restore(receipt.parcelId, receipt.before);
        }
      }
      return { ok: false, skipped: false, applied, skippedEvents, error: error.message };
    }
  }

  view() {
    return {
      entries: clone(this.#entries),
      completed: [...this.#completed],
    };
  }
}
