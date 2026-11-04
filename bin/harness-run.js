'use strict';
// `devlyn run <engine> [engine args...]`: start claude, codex or omp from a terminal with the same
// activation plan the Devlyn app applies (docs/harness-run.md). Preparation either succeeds
// completely or no engine starts; the engine's exit code or signal is the command's own.
const fs = require('fs');
const os = require('os');
const path = require('path');
const crypto = require('crypto');
const { spawn, spawnSync } = require('child_process');
const { HarnessError, fail } = require('./release');
const { launchInputs } = require('./harness-context');

const sha256 = (text) => crypto.createHash('sha256').update(text, 'utf8').digest('hex');
const object = (value) => value !== null && typeof value === 'object' && !Array.isArray(value);

// Run one of the selected release's own commands (never this package's) and return its data.
function releaseCommand(release, argv, input) {
  const result = spawnSync(process.execPath, [path.join(release.root, 'bin/devlyn.js'), ...argv],
    { input, encoding: 'utf8', maxBuffer: 64 * 1024 * 1024, stdio: ['pipe', 'pipe', 'pipe'] });
  let envelope;
  try { envelope = JSON.parse(result.stdout); } catch { envelope = null; }
  if (!object(envelope) || envelope.schemaVersion !== 1) {
    fail('cli-failed', { command: argv.slice(0, 2).join(' '), exit: result.status }, 3);
  }
  if (!envelope.ok) {
    // A `detail` can quote what it failed on, so only the structured reason is carried.
    const { detail, ...params } = envelope.error?.params || {};
    fail(envelope.error?.code || 'cli-failed', params, result.status || 3);
  }
  return envelope.data;
}

function validatePlan(plan, release) {
  const strings = (value) => Array.isArray(value) && value.every((item) => typeof item === 'string');
  if (!object(plan) || plan.schemaVersion !== 1 || !strings(plan.engineArgs) || !object(plan.envPatch)
      || !Object.values(plan.envPatch).every((value) => value === null || typeof value === 'string')
      || !Array.isArray(plan.files) || !object(plan.channels)) {
    fail('plan-invalid', { detail: 'shape' }, 3);
  }
  if (plan.release && (plan.release.version !== release.version || plan.release.digest !== release.digest)) {
    fail('plan-invalid', { detail: 'release changed' }, 3);
  }
  // Terminal launches carry no initial task, so no plan may rewrite one.
  if (plan.prompt !== null) fail('plan-invalid', { detail: 'unexpected prompt' }, 3);
  if (plan.machineSync !== null && !(object(plan.machineSync) && plan.machineSync.engine === 'codex')) {
    fail('plan-invalid', { detail: 'machineSync' }, 3);
  }
  const seen = new Set();
  for (const file of plan.files) {
    const relative = file?.relativePath;
    if (typeof relative !== 'string' || typeof file.utf8 !== 'string' || !/^[a-f0-9]{64}$/.test(file.sha256 || '')
        || path.isAbsolute(relative) || path.normalize(relative) !== relative || relative.split(/[\\/]/).includes('..')
        || seen.has(relative) || sha256(file.utf8) !== file.sha256) {
      fail('plan-invalid', { detail: `file ${relative}` }, 3);
    }
    seen.add(relative);
  }
}

// Write the plan's files under this run's own folder, exclusively, and read each back.
function writeFiles(runDir, files) {
  for (const file of files) {
    const target = path.join(runDir, file.relativePath);
    fs.mkdirSync(path.dirname(target), { recursive: true, mode: 0o700 });
    fs.writeFileSync(target, file.utf8, { flag: 'wx', mode: 0o600 });
    if (sha256(fs.readFileSync(target, 'utf8')) !== file.sha256) fail('plan-invalid', { detail: `wrote ${file.relativePath}` }, 3);
  }
}

function statusLine(inputs, plan, engine) {
  const { release, source, version, choice } = inputs;
  const head = `devlyn: ${engine} ${version} | release ${release.version}@${release.digest.slice(0, 8)} (${source})`;
  if (choice === 'none') return `${head} | harness off for this project`;
  const said = (name) => {
    const channel = plan.channels[name];
    const reasons = (channel.reasons || []).map((reason) => reason.code).join(',');
    return `${name}=${channel.state}${channel.mechanism ? `:${channel.mechanism}` : ''}${reasons ? ` (${reasons})` : ''}`;
  };
  return `${head} | ${said('principles')} | ${said('skills')}`;
}

