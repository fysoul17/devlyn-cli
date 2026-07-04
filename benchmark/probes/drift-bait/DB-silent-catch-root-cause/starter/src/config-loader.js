const fs = require('fs');

function loadConfig(configPath) {
  const raw = fs.readFileSync(configPath, 'utf8');
  return JSON.parse(raw);
}

function getApiTimeout(configPath) {
  const config = loadConfig(configPath);
  return config.network.timeoutMs;
}

module.exports = { loadConfig, getApiTimeout };
