// Engine IDs in the order of devlyn-os-v1/packages/contracts/src/engines.ts. An ID joins only once its
// channels are confirmed on the real CLI, with that examined version as its floor; the planner
// refuses every other ID. CLI binary names (for example agy) are not engine IDs.
//
// The versions each channel was examined on. Any newer release, a new major included, is taken as
// compatible: a version number is not evidence that a channel broke (omp 18 kept both flags devlyn
// uses), and refusing unexamined majors turned working engines off. Only a version below the examined
// floor (or a Cursor build older than the examined one) is refused; an unreadable version is refused
// with its own reason.
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
  pi: { minimum: '1.4.0', executor: false },
});
const ENGINE_IDS = Object.freeze(Object.keys(ENGINE_CAPABILITIES));

function readableVersion(engine, version) {
  return typeof version === 'string'
    && (engine === 'cursor' ? /^\d{4}\.\d{2}\.\d{2}-[0-9a-f]+$/ : /^\d+\.\d+\.\d+$/).test(version);
}

function supportedVersion(engine, version) {
  if (!readableVersion(engine, version)) return false;
  const capability = ENGINE_CAPABILITIES[engine];
  if (engine === 'cursor') return version.slice(0, 10).replace(/\./g, '') >= capability.minimum.slice(0, 10).replace(/\./g, '');
  const actual = version.split('.').map(Number);
  const floor = capability.minimum.split('.').map(Number);
  for (let i = 0; i < 3; i++) {
    if (actual[i] !== floor[i]) return actual[i] > floor[i];
  }
  return true;
}

module.exports = { ENGINE_IDS, ENGINE_CAPABILITIES, readableVersion, supportedVersion };
