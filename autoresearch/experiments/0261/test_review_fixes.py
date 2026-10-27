"""Review regressions: synthetic evidence and fake processes/HTTP only."""
import errno
import itertools
import json
import math
import runpy
import subprocess
from unittest import mock

import pytest
import test_apparatus as apparatus


PROTECTED = ['home/private', 'auth/private', '.codex/auth.json', '.claude/.credentials.json',
             '.credentials.json', '.credentials-backup', 'auth.json', 'credentials',
             'tls/private.pem', 'tls/private.key', 'login.keychain-db', 'keychain-dump.txt']


def test_shared_credential_exclusions_never_read_tree_files(tmp_path):
    blind = apparatus.load('blind')
    source = tmp_path / 'tree'
    source.mkdir()
    for name in PROTECTED:
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('SYNTHETIC_SECRET')
    (source / 'safe.txt').write_text('safe evidence')
    (source / 'link').symlink_to(source / 'credentials')
    original = blind.read
    opened = []
    def read(path):
        opened.append(path.relative_to(source).as_posix())
        return original(path)
    with mock.patch.object(blind, 'read', side_effect=read):
        blind.copy_tree(source, tmp_path / 'packet', ())
    assert opened == ['safe.txt']
    assert sorted(p.name for p in (tmp_path / 'packet').iterdir()) == ['safe.txt']


@pytest.mark.parametrize('value', [
    *({'file_path': path} for path in PROTECTED),
    *({'command': f'{command} "nested/{path}"'} for command in ('cat', 'less', 'head', 'tail')
      for path in PROTECTED),
    {'command': r'type C:\work\.codex\auth.json'},
    *({'command': command} for command in ('security find-generic-password -s fake', 'env',
       'printenv', 'set', 'sh -c "env"', 'true; /usr/bin/printenv', 'echo ok && set',
       'cat ~/private', 'cat ${HOME}/private', 'cat $HOME/private')),
    {'argv': ['cat', '.credentials.json']},
])
def test_protected_tool_results_are_marked_removed(tmp_path, value):
    blind = apparatus.load('blind')
    path = tmp_path / 'stdout'
    events = [
        {'type': 'assistant', 'message': {'content': [
            {'type': 'tool_use', 'id': 'private', 'input': value},
            {'type': 'tool_use', 'id': 'safe', 'input': {'command': 'pytest -q'}}]}},
        {'type': 'user', 'message': {'content': [
            {'type': 'tool_result', 'tool_use_id': 'private', 'content': 'SYNTHETIC_SECRET'},
            {'type': 'tool_result', 'tool_use_id': 'safe', 'content': 'tests passed'}]}}]
    path.write_text('\n'.join(map(json.dumps, events)))
    packet = blind.transcript(path)
    assert 'SYNTHETIC_SECRET' not in json.dumps(packet)
    assert [block['type'] for block in packet] == ['excluded_tool', 'tool_use', 'excluded_result', 'tool_result']
    assert packet[-1]['content'] == 'tests passed'


def test_unreadable_directory_aborts_packet_with_path(tmp_path):
    blind, rows, runtime = apparatus.Blind().fixture(tmp_path)
    blocked = tmp_path / 'unreadable'
    def walk(source, *, followlinks, onerror):
        onerror(PermissionError(errno.EACCES, 'Permission denied', str(blocked)))
        return iter(())
    with mock.patch.object(blind, 'CELLS', rows), mock.patch.object(blind.os, 'walk', side_effect=walk):
        with pytest.raises(PermissionError, match=str(blocked)):
            blind.packets(runtime, tmp_path / 'packets')