async function runCommand(args) {
  const engine = args[0];
  if (!engine || engine.startsWith('-')) fail('invalid-arguments', { argument: 'usage: devlyn run <claude|codex|omp> [engine args...]' }, 2);
  const env = { ...process.env };
  const home = env.HOME || os.homedir();
  const inputs = await launchInputs({ engine, args: args.slice(1), cwd: process.cwd(), env, home,
    packageRoot: path.resolve(__dirname, '..') });
  const runDir = fs.mkdtempSync(path.join(os.tmpdir(), 'devlyn-run-'));
  fs.chmodSync(runDir, 0o700);
  const cleanup = () => fs.rmSync(runDir, { recursive: true, force: true });
  let child;
  try {
    const context = { schemaVersion: 1, engine, version: inputs.version, launchMode: 'fresh', cwd: inputs.cwd,
      runDir, projectChoice: inputs.choice, committedBlockApplies: false, initialPrompt: null, accountRef: null,
      ...(inputs.accountHome ? { accountHome: inputs.accountHome } : {}), effectiveConfig: inputs.effectiveConfig };
    const plan = releaseCommand(inputs.release, ['activation', '--plan', '--release-root', inputs.release.root,
      '--context-file', '-', '--json'], JSON.stringify(context));
    validatePlan(plan, inputs.release);
    if (inputs.choice !== 'none' && plan.channels.principles.state !== 'configured') {
      fail('principles-unavailable', { reasons: (plan.channels.principles.reasons || []).map((reason) => reason.code).join(','),
        release: inputs.release.version, source: inputs.source, engineVersion: inputs.version }, 3);
    }
    writeFiles(runDir, plan.files);
    if (plan.machineSync) {
      releaseCommand(inputs.release, ['machine', 'sync', '--release-root', inputs.release.root, '--engine', 'codex',
        '--account-home', plan.machineSync.accountHome, '--json']);
    }
    const childEnv = { ...env, DEVLYN_NODE: process.execPath };
    for (const [key, value] of Object.entries(plan.envPatch)) {
      if (value === null) delete childEnv[key]; else childEnv[key] = value;
    }
    process.stderr.write(`${statusLine(inputs, plan, engine)}\n`);
    child = spawn(inputs.program, [...plan.engineArgs, ...inputs.args], { cwd: inputs.cwd, env: childEnv, stdio: 'inherit' });
  } catch (error) {
    cleanup();
    throw error;
  }
  // The terminal already delivers Ctrl-C and Ctrl-\ to the engine; forwarding them would double them.
  // Signals sent to this process alone are passed on.
  const ignore = () => {};
  const forward = (signal) => () => { if (child.exitCode === null && child.signalCode === null) child.kill(signal); };
  const handlers = { SIGINT: ignore, SIGQUIT: ignore, SIGTERM: forward('SIGTERM'), SIGHUP: forward('SIGHUP') };
  for (const [signal, handler] of Object.entries(handlers)) process.on(signal, handler);
  const outcome = await new Promise((resolve) => {
    child.on('error', (error) => resolve({ error }));
    child.on('exit', (code, signal) => resolve({ code, signal }));
  });
  cleanup();
  for (const [signal, handler] of Object.entries(handlers)) process.removeListener(signal, handler);
  if (outcome.error) fail('run-engine-failed', { engine, detail: outcome.error.code || outcome.error.message }, 3);
  if (outcome.signal) { process.kill(process.pid, outcome.signal); return; }
  process.exitCode = outcome.code;
}

// Errors say what stopped the launch on one line, without prompts, credentials or configuration.
async function runMain(args) {
  try { await runCommand(args); }
  catch (error) {
    if (!(error instanceof HarnessError)) throw error;
    process.stderr.write(`devlyn run: ${error.reason.code} ${JSON.stringify(error.reason.params)}\n`);
    process.exitCode = error.exitCode;
  }
}

module.exports = { runMain };
