// Engine IDs from devlyn-os-v1/packages/contracts/src/engines.ts, in inventory order.
// CLI binary names (for example agy) are not engine IDs.
const ENGINE_IDS = Object.freeze([
  'claude', 'codex', 'grok', 'omp', 'antigravity', 'cursor', 'opencode', 'kimi', 'copilot', 'qwen',
]);

// Examined versions, not historical feature-introduction claims. Pre-1.0
// engines are bounded to the examined minor; Cursor to the examined build.
const ENGINE_CAPABILITIES = Object.freeze({
  claude: { minimum: '2.1.307', generation: '2', executor: true },
  codex: { minimum: '0.163.0', generation: '0.163', executor: true },
  grok: { minimum: '1.0.62', generation: '1', executor: false },
  omp: { minimum: '16.5.0', generation: '16', executor: false },
  antigravity: { minimum: '1.4.4', generation: '1', executor: false },
  cursor: { minimum: '2025.09.12-4852336', generation: '2025.09.12-4852336', executor: false },
  opencode: { minimum: '1.19.2', generation: '1', executor: false },
  kimi: { minimum: '2.3.0', generation: '2', executor: false },
  copilot: { minimum: '1.0.98', generation: '1', executor: false },
  qwen: { minimum: '0.26.0', generation: '0.26', executor: false },
});

function supportedVersion(engine, version) {
  const capability = ENGINE_CAPABILITIES[engine];
  if (engine === 'cursor') return version === capability.minimum;
  if (typeof version !== 'string' || !/^\d+\.\d+\.\d+$/.test(version)) return false;
  if (!version.startsWith(`${capability.generation}.`)) return false;
  const actual = version.split('.').map(Number);
  const floor = capability.minimum.split('.').map(Number);
  for (let i = 0; i < 3; i++) {
    if (actual[i] !== floor[i]) return actual[i] > floor[i];
  }
  return true;
}

module.exports = { ENGINE_IDS, ENGINE_CAPABILITIES, supportedVersion };
