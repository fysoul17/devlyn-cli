export function createTransfer({
  id,
  mandateId,
  fromAccount,
  toAccount,
  amountCents,
}) {
  if (!id || !mandateId || !fromAccount || !toAccount) {
    throw new TypeError("transfer identifiers are required");
  }
  if (!Number.isSafeInteger(amountCents) || amountCents <= 0) {
    throw new TypeError("amountCents must be a positive safe integer");
  }
  return Object.freeze({ id, mandateId, fromAccount, toAccount, amountCents });
}
