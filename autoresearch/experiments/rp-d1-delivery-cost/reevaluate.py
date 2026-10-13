"""Disclosed post-exposure correction: reevaluate.py <measured-output> <new-dest>.

Offline, read-only evaluation of sealed slots and verified local archives. No
cells, checks, reviewers or GitHub requests are run; raw evidence stays in place.
"""
import argparse
import hashlib
import importlib.util
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('summary_rpd1_reevaluate', HERE / 'summarize.py')
summary = importlib.util.module_from_spec(spec)
spec.loader.exec_module(summary)
github = summary.github
read, write, require = github.read, github.write, github.require
locate = summary.runner.load('locate_rpd1_reevaluate', HERE.parent / '0233/locate.py')
packet = summary.runner.prepare.base.packet


def census(root):
    """Hash every file, including Git/ignored files; hash links without following them."""
    files = {}
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            entry = dict(type='symlink', sha256=hashlib.sha256(os.fsencode(path.readlink())).hexdigest())
        elif path.is_dir():
            continue
        else:
            entry = dict(type='file', **github.record_file(path))
        files[str(path.relative_to(root))] = entry
    return files


def sealed_selection(output, record):
    slot = record['cell']
    out = output / slot
    inherited_path = github.safe_file(output, f'verdict-{slot}.json')
    require(github.digest(inherited_path) == record['inherited_verdict_sha256'],
            slot + ': inherited verdict binding changed')
    inherited = read(inherited_path)
    manifest_path = github.safe_file(out, 'evidence.manifest.json')
    require(inherited['teardown'] == 'CLEAN' and
            github.digest(manifest_path) == inherited['evidence_manifest_sha256'],
            slot + ': evidence seal binding changed')
    manifest = read(manifest_path)
    require(not manifest['failures'] and bool(manifest['files']), slot + ': incomplete evidence seal')
    for name, expected in manifest['files'].items():
        require(github.digest(github.safe_file(out, name)) == expected, slot + ': sealed evidence changed')
    checked = read(github.safe_file(out, 'checked.json'))
    require(checked['snapshot'] == packet.tree(out / 'snapshot') and
            checked['checks_sha256'] == github.digest(out / 'checks.json'),
            slot + ': checked snapshot/checks changed')
    return inherited


def reevaluate(output, dest):
    output, dest = output.resolve(), dest.resolve()
    require(output.is_dir(), 'measured output is not a directory')
    require(not dest.is_relative_to(output) and not output.is_relative_to(dest),
            'destination and measured output must not overlap')
    require(not dest.exists(), 'destination must be new')
    before = census(output)
    evaluators = {str(Path(module.__file__).resolve().relative_to(HERE.parent)):
                  github.digest(Path(module.__file__))
                  for module in (summary, summary.runner, github, locate, packet, packet.base)}
    evaluators[str(Path(__file__).resolve().relative_to(HERE.parent))] = github.digest(Path(__file__))
    dest.mkdir(parents=True)
    report = dict(schema='rp-d1-reevaluation-v1', deviation='post-exposure Git-mode reconciliation correction',
                  measured_output=str(output), status='FAILED', slots=[], evaluator_sha256=evaluators)
    results = {}
    try:
        for record in summary.measured_records(output):
            slot = record['cell']
            archive = github.safe_file(output, 'archives/' + slot)
            if (not record['dispatched'] or record['status'] not in ('ADJUDICATE', 'PRODUCT_INCOMPLETE')
                    or not archive.exists()):
                continue
            out = github.safe_file(output, slot)
            # done_check also verifies this archive before reading its facts.
            github.verify_archive(archive)
            require(github.digest(archive / 'manifest.json') == record['archive']['manifest_sha256'],
                    slot + ': archive manifest binding changed')
            inherited = sealed_selection(output, record)
            original = summary.checklist_for(output, slot)
            done = github.done_check(out, archive, inherited['snapshot'], locate, packet, review=None)
            # Match the runner's status composition: this correction cannot erase
            # independent product/protocol failures from the inherited evaluator.
            if inherited['status'] == 'PRODUCT_INCOMPLETE':
                done['status'] = 'PRODUCT_INCOMPLETE'
                done['failures'].append('inherited product incomplete')
            inputs = {name: entry['sha256'] for name, entry in before.items()
                      if name.startswith((slot + '/', 'archives/' + slot + '/')) or
                      name in ('rp-schedule.json', f'verdict-{slot}.json')}
            report['slots'].append(dict(cell=slot,
                original=dict(status=record['status'], facts=original['facts']),
                corrected=dict(status=done['status'], facts=done['checklist']['facts']),
                input_sha256=inputs, evaluator_sha256=evaluators))
            results[slot] = done
    except (OSError, ValueError, KeyError, TypeError, github.EvidenceError) as exc:
        report['error'] = str(exc)
        raise
    finally:
        after = census(output)
        report['raw_census'] = dict(before=before, after=after, unchanged=before == after)
        write(dest / 'reevaluation.json', report)
        require(before == after, 'measured output changed during reevaluation')
    for slot, done in results.items():
        (dest / slot).mkdir()
        write(dest / slot / 'github-delivery.json', done)
        write(dest / slot / 'report-checklist.json', done['checklist'])
    report['status'] = 'COMPLETE'
    write(dest / 'reevaluation.json', report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('dest', type=Path)
    args = parser.parse_args(argv)
    try:
        report = reevaluate(args.output, args.dest)
    except (OSError, ValueError, KeyError, TypeError, github.EvidenceError) as exc:
        parser.exit(2, 'rp-d1 reevaluation: ' + str(exc) + '\n')
    print(f"Reevaluated {len(report['slots'])} slots; raw census unchanged.")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