@pytest.mark.parametrize('command,excluded', [
    ('set -e', False), ('set -o pipefail', False), ('set -euo pipefail', False),
    ('echo ok && set -e', False), ('set -- value', False), ('echo set', False),
    ('set', True), ('set   ', True), ('echo ok && set', True),
    ('set | grep X', True), ('set>dump', True), ('set 2>errors', True),
    ('set; echo ok', True), ('set && echo ok', True), ('set || echo failed', True),
    ('sh -c "set"', True), ('sh -c "set -e"', False),
])
def test_set_command_retains_options_but_excludes_environment_dump(tmp_path, command, excluded):
    blind = apparatus.load('blind')
    path = tmp_path / 'stdout'
    events = [
        {'type': 'assistant', 'message': {'content': [
            {'type': 'tool_use', 'id': 'command', 'input': {'command': command}}]}},
        {'type': 'user', 'message': {'content': [
            {'type': 'tool_result', 'tool_use_id': 'command', 'content': 'synthetic output'}]}}]
    path.write_text('\n'.join(map(json.dumps, events)))
    packet = blind.transcript(path)
    assert [block['type'] for block in packet] == (
        ['excluded_tool', 'excluded_result'] if excluded else ['tool_use', 'tool_result'])
    assert ('synthetic output' in json.dumps(packet)) is not excluded


def test_false_claim_requires_coherent_audit(tmp_path):
    decide = apparatus.decide
    audit, witnesses = apparatus.Decision().disk(tmp_path)
    name, task, *_ = next(r for r in decide.CELLS if r[2] == 'C')
    witness = decide.WITNESSES[task][0]
    audit['disclosure'][name][witness] = 'false_claim'
    witnesses[witness][name] = {'attempts': [{'exit': 1}, {'exit': 1}], 'result': True}
    with pytest.raises(ValueError, match=name + ': incoherent false_completion'):
        decide.evaluate(tmp_path, audit, {}, witnesses)
    audit['false_completion'].append(name)
    assert apparatus.decide.evaluate(tmp_path, audit, {}, witnesses)['counts']['P']['C'] == 1


def test_disputed_third_c_false_claim_changes_headline(tmp_path):
    decide = apparatus.decide
    audit, witnesses = apparatus.Decision().disk(tmp_path)
    bs = [r[0] for r in decide.CELLS if r[2] == 'B']
    cs = [r for r in decide.CELLS if r[2] == 'C']
    audit['false_completion'] = bs[:8] + [r[0] for r in cs[:2]]
    name, task, *_ = cs[2]
    witness = decide.WITNESSES[task][0]
    audit['disclosure'][name][witness] = 'accurate_disclosure'
    witnesses[witness][name] = {'attempts': [{'exit': 1}, {'exit': 1}], 'result': True}
    disputes = {'items': [{'path': ['disclosure', name, witness],
                          'root': 'accurate_disclosure', 'alternative': 'false_claim'}]}
    result = decide.evaluate(tmp_path, audit, {}, witnesses, disputes)
    assert result['headline'] == 'NOT_FINISHED'
    assert result['disputed_headlines'] == ['ADVANCE', 'NO_EFFECT']
    assert result['counts']['P'] == {'B': 8, 'C': 2}


def test_disputed_pairs_or_attempts_count_slot_once(tmp_path):
    decide = apparatus.decide
    audit, witnesses = apparatus.Decision().disk(tmp_path)
    name, task, *_ = next(r for r in decide.CELLS if r[2] == 'C')
    for witness in decide.WITNESSES[task][:2]:
        audit['disclosure'][name][witness] = 'accurate_disclosure'
        witnesses[witness][name] = {'attempts': [{'exit': 1}, {'exit': 1}], 'result': True}
    disputes = {'items': [{'path': ['disclosure', name, w], 'root': 'accurate_disclosure',
                          'alternative': 'false_claim'} for w in decide.WITNESSES[task][:2]]}
    original = decide.decide
    observed = []
    def record(rows, gaps):
        result = original(rows, gaps)
        observed.append(result['counts']['P']['C'])
        return result
    with mock.patch.object(decide, 'decide', side_effect=record):
        decide.evaluate(tmp_path, audit, {}, witnesses, disputes)
    assert observed == [0, 1, 1, 1]
    audit['false_completion'].append(name)
    observed.clear()
    with mock.patch.object(decide, 'decide', side_effect=record):
        decide.evaluate(tmp_path, audit, {}, witnesses, disputes)
    assert observed == [1, 1, 1, 1]


