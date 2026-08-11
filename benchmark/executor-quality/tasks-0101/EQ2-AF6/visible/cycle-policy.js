export class CyclePolicy {
  constructor(maxPoints) {
    if (!Number.isSafeInteger(maxPoints) || maxPoints <= 0) {
      throw new TypeError("maxPoints must be a positive integer");
    }
    this.maxPoints = maxPoints;
  }

  remaining(pointsAlreadyAwarded) {
    return Math.max(0, this.maxPoints - pointsAlreadyAwarded);
  }
}
