export function executeTransferBatch(writer, mandateCheck, transfers) {
  const decisions = mandateCheck.review(transfers);
  const transferIds = [];

  for (const decision of decisions) {
    if (!decision.authorized) {
      return {
        status: "denied",
        transferIds: [],
        denial: {
          transferId: decision.transfer.id,
          reason: decision.reason,
        },
      };
    }
    writer.write(decision.transfer);
    transferIds.push(decision.transfer.id);
  }

  return { status: "committed", transferIds, denial: null };
}