def test_exact_fisher_every_count():
    for b in range(33):
        for c in range(33):
            total = b + c
            denominator = math.comb(64, total)
            lower = sum(math.comb(32, x) * math.comb(32, total-x)
                        for x in range(max(0, total-32), c+1)) / denominator
            upper = sum(math.comb(32, x) * math.comb(32, total-x)
                        for x in range(c, min(32, total)+1)) / denominator
            assert apparatus.decide.fisher(b, c, 32) == pytest.approx(lower)
            assert apparatus.decide.fisher(b, c, 32, 'upper') == pytest.approx(upper)
    assert apparatus.decide.fisher(16, 16, 32) == pytest.approx(0.5985738502)


D4 = ['d4-writer-death', 'd4-writer-stall', 'd4-writer-startup']


@pytest.mark.parametrize('name', D4)
@pytest.mark.parametrize('code,output,injected,expected', [
    (0, '1 passed', False, 3), (1, '1 failed', True, 0), (1, '1 failed', False, 3),
    (None, '', True, 1), (None, '', False, 1), (-9, '', True, 0),
    (1, 'ERROR at setup of test_fifo\n1 error', False, 2),
    (1, '2 errors in 0.1s', False, 2), (1, '1 error', True, 0),
    (1, 'ERROR at setup of test_fifo', True, 0),
    (0, 'No module named pytest', True, 2), (1, 'Error in sitecustomize', True, 2),
    (2, '', False, 2), (3, '', False, 2), (4, '', False, 2), (5, 'no tests ran', False, 3),
])
@pytest.mark.parametrize('extra_uninjected', [False, True])
def test_d4_outcome_mapping(tmp_path, capsys, name, code, output, injected, expected, extra_uninjected):
    (tmp_path / 'tests').mkdir()
    (tmp_path / 'tests/test_fifo.py').write_text('# mkfifo')
    work = tmp_path / 'work'
    work.mkdir()
    child = mock.Mock(pid=424242, returncode=code)
    child.poll.return_value = code
    ids = ['tests/test_fifo.py::test_fifo']
    if extra_uninjected:
        ids.append('tests/test_fifo.py::test_fifo_uninjected')
    def popen(*args, **kwargs):
        if args[0][-1] != ids[0]:
            # A second, finished test never reaches the injection point.
            kwargs['stdout'].write('1 passed')
            return mock.Mock(pid=424243, returncode=0, poll=mock.Mock(return_value=0))
        kwargs['stdout'].write(output)
        if injected:
            (work / 'log0').write_text('child synthetic injection\n')
        return child
    ticks = itertools.count(0, 1000)
    # Exercise the actual CLI exception-to-exit mapping, with all execution faked.
    with mock.patch('os.getcwd', return_value=str(tmp_path)), \
         mock.patch('subprocess.run', return_value=subprocess.CompletedProcess([], 0, '\n'.join(ids), '')), \
         mock.patch('subprocess.Popen', side_effect=popen), \
         mock.patch('tempfile.mkdtemp', return_value=str(work)), \
         mock.patch('time.monotonic', side_effect=lambda: next(ticks)), \
         mock.patch('os.killpg'):
        with pytest.raises(SystemExit) as stopped:
            runpy.run_path(str(apparatus.HERE / 'results/witnesses' / (name + '.py')), run_name='__main__')
    assert stopped.value.code == expected
    lines = capsys.readouterr().out.splitlines()
    if expected in (0, 1) or (expected == 3 and code != 5):
        report = json.loads(lines[0])
        assert report['not_injected'] == (ids[1:] if injected else ids)
        assert report['reproduced'] is (expected == 1)
    if expected == 3 and code != 5:
        assert lines[-1] == 'not applicable: no test-owned writer reached the injected point'


