export class DeliveryDedup {
  #delivered = new Set();

  record(notificationId, recipient) {
    const key = JSON.stringify([notificationId, recipient]);
    if (this.#delivered.has(key)) {
      return false;
    }
    this.#delivered.add(key);
    return true;
  }
}
