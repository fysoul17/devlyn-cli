const ALLOWED_BUCKETS = new Set(["anonymous", "member", "partner"]);
const ALLOWED_WINDOWS = new Set([1_000, 60_000]);

const LIMIT_CHECKS = [
  {
    reason: "unknown_bucket",
    field: (rule, ruleIndex) => (
      ALLOWED_BUCKETS.has(rule.bucket) ? null : `rules[${ruleIndex}].bucket`
    ),
  },
  {
    reason: "invalid_window",
    field: (rule, ruleIndex) => (
      ALLOWED_WINDOWS.has(rule.windowMs) ? null : `rules[${ruleIndex}].windowMs`
    ),
  },
  {
    reason: "invalid_limit",
    field: (rule, ruleIndex) => (
      Number.isInteger(rule.limit) && rule.limit >= 1 ? null : `rules[${ruleIndex}].limit`
    ),
  },
];

export function selectLimitIssue(change) {
  const rules = Array.isArray(change.rules) ? change.rules : [];
  for (const [ruleIndex, rule] of rules.entries()) {
    for (const check of LIMIT_CHECKS) {
      const field = check.field(rule, ruleIndex);
      if (field !== null) {
        return { reason: check.reason, field, ruleIndex };
      }
    }
  }
  return null;
}