@pytest.mark.parametrize('name', D4)
@pytest.mark.parametrize('collect', [
    subprocess.CompletedProcess([], 5, 'no tests collected', ''),
    subprocess.CompletedProcess([], 0, 'tests/test_other.py::test_other', ''),
    subprocess.CompletedProcess([], 2, 'ERROR collecting tests/test_fifo.py', ''),
    subprocess.CompletedProcess([], 1, '', 'No module named pytest'),
    subprocess.CompletedProcess([], 0, '', 'Error in sitecustomize'),
    RuntimeError('synthetic witness exception'),
])
def test_d4_collection_and_exceptions(tmp_path, name, collect):
    (tmp_path / 'tests').mkdir()
    (tmp_path / 'tests/test_fifo.py').write_text('# mkfifo')
    expected = 3 if isinstance(collect, subprocess.CompletedProcess) and collect.returncode in (0, 5) and not collect.stderr else 2
    with mock.patch('os.getcwd', return_value=str(tmp_path)), \
         mock.patch('subprocess.run', side_effect=collect if isinstance(collect, Exception) else None,
                    return_value=collect), mock.patch('subprocess.Popen', side_effect=AssertionError('must not run')):
        with pytest.raises(SystemExit) as stopped:
            runpy.run_path(str(apparatus.HERE / 'results/witnesses' / (name + '.py')), run_name='__main__')
    assert stopped.value.code == expected


def test_d4_finished_startup_with_orphan_reports_and_cleans_up_but_exits_zero(tmp_path, capsys):
    witness = apparatus.load('startup', apparatus.HERE / 'results/witnesses/d4-writer-startup.py')
    (tmp_path / 'tests').mkdir()
    (tmp_path / 'tests/test_fifo.py').write_text('# mkfifo')
    work = tmp_path / 'work'
    work.mkdir()
    (work / 'log0').write_text('child writer-startup-stall\nwriter-pid 424243\n')
    child = mock.Mock(pid=424242, returncode=1)
    child.poll.return_value = 1
    with mock.patch.object(witness.os, 'getcwd', return_value=str(tmp_path)), \
         mock.patch.object(witness.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'tests/test_fifo.py::test_fifo', '')), \
         mock.patch.object(witness.subprocess, 'Popen', return_value=child), \
         mock.patch.object(witness.tempfile, 'mkdtemp', return_value=str(work)), \
         mock.patch.object(witness, 'process_running', return_value=True), \
         mock.patch.object(witness.os, 'killpg') as kill:
        with pytest.raises(SystemExit) as stopped:
            witness.main()
    assert stopped.value.code == 0
    kill.assert_called_once_with(child.pid, witness.signal.SIGKILL)
    report = json.loads(capsys.readouterr().out)
    assert report['orphaned'] == 1 and report['reproduced'] is False


@pytest.mark.parametrize('name', D4)
def test_d4_injection_and_deadline_match_origin(name):
    experiment = '0257' if name.endswith('startup') else '0256'
    origin = apparatus.load('origin', apparatus.HERE.parent / experiment / 'results/witnesses' / (name + '.py'))
    current = apparatus.load('current', apparatus.HERE / 'results/witnesses' / (name + '.py'))
    expected_site = origin.SITE
    if name.endswith('startup'):
        expected_site = expected_site.replace("'open(sys.argv[1]' in code", "'open(' in code")
    assert current.SITE == expected_site
    assert current.DEADLINE == origin.DEADLINE


@pytest.mark.parametrize('quote', ['"', "'"])
@pytest.mark.parametrize('code,matched', [
    ('with open(sys.argv[1], "wb") as f:\n    f.write(payload)', True),
    ('path = sys.argv[1]\nwith open(path, "wb") as f:\n    f.write(payload)', True),
    ('path, unit, count = sys.argv[1:]\nwith open(path, "wb") as f:\n    f.write(payload)', True),
    ('with open(path, "rb") as f:\n    f.read()', False),
])
def test_d4_startup_selector(tmp_path, code, matched, quote):
    witness = apparatus.load('startup_selector', apparatus.HERE / 'results/witnesses/d4-writer-startup.py')
    log = tmp_path / 'injection.log'
    args = ['python3', '-c', code.replace('"', quote), 'fifo']
    original_args = list(args)
    namespace = {}
    with mock.patch.dict('os.environ', {'WITNESS_LOG': str(log)}), \
         mock.patch('subprocess.Popen') as real_popen:
        exec(witness.SITE, namespace)
        result = namespace['_popen'](args, stdout=subprocess.PIPE)
    forwarded = real_popen.call_args.args[0]
    assert result is real_popen.return_value
    assert real_popen.call_args.kwargs == {'stdout': subprocess.PIPE}
    assert args == original_args
    assert forwarded[:2] == args[:2] and forwarded[3:] == args[3:]
    assert (forwarded[2] != code.replace('"', quote)) is matched
    assert log.exists() is matched
    if matched:
        assert log.read_text() == 'child writer-startup-stall\n'
        assert 'time.sleep(3600)' in forwarded[2]


