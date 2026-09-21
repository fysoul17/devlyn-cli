#!/usr/bin/env node
// Refresh offline migration fingerprints from committed mainline instructions.
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');
const { instructionParagraphs } = require('../bin/instructions');

const root = path.join(__dirname, '..');
const manifestPath = path.join(root, 'bin/instruction-templates.json');
const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
const git = (...args) => execFileSync('git', args, { cwd: root, encoding: 'utf8' });
manifest.paragraphs = {};
for (const name of ['AGENTS.md', 'CLAUDE.md']) {
  const keys = new Set();
  const commits = git('log', '--first-parent', '--format=%H', 'HEAD', '--', name).trim().split('\n');
  for (const commit of commits) {
    for (const paragraph of instructionParagraphs(git('show', `${commit}:${name}`))) {
      keys.add(paragraph.key);
    }
  }
  manifest.paragraphs[name] = [...keys].sort();
}
fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2)
  .replace(/[\u007f-\uffff]/g, (char) => '\\u' + char.charCodeAt(0).toString(16).padStart(4, '0')) + '\n');
