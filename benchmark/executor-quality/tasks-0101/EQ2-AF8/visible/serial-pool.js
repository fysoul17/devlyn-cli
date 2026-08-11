export class SerialPool {
  nextSerial;
  holds = [];
  committed = [];

  constructor(firstSerial = 7000) {
    this.nextSerial = firstSerial;
  }

  reserve(certificateId) {
    const hold = Object.freeze({ serial: this.nextSerial, certificateId });
    this.nextSerial += 1;
    this.holds.push(hold);
    return hold;
  }

  commit(hold) {
    const index = this.holds.indexOf(hold);
    if (index === -1) {
      throw new Error("serial hold is not active");
    }
    this.holds.splice(index, 1);
    this.committed.push(hold.serial);
  }
}