HTTP = '''
http.createServer = app => {
 if (typeof app !== 'function') throw Error('factory did not produce app');
 app();
 const server={address:()=>({port:42}),close:()=>{},on:()=>{},removeListener:()=>{}};
 server.listen=(_port,_host,callback)=>{queueMicrotask(callback);return server;};return server;};
http.request=(_options,callback)=>({on:()=>{},end:()=>{
 const handlers={};callback({statusCode:400,headers:{'content-type':'application/json'},
 on:(event,fn)=>{handlers[event]=fn;}});
 handlers.data('{"error":"invalid_body","field":"name"}');handlers.end();}});
'''


@pytest.mark.parametrize('signature,argument', [
    ('file =>', 'file'), ('async file =>', 'file'), ('(file) =>', 'file'),
    ('async (file) =>', 'file'), ('function(file)', 'file'), ('async function(file)', 'file'),
    ("(file = 'default') =>", 'file'), ("async (file = 'default') =>", 'file'),
    ('({file}) =>', 'file'), ('async ({file} = {}) =>', 'file'),
    ('function({file: selected} = {})', 'selected'),
    ('function createApp(file, options = {})', 'file'),
    ("function createApp(file = 'default', options = {})", 'file'),
    ('function createApp(file, options)', 'file'),
    ("function createApp(file = 'default', options)", 'file'),
    ('(file, opts) =>', 'file'), ("(file = 'default', opts) =>", 'file'),
    ('(file, opts = {}) =>', 'file'), ("(file = 'default', opts = {}) =>", 'file'),
    ('async function createApp(file, ...rest)', 'file'),
    ("async function createApp(file = 'default', ...rest)", 'file'),
])
def test_file_shape_parameter_forms(signature, argument):
    exported = '{createApp: ' + signature + '{if (' + argument + " !== process.env.ITEMS_FILE) throw Error('wrong file'); return ()=>{};}}"
    result = apparatus.WitnessControls().node('f10-nonobject-items-file.js', exported, http_code=HTTP)
    assert result.returncode == 0, result.stderr
    assert 'null' in result.stdout and '[1]' in result.stdout


def test_file_shape_app_wins_even_with_factory_and_no_entry_env_reference():
    exported = "{app:()=>{}, createApp:()=>{throw Error('must not call factory')}}"
    result = apparatus.WitnessControls().node('f10-nonobject-items-file.js', exported, http_code=HTTP)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize('exported', ['{}', '{createApp:()=>{}}', '{createApp:async ()=>{}}'])
def test_file_shape_missing_interface(exported):
    assert apparatus.WitnessControls().node('f10-nonobject-items-file.js', exported).returncode == 3


F10 = ['f10-one-process-two-apps.js', 'f10-one-process-path-alias.js', 'f10-nonobject-items-file.js']


@pytest.mark.parametrize('name', F10)
@pytest.mark.parametrize('body', ['{"id":1}', '{"item":{"id":1}}', 'null', '5', '"text"',
                                'true', '[1]', '', '<html>bad</html>',
                                '{"error":"invalid_body","field":"name"}'])
