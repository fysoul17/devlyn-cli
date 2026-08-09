const reasonOrder = ["format", "account", "amount"];

export function parseLine(line, source) {
  const fields = String(line).split("|");
  if (fields.length !== 4) {
    return { ok: false, error: { source, reason: "format" } };
  }

  const [id, account, amountText, priorityText] = fields;
  const amount = Number(amountText);
  const priority = Number(priorityText);
  const issues = [];

  if (!/^[A-Z]\d{3}$/.test(id) || !Number.isInteger(priority)) {
    issues.push("format");
  }
  if (!/^acct-[a-z]+$/.test(account)) {
    issues.push("account");
  }
  if (!Number.isFinite(amount) || amount <= 0) {
    issues.push("amount");
  }

  if (issues.length > 0) {
    return {
      ok: false,
      error: { source, reason: reasonOrder.find((reason) => issues.includes(reason)) },
      candidate: { id, account, amount, priority, source },
    };
  }

  return { ok: true, value: { id, account, amount, priority, source } };
}
