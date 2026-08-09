"use strict";

class WaveCursor {
  constructor(waveSize) {
    if (!Number.isInteger(waveSize) || waveSize < 1) {
      throw new RangeError("waveSize must be a positive integer");
    }
    this.waveSize = waveSize;
    this.offset = 0;
  }

  allocate() {
    const placement = {
      wave: Math.floor(this.offset / this.waveSize) + 1,
      slot: (this.offset % this.waveSize) + 1,
    };
    this.offset += 1;
    return placement;
  }
}

module.exports = { WaveCursor };
