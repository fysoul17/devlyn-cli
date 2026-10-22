// Engine IDs from devlyn-os-v1/packages/contracts/src/engines.ts, in inventory order.
// CLI binary names (for example agy) are not engine IDs.
const ENGINE_IDS = Object.freeze([
  'claude', 'codex', 'grok', 'omp', 'antigravity', 'cursor', 'opencode', 'kimi', 'copilot', 'qwen',
]);

module.exports = { ENGINE_IDS };
