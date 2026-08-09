function clone(value) {
  return structuredClone(value);
}

export class ShipmentState {
  #parcels;

  constructor(parcels) {
    this.#parcels = clone(parcels);
  }

  read(parcelId) {
    const parcel = this.#parcels[parcelId];
    if (parcel === undefined) {
      throw new Error(`unknown parcel: ${parcelId}`);
    }
    return clone(parcel);
  }

  advance(parcelId, to, state) {
    const parcel = this.#parcels[parcelId];
    if (parcel === undefined) {
      throw new Error(`unknown parcel: ${parcelId}`);
    }
    parcel.location = to;
    parcel.state = state;
    parcel.hops += 1;
  }

  restore(parcelId, snapshot) {
    this.#parcels[parcelId] = clone(snapshot);
  }

  legacyRewind(parcelId, location) {
    const parcel = this.#parcels[parcelId];
    parcel.location = location;
    parcel.state = "ready";
    parcel.hops -= 1;
  }

  view() {
    return clone(this.#parcels);
  }
}
