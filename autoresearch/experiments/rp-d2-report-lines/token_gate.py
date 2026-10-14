"""Token gate: whole-file token counts of an instruction file at two Git revisions.

Claude: Anthropic count_tokens for claude-opus-5-5 (the host's Claude Code OAuth
login, read from the macOS keychain, never printed). Codex: tiktoken o200k_base
as a proxy (the gpt-6-sol tokenizer is not published).

Usage: python token_gate.py <control-rev> <candidate-rev> <path>
Exit 1 when either count increases.
"""
import json
import subprocess
import sys
import urllib.request

import tiktoken


def show(rev, path):
    return subprocess.run(['git', 'show', f'{rev}:{path}'], capture_output=True, text=True, check=True).stdout


def claude_tokens(text, token):
    body = json.dumps({'model': 'claude-opus-5-5', 'messages': [{'role': 'user', 'content': text}]}).encode()
    request = urllib.request.Request(
        'https://api.anthropic.com/v1/messages/count_tokens', data=body,
        headers={'authorization': 'Bearer ' + token, 'anthropic-version': '2023-06-01',
                 'anthropic-beta': 'oauth-2025-04-20', 'content-type': 'application/json'})
    with urllib.request.urlopen(request) as response:
        return json.load(response)['input_tokens']


def main(control, candidate, path):
    raw = subprocess.run(['security', 'find-generic-password', '-s', 'Claude Code-credentials', '-w'],
                         capture_output=True, text=True, check=True).stdout
    token = json.loads(raw)['claudeAiOauth']['accessToken']
    encoding = tiktoken.get_encoding('o200k_base')
    counts = {}
    for label, rev in (('control', control), ('candidate', candidate)):
        text = show(rev, path)
        counts[label] = dict(rev=rev, bytes=len(text.encode()), words=len(text.split()),
                             claude=claude_tokens(text, token), o200k=len(encoding.encode(text)))
    passed = all(counts['candidate'][key] <= counts['control'][key] for key in ('claude', 'o200k'))
    print(json.dumps(dict(path=path, **counts, passed=passed), indent=2))
    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
