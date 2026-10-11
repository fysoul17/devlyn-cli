"""Bounded package payload and offline B/S installation verification; no models."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import tarfile
import time

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[3]
SOURCE = Path('/Users/aipalm/.local/share/nx01/0237-integration-425')
PACKS = Path('/Users/aipalm/.local/share/nx01/0249-live/selected-packs-v1')
OLD = Path('/Users/aipalm/.local/share/nx01/0247-live/selected-packs-v1')
IMAGE = 'sha256:0f472bb41685b7daa5923d51d31983f4b3c70053dd773fdf712bd0dcd6d87998'
BASE = 'd1f170ed3bd57441b95ea525156e80644543acb1'
NODE = '/Users/aipalm/.nvm/versions/node/v20.19.0/bin'
ENV = dict(os.environ, PATH=NODE + os.pathsep + os.environ['PATH'],
           GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1',
           GIT_AUTHOR_NAME='Package verification', GIT_COMMITTER_NAME='Package verification',
           GIT_AUTHOR_EMAIL='verification@localhost', GIT_COMMITTER_EMAIL='verification@localhost',
           PYTHONDONTWRITEBYTECODE='1')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def command(argv, folder, label, cwd=None):
    started = time.monotonic()
    completed = subprocess.run(argv, cwd=cwd, env=ENV, capture_output=True, timeout=300)
    stdout, stderr = folder / (label + '.stdout'), folder / (label + '.stderr')
    stdout.write_bytes(completed.stdout)
    stderr.write_bytes(completed.stderr)
    row = dict(argv=argv, cwd=str(cwd) if cwd else None, exit_code=completed.returncode,
               seconds=time.monotonic() - started, stdout=str(stdout), stderr=str(stderr),
               stdout_sha256=sha(stdout), stderr_sha256=sha(stderr))
    write(folder / (label + '.json'), row)
    if completed.returncode:
        raise RuntimeError(f'{label} exited {completed.returncode}; inspect retained logs')
    return row


def verify_inputs():
    prediction = read(HERE / 'package-prediction-v1.json')
    gate = read(SOURCE / '.devlyn/integration-verification-v1/summary.json')
    assert gate['status'] == 'PASS' and gate['inputs_unchanged']
    assert gate['inputs_before'] == gate['inputs_after'] == prediction['source_twelve_inputs']
    assert len(gate['inputs_after']) == 12
    for path, expected in prediction['inputs_before'].items():
        assert sha(Path(path)) == expected, ('input changed', path)
    head = subprocess.check_output(['git', '-C', str(SOURCE), 'rev-parse', 'HEAD'],
                                   env=ENV, text=True).strip()
    assert head == BASE
    return prediction


def inventory(path):
    with tarfile.open(path) as archive:
        members = [member for member in archive if member.isfile()]
        assert len(members) == len({member.name for member in members})
        return {member.name: dict(sha256=hashlib.sha256(archive.extractfile(member).read()).hexdigest(),
                                  mode=member.mode, bytes=member.size) for member in members}


def payload_bytes(archive, name):
    with tarfile.open(archive) as package:
        return package.extractfile(name).read()


def local():
    prediction = verify_inputs()
    current, old = read(PACKS / 'packages.json'), read(OLD / 'packages.json')
    assert current['base'] == BASE and current['versions'] == {'node': 'v20.19.0', 'npm': '10.8.2'}
    assert current['selected_confirmation_arms'] == ['A', 'B', 'S']
    assert current['trigger'] == old['trigger']
    assert current['treatment_source'] == str(STUDY / 'autoresearch/experiments/0247')
    assert current['source_repository'] == str(SOURCE)
    assert len(current['baseline_inputs']) == 7
    assert all(sha(SOURCE / p) == h for p, h in current['baseline_inputs'].items())
    inventories, previous, differences, mode_changes = {}, {}, {}, {}
    for arm in ('B', 'S', 'H', 'P'):
        archive = PACKS / (arm + '.tgz')
        inventories[arm], previous[arm] = inventory(archive), inventory(OLD / (arm + '.tgz'))
        assert sha(archive) == current['packages'][arm]['sha256']
        assert {p: x['sha256'] for p, x in inventories[arm].items()} == current['packages'][arm]['files']
        assert {p: x['sha256'] for p, x in previous[arm].items()} == old['packages'][arm]['files']
        assert sha(OLD / (arm + '.tgz')) == old['packages'][arm]['sha256']
        differences[arm] = [p for p in sorted(inventories[arm].keys() | previous[arm].keys())
                            if inventories[arm].get(p) != previous[arm].get(p)]
        mode_changes[arm] = [p for p in inventories[arm].keys() & previous[arm].keys()
                             if inventories[arm][p]['mode'] != previous[arm][p]['mode']]
        assert not mode_changes[arm]
        assert set(inventories[arm]) == set(previous[arm])
        assert json.loads(payload_bytes(archive, 'package/package.json'))['version'] == '4.2.5'
        for name in differences[arm]:
            source_path = SOURCE / name.removeprefix('package/')
            assert source_path.is_file() and sha(source_path) == inventories[arm][name]['sha256'], name
        if arm != 'B':
            guide = inventories[arm]['package/config/skills/_shared/pair.md']['sha256']
            assert guide == old['packages'][arm]['files']['package/config/skills/_shared/pair.md']
            assert guide == sha(STUDY / f'autoresearch/experiments/0247/guides/{arm}.md')
        if arm in ('H', 'P'):
            assert inventories[arm]['package/config/skills/_shared/peer.py'] == previous[arm]['package/config/skills/_shared/peer.py']
    assert all(value == differences['B'] for value in differences.values())
    bs = [p for p in sorted(inventories['B'].keys() | inventories['S'].keys())
          if inventories['B'].get(p) != inventories['S'].get(p)]
    expected = sorted(['package/AGENTS.md', 'package/CLAUDE.md',
                       'package/config/skills/_shared/runtime-principles.md',
                       'package/config/skills/_shared/pair.md', 'package/bin/instruction-templates.json'])
    assert bs == expected
    trigger = current['trigger']
    anchor = 'Zero CRITICAL, zero HIGH security/design findings on the shippable path.'
    instruction_bindings = {}
    for name in ['AGENTS.md', 'CLAUDE.md', 'config/skills/_shared/runtime-principles.md']:
        b = payload_bytes(PACKS / 'B.tgz', 'package/' + name).decode()
        s = payload_bytes(PACKS / 'S.tgz', 'package/' + name).decode()
        assert b == (SOURCE / name).read_text() and b.count(anchor) == 1
        assert s == b.replace(anchor, anchor + ' ' + trigger)
        assert s == payload_bytes(OLD / 'S.tgz', 'package/' + name).decode()
        instruction_bindings[name] = dict(b_sha256=hashlib.sha256(b.encode()).hexdigest(),
                                          s_sha256=hashlib.sha256(s.encode()).hexdigest(),
                                          b_words=len(b.split()), s_words=len(s.split()))
    assert instruction_bindings['AGENTS.md']['b_words'] == instruction_bindings['CLAUDE.md']['b_words'] == 597
    assert current['packages']['S']['files']['package/config/skills/_shared/pair.md'] == '34287e59aa0e32ba09dacb92115715466e1408de0f0620f92fb6ff2db1e9acc3'
    # The history-aware generated fingerprints are exactly the prior treatment's bytes.
    for arm in ('B', 'S'):
        assert inventories[arm]['package/bin/instruction-templates.json'] == previous[arm]['package/bin/instruction-templates.json']
        dest = HERE / 'package-payload-v1' / arm
        dest.mkdir(parents=True, exist_ok=False)
        with tarfile.open(PACKS / (arm + '.tgz')) as archive:
            archive.extractall(dest, filter='data')
        extracted = {str(p.relative_to(dest)): dict(sha256=sha(p), mode=p.stat().st_mode & 0o777, bytes=p.stat().st_size)
                     for p in dest.rglob('*') if p.is_file() and not p.is_symlink()}
        assert extracted == inventories[arm]
    write(HERE / 'package-payload-inventory-v1.json', inventories)
    verify_inputs()
    report = dict(status='PASS', at=datetime.now(timezone.utc).isoformat(),
                  base=BASE, version='4.2.5', selected_native_arms=['A', 'B', 'S'],
                  unused_archive_arms=['H', 'P'], package_metadata_sha256=sha(PACKS / 'packages.json'),
                  packages={a: current['packages'][a]['sha256'] for a in inventories},
                  regular_payloads={a: len(entries) for a, entries in inventories.items()},
                  payload_differences_from_0247=differences, mode_changes=mode_changes,
                  B_vs_S_exact_differences=bs, instructions=instruction_bindings,
                  S_trigger=current['trigger'], S_trigger_sha256=hashlib.sha256(trigger.encode()).hexdigest(),
                  S_guide_sha256=current['packages']['S']['files']['package/config/skills/_shared/pair.md'],
                  S_treatment_bytes='IDENTICAL_TO_0247', fingerprints='IDENTICAL_TO_0247_PER_ARM',
                  baseline_inputs=current['baseline_inputs'], builder_adapter_sha256=current['builder_adapter_sha256'],
                  builder_sha256=current['builder_sha256'], source_HEAD_unchanged=True,
                  source_twelve_inputs_unchanged=True, all_prediction_inputs_unchanged=True,
                  inventory_sha256=sha(HERE / 'package-payload-inventory-v1.json'),
                  verification_script_sha256=sha(Path(__file__)),
                  prediction_sha256=sha(HERE / 'package-prediction-v1.json'),
                  full_product_suites='REUSED_425_INTEGRATION_PASS_NOT_RERUN', native_models_auth='NOT_ACCESSED')
    write(HERE / 'package-local-verification-v1.json', report)
    print(json.dumps(dict(status=report['status'], counts=report['regular_payloads'],
                         B_vs_S=bs, changed_from_0247=differences['B'])))


def install(arm, engine, metadata, inventories):
    folder = HERE / f'package-install-{arm.lower()}-{engine}-v1'
    folder.mkdir(exist_ok=False)
    work, home = folder / 'work', folder / 'home'
    work.mkdir(); home.mkdir()
    command(['git', 'init', '-q', '-b', 'main'], folder, 'git-init', work)
    command(['git', '-c', 'commit.gpgsign=false', 'commit', '--allow-empty', '-qm',
             'package installation fixture'], folder, 'git-baseline', work)
    argv = ['docker', 'run', '--rm', '--init', '--network', 'none', '--cap-drop', 'ALL',
            '--security-opt', 'no-new-privileges', '--env', 'HOME=/home/participant', '-w', '/work',
            '--mount', f'type=bind,src={work},dst=/work',
            '--mount', f'type=bind,src={home},dst=/home/participant',
            '--mount', f'type=bind,src={HERE / "package-payload-v1" / arm},dst=/install,readonly',
            IMAGE, 'node', '/install/package/bin/devlyn.js', '-y']
    if engine == 'claude': argv.append('--claude')
    run = command(argv, folder, 'installer')
    roots = ['.agents/skills'] + (['.claude/skills'] if engine == 'claude' else [])
    expected = {p.removeprefix('package/config/skills/'): row for p, row in inventories[arm].items()
                if p.startswith('package/config/skills/')}
    installed = {}
    for skills in roots:
        actual = {str(p.relative_to(work / skills)): dict(sha256=sha(p), mode=p.stat().st_mode & 0o777, bytes=p.stat().st_size)
                  for p in (work / skills).rglob('*') if p.is_file() and p.name != '.devlyn-install.json'}
        assert actual == expected, (arm, engine, skills)
        marker = read(work / skills / '.devlyn-install.json')
        assert marker['schemaVersion'] == 1 and marker['package'] == 'devlyn-cli' and marker['version'] == '4.2.5'
        assert set(marker['skills']) == {'devlyn-ideate', 'devlyn-engines', '_shared'}
        assert not (work / skills / '_shared/peer.py').exists()
        if arm == 'B': assert not (work / skills / '_shared/pair.md').exists()
        if arm == 'S': assert sha(work / skills / '_shared/pair.md') == '34287e59aa0e32ba09dacb92115715466e1408de0f0620f92fb6ff2db1e9acc3'
        installed[skills] = actual
    agents = (work / 'AGENTS.md').read_text()
    template = (HERE / 'package-payload-v1' / arm / 'package/AGENTS.md').read_text().strip()
    assert template in agents and agents.count(metadata['trigger']) == (1 if arm == 'S' else 0)
    if engine == 'claude':
        assert (work / 'CLAUDE.md').read_text() == '@AGENTS.md\n'
        assert read(work / '.claude/settings.json')['env']['ENABLE_PROMPT_CACHING_1H'] == 'true'
    else:
        assert not (work / 'CLAUDE.md').exists() and not (work / '.claude').exists()
    assert not (work / '.devlyn/pair').exists()
    row = dict(arm=arm, engine=engine, status='PASS', installer=run,
               installed_roots=roots, installed_skill_files_per_root=len(expected),
               exact_installed_payloads=installed, root_instructions_sha256=sha(work / 'AGENTS.md'),
               root_instructions_match=True, marker_version='4.2.5', payload_bytes_modes_match=True,
               peer_helper_absent=True, S_guide_and_trigger_unchanged=(arm == 'S'),
               models_auth_network='NO_MODELS_NO_AUTH_NETWORK_NONE')
    write(folder / 'verification.json', row)
    return row


def installs():
    verify_inputs()
    local_report = read(HERE / 'package-local-verification-v1.json')
    assert local_report['status'] == 'PASS'
    metadata, inventories = read(PACKS / 'packages.json'), read(HERE / 'package-payload-inventory-v1.json')
    image = command(['docker', 'image', 'inspect', IMAGE, '--format', '{{.Id}}'], HERE, 'package-image-v1')
    assert (HERE / 'package-image-v1.stdout').read_text().strip() == IMAGE
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(install, a, e, metadata, inventories) for a in ('B', 'S') for e in ('claude', 'codex')]
        installations = [f.result() for f in futures]
    verify_inputs()
    for a in metadata['packages']:
        assert sha(PACKS / (a + '.tgz')) == metadata['packages'][a]['sha256']
    report = dict(local_report, installations=installations, installation_count=len(installations),
                  build=read(HERE / 'build-v1.json'), image=IMAGE, image_inspect=image,
                  inputs_before_and_after=read(HERE / 'package-prediction-v1.json')['inputs_before'],
                  completed_at=datetime.now(timezone.utc).isoformat(), source_mutations='NONE',
                  runtime_task_staging='NOT_PERFORMED')
    write(HERE / 'package-integrity-v1.json', report)
    print(json.dumps(dict(status='PASS', installations=len(installations),
                         report_sha256=sha(HERE / 'package-integrity-v1.json'),
                         packages=report['packages'], counts=report['regular_payloads'])))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['local', 'installs'])
    phase = parser.parse_args().phase
    (local if phase == 'local' else installs)()
