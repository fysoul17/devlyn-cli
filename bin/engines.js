// Engine IDs from devlyn-os-v1/packages/contracts/src/engines.ts, in inventory order.
// CLI binary names (for example agy) are not engine IDs.
const ENGINE_IDS = Object.freeze([
  'claude', 'codex', 'grok', 'omp', 'antigravity', 'cursor', 'opencode', 'kimi', 'copilot', 'qwen',
]);

// The versions each channel was examined on. Newer releases of the same major are taken as
// compatible: these CLIs ship minor releases weekly, and gating on the examined minor would turn
// the harness off at every one of them. A new major (or a Cursor build older than the examined one)
// is refused, since any flag may change there.
const ENGINE_CAPABILITIES = Object.freeze({
  claude: { minimum: '2.1.307', executor: true },
  codex: { minimum: '0.163.0', executor: true },
  grok: { minimum: '1.0.62', executor: false },
  omp: { minimum: '16.5.0', executor: false },
  antigravity: { minimum: '1.4.4', executor: false },
  cursor: { minimum: '2025.09.12-4852336', executor: false },
  opencode: { minimum: '1.19.2', executor: false },
  kimi: { minimum: '2.3.0', executor: false },
  copilot: { minimum: '1.0.98', executor: false },
  qwen: { minimum: '0.26.0', executor: false },
});

function supportedVersion(engine, version) {
  const capability = ENGINE_CAPABILITIES[engine];
  if (engine === 'cursor') {
    const build = typeof version === 'string' && version.match(/^(\d{4})\.(\d{2})\.(\d{2})-[0-9a-f]+$/);
    return Boolean(build) && build.slice(1).join('') >= capability.minimum.slice(0, 10).replace(/\./g, '');
  }
  if (typeof version !== 'string' || !/^\d+\.\d+\.\d+$/.test(version)) return false;
  const actual = version.split('.').map(Number);
  const floor = capability.minimum.split('.').map(Number);
  if (actual[0] !== floor[0]) return false;
  for (let i = 1; i < 3; i++) {
    if (actual[i] !== floor[i]) return actual[i] > floor[i];
  }
  return true;
}

module.exports = { ENGINE_IDS, ENGINE_CAPABILITIES, supportedVersion };
