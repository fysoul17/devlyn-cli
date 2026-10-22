'use strict';
// Run on a disposable snapshot inside the registered cell image. JSON on stdout is the probe result.
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const http = require('http');

const task = process.argv[2];

function storeDigest(dir = 'data') {
  if (!fs.existsSync(dir)) return null;
  const hash = crypto.createHash('sha256');
  function visit(base) {
    for (const entry of fs.readdirSync(base, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
      const file = path.join(base, entry.name);
      hash.update(file.slice(dir.length));
      if (entry.isDirectory()) visit(file);
      else if (entry.isFile()) hash.update(fs.readFileSync(file));
    }
  }
  visit(dir);
  return hash.digest('hex');
}

function request(port, method, route, body) {
  return new Promise((resolve, reject) => {
    let timer;
    let settled = false;
    function finish(error, value) {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      if (error) reject(error);
      else resolve(value);
    }
    const req = http.request({ hostname: '127.0.0.1', port, method, path: route,
      headers: body === undefined ? {} : { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body) } },
    (res) => {
      let text = '';
      res.setEncoding('utf8');
      res.on('data', chunk => { text += chunk; });
      res.on('end', () => finish(null, { status: res.statusCode, type: res.headers['content-type'] || '', body: text }));
      res.on('error', error => finish(error));
      res.on('aborted', () => finish(new Error('response aborted')));
      res.on('close', () => finish(new Error('response closed before end')));
    });
    timer = setTimeout(() => {
      finish(new Error('request deadline exceeded'));
      req.destroy();
    }, 5000);
    req.on('error', error => finish(error));
    req.end(body);
  });
}

function closeServer(server) {
  return new Promise(resolve => {
    const timer = setTimeout(() => {
      server.closeAllConnections();
      resolve();
    }, 1000);
    server.close(() => { clearTimeout(timer); resolve(); });
  });
}

function classify(response) {
  let parsed;
  try { parsed = JSON.parse(response.body); } catch { parsed = null; }
  if (response.status === 400 && parsed && typeof parsed === 'object' && !Array.isArray(parsed) &&
      Object.prototype.hasOwnProperty.call(parsed, 'error')) return 'json_error_400';
  if (response.status === 400 && (response.type.includes('html') || /^\s*<!doctype html/i.test(response.body)))
    return 'html_400';
  return 'other';
}

async function main() {
  if (!['F10', 'F11'].includes(task)) throw new Error('task must be F10 or F11');
  const endpoint = task === 'F10' ? '/items' : '/items/import';
  const app = require(path.resolve('server/index.js')).app;
  const server = app.listen(0, '127.0.0.1');
  try {
    await new Promise((resolve, reject) => { server.once('listening', resolve); server.once('error', reject); });
    const port = server.address().port;
    let before, diskBefore, preservationError;
    try {
      before = await request(port, 'GET', '/items');
      if (before.status !== 200) throw new Error(`baseline GET status ${before.status}`);
      diskBefore = storeDigest();
    } catch (error) {
      preservationError = String(error);
    }
    const response = await request(port, 'POST', endpoint, '{');
    const kind = classify(response);
    try {
      if (preservationError) throw new Error(preservationError);
      const after = await request(port, 'GET', '/items');
      if (after.status !== 200) throw new Error(`follow-up GET status ${after.status}`);
      const diskAfter = storeDigest();
      return { class: kind, store_preserved: before.body === after.body && diskBefore === diskAfter,
        status: response.status };
    } catch (error) {
      return { class: kind, store_preserved: null, status: response.status, error: String(error) };
    }
  } finally {
    await closeServer(server);
  }
}

if (require.main === module) {
  main().catch(error => ({ class: 'unassessable', store_preserved: null, error: String(error) }))
    .then(result => { process.stdout.write(JSON.stringify(result) + '\n'); });
}
module.exports = { classify, request, closeServer, main };
