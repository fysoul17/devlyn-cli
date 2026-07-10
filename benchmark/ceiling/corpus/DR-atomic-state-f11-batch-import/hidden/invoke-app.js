'use strict';
const http = require('node:http');
const { Duplex } = require('node:stream');

class MemorySocket extends Duplex {
  constructor() {
    super();
    this.responseChunks = [];
    this.remoteAddress = '127.0.0.1';
  }

  _read() {}

  _write(chunk, _encoding, callback) {
    this.responseChunks.push(Buffer.from(chunk));
    callback();
  }
}

function responseBody(socket) {
  const raw = Buffer.concat(socket.responseChunks);
  const separator = raw.indexOf('\r\n\r\n');
  if (separator === -1) throw new Error('invalid in-memory HTTP response');
  return raw.subarray(separator + 4).toString('utf8');
}

function invokeApp(app, { method = 'GET', path = '/', headers = {}, body } = {}) {
  return new Promise((resolve, reject) => {
    const bytes = body === undefined
      ? Buffer.alloc(0)
      : Buffer.isBuffer(body) ? body : Buffer.from(body);
    const normalizedHeaders = {};
    const rawHeaders = [];
    for (const [name, value] of Object.entries(headers)) {
      normalizedHeaders[name.toLowerCase()] = String(value);
      rawHeaders.push(name, String(value));
    }
    if (bytes.length > 0 && normalizedHeaders['content-length'] === undefined) {
      normalizedHeaders['content-length'] = String(bytes.length);
      rawHeaders.push('Content-Length', String(bytes.length));
    }

    const socket = new MemorySocket();
    const req = new http.IncomingMessage(socket);
    req.method = method;
    req.url = path;
    req.headers = normalizedHeaders;
    req.rawHeaders = rawHeaders;
    const res = new http.ServerResponse(req);
    res.assignSocket(socket);

    socket.on('error', reject);
    res.on('error', reject);
    res.on('finish', () => {
      try {
        const text = responseBody(socket);
        resolve({
          status: res.statusCode,
          text,
          body: text.length === 0 ? null : JSON.parse(text),
        });
      } catch (error) {
        reject(error);
      }
    });

    app(req, res);
    process.nextTick(() => {
      if (bytes.length > 0) req.push(bytes);
      req.push(null);
    });
  });
}

module.exports = { invokeApp };
