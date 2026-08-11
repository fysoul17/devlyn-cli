function deniedResult(batchId, decision) {
  return {
    status: "denied",
    batchId,
    transferIds: [],
    denial: {
      transferId: decision.transfer.id,
      reason: decision.reason,
    },
  };
}

export function executeTransferBatch(writer, mandateCheck, batchId, effectiveDate, transfers) {
  const decisions = transfers.map((transfer) => mandateCheck.reviewTransfer(transfer, effectiveDate));
  const denied = decisions.find((decision) => !decision.authorized);
  if (denied) {
    return deniedResult(batchId, denied);
  }

  for (const decision of decisions) {
    writer.postBatch(`${batchId}:${decision.transfer.id}`, [decision.transfer]);
  }
  return {
    status: "committed",
    batchId,
    transferIds: decisions.map((decision) => decision.transfer.id),
    denial: null,
  };
}
