const ALLOWED_BUCKETS = new Set(["anonymous", "member", "partner"]);
const ALLOWED_WINDOWS = new Set([1_000, 60_000]);

const REASON_PRIORITY = {
  unknown_bucket: 0,
  invalid_window: 1,
  invalid_limit: 2,
};

export function collectLimitIssues(change) {
  const issues = [];
  const rules = Array.isArray(change.rules) ? change.rules : [];
  rules.forEach((rule, ruleIndex) => {
    if (!ALLOWED_BUCKETS.has(rule.bucket)) {
      issues.push({
        reason: "unknown_bucket",
        field: `rules[${ruleIndex}].bucket`,
        ruleIndex,
      });
    }
    if (!ALLOWED_WINDOWS.has(rule.windowMs)) {
      issues.push({
        reason: "invalid_window",
        field: `rules[${ruleIndex}].windowMs`,
        ruleIndex,
      });
    }
    if (!Number.isInteger(rule.limit) || rule.limit < 1) {
      issues.push({
        reason: "invalid_limit",
        field: `rules[${ruleIndex}].limit`,
        ruleIndex,
      });
    }
  });
  return issues;
}

export function rankLimitIssues(issues) {
  return [...issues].sort((left, right) => left.ruleIndex - right.ruleIndex);
}

export { REASON_PRIORITY };
