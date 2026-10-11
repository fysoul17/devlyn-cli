'use strict';
const fs = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const {execFile} = require('node:child_process');
const {promisify} = require('node:util');
const lockfile = require('proper-lockfile');
const exec = promisify(execFile);
const runtimePath = '/Users/aipalm/.local/share/nx01/0244-live/runtime-smoke.json';
const cli = '/Users/aipalm/.local/share/claude/versions/2.1.296';
const hostConfig = path.join(os.homedir(), '.claude').normalize('NFC');
const reportPath = process.argv[2];
const releases = [];
let compromised = false;
let phase = 'initial';
const report = {at: new Date().toISOString(), prediction: 'The native CLI renews the same host account under its two cooperative refresh locks; persisted identity/scopes stay equal and lifetime exceeds 6300 seconds. No browser, inference, custom grant request or manual credential write.', mutations: 'Only native claude auth login may persist credentials.'};
const hash = value => crypto.createHash('sha256').update(value).digest('hex');
function guard() {if (compromised) throw new Error('refresh-lock-compromised');}
async function credentials() {
  const {stdout} = await exec('security', ['find-generic-password', '-s', 'Claude Code-credentials', '-w']);
  return JSON.parse(stdout).claudeAiOauth;
}
async function identity(oauth) {
  const response = await fetch('https://api.anthropic.com/api/oauth/profile', {headers: {Authorization: 'Bearer ' + oauth.accessToken, 'anthropic-beta': 'oauth-2025-04-20'}, signal: AbortSignal.timeout(20000)});
  if (!response.ok) throw new Error('profile-http-' + response.status);
  const value = await response.json();
  return [hash(value.account.uuid).slice(0, 12), hash(value.organization.uuid).slice(0, 12)];
}
async function run() {
  if (!reportPath) throw new Error('missing-report-path');
  await fs.writeFile(reportPath + '.prediction.json', JSON.stringify(report, null, 2) + '\n', {flag: 'wx', mode: 0o600});
  for (const name of ['CLAUDE_CONFIG_DIR', 'CLAUDE_SECURESTORAGE_CONFIG_DIR', 'CLAUDE_CODE_OAUTH_CLIENT_ID', 'CLAUDE_CODE_CUSTOM_OAUTH_URL', 'CLAUDE_CODE_API_BASE_URL', 'CLAUDE_CODE_OAUTH_REFRESH_TOKEN', 'CLAUDE_CODE_OAUTH_TOKEN', 'ANTHROPIC_AUTH_TOKEN', 'ANTHROPIC_API_KEY']) {
    if (process.env[name] !== undefined) throw new Error('unexpected-auth-override');
  }
  const expected = JSON.parse(await fs.readFile(runtimePath, 'utf8')).account;
  report.cli_sha256 = hash(await fs.readFile(cli));
  report.operator_sha256 = hash(await fs.readFile(__filename));
  report.dependency_lock_sha256 = hash(await fs.readFile(path.join(__dirname, 'package-lock.json')));
  phase = 'lock';
  const options = {realpath: false, stale: 60000, update: 5000, retries: {retries: 20, minTimeout: 250, maxTimeout: 1000}, onCompromised: () => {compromised = true;}};
  releases.push(await lockfile.lock(hostConfig, {...options, lockfilePath: path.join(hostConfig, '.oauth_refresh.lock')}));
  guard();
  const legacy = await fs.realpath(hostConfig) + '.lock';
  releases.push(await lockfile.lock(legacy, {...options, lockfilePath: legacy}));
  guard();
  const {stdout: processList} = await exec('ps', ['-axo', 'pid=,command=']);
  const concurrent = processList.split('\n').some(line => /(?:^|\s)(?:[^\s]*\/)?(?:token-keeper\.sh|refresh-token\.py)(?:\s|$)/.test(line) || /(?:^|\s)(?:[^\s]*\/)?(?:claude|versions\/\d+\.\d+\.\d+(?:-[\w.-]+)?)\s+auth\s+login(?:\s|$)/.test(line));
  if (concurrent) throw new Error('uncoordinated-auth-writer');
  const {stdout: containers} = await exec('docker', ['ps', '--format', '{{.Names}}']);
  if (containers.split('\n').some(name => /02(?:37|38|4\d)/.test(name))) throw new Error('active-benchmark-container');
  phase = 'before';
  const before = await credentials();
  if (!before.refreshToken || !Array.isArray(before.scopes) || !before.scopes.length) throw new Error('incomplete-native-grant');
  report.identity_before = await identity(before);
  if (JSON.stringify(report.identity_before) !== JSON.stringify(expected)) throw new Error('unexpected-account-before');
  report.seconds_before = Math.floor(before.expiresAt / 1000 - Date.now() / 1000);
  guard();
  phase = 'native-login';
  const started = Date.now();
  const result = await exec(cli, ['auth', 'login', '--claudeai'], {cwd: __dirname, env: {...process.env, CLAUDE_CODE_OAUTH_REFRESH_TOKEN: before.refreshToken, CLAUDE_CODE_OAUTH_SCOPES: before.scopes.join(' ')}, timeout: 120000, maxBuffer: 1024 * 1024});
  report.native_seconds = (Date.now() - started) / 1000;
  report.native_stdout_sha256 = hash(result.stdout);
  report.native_stderr_sha256 = hash(result.stderr);
  report.native_login_success_message = result.stdout.includes('Login successful.');
  guard();
  phase = 'after';
  const after = await credentials();
  report.identity_after = await identity(after);
  report.same_account = JSON.stringify(report.identity_after) === JSON.stringify(expected);
  report.same_scopes = JSON.stringify([...after.scopes].sort()) === JSON.stringify([...before.scopes].sort());
  report.seconds_after = Math.floor(after.expiresAt / 1000 - Date.now() / 1000);
  guard();
  if (!report.same_account || !report.same_scopes || report.seconds_after < 6300 || !report.native_login_success_message) throw new Error('persisted-renewal-contract');
  report.status = 'PASS';
}
run().catch(error => {
  report.status = 'FAILED';
  report.failure_phase = phase;
  report.failure_type = error.name;
  const safeReasons = new Set(['refresh-lock-compromised', 'missing-report-path', 'unexpected-auth-override', 'uncoordinated-auth-writer', 'active-benchmark-container', 'incomplete-native-grant', 'unexpected-account-before', 'persisted-renewal-contract']);
  report.failure_reason = safeReasons.has(error.message) || /^profile-http-\d{3}$/.test(error.message) ? error.message : 'native-command-or-io-failure';
  report.failure_code = typeof error.code === 'number' ? error.code : undefined;
  report.credentials_restored = false;
  process.exitCode = 1;
}).finally(async () => {
  report.lock_compromised = compromised;
  report.release_failures = 0;
  for (const release of releases.reverse()) {
    try {await release();} catch {report.release_failures++;}
  }
  if (report.release_failures || compromised) {report.status = 'FAILED'; process.exitCode = 1;}
  report.finished_at = new Date().toISOString();
  await fs.writeFile(reportPath, JSON.stringify(report, null, 2) + '\n', {flag: 'wx', mode: 0o600});
  process.stdout.write(JSON.stringify(report) + '\n');
});