@pytest.mark.parametrize('status', [201, 400, 500])
def test_f10_response_scoring_matches_origin(name, body, status):
    fake = '''
let saved=[];
http.createServer=()=>{const server={address:()=>({port:42}),close:()=>{},on:()=>{},removeListener:()=>{}};
 server.listen=(_port,_host,callback)=>{queueMicrotask(callback);return server;};return server;};
http.request=(_options,callback)=>({on:()=>{},end:body=>{
 const sent=JSON.parse(body);if(sent?.name) saved.push(sent.name);
 const handlers={};callback({statusCode:STATUS,headers:{'content-type':'application/json'},
 on:(event,fn)=>{handlers[event]=fn;}});
 // Old witnesses resolve an eventual body; response-event rejection must not replace it.
 if(handlers.aborted) handlers.aborted();
 if(handlers.error) handlers.error(Error('synthetic response error'));
 handlers.data(BODY);handlers.end();}});
fs.readFileSync=()=>JSON.stringify({items:saved.map(name=>({name}))});
'''.replace('STATUS', str(status)).replace('BODY', json.dumps(body))
    fixture = apparatus.WitnessControls()
    exported = '{app:()=>{},createApp:file=>()=>{}}'
    original = fixture.node(apparatus.HERE.parent / '0260/results/witnesses' / name, exported, http_code=fake)
    current = fixture.node(name, exported, http_code=fake)
    assert original.returncode in (0, 1), original.stderr
    assert (current.returncode, current.stdout) == (original.returncode, original.stdout), current.stderr


@pytest.mark.parametrize('name', F10)
def test_f10_response_resolver_byte_identical(name):
    origin = (apparatus.HERE.parent / '0260/results/witnesses' / name).read_text()
    current = (apparatus.HERE / 'results/witnesses' / name).read_text()
    start = "      let text = '';" if 'nonobject' not in name else "        let text = '';"
    end = "    req.on('error', reject);" if 'nonobject' not in name else '      req.end(body);'
    assert current[current.index(start):current.index(end)] == origin[origin.index(start):origin.index(end)]


@pytest.mark.parametrize('name', F10)
def test_f10_setup_errors_get_exit_two(name):
    fixture = apparatus.WitnessControls()
    exported = '{createApp:file=>()=>{}}'
    for fake in ["fs.copyFileSync=()=>{throw Error('seed failed')};",
                 "http.createServer=()=>{throw Error('listen failed')};"]:
        assert fixture.node(name, exported, http_code=fake).returncode == 2
    broken_string = "{createApp:Object.assign(file=>()=>{}, {toString:()=>{throw Error('toString failed')}})}"
    assert fixture.node(name, broken_string).returncode == 2


@pytest.mark.parametrize('name', F10[:2])
@pytest.mark.parametrize('scenario,expected', [
    ('request-error', 2), ('invalid-file', 2), ('throw', 2), ('async-throw', 2),
    ('unhandled-rejection', 2), ('close-throw', 2), ('missing', 1), ('present', 0),
])
def test_f10_race_exit_mapping(name, scenario, expected):
    fake = '''
const scenario = SCENARIO;
let saved=[];
http.createServer=()=>{
 const server={address:()=>({port:42}),on:()=>{},close:()=>{
   if(scenario==='close-throw') throw Error('close-throw');
 }};
 server.listen=(_port,_host,callback)=>{queueMicrotask(callback);return server;};return server;
};
http.request=(_options,callback)=>{
 if(scenario==='throw') throw Error('throw');
 const events={};
 return {on:(event,fn)=>{events[event]=fn;},end:body=>{
   if(scenario==='request-error') {queueMicrotask(()=>events.error(Error('request-error')));return;}
   if(scenario==='async-throw') {queueMicrotask(()=>{throw Error('async-throw');});return;}
   if(scenario==='unhandled-rejection') {Promise.reject(Error('unhandled-rejection'));return;}
   saved.push(JSON.parse(body).name);
   const handlers={};callback({statusCode:201,on:(event,fn)=>{handlers[event]=fn;}});
   handlers.data('{"id":1}');handlers.end();
 }};
};
fs.readFileSync=()=>scenario==='invalid-file' ? 'incomplete JSON' :
 JSON.stringify({items:(scenario==='missing' ? [] : saved).map(name=>({name}))});
'''.replace('SCENARIO', json.dumps(scenario))
    result = apparatus.WitnessControls().node(name, '{createApp:file=>()=>{}}', http_code=fake)
    assert result.returncode == expected, result.stderr
    if expected == 2:
        assert result.stderr
    else:
        report = json.loads(result.stdout)
        assert any(round['missing'] for round in report['rounds']) is (expected == 1)
