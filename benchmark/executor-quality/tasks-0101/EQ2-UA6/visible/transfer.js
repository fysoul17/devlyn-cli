export function createTransfer({
  id,
  mandateId,
  fromAccount,
  toAccount,
  currency,
  amountCents,
}) {
  if (!id || !mandateId || !fromAccount || !toAccount || !currency) {
    throw new TypeError("transfer identifiers and currency are required");
  }
  if (!Number.isSafeInteger(amountCents) || amountCents <= 0) {
    throw new TypeError("amountCents must be a positive safe integer");
  }
  return Object.freeze({ id, mandateId, fromAccount, toAccount, currency, amountCents });
}
