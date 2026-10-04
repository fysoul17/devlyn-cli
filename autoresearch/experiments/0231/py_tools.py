"""Hash-pinned requirements for D4's typing tools from click's own uv.lock: uv.lock on stdin, requirements on stdout."""
import sys
import tomllib

TOOLS = ('mypy',)  # pyright comes from npm at the lock's version (pyright/package-lock.json)


def main():
    lock = tomllib.loads(sys.stdin.read())
    packages = {p['name']: p for p in lock['package']}
    wanted, queue = {}, list(TOOLS)
    while queue:
        name = queue.pop()
        if name in wanted:
            continue
        package = packages[name]
        wanted[name] = package
        queue += [dep['name'] for dep in package.get('dependencies', ())]
    for name in sorted(wanted):
        package = wanted[name]
        hashes = sorted({w['hash'] for w in package.get('wheels', ())} | ({package['sdist']['hash']} if 'sdist' in package else set()))
        marker = next((d.get('marker') for p in wanted.values() for d in p.get('dependencies', ()) if d['name'] == name and d.get('marker')), None)
        line = f'{name}=={package["version"]}' + (f' ; {marker}' if marker else '')
        print(' \\\n    '.join([line, *(f'--hash={h}' for h in hashes)]))


if __name__ == '__main__':
    main()
