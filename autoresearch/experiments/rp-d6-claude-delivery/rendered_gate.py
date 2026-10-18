"""Rendered-block token gate: count installed CLAUDE.md / AGENTS.md from X and Y installs.

Usage: python rendered_gate.py <x CLAUDE.md> <y CLAUDE.md> <x AGENTS.md> <y AGENTS.md>
Claude: Anthropic count_tokens (host OAuth from the macOS keychain, never printed); Codex proxy: o200k.
Exit 1 when any count increases.
"""
import json, subprocess, sys, urllib.request
import tiktoken


def claude_tokens(text, token):
    body = json.dumps({'model': 'claude-opus-5-5', 'messages': [{'role': 'user', 'content': text}]}).encode()
    request = urllib.request.Request('https://api.anthropic.com/v1/messages/count_tokens', data=body,
        headers={'authorization': 'Bearer ' + token, 'anthropic-version': '2023-06-01',
                 'anthropic-beta': 'oauth-2025-04-20', 'content-type': 'application/json'})
    with urllib.request.urlopen(request) as response:
        return json.load(response)['input_tokens']


def main(xc, yc, xa, ya):
    raw = subprocess.run(['security', 'find-generic-password', '-s', 'Claude Code-credentials', '-w'],
                         capture_output=True, text=True, check=True).stdout
    token = json.loads(raw)['claudeAiOauth']['accessToken']
    enc = tiktoken.get_encoding('o200k_base')
    rows, passed = {}, True
    for name, x, y in (('CLAUDE.md', xc, yc), ('AGENTS.md', xa, ya)):
        tx, ty = open(x).read(), open(y).read()
        rows[name] = dict(bytes=[len(tx.encode()), len(ty.encode())],
                          claude=[claude_tokens(tx, token), claude_tokens(ty, token)],
                          o200k=[len(enc.encode(tx)), len(enc.encode(ty))])
        passed &= all(rows[name][k][1] <= rows[name][k][0] for k in ('claude', 'o200k'))
    print(json.dumps(dict(rows, passed=passed), indent=1))
    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
