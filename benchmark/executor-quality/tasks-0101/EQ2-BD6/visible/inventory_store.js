import { CommitFault, WriteFault } from "./errors.js";
import { decodeState, encodeState } from "./state_codec.js";

export class InventoryStore {
  constructor(stock, { locked = [] } = {}) {
    this.state = {
      completedWaves: [],
      locked: [...locked],
      picks: [],
      revision: 0,
      stock: { ...stock },
    };
  }

  snapshotBytes() {
    return encodeState(this.state);
  }

  restoreBytes(bytes) {
    this.state = decodeState(bytes);
  }

  view() {
    return decodeState(this.snapshotBytes());
  }

  problemFor(row) {
    if (this.state.locked.includes(row.sku)) {
      return "conflict";
    }
    const available = this.state.stock[row.sku] ?? 0;
    if (available < row.quantity) {
      return "shortage";
    }
    return null;
  }

  take(row) {
    this.state.stock[row.sku] -= row.quantity;
    this.state.picks.push({ quantity: row.quantity, sku: row.sku });
    this.state.revision += 1;
    if (row.failAfterWrite === true) {
      throw new WriteFault();
    }
  }

  commitWave(waveId, { fail = false } = {}) {
    this.state.completedWaves.push(waveId);
    this.state.revision += 1;
    if (fail) {
      throw new CommitFault();
    }
  }
}
