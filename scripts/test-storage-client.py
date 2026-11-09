#!/usr/bin/env python3
"""Stdlib protocol/authentication tests. Fake peers are not native interop proof.

The OS prerequisite supplies cross-language vectors and their release digest.
The shared fixture package is copied verbatim from the merged Rust prerequisite.
Socket-pair peers below remain unit tests, not native interop proof.
"""
from __future__ import annotations

import ast
import contextlib
import ctypes
import errno
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import runpy
import shlex
import socket
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
PACKAGED = '--package-root' in sys.argv
if PACKAGED:
    offset = sys.argv.index('--package-root')
    ROOT = Path(sys.argv[offset + 1]).resolve()
    del sys.argv[offset:offset + 2]
FIXTURES = Path(__file__).resolve().parent / 'fixtures'
SHARED = ROOT / "config/skills/_shared"
# With --package-root this imports from the installed release; cached bytecode written
# there would no longer match release.json for the next suite that verifies it.
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("storage_client", SHARED / "storage-client.py")
client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client)
REFUSAL = client.StorageRefusal


def write_retirement(home):
    """Rust-shaped completed unenroll evidence bound to this native lifecycle."""
    root = home / '.devlyn'
    root.mkdir(exist_ok=True)
    (root / 'storage-client-recovery').mkdir(exist_ok=True)
    (root / 'storage-client.lock').touch(exist_ok=True)
    fence = {'schema': 1, 'operation_id': client.operation_id(),
             'root_identity': client.persistent_identity(root),
             'lock_identity': client.persistent_identity(root / 'storage-client.lock')}
    journal = {**fence, 'retired': True, 'archives': []}
    (root / 'storage-client-fence.json').write_text(json.dumps(fence), encoding='utf-8')
    (root / 'storage-client-unenroll.json').write_text(json.dumps(journal), encoding='utf-8')
    return journal


def write_recovery_pins(home, record):
    """Current Rust-shaped pins, with a private, hashable runtime closure."""
    root = home / '.devlyn'
    runtime = root / 'runtime'
    runtime.mkdir(exist_ok=True)
    node = runtime / 'node'
    node.write_bytes(b'verified runtime fixture')
    pins = {'schema': 1, 'enrollment': json.loads(json.dumps(record)),
            'runtime': {'path': str(runtime), 'identity': client.persistent_identity(runtime),
                        'sha256': client.package_digest(runtime)}, 'node': str(node)}
    path = root / 'storage-client-recovery/pins.json'
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(pins))
    return path


def load_cross_language_golden_vectors(directory=FIXTURES / "storage-protocol-1"):
    try:
        paths = sorted(p for p in directory.rglob('*') if p.is_file() and p.name not in {'SHA256SUMS', 'DIGEST'})
        sums = ''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(directory).as_posix()+'\n' for p in paths).encode()
        digest = hashlib.sha256(sums).hexdigest()
        client.require(sums == (directory/'SHA256SUMS').read_bytes(), 'vector inventory or hashes changed', 'storage_unsupported')
        client.require((directory/'DIGEST').read_bytes() == (digest+'\n').encode()
                       and digest == '715f7562a489c1976ba483549c41e6c915f124e746fc307ce8e3d32701b5ad3f',
                       'unverified protocol package', 'storage_unsupported')
        return json.loads((directory/'manifest.json').read_bytes())
    except OSError as exc:
        raise REFUSAL('storage_unsupported', str(exc)) from exc


def frame(kind="hello", value=None, **extra):
    if value is None:
        value = {"storage_protocol": 1, "schema": 2, "capabilities": ["reserve", "leaf_leases"]}
    return json.dumps({"ok": {"kind": kind, "value": value}, **extra}, ensure_ascii=False).encode()+b"\n"


def error(code="busy", message="private diagnostic"):
    return json.dumps({"error": {"code": code, "message": message}}).encode()+b"\n"


class Peer:
    """Socket-pair peer with a fake pathname/connect boundary.

    Uses real selectors, byte I/O and kernel uid/pid/start authentication without
    requiring sandbox permission to bind a pathname. Not endpoint-path proof.
    """

    def __init__(self, root, responses):
        self.root, self.responses = root, responses
        self.requests, self.errors = [], []
        root.chmod(0o700)
        self.pairs = [socket.socketpair() for _ in range(max(1, len(responses)))]
        self.clients = iter(a for a, _ in self.pairs)
        self.thread = threading.Thread(target=self.serve, daemon=True)
        self.patches = contextlib.ExitStack()

    def serve(self):
        try:
            for (_, stream), response in zip(self.pairs, self.responses):
                with stream:
                    stream.settimeout(0.5)
                    if callable(response):
                        response(stream)
                        continue
                    data = bytearray()
                    while b"\n" not in data:
                        part = stream.recv(65536)
                        if not part:
                            break
                        data.extend(part)
                    self.requests.append(bytes(data))
                    stream.sendall(response)
        except (OSError, AssertionError) as exc:
            self.errors.append(exc)

    def __enter__(self):
        original_lstat = Path.lstat
        endpoint = self.root/"control.sock"
        def lstat(path, *args, **kwargs):
            if path == endpoint:
                import stat
                return SimpleNamespace(st_mode=stat.S_IFSOCK | 0o600, st_uid=os.geteuid(), st_dev=1, st_ino=2)
            return original_lstat(path, *args, **kwargs)
        class Connected:
            def __init__(self, stream):
                self.stream = stream
            def connect_ex(self, path):
                return 0
            def __getattr__(self, name):
                return getattr(self.stream, name)
        self.connection_type = Connected
        self.patches.enter_context(patch.object(Path, "lstat", lstat))
        self.patches.enter_context(patch.object(client.socket, "socket", side_effect=lambda *args: Connected(next(self.clients))))
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.thread.join(2)
        self.patches.close()
        for a, b in self.pairs:
            a.close()
            b.close()
        assert not self.thread.is_alive(), "fake peer failed to stop"
        assert not self.errors, self.errors


class FakePipeAPI:
    def __init__(self, response=None, *, early=False, stalled=False, fail_write=False):
        self.response = response or frame()
        self.early, self.stalled, self.fail_write = early, stalled, fail_write
        self.written = bytearray()
        self.closed, self.finished = [], []
        self.operations = []
        self.snapshots = []
        self.read_polls = 0

    def directory(self, directory):
        return "C:\\Devlyn\\control", ("123", "00112233445566778899aabbccddeeff")

    def sid(self):
        return "S-1-5-21-123"

    def open_pipe(self, name, deadline):
        self.name = name
        return 27

    def server(self, handle):
        return self.snapshots.pop(0) if self.snapshots else (50, self.sid(), "windows:987654321")

    def start_io(self, handle, data=None):
        if data is not None and self.fail_write:
            raise BrokenPipeError("early close")
        operation = {"data": data, "done": False}
        self.operations.append(operation)
        return operation

    def poll_io(self, handle, operation):
        if operation["data"] is not None:
            if self.stalled:
                return None
            self.written.extend(operation["data"])
            operation["done"] = True
            return len(operation["data"]), b""
        self.read_polls += 1
        if self.stalled or self.read_polls == 1 or (not self.early and not self.written):
            return None
        operation["done"] = True
        return len(self.response), self.response

    def finish_io(self, handle, operation, deadline):
        self.finished.append(operation)

    def close(self, handle):
        self.closed.append(handle)


class WireTests(unittest.TestCase):
    def test_wire_envelope_roundtrip(self):
        raw = client.encode_request({"op": "hello"})
        self.assertEqual(json.loads(raw), {"storage_protocol": 1, "request": {"op": "hello"}})
        self.assertEqual(client.decode_reply(frame(), "hello")["schema"], 2)

    def test_additive_reply_fields(self):
        value = {"storage_protocol": 1, "schema": 2, "capabilities": ["reserve"], "future": {"count": 3}}
        self.assertEqual(client.decode_reply(frame(value=value, future=True), "hello"), value)

    def test_negative_frames(self):
        bad = [b"", b"{}", b"{}\n{}\n", b"\xff\n", b"[]\n", b"{}\n", b"{\"ok\":{},\"error\":{}}\n",
               b'{"ok":{"kind":"hello","value":{"storage_protocol":true,"schema":2,"capabilities":[]}}}\n',
               b'{"ok":{"kind":"hello","value":{"storage_protocol":1,"storage_protocol":1,"schema":2,"capabilities":[]}}}\n',
               b'{"ok":{"kind":"hello","value":{"storage_protocol":1,"schema":2,"capabilities":[]}},"x":NaN}\n',
               b'{"ok":{"kind":"hello","value":{"storage_protocol":1,"schema":2,"capabilities":[]}},"x":1e999}\n',
               b'{"ok":{"kind":"hello","value":{"storage_protocol":1,"schema":2,"capabilities":["\\ud800"]}}}\n',
               frame(kind="cache"), frame(value={}), error(code=True), b"["*2000+b"\n"]
        for raw in bad:
            with self.subTest(raw=raw[:100]), self.assertRaises(REFUSAL):
                client.decode_reply(raw, "hello")

    def test_frame_limits_include_boundary_exclude_newline(self):
        request = {"op": "locate", "parent": "/", "entry": ""}
        base = len(client.encode_request(request))-1
        request["entry"] = "x"*(client.MAX_REQUEST-base)
        self.assertEqual(len(client.encode_request(request)), client.MAX_REQUEST+1)
        request["entry"] += "x"
        with self.assertRaises(REFUSAL):
            client.encode_request(request)
        base_frame = frame(padding="")
        raw = frame(padding="x"*(client.MAX_REPLY-len(base_frame)))
        self.assertEqual(len(raw), client.MAX_REPLY)
        client.decode_reply(raw, "hello")
        with self.assertRaises(REFUSAL):
            client.decode_reply(raw[:-1]+b"x\n", "hello")

    def test_unknown_request_fields_and_operations_refuse(self):
        for request in ({"op": "hello", "extra": True}, {"op": "fake"}, {"op": "lease"},
                        {"op": "release", "lease_id": "id", "descendants_reconciled": 1}):
            with self.subTest(request=request), self.assertRaises(REFUSAL):
                client.encode_request(request)

    def test_decimal_boundaries_and_bool_as_integer(self):
        for value in ("0", "1", str(2**64-1)):
            client.validate(value, "decimal")
        for value in (0, True, "00", "01", "+1", "-1", "1.0", str(2**64), "１", " 1"):
            with self.subTest(value=value), self.assertRaises(REFUSAL):
                client.validate(value, "decimal")
        client.validate({"pid": 42, "created": 2**64-1}, "consumer", windows=True)
        for value in (True, "42", 2**64):
            with self.assertRaises(REFUSAL):
                client.validate({"pid": 42, "created": value}, "consumer", windows=True)
        with self.assertRaises(REFUSAL):
            client.validate({"pid": True, "start": "linux:boot:1"}, "stamp")

    def test_reservation_decimal_wire_roundtrip(self):
        owner = {"repository": {"volume": "vol", "file": "id"}, "allocation_id": "alloc", "receipt": "/receipt"}
        plan = {"kind": "known", "writes": [{"parent": "/", "relative": "tree", "phase": "checkout", "bytes": str(2**64-1)}], "digest": "digest"}
        request = {"op": "reserve", "operation_id": "durable-id", "owner": owner, "plan": plan}
        self.assertEqual(json.loads(client.encode_request(request))["request"], request)
        value = {"reservation_id": "grant", "operation_id": "durable-id", "generation": "9", "boot_id": None,
                 "owner": owner, "holder": {"pid": 42, "start": "macos:1:2"}, "plan": plan,
                 "destinations": [], "pools": [{"id": "pool", "bytes": "18446744073709551615"}],
                 "volumes": [], "workers": [], "granted_at": "now", "released_at": None}
        self.assertEqual(client.decode_reply(frame("reservation", value), "reservation"), value)
        for generation in (9, True, "09"):
            with self.assertRaises(REFUSAL):
                client.decode_reply(frame("reservation", {**value, "generation": generation}), "reservation")

    def test_refusal_prose_never_contains_peer_diagnostics(self):
        for code, sentence in client.REFUSAL_TEXT.items():
            with self.subTest(code=code), self.assertRaises(REFUSAL) as raised:
                client.decode_reply(error(code, "SECRET /registry; rm -rf"), "hello")
            value = raised.exception
            self.assertEqual(str(value), sentence)
            self.assertNotIn("SECRET", str(value))
            self.assertIn("SECRET", value.result()["diagnostic"])
        with self.assertRaises(REFUSAL) as raised:
            client.decode_reply(error("future_error", "secret"), "hello")
        self.assertEqual(raised.exception.code, "storage_unavailable")
        self.assertFalse(raised.exception.retryable)

    def test_golden_loader_fails_closed_even_if_unverified_files_exist(self):
        with tempfile.TemporaryDirectory() as directory:
            for path in (Path(directory)/"absent", Path(directory)):
                with self.assertRaises(REFUSAL) as raised:
                    load_cross_language_golden_vectors(path)
                self.assertEqual(raised.exception.code, "storage_unsupported")


@unittest.skipIf(os.name == "nt", "Unix endpoint tests")
class UnixTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="sc-", dir="/tmp")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def test_authenticated_roundtrip_negotiates_hello_first(self):
        with Peer(self.root, [frame(), frame()]) as peer:
            result = client.Client(self.root).call({"op": "hello"})
            self.assertEqual(result["storage_protocol"], 1)
            # hello itself is returned after negotiation, no second request.
            with contextlib.closing(client.UnixStream(self.root, time.monotonic()+1)) as stream:
                self.assertEqual(stream.identity[0], os.getpid())
                raw = stream.exchange(client.encode_request({"op": "hello"}), time.monotonic()+1)
                client.decode_reply(raw, "hello")
        self.assertEqual([json.loads(r)["request"]["op"] for r in peer.requests], ["hello", "hello"])

    def test_foreign_or_reused_peer_gets_zero_bytes(self):
        for kind in ("foreign", "reused"):
            path = self.root / "control.sock"
            path.unlink(missing_ok=True)
            observed = []
            def read_empty(stream):
                observed.append(stream.recv(1))
            with Peer(self.root, [read_empty]):
                if kind == "foreign":
                    context = patch.object(client, "unix_peer", side_effect=REFUSAL("storage_unavailable", "foreign uid"))
                else:
                    context = patch.object(client, "unix_start", side_effect=["macos:1:2", "macos:1:3"])
                with context, self.assertRaises(REFUSAL):
                    client.Client(self.root).call({"op": "hello"})
            self.assertEqual(observed, [b""])

    def test_reuse_immediately_before_first_byte_gets_zero_bytes(self):
        observed = []
        with Peer(self.root, [lambda stream: observed.append(stream.recv(1))]):
            with contextlib.closing(client.UnixStream(self.root, time.monotonic()+1)) as stream:
                with patch.object(client, "unix_start", return_value="changed"), self.assertRaises(REFUSAL):
                    stream.exchange(client.encode_request({"op": "hello"}), time.monotonic()+1)
        self.assertEqual(observed, [b""])

    def test_busy_then_retry_same_request_bytes(self):
        response = frame("removal", {"removal_id": "r", "operation_id": "id", "supervisor": {"pid": 42, "start": "s"}, "entries": [], "finished_at": None})
        with Peer(self.root, [frame(), error(), frame(), response]) as peer:
            result = client.Client(self.root).call({"op": "finish_removal", "removal_id": "r"})
        self.assertEqual(result["removal_id"], "r")
        self.assertEqual(peer.requests[1], peer.requests[3])

    def test_early_busy_reply_survives_write_failure(self):
        done = threading.Event()
        def early(stream):
            stream.sendall(error())
            assert done.wait(1), "client failed to finish early reply"
        with Peer(self.root, [early]):
            try:
                with contextlib.closing(client.UnixStream(self.root, time.monotonic()+1)) as stream:
                    recv = stream.stream.recv
                    # Force the concurrent failure ordering, independent of
                    # socket buffering or the scheduler's ready-event order.
                    calls = iter((True, False))
                    def read(size):
                        if next(calls):
                            raise BlockingIOError()
                        return recv(size)
                    with patch.object(stream.stream, "recv", side_effect=read), \
                         patch.object(stream.stream, "send", side_effect=BrokenPipeError()) as send:
                        raw = stream.exchange(b"x"*client.MAX_REQUEST+b"\n", time.monotonic()+1)
                    self.assertEqual(send.call_count, 1)
            finally:
                done.set()
        with self.assertRaises(REFUSAL) as raised:
            client.decode_reply(raw, "hello")
        self.assertEqual(raised.exception.code, "storage_busy")

    def test_missing_capability_never_sends_operation(self):
        for value in ({"storage_protocol": 1, "schema": 2, "capabilities": []},
                      {"storage_protocol": 2, "schema": 2, "capabilities": ["reserve"]}):
            (self.root/"control.sock").unlink(missing_ok=True)
            with Peer(self.root, [frame(value=value)]) as peer, self.assertRaises(REFUSAL) as raised:
                client.Client(self.root).call({"op": "finish_removal", "removal_id": "r"})
            self.assertEqual(raised.exception.code, "storage_unsupported")
            self.assertEqual(len(peer.requests), 1)

    def test_leaf_lease_requires_capability_before_operation(self):
        value = {"storage_protocol": 1, "schema": 2, "capabilities": ["reserve"]}
        with Peer(self.root, [frame(value=value)]) as peer, self.assertRaises(REFUSAL) as raised:
            client.Client(self.root).call({"op": "lease", "cache_id": "c", "operation_id": "id", "consumers": [], "leaf": True})
        self.assertEqual(raised.exception.code, "storage_unsupported")
        self.assertEqual(len(peer.requests), 1)

    def test_read_deadline_and_no_transport_retry(self):
        def stalled(stream):
            stream.recv(65536)
            time.sleep(0.08)
        start = time.monotonic()
        with Peer(self.root, [stalled]), patch.object(client, "EXCHANGE_SECONDS", 0.025), self.assertRaises(REFUSAL) as raised:
            client.Client(self.root).call({"op": "hello"})
        self.assertLess(time.monotonic()-start, 0.5)
        self.assertIn("deadline", raised.exception.diagnostic)

    def test_nonprivate_directory_and_redirected_socket_refuse(self):
        with Peer(self.root, []) as peer:
            self.root.chmod(0o755)
            with self.assertRaises(REFUSAL):
                client.Client(self.root).call({"op": "hello"})
            self.root.chmod(0o700)
        (self.root/"control.sock").unlink(missing_ok=True)
        (self.root/"control.sock").symlink_to(self.root/"missing")
        with self.assertRaises(REFUSAL):
            client.Client(self.root).call({"op": "hello"})

    def test_native_start_encoding(self):
        identity = client.unix_start(os.getpid())
        pattern = r"macos:[0-9]+:[0-9]+" if sys.platform == "darwin" else r"linux:[0-9a-f-]{36}:[0-9]+"
        self.assertRegex(identity, pattern)

    def test_kernel_uid_check_refuses_foreign_uid_before_writing(self):
        observed = []
        with Peer(self.root, [lambda stream: observed.append(stream.recv(1))]):
            with contextlib.closing(client.UnixStream(self.root, time.monotonic()+1)) as stream:
                uid = os.geteuid()
                with patch.object(client.os, "geteuid", return_value=uid+1), self.assertRaises(REFUSAL):
                    client.unix_peer(stream.stream)
        self.assertEqual(observed, [b""])

    def test_full_backlog_connect_retry_and_deadline(self):
        with Peer(self.root, [frame()]) as peer:
            with patch.object(peer.connection_type, "connect_ex", side_effect=[errno.EAGAIN, 0]) as connect:
                client.Client(self.root).call({"op": "hello"})
            self.assertEqual(connect.call_count, 2)
        observed = []
        with Peer(self.root, [lambda stream: observed.append(stream.recv(1))]) as peer:
            start = time.monotonic()
            with patch.object(peer.connection_type, "connect_ex", return_value=errno.EAGAIN), self.assertRaises(REFUSAL):
                client.UnixStream(self.root, start+0.025)
            self.assertLess(time.monotonic()-start, 0.2)
        self.assertEqual(observed, [b""])

    def test_stream_truncation_is_not_a_complete_reply(self):
        with Peer(self.root, [frame()[:-1]]), self.assertRaises(REFUSAL) as raised:
            client.Client(self.root).call({"op": "hello"})
        self.assertIn("truncated", raised.exception.diagnostic)

    def test_blocked_write_keeps_exchange_deadline(self):
        def consume_nothing(stream):
            time.sleep(0.08)
        with Peer(self.root, [consume_nothing]):
            with contextlib.closing(client.UnixStream(self.root, time.monotonic()+1)) as stream:
                with patch.object(stream.stream, "send", side_effect=BlockingIOError()), self.assertRaises(REFUSAL) as raised:
                    stream.exchange(b"request\n", time.monotonic()+0.02)
        self.assertIn("deadline", raised.exception.diagnostic)


class ClientTests(unittest.TestCase):
    def test_linux_ucred_preserves_unsigned_uid(self):
        uid = 2**32-2
        stream = SimpleNamespace(getsockopt=lambda *args: struct.pack("=iII", 42, uid, uid))
        with patch.object(client.sys, "platform", "linux"), \
             patch.object(client.socket, "SO_PEERCRED", 17, create=True), \
             patch.object(client.os, "geteuid", return_value=uid, create=True), \
             patch.object(client, "unix_start", return_value="linux:boot:1"):
            self.assertEqual(client.unix_peer(stream), (42, uid, "linux:boot:1"))

    def test_busy_window_is_bounded(self):
        budget = 0.035
        for wake_delay in (0.0, 0.1):
            clock, attempts = SimpleNamespace(now=0.0), []
            def busy(*args, **kwargs):
                self.assertLess(clock.now, budget, 'retry admitted after its deadline')
                attempts.append(clock.now)
                raise REFUSAL('busy')
            def sleep(seconds):
                self.assertGreater(seconds, 0)
                self.assertLessEqual(seconds, budget - clock.now)
                clock.now += seconds + wake_delay
            with self.subTest(wake_delay=wake_delay), \
                 patch.object(client, 'time', SimpleNamespace(monotonic=lambda: clock.now, sleep=sleep)), \
                 patch.object(client.Client, '_exchange', side_effect=busy), patch.object(client, 'EXCHANGE_SECONDS', budget):
                with self.assertRaises(REFUSAL) as raised:
                    client.Client('unused').call({'op': 'hello'})
            self.assertEqual(raised.exception.code, 'storage_busy')
            self.assertGreaterEqual(clock.now, budget)
            self.assertEqual(attempts[0], 0.0)
            if wake_delay:
                self.assertEqual(len(attempts), 1, 'overslept wakeup retried')

    def test_busy_is_waited_out_as_long_as_one_exchange(self):
        # devlynd's own clients wait EXCHANGE_BUDGET (15 s) behind a busy worker; so does this one.
        hello = {"storage_protocol": 1, "capabilities": ["reserve"]}
        for busy_for, answered in ((2.5, True), (float('inf'), False)):
            clock, attempts = SimpleNamespace(now=0.0), []
            def exchange(*args, **kwargs):
                attempts.append(clock.now)
                if clock.now < busy_for:
                    raise REFUSAL('busy')
                return hello, 'server'
            def sleep(seconds):
                clock.now += seconds
            with self.subTest(busy_for=busy_for), \
                 patch.object(client, 'time', SimpleNamespace(monotonic=lambda: clock.now, sleep=sleep)), \
                 patch.object(client.Client, '_exchange', side_effect=exchange):
                if answered:
                    self.assertEqual(client.Client('unused').call({'op': 'hello'}), hello)
                    self.assertGreaterEqual(clock.now, busy_for)
                else:
                    with self.assertRaises(REFUSAL) as raised:
                        client.Client('unused').call({'op': 'hello'})
                    self.assertEqual(raised.exception.code, 'storage_busy')
                    self.assertGreaterEqual(clock.now, client.EXCHANGE_SECONDS)
                    self.assertLess(attempts[-1], client.EXCHANGE_SECONDS)

    def test_unknown_and_nonbusy_errors_are_never_retried(self):
        for code in ("storage_io", "storage_unavailable", "storage_not_found", "storage_expired", "new_code"):
            with patch.object(client.Client, "_exchange", side_effect=REFUSAL(code)) as exchange:
                with self.assertRaises(REFUSAL):
                    client.Client("unused").call({"op": "hello"})
                self.assertEqual(exchange.call_count, 1)

    def test_new_server_between_hello_and_operation_gets_zero_bytes(self):
        sent = []
        class Stream:
            identity = (10, "uid", "new-start")
            def close(self):
                pass
            def exchange(self, *args):
                sent.append(args)
        with patch.object(client, "connect", return_value=Stream()), self.assertRaises(REFUSAL):
            client.Client("unused")._exchange(b"request", "hello", time.monotonic()+1, (10, "uid", "old-start"))
        self.assertEqual(sent, [])


class PipeTests(unittest.TestCase):
    def test_fake_pipe_roundtrip_exact_name_and_handle_closure(self):
        api = FakePipeAPI()
        with contextlib.closing(client.WindowsStream("unused", time.monotonic()+1, api=api)) as pipe:
            raw = pipe.exchange(client.encode_request({"op": "hello"}), time.monotonic()+1)
            client.decode_reply(raw, "hello")
        self.assertEqual(api.name, client.pipe_name(api.sid(), "C:\\Devlyn\\control"))
        self.assertTrue(api.written.endswith(b"\n"))
        self.assertEqual(len(api.finished), len(api.operations))
        self.assertEqual(api.closed, [27])

    def test_foreign_and_reused_pipe_servers_get_zero_bytes(self):
        for snapshots in ([(50, "foreign", "windows:1")],
                          [(50, "S-1-5-21-123", "windows:1"), (50, "S-1-5-21-123", "windows:2")]):
            api = FakePipeAPI()
            api.snapshots = snapshots
            with self.assertRaises(REFUSAL):
                client.WindowsStream("unused", time.monotonic()+1, api=api)
            self.assertFalse(api.written)
            self.assertEqual(api.closed, [27])

    def test_reused_pipe_server_before_write_gets_zero_bytes(self):
        api = FakePipeAPI()
        with contextlib.closing(client.WindowsStream("unused", time.monotonic()+1, api=api)) as pipe:
            api.snapshots = [(50, api.sid(), "windows:2")]*2
            with self.assertRaises(REFUSAL):
                pipe.exchange(b"secret\n", time.monotonic()+1)
        self.assertFalse(api.written)

    def test_early_busy_retained_after_pipe_write_failure(self):
        api = FakePipeAPI(error(), early=True, fail_write=True)
        with contextlib.closing(client.WindowsStream("unused", time.monotonic()+1, api=api)) as pipe:
            raw = pipe.exchange(b"request\n", time.monotonic()+1)
        with self.assertRaises(REFUSAL) as raised:
            client.decode_reply(raw, "hello")
        self.assertEqual(raised.exception.code, "storage_busy")
        self.assertEqual(len(api.finished), len(api.operations))

    def test_pipe_deadline_cancels_all_pending_io(self):
        api = FakePipeAPI(stalled=True)
        start = time.monotonic()
        with contextlib.closing(client.WindowsStream("unused", start+1, api=api)) as pipe:
            with self.assertRaises(REFUSAL):
                pipe.exchange(b"request\n", time.monotonic()+0.02)
        self.assertLess(time.monotonic()-start, 0.2)
        self.assertEqual(len(api.finished), len(api.operations))
        self.assertEqual(api.closed, [27])

    def test_first_native_open_is_anonymous_and_overlapped_busy_retry(self):
        from types import SimpleNamespace
        opened, waited = [], []
        handles = iter((ctypes.c_void_p(-1).value, 44))
        api = client.WindowsAPI.__new__(client.WindowsAPI)
        def open_file(*args):
            opened.append(args)
            return next(handles)
        api.kernel = SimpleNamespace(CreateFileW=open_file, WaitNamedPipeW=lambda *args: waited.append(args) or 1)
        with patch.object(ctypes, "get_last_error", return_value=231, create=True):
            self.assertEqual(api.open_pipe("pipe", time.monotonic()+1), 44)
        self.assertEqual(len(opened), 2)
        self.assertEqual(opened[0][5], 0x40000000 | 0x00100000)
        self.assertEqual(opened[0][5] & 0x00030000, 0)  # SECURITY_ANONYMOUS from first open.
        self.assertTrue(waited)

    def test_windows_canonical_path_retains_reserved_and_unc_prefixes(self):
        self.assertEqual(client.rust_windows_path("\\\\?\\C:\\control"), "C:\\control")
        for path in ("\\\\?\\UNC\\host\\share", "\\\\?\\C:\\CON", "\\\\?\\C:\\name.",
                     "\\\\?\\C:\\file:stream", "\\\\?\\C:\\COM¹.txt", "\\\\?\\C:\\x\x7f"):
            self.assertEqual(client.rust_windows_path(path), path)

    def test_delayed_native_cancellation_keeps_deadline_and_buffer_lifetime(self):
        api = client.WindowsAPI.__new__(client.WindowsAPI)
        api.cleanup_diagnostics = []
        release, drained = threading.Event(), threading.Event()
        closed = []
        def duplicate(process, handle, target, result, *args):
            result._obj.value = 99
            return 1
        def drain(handle, overlap, count, wait):
            assert handle.value == 99 and wait
            assert release.wait(1), "cancellation reaper did not receive completion"
            return 0
        def close(handle):
            value = handle.value if hasattr(handle, "value") else handle
            closed.append(value)
            if value == 99:
                drained.set()
            return 1
        api.kernel = SimpleNamespace(CancelIoEx=lambda *args: 1, WaitForSingleObject=lambda *args: 258,
                                     GetCurrentProcess=lambda: -1, DuplicateHandle=duplicate,
                                     GetOverlappedResult=drain, CloseHandle=close)
        operation = [client.Overlapped(hEvent=42), ctypes.create_string_buffer(10), 42, False]
        try:
            with patch.object(ctypes, "get_last_error", return_value=995, create=True):
                start = time.monotonic()
                api.finish_io(27, operation, start)
                self.assertLess(time.monotonic()-start, 0.1)
                self.assertEqual(closed, [])
                api.close(27)  # Stream can close while duplicate retains I/O.
                release.set()
                self.assertTrue(drained.wait(1))
        finally:
            release.set()
        self.assertEqual(closed, [27, 42, 99])
        self.assertEqual(len(api.cleanup_diagnostics), 1)

    def test_native_cancel_closes_event_after_positive_completion(self):
        api = client.WindowsAPI.__new__(client.WindowsAPI)
        closed = []
        api.kernel = SimpleNamespace(CancelIoEx=lambda *args: 1, WaitForSingleObject=lambda *args: 0,
                                     GetOverlappedResult=lambda *args: 0, CloseHandle=lambda handle: closed.append(handle) or 1)
        operation = [client.Overlapped(hEvent=42), ctypes.create_string_buffer(10), 42, False]
        with patch.object(ctypes, "get_last_error", return_value=995, create=True):
            api.finish_io(27, operation, time.monotonic()+1)
        self.assertEqual(closed, [42])

    def test_cancellation_setup_failures_retain_every_resource_until_completion(self):
        for failure in ('duplicate', 'thread', 'started_thread', 'cancel', 'wait', 'unexpected_completion'):
            with self.subTest(failure=failure):
                api = client.WindowsAPI.__new__(client.WindowsAPI)
                api.cleanup_diagnostics = []
                completed = threading.Event()
                closed = []
                queries = []
                def duplicate(process, handle, target, result, *args):
                    if failure == 'duplicate':
                        raise OSError('duplicate failed')
                    result._obj.value = 99
                    return 1
                def result(handle, overlap, count, wait):
                    queries.append(wait)
                    if not wait and failure == 'unexpected_completion':
                        return 0
                    completed.set()
                    return 1
                def close(handle):
                    self.assertTrue(completed.is_set(), 'native resource freed before completion')
                    closed.append(handle.value if hasattr(handle, 'value') else handle)
                    return 1
                api.kernel = SimpleNamespace(CancelIoEx=lambda *args: 0 if failure == 'cancel' else 1,
                    WaitForSingleObject=lambda *args: 0xFFFFFFFF if failure == 'wait' else 0 if failure == 'unexpected_completion' else 258,
                    GetCurrentProcess=lambda: -1, DuplicateHandle=duplicate, GetOverlappedResult=result, CloseHandle=close)
                operation = [client.Overlapped(hEvent=42), ctypes.create_string_buffer(b'pending'), 42, False]
                with patch.object(ctypes, 'get_last_error', return_value=5, create=True):
                    if failure in ('duplicate', 'thread', 'started_thread'):
                        original_start = threading.Thread.start
                        def interrupted_start(worker):
                            original_start(worker)
                            raise RuntimeError('started then interrupted')
                        startup = patch.object(threading.Thread, 'start', interrupted_start) if failure == 'started_thread' else (patch.object(threading.Thread, 'start', side_effect=RuntimeError('thread failed')) if failure == 'thread' else contextlib.nullcontext())
                        with startup:
                            with self.assertRaises((OSError, RuntimeError)):
                                api.finish_io(27, operation, time.monotonic())
                    else:
                        try:
                            api.finish_io(27, operation, time.monotonic())
                        except REFUSAL:
                            self.assertIn(failure, ('cancel', 'wait'))
                        self.assertTrue(completed.wait(1))
                        deadline = time.monotonic()+1
                        while 42 not in closed and time.monotonic() < deadline:
                            time.sleep(.001)
                self.assertTrue(operation[3])
                self.assertEqual(closed.count(42), 1)
                self.assertLessEqual(closed.count(99), 1)
                self.assertIn(True, queries)



class EnrollmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="storage-enrollment-")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name).resolve()
        environment = patch.dict(os.environ, HOME=str(self.home), USERPROFILE=str(self.home))
        environment.start()
        self.addCleanup(environment.stop)

    def write(self, value):
        root = self.home/".devlyn"
        root.mkdir(exist_ok=True)
        path = root/"storage-client.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def test_queue_handoff_follows_devlyn_hold(self):
        common = self.home / 'common'
        common.mkdir()
        release = self.home / 'release'
        release.mkdir()
        reference = {'package': 'devlyn-cli', 'version': '4.3.20', 'digest': 'a'*64, 'root': str(release)}
        binding = {'release': reference}
        manifest = {'schemaVersion': 1, 'package': reference['package'], 'version': reference['version'],
                    'digest': {'algorithm': 'sha256', 'value': reference['digest']}, 'files': []}
        file = release / 'release.json'
        file.write_text(json.dumps(manifest))
        completion = common / 'devlyn-completion'
        with patch.object(Path, 'iterdir', side_effect=AssertionError('never-enrolled listing')), \
             patch.object(os, 'open', side_effect=AssertionError('never-enrolled open')):
            self.assertIsNone(client.queue_handoff(common, binding))
        # All eight table rows, including refusal precedence and never-enrolled zero scan.
        refusal = REFUSAL('storage_unavailable', message='repair registration')
        with patch.object(client, 'operation_enrollment', side_effect=refusal):
            self.assertEqual(client.queue_handoff(common, binding), 'repair registration')
        with patch.object(client, 'operation_enrollment', return_value={'mode': 'standalone'}), \
             patch.object(client, 'recovery_marker', return_value=False):
            self.assertIsNone(client.queue_handoff(common, binding))
        for managed in (False, True):
            for listed in (False, True):
                for present in (False, True):
                    with self.subTest(managed=managed, listed=listed, present=present):
                        manifest['files'] = [{'path': 'config/storage-client-contract.json'}] if listed else []
                        file.write_text(json.dumps(manifest))
                        if completion.exists():
                            shutil.rmtree(completion)
                        if present:
                            holder = completion / 'task'
                            holder.mkdir(parents=True)
                            (holder / 'receipt.json').write_text('{"allocation":"managed_pending"}')
                        with patch.object(client, 'operation_enrollment', return_value={'mode': 'managed' if managed else 'standalone'}), \
                             patch.object(client, 'recovery_marker', return_value=True):
                            line = client.queue_handoff(common, binding)
                        if present and not listed:
                            self.assertIn(str(completion / 'task/receipt.json'), line)
                            self.assertIn('then start it with Drain in Devlyn' if managed else 'then run this again', line)
                            self.assertNotIn('delete', line)
                        elif managed:
                            self.assertEqual(line, 'Devlyn runs this queue on this computer: start it with Drain in Devlyn')
                            self.assertNotIn(str(completion / 'task/receipt.json'), line)
                        else:
                            self.assertIsNone(line)
        manifest['files'] = []
        file.write_text(json.dumps(manifest))
        shutil.rmtree(completion)
        completion.mkdir()
        for name in ('retired', 'moved'):
            archive = completion / name / 'id.operation'
            archive.mkdir(parents=True)
            (archive / 'receipt.json').write_text('{"mode":"managed"}')
        holder = completion / 'task'
        holder.mkdir()
        receipt = holder / 'receipt.json'
        def line():
            with patch.object(client, 'operation_enrollment', return_value={'mode': 'standalone'}), \
                 patch.object(client, 'recovery_marker', return_value=True):
                return client.queue_handoff(common, binding)
        self.assertIsNone(line())
        for raw in ('{"mode":"managed"}', '{"allocation_state":"managed_future"}',
                    '{"allocation":"managed_owned"}', '{"allocation":5}', '{"mode":5}', '{"mode":null,"mode":null}', '[]', '{'):
            receipt.write_text(raw)
            self.assertIn(str(receipt), line())
        receipt.write_text(json.dumps({'allocation': 'managed_pending', 'large': 'x'*700000}))
        self.assertNotIn('cannot be read', line())
        receipt.write_text('{"allocation":"owned","mode":null}')
        self.assertIsNone(line())
        receipt.write_text('{')
        (holder / 'storage-allocation.json').touch()
        self.assertNotIn('cannot be read', line())  # Rust marker wins over malformed Python receipt.
        (holder / 'storage-allocation.json').unlink()
        receipt.unlink()
        receipt.mkdir()
        self.assertIn('cannot be read', line())
        receipt.rmdir()
        (holder / 'storage-allocation.json').touch()
        self.assertIn(str(receipt), line())
        (holder / 'storage-allocation.json').unlink()
        if os.name != 'nt':
            if os.geteuid() != 0:  # Root reads a file whatever its mode.
                receipt.write_text('{"allocation":"managed_pending"}')
                receipt.chmod(0)
                try:
                    self.assertIn('cannot be read', line())
                finally:
                    receipt.chmod(0o600)
                    receipt.unlink()
            receipt.symlink_to(file)
            self.assertIn('cannot be read', line())
            receipt.unlink()
            os.mkfifo(receipt)
            self.assertIn('cannot be read', line())
            receipt.unlink()
            (completion / 'redirect').symlink_to(release, target_is_directory=True)
            self.assertIn('cannot be read', line())
            (completion / 'redirect').unlink()
        with patch.object(Path, 'iterdir', side_effect=PermissionError('denied')):
            self.assertIn('cannot be read', line())
        # Duplicate contract listings and every manifest identity mismatch mean pre-contract.
        receipt.write_text('{"mode":"managed"}')
        for change in ({'schemaVersion': 2}, {'package': 'other'}, {'version': '0.0.0'},
                       {'digest': {'algorithm': 'sha512', 'value': 'a'*64}},
                       {'files': [{'path': 'config/storage-client-contract.json'}]*2}):
            file.write_text(json.dumps({**manifest, **change}))
            self.assertIn('tasks in progress', line())
        file.unlink()
        self.assertIn('tasks in progress', line())

    def test_completion_refusal_deduplicates_resume_and_keeps_repair_suffix(self):
        helper = runpy.run_path(str(SHARED / 'task-complete.py'))
        storage = helper['shared']('storage-client')
        resume = 'retained-helper storage-client unenroll --reconcile --json'
        for message, command, expected in (
                ('Finish this storage retirement; resume ' + resume, resume,
                 'Finish this storage retirement; resume ' + resume),
                ('Finish this storage retirement', resume, 'Finish this storage retirement; resume ' + resume),
                ('registration unavailable', None, 'registration unavailable; repair Devlyn enrollment and retry')):
            refusal = storage['StorageRefusal']('storage_unavailable', message=message, resume=command)
            with self.subTest(message=message), patch.dict(storage, retirement_refusal=unittest.mock.Mock(side_effect=refusal)), \
                 self.assertRaises(helper['CompletionError']) as raised:
                helper['storage_call']('retirement_refusal')
            self.assertEqual(str(raised.exception), expected)
            self.assertEqual(raised.exception.storage_error['resume'], command)
        # An unsupported refusal's remedy is an update, so no repair suffix follows it.
        refusal = storage['StorageRefusal']('storage_unsupported', 'recovery pins from a newer Devlyn')
        with patch.dict(storage, retirement_refusal=unittest.mock.Mock(side_effect=refusal)), \
             self.assertRaises(helper['CompletionError']) as raised:
            helper['storage_call']('retirement_refusal')
        self.assertEqual(str(raised.exception), storage['REFUSAL_TEXT']['storage_unsupported'])

    def test_unset_home_platform_branches_and_json_contract(self):
        import io
        helper = runpy.run_path(str(SHARED / 'task-complete.py'))
        storage = helper['shared']('storage-client')
        for platform in ('linux', 'win32'):
            for unavailable in (False, True):
                with self.subTest(platform=platform, unavailable=unavailable), \
                     patch.dict(os.environ, {}, clear=True), patch.object(sys, 'platform', platform), \
                     contextlib.ExitStack() as stack:
                    platform_os = SimpleNamespace(**{**vars(os), 'name': 'nt' if platform == 'win32' else 'posix',
                                                     'getuid': lambda: 42})
                    stack.enter_context(patch.dict(storage['user_home'].__globals__, os=platform_os))
                    if platform == 'win32':
                        stack.enter_context(patch.dict(storage['user_home'].__globals__, windows_profile=
                            unittest.mock.Mock(side_effect=OSError('profile denied')) if unavailable else lambda: self.home))
                    else:
                        stack.enter_context(patch.dict(sys.modules, pwd=SimpleNamespace(getpwuid=unittest.mock.Mock(
                            side_effect=OSError('passwd denied') if unavailable else KeyError('no passwd entry')))))
                        stack.enter_context(patch.object(os, 'getuid', return_value=42, create=True))
                    output = io.StringIO()
                    def allocate(args):
                        return helper['storage_call']('operation_enrollment')
                    stack.enter_context(patch.dict(helper['main'].__globals__, allocate=allocate))
                    stack.enter_context(patch.object(sys, 'argv', ['task-complete.py', 'allocate', '--task', 'home',
                        '--branch', 'task/home', '--worktree', str(self.home / 'tree')]))
                    with contextlib.redirect_stdout(output):
                        status = helper['main']()
                    result = json.loads(output.getvalue())
                    self.assertEqual(status, int(unavailable))
                    if unavailable:
                        self.assertEqual(result['status'], 'BLOCKED')
                        self.assertIn('repair', result['storage_error']['diagnostic'])
                    else:
                        self.assertEqual(result['mode'], 'standalone')

    def test_profile_resolver_matches_rust_ignoring_homedrive_and_homepath(self):
        # util::home_dir chooses nonempty USERPROFILE, else the known folder.
        windows_os = SimpleNamespace(**{**vars(os), 'name': 'nt'})
        with patch.object(client, 'os', windows_os), patch.object(sys, 'platform', 'win32'), \
             patch.dict(os.environ, USERPROFILE=str(self.home), HOMEDRIVE='Z:', HOMEPATH='\\wrong'), \
             patch.object(client, 'windows_profile', side_effect=AssertionError('unexpected fallback')):
            self.assertEqual(client.user_home(), self.home)
        for value in (None, ''):
            with patch.object(client, 'os', windows_os), patch.object(sys, 'platform', 'win32'), patch.dict(os.environ, HOMEDRIVE='Z:', HOMEPATH='\\wrong'), \
                 patch.object(client, 'windows_profile', return_value=self.home):
                if value is None:
                    os.environ.pop('USERPROFILE', None)
                else:
                    os.environ['USERPROFILE'] = value
                self.assertEqual(client.user_home(), self.home)

    @unittest.skipUnless(os.name == 'nt', 'native SHGetKnownFolderPath requires Windows')
    def test_native_windows_profile_fallback_without_home_environment(self):
        expected = client.windows_profile()
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(client.user_home(), expected)
        with patch.dict(os.environ, USERPROFILE=str(self.home), HOMEDRIVE='Z:', HOMEPATH='\\wrong'):
            self.assertEqual(client.user_home(), self.home)

    def test_positive_absence_and_bare_directory_are_standalone_without_creation(self):
        self.assertEqual(client.enrollment()["mode"], "standalone")
        self.assertEqual(list(self.home.iterdir()), [])
        (self.home/".devlyn").mkdir()
        self.assertEqual(client.enrollment()["mode"], "standalone")
        self.assertEqual(list((self.home/".devlyn").iterdir()), [])

    def test_absent_home_is_standalone_but_invalid_evidence_refuses(self):
        absent = self.home / 'absent'
        with patch.dict(os.environ, HOME=str(absent), USERPROFILE=str(absent)):
            self.assertEqual(client.operation_enrollment()['mode'], 'standalone')
            self.assertFalse(absent.exists())
            with self.assertRaises(REFUSAL):
                client.enrollment(receipt={'mode': 'managed'})
            absent.write_text('not a directory')
            if os.name == 'nt':  # Rust canonical_root also sees ERROR_PATH_NOT_FOUND.
                self.assertEqual(client.enrollment()['mode'], 'standalone')
            else:
                with self.assertRaises(REFUSAL):
                    client.enrollment()

    def test_completed_unenroll_ignores_all_receipts_and_warm_uses_same_mode(self):
        write_retirement(self.home)
        common = self.home / 'common'
        for name in ('active', 'retired/task.operation'):
            directory = common / 'devlyn-completion' / name
            directory.mkdir(parents=True)
            (directory / 'receipt.json').write_text('malformed managed receipt')
            (directory / 'storage-allocation.json').mkdir()
        with patch.object(Path, 'iterdir', side_effect=AssertionError('receipt scan')), \
             patch.object(os, 'walk', side_effect=AssertionError('walk')):
            self.assertEqual(client.operation_enrollment()['mode'], 'standalone')
        if sys.platform not in {'darwin', 'linux'}:
            return  # Native Windows does not warm Cargo.
        (self.home / 'Cargo.toml').write_text('[workspace]')
        warm = runpy.run_path(str(SHARED / 'warm-build-dirs.py'))
        with patch.dict(warm['warm'].__globals__, destination=unittest.mock.Mock(side_effect=warm['Skip']('standalone reached'))), \
             patch.object(shutil, 'which', return_value='cargo'):
            self.assertIn('standalone reached', warm['warm'](self.home, self.home, self.home)[0]['reason'])

    def test_enrolled_with_absent_registry(self):
        path = self.write({"schema": 1})
        verified = {"control_directory": "verified", "helper": "verified release"}
        before = path.read_bytes()
        result = client.enrollment(verify_registration=lambda record: verified)
        self.assertEqual(result["mode"], "managed")
        self.assertEqual(result["registration"], verified)
        self.assertFalse((self.home/".devlyn/storage").exists())
        self.assertEqual(path.read_bytes(), before)

    def test_registration_is_never_assumed_without_prerequisite_verifier(self):
        self.write({"schema": 1})
        with self.assertRaises(REFUSAL) as raised:
            client.enrollment()
        self.assertEqual(raised.exception.code, "storage_unavailable")

    def test_legacy_named_evidence_is_standalone_without_helper(self):
        for name in ("storage/v1", "control", "harness/state.json"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                home = Path(directory).resolve()
                path = home/".devlyn"/name
                path.parent.mkdir(parents=True)
                if name.endswith(".json"):
                    path.write_text("{}")
                else:
                    path.mkdir()
                with patch.dict(os.environ, HOME=str(home), USERPROFILE=str(home)):
                    self.assertEqual(client.enrollment()["mode"], "standalone")

    def test_managed_receipt_never_downgrades(self):
        for state in (*client.MANAGED_STATES, "managed_future"):
            with self.subTest(state=state), self.assertRaises(REFUSAL):
                client.enrollment(receipt={"allocation": state})
        self.assertEqual(list(self.home.iterdir()), [])

    def test_malformed_newer_inaccessible_redirected_evidence_refuses(self):
        for record in ([], {}, {"schema": True}, {"schema": 0}, {"schema": 2}):
            self.write(record)
            with self.subTest(record=record), self.assertRaises(REFUSAL):
                client.enrollment(verify_registration=lambda record: {"verified": True})
        path = self.write({"schema": 1})
        path.write_text('{"schema":1,"schema":1}')
        with self.assertRaises(REFUSAL):
            client.enrollment()
        with patch.object(Path, "lstat", side_effect=PermissionError("denied")), self.assertRaises(REFUSAL):
            client.enrollment()
    @unittest.skipIf(os.name == 'nt', 'symlink creation requires Windows privileges')
    def test_redirected_expectation_refuses(self):
        path = self.write({"schema": 1})
        path.unlink()
        try:
            path.symlink_to(self.home/"absent")
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        with self.assertRaises(REFUSAL):
            client.enrollment()

    def test_stale_completed_retirement_uses_live_inventory(self):
        root = self.home / '.devlyn'
        for moved in (False, True):
            journal = write_retirement(self.home)
            if not moved:
                for key in ('root_identity', 'lock_identity'):
                    journal[key] = {'volume': 'copied', 'file': 'different'}
            if moved:
                old = self.home / 'old-home/.devlyn'
                journal['archives'] = [{'source': str(old / 'storage'),
                    'destination': str(old / 'storage-client-retired' / journal['operation_id'] / 'storage'),
                    'identity': {'volume': 'old', 'file': 'old'}, 'sha256': 'old digest'}]
            fence = {key: journal[key] for key in ('schema', 'operation_id', 'root_identity', 'lock_identity')}
            (root / 'storage-client-unenroll.json').write_text(json.dumps(journal))
            (root / 'storage-client-fence.json').write_text(json.dumps(fence))
            with self.subTest(moved=moved):
                self.assertEqual(client.operation_enrollment()['mode'], 'standalone')
                for source in ('storage', 'control', 'harness/state.json', 'storage-client.json'):
                    live = root / source
                    live.parent.mkdir(exist_ok=True)
                    live.mkdir() if source in ('storage', 'control') else live.write_text('{}')
                    with self.subTest(live=source), self.assertRaises(REFUSAL):
                        client.operation_enrollment()
                    live.rmdir() if live.is_dir() else live.unlink()

    @unittest.skipIf(os.name == 'nt', 'symlink privileges and FIFO semantics are POSIX-only')
    def test_redirected_ancestor_and_fifo_expectation_refuse(self):
        root = self.home/".devlyn"
        root.mkdir()
        try:
            (root/"storage").symlink_to(self.home/"absent")
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        self.assertEqual(client.enrollment()["mode"], "standalone")
        (root/"storage").unlink()
        if hasattr(os, "mkfifo"):
            os.mkfifo(root/"storage-client.json")
            with self.assertRaises(REFUSAL):
                client.enrollment()

    def test_evidence_replacement_during_verification_refuses(self):
        path = self.write({"schema": 1})
        def replace(record):
            path.unlink()
            path.write_text('{"schema":1,"changed":true}')
            return {"verified": True}
        with self.assertRaises(REFUSAL) as raised:
            client.enrollment(verify_registration=replace)
        self.assertIn("changed during inspection", raised.exception.diagnostic)

    def test_devlyn_directory_activity_during_verification_is_not_enrollment_change(self):
        self.write({'schema': 1})
        def verify(record):
            (self.home / '.devlyn/harness').mkdir()
            (self.home / '.devlyn/harness/state.json').write_text('{}')
            return {'verified': True}
        self.assertEqual(client.enrollment(verify_registration=verify)['mode'], 'managed')

    def test_never_enrolled_has_zero_receipt_or_retirement_reads_or_walks(self):
        opened = os.open
        def no_retirement(path, *args, **kwargs):
            self.assertNotIn(Path(path).name, {'storage-client-unenroll.json', 'storage-client-fence.json', 'storage-client.lock'})
            return opened(path, *args, **kwargs)
        with patch.object(Path, 'iterdir', side_effect=AssertionError('receipt scan')), \
             patch.object(os, 'walk', side_effect=AssertionError('walk')), patch.object(os, 'open', no_retirement):
            self.assertEqual(client.operation_enrollment()['mode'], 'standalone')
        self.assertEqual(list(self.home.iterdir()), [])

    def test_lost_record_or_in_progress_unenroll_requires_registration_repair(self):
        journal = write_retirement(self.home)
        path = self.home / '.devlyn/storage-client-unenroll.json'
        helper = runpy.run_path(str(SHARED / 'task-complete.py'))
        for raw in (None, b'broken', json.dumps({**journal, 'retired': False}).encode(),
                    json.dumps({**journal, 'retired': 1}).encode(), b'{"retired":true,"retired":true}'):
            if raw is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(raw)
            with self.subTest(raw=raw), self.assertRaises(helper['CompletionError']) as raised:
                helper['storage_call']('operation_enrollment')
            error = raised.exception.storage_error
            self.assertEqual(error['message'], 'Open Devlyn to repair its storage registration')
            self.assertEqual(error['resume'], error['message'])
            self.assertIsNone(error['receipt'])
        with patch.object(os, 'open', side_effect=PermissionError('journal denied')), self.assertRaises(REFUSAL):
            client.operation_enrollment()

    def test_missing_fence_and_disagreeing_retirement_evidence_refuse(self):
        root = self.home / '.devlyn'
        for changed in ('missing fence', 'operation_id', 'root_identity', 'lock_identity', 'lock directory'):
            journal = write_retirement(self.home)
            fence_path = root / 'storage-client-fence.json'
            fence = json.loads(fence_path.read_text())
            if changed == 'missing fence':
                fence_path.unlink()
            elif changed == 'lock directory':
                lock = root / 'storage-client.lock'
                lock.unlink()
                lock.mkdir()
                journal['lock_identity'] = fence['lock_identity'] = client.persistent_identity(lock)
                (root / 'storage-client-unenroll.json').write_text(json.dumps(journal))
                fence_path.write_text(json.dumps(fence))
            else:
                fence[changed] = client.operation_id() if changed == 'operation_id' else {'volume': 'wrong', 'file': 'wrong'}
                fence_path.write_text(json.dumps(fence))
            with self.subTest(changed=changed), self.assertRaises(REFUSAL):
                client.operation_enrollment()

    @unittest.skipIf(os.name == 'nt', 'symlink privileges and FIFO semantics are POSIX-only')
    def test_retirement_evidence_is_read_nofollow_and_never_blocks_on_fifo(self):
        write_retirement(self.home)
        path = self.home / '.devlyn/storage-client-unenroll.json'
        original = self.home / 'copied-journal'
        path.rename(original)
        path.symlink_to(original)
        with self.assertRaises(REFUSAL):
            client.operation_enrollment()
        path.unlink()
        os.mkfifo(path)
        with self.assertRaises(REFUSAL):
            client.operation_enrollment()

    def test_retirement_strict_schema_archives_and_valid_registration_precedence(self):
        original = write_retirement(self.home)
        path = self.home / '.devlyn/storage-client-unenroll.json'
        entry = {'source': str(self.home / '.devlyn/storage'),
                 'destination': str(self.home / '.devlyn/storage-client-retired' / original['operation_id'] / 'storage'),
                 'identity': {'volume': 'archive', 'file': 'archive'}, 'sha256': 'archive digest'}
        for mutation in ({'schema': True}, {'schema': 2}, {'unknown': 1}, {'archives': [entry, entry]},
                         {'archives': [{**entry, 'destination': 'elsewhere'}]},
                         {'archives': [{**entry, 'source': 'elsewhere'}]}, {'archives': [{**entry, 'unknown': 1}]}):
            path.write_text(json.dumps({**original, **mutation}))
            with self.subTest(mutation=mutation), self.assertRaises(REFUSAL):
                client.operation_enrollment()
        path.write_text(json.dumps({**original, 'archives': [entry]}))
        self.assertEqual(client.operation_enrollment()['mode'], 'standalone')
        self.write({'schema': 1})
        with patch.object(client, 'enrollment', return_value={'mode': 'managed'}), \
             patch.object(client, 'recovery_marker', side_effect=AssertionError('managed read retirement')):
            self.assertEqual(client.operation_enrollment()['mode'], 'managed')





@unittest.skipIf(PACKAGED, 'historical main source is not part of the released artifact')
class LegacyGuardTests(unittest.TestCase):
    def test_actual_4320_guard_refuses_both_states_even_with_new_fields(self):
        native_argv = runpy.run_path(str(SHARED/"platform-support.py"))["native_argv"]
        # Pin the pre-storage main baseline; HEAD now includes round-1's guard. Execute the
        # actual function AST, never a test-side reconstruction of its condition.
        proc = subprocess.run(native_argv(["git", "show", "5a94e810:config/skills/_shared/task-complete.py"]),
                              cwd=ROOT, capture_output=True, text=True, check=True)
        source = proc.stdout
        tree = ast.parse(source)
        guard = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "locked_receipt")
        helper = runpy.run_path(str(SHARED/"task-complete.py"))
        namespace = helper.copy()
        exec(compile(ast.Module(body=[guard], type_ignores=[]), "actual-4.3.20-guard", "exec"), namespace)
        with tempfile.TemporaryDirectory() as directory:
            common = Path(directory).resolve()
            branch = "task/storage-test"
            identity = hashlib.sha256(branch.encode()).hexdigest()[:24]
            path = common/"devlyn-completion"/identity/"receipt.json"
            path.parent.mkdir(parents=True)
            receipt = {"id": identity, "common_gitdir": str(common), "branch": branch, "base": "main",
                       "schemaVersion": 999, "storage": {"managed": True}, "allocation": "owned"}
            path.write_text(json.dumps(receipt))
            with namespace["locked_receipt"](path):
                pass  # Added fields alone do not protect an old 'owned' receipt.
            for allocation in ("owned", "allocating", "unknown", None, True, [], {}):
                receipt["allocation"] = allocation
                path.write_text(json.dumps(receipt))
                outcomes = []
                for guard_function in (namespace["locked_receipt"], helper["locked_receipt"]):
                    try:
                        with guard_function(path):
                            outcomes.append("accepted")
                    except helper["CompletionError"] as exc:
                        outcomes.append(str(exc))
                if allocation in ("owned", "allocating", "unknown", None):
                    self.assertEqual(outcomes[0], outcomes[1], allocation)
                else:
                    self.assertNotIn("accepted", outcomes)
            for state in client.MANAGED_STATES:
                receipt["allocation"] = state
                path.write_text(json.dumps(receipt))
                with self.subTest(state=state), self.assertRaisesRegex(helper["CompletionError"], "allocation was interrupted"):
                    with namespace["locked_receipt"](path):
                        self.fail("old helper admitted managed receipt")



def normalized(value, shape, *, windows=False):
    """Typed serde projection, using the production client's field definitions."""
    client.validate(value, shape, windows=windows)
    if isinstance(shape, dict):
        result = {}
        for key, child in shape.items():
            name = key.removesuffix('?')
            if name in value:
                result[name] = normalized(value[name], child, windows=windows)
            elif key.endswith('?'):
                defaults = {'leaf': False, 'removal_generation': 0}
                if name not in {'warnings', 'parent_evidence'}:
                    result[name] = defaults.get(name)
        return result
    if isinstance(shape, list):
        return [normalized(v, shape[0], windows=windows) for v in value]
    if isinstance(shape, tuple):
        return value
    if shape.endswith('?'):
        return None if value is None else normalized(value, shape[:-1], windows=windows)
    if shape == 'consumer':
        fields = {'pid': 'i64', 'created': 'u64'} if windows else {'pid': 'i64', 'pgid': 'i64', 'start?': 'str?'}
        return normalized(value, fields, windows=windows)
    if shape == 'plan':
        fields = {'kind': ('known',), 'writes': ['write'], 'digest': 'str'} if value['kind'] == 'known' else {'kind': ('unknown',), 'reason': ('external_filter', 'lfs_extension', 'encoding', 'attributes', 'lfs_transfer', 'missing_object', 'plan_changed', 'unsupported_git', 'overflow')}
        return normalized(value, fields, windows=windows)
    if shape in client.SHAPES:
        return normalized(value, client.SHAPES[shape], windows=windows)
    return value


def request_vector(value, *, windows=False):
    client.validate(value.get('storage_protocol'), 'u32')
    client.require(value['storage_protocol'] == 1, 'unsupported protocol', 'storage_unsupported')
    request = value['request']
    client.require(request.get('op') in client.REQUESTS, 'unknown operation', 'storage_unsupported')
    fields = {'op': (request['op'],), **client.REQUESTS[request['op']][0]}
    try:
        client.validate(value, {'storage_protocol': 'u32', 'request': fields}, exact=True, windows=windows)
    except REFUSAL as exc:
        raise REFUSAL('storage_invalid', exc.diagnostic) from exc
    return {'storage_protocol': 1, 'request': normalized(request, fields, windows=windows)}


class SharedVectorTests(unittest.TestCase):
    def test_pinned_digest_and_every_labelled_vector(self):
        manifest = load_cross_language_golden_vectors()
        root = FIXTURES/'storage-protocol-1'
        adapter = runpy.run_path(str(SHARED/'storage-checkout.py'))
        seen = set()
        for vector in manifest['vectors']:
            with self.subTest(path=vector['path']):
                seen.add(vector['path'])
                raw = (root/vector['path']).read_bytes()
                codec, expected = vector['codec'], vector['expected']
                if codec.startswith('frame:'):
                    self.check_frame(raw, codec, expected)
                    continue
                value = client.loads(raw)
                self.assertEqual(client.loads(json.dumps(value, ensure_ascii=False).encode()), value)
                if codec in {'identity', 'uuid', 'pipe_digest'}:
                    self.assertEqual(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode()+b'\n', raw)
                if codec in {'storage_request', 'process:unix', 'process:windows'}:
                    try:
                        back = request_vector(value, windows=codec == 'process:windows')
                        outcome = 'storage_protected'  # No authenticated peer: Door refuses before policy.
                    except REFUSAL as exc:
                        outcome = exc.code if exc.code in {'storage_invalid', 'storage_unsupported'} else 'storage_invalid'
                    self.assertEqual(outcome, expected)
                    if outcome == 'storage_protected':
                        # Process defaults are intentionally omitted and are not annotated with expected_reencoded.
                        if not (codec.startswith('process:') and 'default' in vector['note']):
                            self.assertEqual(back, vector.get('expected_reencoded', value))
                elif codec == 'storage_reply':
                    try:
                        kind = value.get('kind')
                        client.require(kind in {*client.SHAPES, 'reported'}, 'unknown reply')
                        back = {'kind': kind}
                        if kind != 'reported':
                            back['value'] = normalized(value['value'], kind)
                    except REFUSAL:
                        self.assertEqual(expected, 'reject')
                    else:
                        self.assertEqual(expected, 'decode')
                        self.assertEqual(back, vector.get('expected_reencoded', value))
                        client.decode_reply(json.dumps({'ok': value}).encode()+b'\n', kind)
                elif codec == 'response':
                    client.validate(value, {'error': {'code': 'str', 'message': 'str'}})
                    with self.assertRaises(REFUSAL) as raised:
                        client.decode_reply(json.dumps(value).encode()+b'\n', 'hello')
                    self.assertEqual(raised.exception.code, value['error']['code'])
                elif codec == 'receipt-discriminators':
                    try:
                        outcome = 'managed' if client.managed_receipt(value) else 'standalone'
                    except REFUSAL:
                        outcome = 'reject'
                    self.assertEqual(outcome, expected)
                elif codec == 'uuid':
                    identifier = value['request']['request']['operation_id']
                    try:
                        client.canonical_operation(identifier, now=value.get('reference_unix_seconds'))
                        outcome = 'accept'
                    except REFUSAL as exc:
                        outcome = exc.code
                    self.assertEqual(outcome, expected)
                    if outcome != 'storage_invalid':
                        self.assertEqual((int(identifier.replace('-', ''), 16) >> 80)//1000-value['reference_unix_seconds'], value['offset_seconds'])
                elif codec == 'identity':
                    client.validate(value, 'stamp' if expected == 'stamp' else 'identity')
                    self.assertEqual(normalized(value, 'stamp' if expected == 'stamp' else 'identity'), value)
                elif codec == 'pipe_digest':
                    self.assertEqual(client.pipe_name(value['sid'], value['canonical_control_directory']), value['pipe'])
                    self.assertEqual(hashlib.sha256((value['sid']+'\0'+value['canonical_control_directory']).encode()).hexdigest(), value['sha256'])
                elif codec in {'adapter:allocate', 'adapter:reconcile-for-removal', 'adapter:capabilities', 'adapter:unenroll'}:
                    try:
                        back = adapter['validate_request'](codec.split(':')[1], value, windows='-windows' in vector['path'])
                    except adapter['StorageRefusal']:
                        self.assertIn(expected, {'reject', 'invalid'})
                    else:
                        self.assertEqual(expected, 'decode')
                        self.assertEqual(back, value)
                elif codec in {'adapter:result', 'adapter:failure'}:
                    try:
                        back = adapter['decode_reply'](json.dumps(value, ensure_ascii=False).encode()+b'\n', value['op'], 2 if 'error' in value else 0)
                    except adapter['StorageRefusal'] as exc:
                        self.assertEqual(codec, 'adapter:failure')
                        self.assertEqual(value['error']['code'], expected)
                        self.assertEqual(exc.code, 'storage_invalid')
                    else:
                        self.assertIn(value['op'], {expected, 'reconcile-for-removal'})
                        self.assertEqual(back, value['result'])
                elif codec.startswith('adapter:unenroll-'):
                    self.check_unenroll(value, codec, expected)
                else:
                    self.fail('unhandled codec '+codec)
        self.assertEqual(seen, {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}-{'manifest.json', 'SHA256SUMS', 'DIGEST'})

    def check_unenroll(self, value, codec, expected):
        client.validate(value, {'adapter_protocol': 'u32', 'op': ('unenroll',)})
        if codec == 'adapter:unenroll-failure':
            client.validate(value['error'], {'code': 'str', 'phase': 'str', 'retryable': 'bool', 'receipt': 'str?', 'diagnostic': 'str'})
            self.assertEqual(value['error']['code'], expected)
        elif codec == 'adapter:unenroll-cancel-result':
            client.validate(value['result'], {'cancelled': 'bool'})
        else:
            client.validate(value['result'], {'schema': 'u32', 'operation_id': 'str', 'retired': 'bool',
                'root_identity': 'identity', 'lock_identity': 'identity',
                'archives': [{'source': 'str', 'destination': 'str', 'identity': 'identity', 'sha256': 'str'}]})

    def check_frame(self, raw, codec, expected):
        request = codec == 'frame:request'
        if expected in {'UnexpectedEof', 'malformed', 'InvalidData', 'response_too_large'}:
            if expected == 'UnexpectedEof':
                self.assertFalse(raw.endswith(b'\n'))
                with self.assertRaises(REFUSAL):
                    client.decode_reply(raw, 'hello')
            elif expected == 'InvalidData':
                self.assertGreater(len(raw)-1, client.MAX_REQUEST)
                with self.assertRaises(REFUSAL):
                    client.encode_request(client.loads(raw)['request'])
            elif expected == 'response_too_large':
                self.assertGreater(len(raw), client.MAX_REPLY)
                with self.assertRaises(REFUSAL):
                    client.decode_reply(raw, 'hello')
            else:
                with self.assertRaises(REFUSAL):
                    client.loads(raw)
            return
        value = client.loads(raw)
        self.assertEqual(json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode()+b'\n', raw)
        if request:
            self.assertEqual(len(raw)-1, client.MAX_REQUEST)
            self.assertEqual(json.loads(client.encode_request(value['request'])), value)
        elif expected == 'decode':
            self.assertEqual(len(raw), client.MAX_REPLY)
            self.assertIsInstance(value['ok'], str)
        elif expected in {'busy', 'BrokenPipe'}:
            with self.assertRaises(REFUSAL) as raised:
                client.decode_reply(raw, 'hello')
            self.assertEqual(raised.exception.code, 'storage_busy')
            if expected == 'BrokenPipe':
                reader, writer = os.pipe()
                os.close(reader)
                try:
                    with self.assertRaises(OSError) as raised:
                        os.write(writer, raw)
                    self.assertIn(raised.exception.errno, (errno.EPIPE, errno.EINVAL) if os.name == 'nt' else (errno.EPIPE,))
                finally:
                    os.close(writer)
        else:
            self.fail('unhandled frame outcome '+expected)


FAULT_DRIVER = r'''
import json, os, runpy, subprocess, sys
from pathlib import Path
from types import SimpleNamespace
shared, config_path = sys.argv[1:]
config = json.loads(Path(config_path).read_text())
helper = runpy.run_path(str(Path(shared) / 'task-complete.py'))
env = helper['allocate'].__globals__
schedule = config['schedule']
def pause(label, **extra):
    if label == schedule:
        Path(config['ready']).write_text(json.dumps({'label': label, **extra}))
        sys.stdin.buffer.read(1)  # Parent kills only this client, never its helper.
        raise AssertionError('fault client was released instead of killed')
atomic = env['atomic_json']
def save(path, receipt):
    atomic(path, receipt)
    state = receipt.get('storage', {})
    if path.name == 'receipt.json':
        if receipt.get('allocation') == 'managed_pending' and 'result' not in state:
            pause('allocate_intent_persisted')
        if receipt.get('allocation') == 'managed_owned' and 'removal_request' not in state:
            pause('allocate_receipt_sync')
        if 'removal_request' in state and 'removal_result' not in state:
            pause('removal_fence_persisted')
        if state.get('removal_finished') and receipt.get('status') != 'ABANDONED':
            pause('removal_finish_persisted')
env['atomic_json'] = save
call = env['storage_call']
run = subprocess.run
def sent(argv, **kwargs):
    if schedule == 'allocate_adapter_call_sent' and 'storage-checkout' in argv and 'allocate' in argv:
        raw = kwargs.pop('input')
        kwargs['stdout'] = open(str(config_path) + '.helper-reply', 'wb')
        kwargs['stderr'] = open(str(config_path) + '.helper-error', 'wb')
        process = subprocess.Popen(argv, stdin=subprocess.PIPE, **kwargs)
        process.stdin.write(raw)
        process.stdin.close()
        pause(schedule, helper_pid=process.pid)
    return run(argv, **kwargs)
subprocess.run = sent
def storage_call(name, *args, **kwargs):
    result = call(name, *args, **kwargs)
    if name == 'call' and kwargs.get('adapter') and args[1] == 'allocate':
        pause('allocate_reply_lost')
    return result
env['storage_call'] = storage_call
rpc = env['storage_rpc']
def storage_rpc(registration, request, path=None):
    if request['op'] == 'finish_removal':
        pause('removal_before_finish')
    result = rpc(registration, request, path)
    if request['op'] == 'begin_removal':
        pause('removal_begin_sent')
    return result
env['storage_rpc'] = storage_rpc
unlink = os.unlink
def deleting(name, *args, **kwargs):
    result = unlink(name, *args, **kwargs)
    if kwargs.get('dir_fd') is not None and name == '.gitignore':
        pause('removal_partial_deletion')
    return result
os.unlink = deleting
try:
    if schedule.startswith('allocate_'):
        helper['allocate'](SimpleNamespace(**config['args']))
    else:
        helper['recover_storage'](SimpleNamespace(receipt=config['receipt'], for_removal=True))
except helper['CompletionError'] as exc:
    print('REAL HELPER DIAGNOSTIC:', getattr(exc.__cause__, 'diagnostic', str(exc)), flush=True)
    raise
raise AssertionError('fault handoff was not reached: ' + schedule)
'''


class RealAdapterTests(unittest.TestCase):
    """Private-home tests execute the supplied devlynd; never substitute a helper."""
    def setUp(self):
        binary = os.environ.get('DEVLYND_BIN')
        if not binary or not Path(binary).is_file():
            self.skipTest('DEVLYND_BIN absent; real helper required')
        source_binary = Path(binary).resolve()
        temporary = tempfile.TemporaryDirectory(prefix='scr-', dir='/private/tmp' if sys.platform == 'darwin' else None)
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        staged = self.root/('devlynd.exe' if os.name == 'nt' else 'devlynd')
        shutil.copyfile(source_binary, staged)
        staged.chmod(0o755)
        self.assertEqual(client.regular_digest(staged), client.regular_digest(source_binary))
        self.binary = str(staged)
        self.home = self.root/'home'
        self.home.mkdir()
        clean_env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        env = patch.dict(os.environ, {**clean_env, 'HOME': str(self.home), 'USERPROFILE': str(self.home),
            'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_CONFIG_NOSYSTEM': '1',
            'GIT_ALLOW_PROTOCOL': 'file', 'GIT_AUTHOR_NAME': 'Fixture', 'GIT_AUTHOR_EMAIL': 'fixture@example.invalid',
            'GIT_COMMITTER_NAME': 'Fixture', 'GIT_COMMITTER_EMAIL': 'fixture@example.invalid'}, clear=True)
        env.start()
        self.addCleanup(env.stop)
        self.repo = self.root/'repo'
        self.repo.mkdir()
        self.git('init', '-q', '-b', 'main')
        (self.repo/'.gitignore').write_text('target/\n.devlyn/\n')
        (self.repo/'Cargo.toml').write_text('[package]\nname="adapter_fixture"\nversion="0.1.0"\nedition="2021"\n')
        (self.repo/'src').mkdir()
        (self.repo/'src/lib.rs').write_text('pub fn fixture() {}\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'baseline')
        self.baseline = self.git('rev-parse', 'HEAD')
        self.helper = runpy.run_path(str(SHARED/'task-complete.py'))
        self.adapter = runpy.run_path(str(SHARED/'storage-checkout.py'))
        self.control = self.home/'.devlyn/control'
        self.control.mkdir(parents=True, mode=0o700)
        recovery = self.home/'.devlyn/recovery'
        recovery.mkdir()
        (recovery/'nested').mkdir()
        (recovery/'nested/runtime.txt').write_bytes(b'nested retained bytes')
        (recovery/'contract.json').write_bytes((ROOT/'config/storage-client-contract.json').read_bytes())
        digest = client.regular_digest(self.binary)
        self.registration = {'schema': 1, 'control_directory': str(self.control),
            'control_identity': client.persistent_identity(self.control), 'helper_path': self.binary,
            'helper_release': {'version': '0.1.0', 'target': sys.platform, 'sha256': digest},
            'recovery_release': {'package': 'devlyn-cli', 'version': '4.3.21', 'digest': 'fixture', 'root': str(recovery)},
            'retained_helper': {'path': self.binary, 'identity': client.persistent_identity(self.binary), 'sha256': digest},
            'retained_recovery': {'path': str(recovery), 'identity': client.persistent_identity(recovery), 'sha256': client.package_digest(recovery)}}
        self.enrollment_path = self.home/'.devlyn/storage-client.json'
        self.enrollment_path.write_text(json.dumps(self.registration))
        write_recovery_pins(self.home, self.registration)
        self.log = (self.root/'service.log').open('w+b')
        self.addCleanup(self.log.close)
        if os.name == 'nt':
            # Both Python enrollment and Rust registry discovery must use USERPROFILE.
            os.environ.update(HOMEDRIVE='Z:', HOMEPATH='\\wrong-profile')
        self.service_env = dict(os.environ)
        self.start_service()
        self.addCleanup(self.stop_service)

    def start_service(self):
        self.service = subprocess.Popen([self.binary, 'control', 'serve', '--dir', str(self.control)],
                                        stdin=subprocess.PIPE, stdout=self.log, stderr=self.log, env=self.service_env)
        deadline = time.monotonic()+15
        while time.monotonic() < deadline:
            if self.service.poll() is not None:
                self.log.seek(0)
                self.fail('real service exited: '+self.log.read().decode(errors='replace'))
            try:
                client.Client(self.control).call({'op': 'hello'})
                break
            except REFUSAL:
                time.sleep(0.02)
        else:
            self.fail('real authority did not become ready')

    def stop_service(self):
        if self.service.poll() is None:
            self.service.terminate()
            try:
                self.service.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.service.kill()
                self.service.wait(timeout=5)
        self.service.stdin.close()

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.repo), *args], capture_output=True, text=True, check=True).stdout.strip()

    def args(self, *, local=True):
        return SimpleNamespace(repo=str(self.repo), task='adapter fixture', branch='task/adapter', base=None,
            remote='origin', repository=None, worktree=str(self.root/'checkout'), keep_root=None,
            local_base=self.baseline if local else None, from_receipt=None, start=None)

    def allocate(self, *, local=True):
        try:
            return self.helper['allocate'](self.args(local=local))
        except self.helper['CompletionError'] as exc:
            if exc.__cause__ is not None and hasattr(exc.__cause__, 'diagnostic'):
                print('REAL HELPER DIAGNOSTIC:', exc.__cause__.diagnostic, file=sys.stderr)
            raise

    def test_enrollment_with_absent_registry_still_requires_authority(self):
        self.assertFalse((self.home/'.devlyn/storage/v1/registry.json').exists())
        self.assertEqual(client.enrollment()['mode'], 'managed')
        self.stop_service()
        with self.assertRaises(self.helper['CompletionError']):
            self.allocate()
        self.assertFalse((self.root/'checkout').exists())
        self.assertEqual(self.git('branch', '--list', 'task/adapter'), '')

    def test_delegated_checkout_uses_exact_remote_or_local_baseline(self):
        # Main HEAD deliberately differs from the requested immutable baseline.
        (self.repo/'later').write_text('later')
        self.git('add', '.')
        self.git('commit', '-qm', 'later')
        result = self.allocate()
        path = Path(result['receipt'])
        receipt = json.loads(path.read_bytes())
        self.assertEqual(receipt['storage']['request']['baseline'], self.baseline)
        self.assertEqual(receipt['allocation'], 'managed_owned')
        self.assertFalse((self.root/'checkout/later').exists())
        self.assertTrue(result['build_dirs'])
        self.assertTrue(all(row['cache_id'] and row['lease_id'] for row in result['build_dirs']))

    def test_managed_checkout_never_runs_unreserved_git(self):
        original = self.helper['command']
        commands = []
        def checked(argv, **kwargs):
            commands.append(argv)
            self.assertFalse('worktree' in argv and 'add' in argv, argv)
            return original(argv, **kwargs)
        with patch.dict(self.helper['allocate'].__globals__, {'command': checked}), patch.object(
                self.helper['shutil'], 'disk_usage', side_effect=AssertionError('standalone disk precheck')):
            result = self.allocate()
        self.assertEqual(result['status'], 'ALLOCATED')
        self.assertTrue(commands)

    def test_lost_helper_reply_reuses_v3_receipt_without_second_checkout(self):
        call = self.helper['storage_call']
        saved_requests = []
        def lose(name, *args, **kwargs):
            result = call(name, *args, **kwargs)
            if kwargs.get('adapter') and name == 'call' and args[1] == 'allocate':
                saved_requests.append(args[2].copy())
                raise self.helper['CompletionError']('lost helper reply; replay original receipt')
            return result
        with patch.dict(self.helper['allocate'].__globals__, {'storage_call': lose}):
            with self.assertRaises(self.helper['CompletionError']):
                self.allocate()
        key = hashlib.sha256(b'task/adapter').hexdigest()[:24]
        path = self.repo/'.git/devlyn-completion'/key/'receipt.json'
        pending = json.loads(path.read_bytes())
        self.assertEqual(pending['allocation'], 'managed_pending')
        rust_path = path.with_name('storage-allocation.json')
        rust = rust_path.read_bytes()
        first = json.loads(rust)
        result = self.allocate()
        receipt = json.loads(path.read_bytes())
        self.assertEqual(receipt['storage']['request'], saved_requests[0])
        self.assertEqual(rust_path.read_bytes(), rust)
        self.assertEqual(receipt['storage']['result']['publications'], first['publications'])
        self.assertEqual(result['status'], 'ALLOCATED')

    def test_completed_adapter_replay_returns_original_cache_and_lease_ids(self):
        result = self.allocate()
        receipt = json.loads(Path(result['receipt']).read_bytes())
        state = receipt['storage']
        replay = self.adapter['call'](self.registration, 'allocate', state['request'])
        self.assertEqual(replay, state['result'])

    def test_removal_fence_precedes_reconciliation_and_blocks_reallocation(self):
        result = self.allocate()
        path = Path(result['receipt'])
        with self.helper['locked_receipt'](path) as receipt:
            self.helper['managed_removal_gate'](receipt, path)
            rust = json.loads(path.with_name('storage-allocation.json').read_bytes())
            self.assertEqual(rust['removal_operation_id'], receipt['storage']['removal_request']['removal_operation_id'])
            self.assertEqual(rust['removal_reconciliation']['cache_ids'], receipt['storage']['removal_result']['cache_ids'])
            with self.assertRaises(self.adapter['StorageRefusal']):
                self.adapter['call'](self.registration, 'allocate', receipt['storage']['request'])
        with self.assertRaises(self.helper['CompletionError']):
            self.allocate()
        self.assertTrue((self.root/'checkout').exists())

    def test_empty_cache_removal_requires_positive_reservation_closure(self):
        self.git('rm', '-r', 'Cargo.toml', 'src')
        self.git('commit', '-qm', 'non cargo')
        self.baseline = self.git('rev-parse', 'HEAD')
        result = self.allocate()
        path = Path(result['receipt'])
        with self.helper['locked_receipt'](path) as receipt:
            self.assertEqual(receipt['storage']['result']['publications'], [])
            self.helper['managed_removal_gate'](receipt, path)
            self.assertEqual(receipt['storage']['removal_result']['cache_ids'], [])
            self.assertEqual(receipt['storage']['removal_result']['closure_result']['established_by'], 'released')
            self.assertNotIn('begin_removal', receipt['storage'])
            request = receipt['storage']['removal_request']
            self.stop_service()
            # Durable adapter closure replays even while the authority is offline.
            replay = self.adapter['call'](self.registration, 'reconcile-for-removal', request)
            self.assertEqual(replay, receipt['storage']['removal_result'])

    def test_failed_pending_allocation_without_rust_receipt_can_be_abandoned(self):
        (self.repo / '.gitattributes').write_text('*.rs filter=fixture\n')
        self.git('add', '.gitattributes')
        self.git('commit', '-qm', 'unknown checkout size')
        self.git('config', 'filter.fixture.required', 'true')
        self.baseline = self.git('rev-parse', 'HEAD')
        with self.assertRaises(self.helper['CompletionError']):
            self.allocate()
        path, = (self.repo / '.git/devlyn-completion').glob('*/receipt.json')
        result = self.helper['recover_storage'](SimpleNamespace(receipt=str(path), for_removal=True))
        self.assertEqual(result['status'], 'ABANDONED')
        self.assertFalse(path.exists())
        self.assertTrue(Path(result['receipt']).exists())
        self.assertFalse((self.root / 'checkout').exists())

    def test_current_pins_recovery_survives_original_helper_and_enrollment_removal(self):
        original = self.root / ('original-devlynd.exe' if os.name == 'nt' else 'original-devlynd')
        shutil.copyfile(self.binary, original)
        original.chmod(0o755)
        self.registration['helper_path'] = str(original)
        self.enrollment_path.write_text(json.dumps(self.registration))
        result = self.allocate()
        path = Path(result['receipt'])
        original.unlink()
        with self.assertRaises(REFUSAL):
            client.enrollment()
        self.enrollment_path.unlink()
        if os.name == 'nt':
            with self.assertRaisesRegex(self.helper['CompletionError'], 'remove the task checkout by hand'):
                self.helper['recover_storage'](SimpleNamespace(receipt=str(path), for_removal=True))
            self.assertTrue(Path(result['worktree']).exists())
            self.assertTrue(path.exists())
            return
        recovered = self.helper['recover_storage'](SimpleNamespace(receipt=str(path), for_removal=True))
        self.assertEqual(recovered['status'], 'ABANDONED')
        self.assertFalse(Path(result['worktree']).exists())
        self.assertTrue(Path(recovered['receipt']).with_name('storage-allocation.json').exists())

    def test_scratch_cleanup_keeps_live_cache_active(self):
        result = self.allocate()
        path = Path(result['receipt'])
        with self.helper['locked_receipt'](path) as receipt:
            scratch = path.parent / 'scratch'
            (scratch / 'disposable').write_bytes(b'bytes')
            with patch.dict(self.helper['clean_scratch'].__globals__, stopped_writers=lambda work: None, scratch_mounts=lambda: []):
                if os.name == 'nt':
                    with self.assertRaisesRegex(self.helper['CompletionError'], 'safe scratch removal unsupported'):
                        self.helper['clean_scratch'](receipt, path, True)
                    self.assertEqual((scratch / 'disposable').read_bytes(), b'bytes')
                else:
                    cleaned = self.helper['clean_scratch'](receipt, path, True)
                    self.assertEqual(cleaned['status'], 'CLEAN')
            self.assertNotIn('removal_request', receipt['storage'])
            publication = receipt['storage']['result']['publications'][0]
            snapshot = client.Client(self.control).call({'op': 'query', 'cache_id': publication['cache']['cache_id']})
            self.assertEqual(snapshot['cache']['state'], 'active')

    @contextlib.contextmanager
    def fault_diagnostics(self, schedule):
        try:
            yield
        except self.helper['CompletionError'] as exc:
            diagnostic = getattr(exc.__cause__, 'diagnostic', str(exc))
            print('REAL FAULT BLOCKED:', schedule, diagnostic, file=sys.stderr)
            raise

    @unittest.skipIf(os.name == 'nt', 'kill/removal matrix uses POSIX; Windows retains trees')
    def test_managed_handoff_fault_matrix_with_real_helper(self):
        schedules = ('allocate_intent_persisted', 'allocate_adapter_call_sent', 'allocate_reply_lost', 'allocate_receipt_sync',
                     'removal_fence_persisted', 'removal_begin_sent', 'removal_partial_deletion', 'removal_before_finish', 'removal_finish_persisted',
                     'accept_storage_outage', 'complete_storage_outage', 'cacheless_storage_outage')
        for number, schedule in enumerate(schedules):
            with self.subTest(schedule=schedule), self.fault_diagnostics(schedule):
                if schedule.endswith('storage_outage'):
                    fixture = self.helper['CompletionTests']('test_standalone_without_devlyn_keeps_existing_allocation_and_warm_behavior')
                    fixture.setUp()
                    try:
                        if schedule != 'cacheless_storage_outage':
                            with (fixture.work / '.gitignore').open('a', encoding='utf-8') as ignore:
                                ignore.write('target/\n')
                            (fixture.work / 'Cargo.toml').write_text('[package]\nname="outage_fixture"\nversion="0.1.0"\nedition="2021"\n')
                            (fixture.work / 'src').mkdir()
                            (fixture.work / 'src/lib.rs').write_text('pub fn fixture() {}\n')
                            fixture.g('add', '.')
                            fixture.g('commit', '-m', 'Cargo outage fixture')
                            fixture.g('push', 'origin', 'main')
                        environment = {**fixture.env, 'HOME': str(self.home), 'USERPROFILE': str(self.home)}
                        # Rust correctly rejects every GIT_CONFIG_COUNT override,
                        # including the standalone fixture's zero-valued sentinel.
                        environment.pop('GIT_CONFIG_COUNT', None)
                        fixture.env = environment
                        with patch.dict(os.environ, environment, clear=True):
                            args = fixture.allocation_args('fixture', self.root / ('delivery-' + str(number)))
                            allocated = self.helper['allocate'](args)
                            self.assertEqual(bool(allocated['build_dirs']), schedule != 'cacheless_storage_outage', allocated)
                            allocation_ids = [(p['cache_id'], p['lease_id']) for p in allocated['build_dirs']]
                            path = fixture.receipt = Path(allocated['receipt'])
                            publications = json.loads(path.read_text())['storage']['result']['publications']
                            self.assertEqual(allocation_ids, [(p['cache']['cache_id'], p['lease']['lease_id']) for p in publications])
                            fixture.task = Path(allocated['worktree'])
                            fixture.accept()
                            if schedule == 'complete_storage_outage':
                                self.helper['accept'](SimpleNamespace(receipt=str(path), acceptance=str(fixture.acceptance)))
                            self.stop_service()
                            # Source custody and delivery use real Git/fake GitHub;
                            # every storage call still uses the real helper/authority.
                            accepted = self.helper['accept'](SimpleNamespace(receipt=str(path), acceptance=str(fixture.acceptance)))
                            self.assertEqual(accepted['status'], 'ACCEPTED')
                            opts = SimpleNamespace(receipt=str(path), acceptance=None, mode='auto', local_only=False, writers_stopped=True)
                            delivered = self.helper['complete'](opts)
                            expected = 'COMPLETE' if schedule == 'cacheless_storage_outage' else 'CLEANUP_PENDING'
                            self.assertEqual((delivered['status'], delivered['delivery_status']), (expected, 'COMPLETE'), delivered)
                            if expected == 'CLEANUP_PENDING':
                                self.assertTrue(delivered['workspace_cleanup']['resume'])
                            saved = json.loads(Path(delivered['receipt']).read_text())
                            ids = [(p['cache']['cache_id'], p['lease']['lease_id']) for p in saved['storage']['result']['publications']]
                            self.assertEqual(ids, allocation_ids)
                            self.assertEqual(bool(ids), schedule != 'cacheless_storage_outage')
                            self.start_service()
                            completed = self.helper['complete'](opts)
                            self.assertEqual(completed['status'], 'COMPLETE', completed)
                            audit = json.loads(Path(completed['receipt']).read_text())
                            self.assertEqual(ids, [(p['cache']['cache_id'], p['lease']['lease_id']) for p in audit['storage']['result']['publications']])
                            self.assertTrue(audit['storage']['removal_finished'])
                            self.assertCountEqual(audit['storage']['removal_result']['cache_ids'], [cache for cache, lease in allocation_ids])
                            self.assertFalse(fixture.task.exists())
                    finally:
                        if self.service.poll() is not None:
                            self.start_service()
                        fixture.doCleanups()
                    continue
                args = self.args()
                args.branch = 'task/fault-' + str(number)
                args.worktree = str(self.root / ('fault-' + str(number)))
                key = hashlib.sha256(args.branch.encode()).hexdigest()[:24]
                path = self.repo / '.git/devlyn-completion' / key / 'receipt.json'
                if schedule.startswith('removal_'):
                    self.helper['allocate'](args)
                config_path = self.root / ('fault-' + str(number) + '.json')
                ready = self.root / ('ready-' + str(number))
                config_path.write_text(json.dumps({'schedule': schedule, 'args': vars(args), 'receipt': str(path), 'ready': str(ready)}))
                with (self.root / ('client-' + str(number) + '.log')).open('w+b') as log:
                    child = subprocess.Popen([sys.executable, '-B', '-c', FAULT_DRIVER, str(SHARED), str(config_path)],
                                             stdin=subprocess.PIPE, stdout=log, stderr=log)
                    try:
                        deadline = time.monotonic() + 30
                        while not ready.exists() and child.poll() is None and time.monotonic() < deadline:
                            time.sleep(0.02)
                        log.seek(0)
                        self.assertTrue(ready.exists(), f'{schedule}: client did not reach handoff: ' + log.read().decode(errors='replace'))
                        handoff = json.loads(ready.read_text())
                        child.kill()
                        self.assertLess(child.wait(timeout=10), 0)
                    finally:
                        if child.poll() is None:
                            child.kill()
                            child.wait(timeout=10)
                        child.stdin.close()
                before = json.loads(path.read_text())
                request = before['storage']['request']
                removal_request = before['storage'].get('removal_request')
                rust_path = path.with_name('storage-allocation.json')
                if 'helper_pid' in handoff:
                    # The sent helper remains an independent writer until its
                    # durable closure; do not launch a replay while it still runs.
                    deadline = time.monotonic() + 30
                    while time.monotonic() < deadline:
                        reply = config_path.with_name(config_path.name + '.helper-reply')
                        if reply.exists():
                            raw = reply.read_bytes()
                            if raw.endswith(b'\n') and 'error' in json.loads(raw):
                                self.fail(schedule + ': real sent helper refused: ' + raw.decode(errors='replace'))
                        if rust_path.exists():
                            rust = json.loads(rust_path.read_text())
                            if rust.get('closure_result') and rust.get('publications'):
                                break
                        time.sleep(0.02)
                    else:
                        diagnostic = config_path.with_name(config_path.name + '.helper-error').read_text(errors='replace')
                        self.fail(schedule + ': sent helper never persisted closure: ' + diagnostic)
                first_rust = json.loads(rust_path.read_text()) if rust_path.exists() else None
                if schedule.startswith('allocate_'):
                    allocated = self.helper['allocate'](args)
                    after = json.loads(path.read_text())
                    self.assertEqual(after['storage']['request'], request)
                    publications = after['storage']['result']['publications']
                    identity = client.persistent_identity(args.worktree)
                    self.assertEqual(self.helper['allocate'](args)['receipt'], allocated['receipt'])
                    self.assertEqual(client.persistent_identity(args.worktree), identity)
                    if first_rust:
                        self.assertEqual(publications, first_rust['publications'])
                    closure = after['storage']['result']['closure_result']
                    if closure['established_by'] == 'released':
                        reservation = client.Client(self.control).call({'op': 'query_reservation', 'operation_id': closure['reservation']['operation_id']})
                        self.assertEqual(reservation['workers'], closure['reservation']['workers'])
                        self.assertTrue(reservation.get('released_at'))
                    registrations = self.helper['registrations'](after)
                    self.assertEqual(sum(row.get('branch') == 'refs/heads/' + args.branch for row in registrations.values()), 1)
                    for p in publications:
                        snapshot = client.Client(self.control).call({'op': 'query', 'cache_id': p['cache']['cache_id']})
                        self.assertEqual([lease['lease_id'] for lease in snapshot['leases'] if not lease.get('released_at')], [p['lease']['lease_id']])
                        self.assertEqual(snapshot['cache']['state'], 'active')
                abandoned = self.helper['recover_storage'](SimpleNamespace(receipt=str(path), for_removal=True))
                audit_path = Path(abandoned['receipt'])
                audit = json.loads(audit_path.read_text())
                self.assertEqual(audit['storage']['request'], request)
                if removal_request:
                    self.assertEqual(audit['storage']['removal_request'], removal_request)
                self.assertTrue(audit['storage']['removal_finished'])
                self.assertEqual(sorted(audit['storage']['removal_result']['cache_ids']), sorted(
                    p['cache']['cache_id'] for p in audit['storage']['result']['publications']))
                if before['storage'].get('begin_removal'):
                    self.assertEqual(audit['storage']['begin_removal'], before['storage']['begin_removal'])
                self.assertFalse(Path(args.worktree).exists())
                self.assertFalse(path.exists())
                self.assertFalse(audit_path.with_name('tree-removal.json').exists())
                self.assertNotIn(str(Path(args.worktree)), self.helper['registrations'](audit))
                for cache_id in audit['storage']['removal_result']['cache_ids']:
                    snapshot = client.Client(self.control).call({'op': 'query', 'cache_id': cache_id})
                    self.assertEqual(snapshot['cache']['state'], 'deleted')
                    self.assertTrue(all(lease.get('released_at') for lease in snapshot['leases']))
                print('REAL FAULT REPLAY:', schedule, request['operation_id'], audit['storage']['removal_request']['removal_operation_id'],
                      audit['storage']['removal_result']['cache_ids'], file=sys.stderr)



class EnrollmentLifecycleTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='storage-lifecycle-')
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name).resolve()
        environment = patch.dict(os.environ, HOME=str(self.home), USERPROFILE=str(self.home))
        environment.start()
        self.addCleanup(environment.stop)
        self.root = self.home/'.devlyn'
        self.control = self.root/'control'
        self.control.mkdir(parents=True)
        recovery = self.root/'recovery'
        recovery.mkdir()
        (recovery/'nested').mkdir()
        (recovery/'nested/runtime.txt').write_bytes(b'nested retained bytes')
        (recovery/'contract.json').write_bytes((ROOT/'config/storage-client-contract.json').read_bytes())
        binary = str(Path(sys.executable).resolve())
        digest = client.regular_digest(binary)
        self.record = {'schema': 1, 'control_directory': str(self.control),
            'control_identity': client.persistent_identity(self.control), 'helper_path': binary,
            'helper_release': {'version': '1.2.3', 'target': sys.platform, 'sha256': digest},
            'recovery_release': {'package': 'devlyn-cli', 'version': '4.3.21', 'digest': 'fixture', 'root': str(recovery)},
            'retained_helper': {'path': binary, 'identity': client.persistent_identity(binary), 'sha256': digest},
            'retained_recovery': {'path': str(recovery), 'identity': client.persistent_identity(recovery), 'sha256': client.package_digest(recovery)}}
        self.path = self.root/'storage-client.json'
        self.path.write_text(json.dumps(self.record))
        self.pins_path = write_recovery_pins(self.home, self.record)

    def moved_retirement(self, *, retired=True):
        journal = write_retirement(self.home)
        journal['retired'] = retired
        pins = json.loads(self.pins_path.read_text())
        # The native move tests own real cross-volume proof; rewrite stored volumes only here.
        def old(value):
            if isinstance(value, dict):
                if set(value) == {'volume', 'file'}:
                    value['volume'] = 'old-volume'
                else:
                    for child in value.values():
                        old(child)
            elif isinstance(value, list):
                for child in value:
                    old(child)
        old(pins)
        old(journal)
        self.path.unlink()
        self.control.rmdir()
        self.pins_path.write_text(json.dumps(pins))
        (self.root / 'storage-client-unenroll.json').write_text(json.dumps(journal))
        (self.root / 'storage-client-fence.json').write_text(json.dumps({k: v for k, v in journal.items() if k not in {'archives', 'retired'}}))
        return journal, pins

    def test_newer_recovery_pins_refuse_as_unsupported_never_as_repairable(self):
        # Prediction: pins a newer Devlyn wrote (schema above 1 on the pins or their enrollment, with or without a
        # field this CLI does not know) refuse as storage_unsupported with the update sentence, in recovery and in
        # the moved-receipt check, and never ask to repair them; schema 0 stays an ordinary invalid pins refusal.
        original = self.pins_path.read_text()
        for name, change in (('pins', lambda pins: pins.update(schema=2)),
                             ('pins and unknown field', lambda pins: pins.update(schema=2, later={'shape': 2})),
                             ('enrollment', lambda pins: pins['enrollment'].update(schema=2))):
            with self.subTest(change=name):
                pins = json.loads(original)
                change(pins)
                self.pins_path.write_text(json.dumps(pins))
                with self.assertRaises(REFUSAL) as raised:
                    client.recovery_registration()
                self.assertEqual(raised.exception.code, 'storage_unsupported')
                self.assertEqual(str(raised.exception), client.REFUSAL_TEXT['storage_unsupported'])
                self.assertNotIn('repair', str(raised.exception))
        for schema in (0, True, '2'):
            pins = json.loads(original)
            pins['schema'] = schema
            self.pins_path.write_text(json.dumps(pins))
            with self.subTest(schema=schema), self.assertRaises(REFUSAL) as raised:
                client.recovery_registration()
            self.assertEqual(raised.exception.code, 'storage_unavailable')
        journal, moved = self.moved_retirement()
        for name, change in (('pins', lambda pins: pins.update(schema=2)),
                             ('enrollment', lambda pins: pins['enrollment'].update(schema=2))):
            newer = json.loads(json.dumps(moved))
            change(newer)
            self.pins_path.write_text(json.dumps(newer))
            with self.subTest(moved=name), self.assertRaises(REFUSAL) as raised:
                client.moved_operation(moved['enrollment'])
            self.assertEqual(raised.exception.code, 'storage_unsupported')
            self.assertEqual(str(raised.exception), client.REFUSAL_TEXT['storage_unsupported'])

    def test_newer_pins_reach_retirement_and_the_queue_hold_as_an_update(self):
        # Prediction: an unfinished retirement and a queue hold over a managed receipt both pass the newer pins'
        # storage_unsupported refusal on unchanged, whether or not the receipt has an adapter marker.
        journal, pins = self.moved_retirement(retired=False)
        pins['schema'] = 2
        self.pins_path.write_text(json.dumps(pins))
        with self.assertRaises(REFUSAL) as raised:
            client.retirement_refusal()
        self.assertEqual(raised.exception.code, 'storage_unsupported')
        common = self.home / 'common'
        receipt = common / 'devlyn-completion/task/receipt.json'
        receipt.parent.mkdir(parents=True)
        binding = {key: pins['enrollment'][key] for key in ('control_directory', 'control_identity')}
        receipt.write_text(json.dumps({'allocation': 'managed_pending', 'storage': {
            'decision': {'registration': binding}, 'request': {'operation_id': client.operation_id()}}}))
        reference = {'release': {'root': str(self.home), 'package': 'devlyn-cli', 'version': '4.3.20', 'digest': 'a'*64}}
        for marker in (False, True):
            if marker:
                (receipt.parent / 'storage-allocation.json').touch()
            with self.subTest(marker=marker), patch.object(client, 'operation_enrollment', return_value={'mode': 'standalone'}), \
                 patch.object(client, 'recovery_marker', return_value=True):
                self.assertEqual(client.queue_handoff(common, reference),
                                 f"{receipt}: {client.REFUSAL_TEXT['storage_unsupported']}")

    def test_retired_moved_home_bootstraps_from_retained_bytes(self):
        journal, pins = self.moved_retirement()
        self.assertEqual(client.recovery_registration(), pins['enrollment'])
        self.assertEqual(client.moved_operation(pins['enrollment']), journal['operation_id'])
        self.assertEqual(set(json.loads(self.pins_path.read_text())), {'schema', 'enrollment', 'runtime', 'node'})
        # Lost retirement reply: authenticate by bytes, replay the same operation,
        # and require the helper to commit the journal before task reconciliation.
        journal['retired'] = False
        journal_path = self.root / 'storage-client-unenroll.json'
        journal_path.write_text(json.dumps(journal))
        def replay(argv, **kwargs):
            self.assertEqual(argv, [pins['enrollment']['retained_helper']['path'],
                                   'storage-client', 'unenroll', '--reconcile', '--json'])
            self.assertEqual(json.loads(kwargs['input'])['operation_id'], journal['operation_id'])
            journal['retired'] = True
            journal_path.write_text(json.dumps(journal))
            kwargs['stdout'].write(json.dumps({'adapter_protocol': 1, 'op': 'unenroll',
                'result': journal}).encode()+b'\n')
            return SimpleNamespace(returncode=0)
        with patch.object(client.subprocess, 'run', side_effect=replay):
            client.replay_retirement(client.recovery_registration())
        # Malformed enrollment metadata is NotMoved, never a digest-only bootstrap.
        for keys, value in ((('helper_release', 'version'), 'not-semver'),
                            (('helper_release', 'target'), ''),
                            (('helper_release', 'sha256'), 'changed'),
                            (('recovery_release', 'package'), 'another-package'),
                            (('recovery_release', 'version'), ''),
                            (('recovery_release', 'digest'), '')):
            changed = json.loads(json.dumps(pins))
            changed['enrollment'][keys[0]][keys[1]] = value
            self.pins_path.write_text(json.dumps(changed))
            with self.subTest(keys=keys), self.assertRaises(REFUSAL):
                client.recovery_registration()
        self.pins_path.write_text(json.dumps(pins))
        # No identity-only bootstrap on a same-volume replacement, mixed set or changed bytes.
        changed = json.loads(json.dumps(pins))
        changed['runtime']['identity']['volume'] = client.persistent_identity(self.root)['volume']
        self.pins_path.write_text(json.dumps(changed))
        with self.assertRaises(REFUSAL):
            client.recovery_registration()
        self.pins_path.write_text(json.dumps(pins))
        Path(pins['node']).write_bytes(b'tampered')
        with self.assertRaises(REFUSAL):
            client.recovery_registration()

    def test_retirement_replay_refusal_keeps_operation_specific_resume(self):
        journal, pins = self.moved_retirement(retired=False)
        before = (self.root / 'storage-client-unenroll.json').read_bytes()
        reply = {'adapter_protocol': 1, 'op': 'unenroll', 'error': {'code': 'storage_protected',
                 'phase': 'reconcile', 'retryable': False, 'receipt': 'storage-client-unenroll.json',
                 'diagnostic': 'retirement blocked'}}
        def refuse(argv, **kwargs):
            kwargs['stdout'].write(json.dumps(reply).encode()+b'\n')
            return SimpleNamespace(returncode=2 if 'error' in reply else 0)
        for result in ('native-refusal', None, [], {}, {'operation_id': client.operation_id(), 'retired': True},
                       {'operation_id': journal['operation_id'], 'retired': False}):
            if result != 'native-refusal':
                reply = {'adapter_protocol': 1, 'op': 'unenroll', 'result': result}
            with self.subTest(result=result), patch.object(client.subprocess, 'run', side_effect=refuse), self.assertRaises(REFUSAL) as raised:
                client.replay_retirement(client.recovery_registration())
            self.assertIn(journal['operation_id'], raised.exception.resume)
            self.assertIn('--reconcile', raised.exception.resume)
        self.assertEqual((self.root / 'storage-client-unenroll.json').read_bytes(), before)

    def test_fence_refusal_names_replay_or_cancel(self):
        journal, pins = self.moved_retirement(retired=False)
        with self.assertRaises(REFUSAL) as raised:
            client.operation_enrollment()
        argv = shlex.split(raised.exception.resume)
        self.assertEqual(argv[-5:], [pins['enrollment']['retained_helper']['path'], 'storage-client', 'unenroll', '--reconcile', '--json'])
        self.assertEqual(json.loads(argv[2])['operation_id'], journal['operation_id'])
        self.assertNotIn('--cancel', argv)
        (self.root / 'storage-client-unenroll.json').unlink()
        with self.assertRaises(REFUSAL) as raised:
            client.operation_enrollment()
        self.assertIn('--cancel', shlex.split(raised.exception.resume))
        self.assertEqual(json.loads(shlex.split(raised.exception.resume)[2])['operation_id'], journal['operation_id'])
        # An intact fence offers reconciliation and names cancellation separately;
        # the resume itself must remain one executable operation-specific command.
        write_recovery_pins(self.home, self.record)
        fence = {key: journal[key] for key in ('schema', 'operation_id', 'root_identity', 'lock_identity')}
        fence.update(root_identity=client.persistent_identity(self.root),
                     lock_identity=client.persistent_identity(self.root / 'storage-client.lock'))
        (self.root / 'storage-client-fence.json').write_text(json.dumps(fence))
        with self.assertRaises(REFUSAL) as raised:
            client.operation_enrollment()
        argv = shlex.split(raised.exception.resume)
        self.assertEqual(argv[-5:], [self.record['retained_helper']['path'], 'storage-client', 'unenroll', '--reconcile', '--json'])
        self.assertNotIn(';', raised.exception.resume)
        self.assertIn('--cancel', str(raised.exception))

    def test_unlisted_changed_binding_still_refuses(self):
        helper = runpy.run_path(str(SHARED / 'task-complete.py'))
        changed = {**self.record, 'control_identity': {'volume': 'other', 'file': 'other'}}
        receipt = {'storage': {'decision': {'registration': changed}, 'request': {'external_receipt': str(self.home / 'receipt.json')}}}
        for recovery in (False, True):
            with self.subTest(recovery=recovery), self.assertRaisesRegex(helper['CompletionError'], 'binding changed'):
                helper['managed_registration'](receipt, recovery=recovery)

    def test_move_manifest_requires_exact_binding_and_current_takes_precedence(self):
        operation = client.operation_id()
        archive = self.root / 'storage-client-moved' / operation
        archive.mkdir(parents=True)
        binding = {key: self.record[key] for key in ('control_directory', 'control_identity')}
        manifest = {'schema': 1, 'operation_id': operation, 'from_volume': binding['control_identity']['volume'],
                    'to_volume': 'another-volume', 'old_binding': binding}
        path = archive / 'storage-client-move.json'
        path.write_text(json.dumps(manifest))
        self.assertIsNone(client.moved_operation(binding))
        self.path.unlink()
        self.assertEqual(client.moved_operation(binding), operation)
        common = self.home / 'common'
        receipt = common / 'devlyn-completion/task/receipt.json'
        receipt.parent.mkdir(parents=True)
        allocation = client.operation_id()
        saved = {'allocation': 'managed_pending', 'storage': {'decision': {'registration': binding},
                 'request': {'operation_id': allocation}}}
        receipt.write_text(json.dumps(saved))
        (receipt.parent / 'storage-allocation.json').touch()
        with patch.object(client, 'operation_enrollment', return_value={'mode': 'standalone'}), \
             patch.object(client, 'recovery_marker', return_value=True):
            line = client.queue_handoff(common, {'release': {'root': str(self.home), 'package': 'devlyn-cli',
                                         'version': '4.3.20', 'digest': 'a'*64}})
        self.assertIn('recover-storage --receipt ' + shlex.quote(str(receipt)), line)
        self.assertIn('--operation-id ' + allocation, line)
        self.assertNotIn('--for-removal --receipt', line)
        helper = runpy.run_path(str(SHARED / 'task-complete.py'))
        with self.assertRaises(helper['CompletionError']) as raised:
            helper['refuse_moved'](saved, receipt)
        argv = shlex.split(raised.exception.storage_error['resume'])
        self.assertNotIn('--for-removal', argv)
        self.assertEqual(argv[-2:], ['--operation-id', allocation])
        for mutation in ({'schema': 2}, {'schema': True}, {'operation_id': client.operation_id()},
                         {'from_volume': manifest['to_volume']}, {'unknown': True},
                         {'old_binding': {**binding, 'unknown': True}}):
            path.write_text(json.dumps({**manifest, **mutation}))
            with self.subTest(mutation=mutation), self.assertRaises(REFUSAL):
                client.moved_operation(binding)
        path.write_text('[]')
        with self.assertRaises(REFUSAL):
            client.moved_operation(binding)
        path.write_text(json.dumps({**manifest, 'old_binding': None}))
        self.assertIsNone(client.moved_operation(binding))
        path.unlink()
        if os.name != 'nt':
            path.symlink_to(self.pins_path)
            with self.assertRaises(REFUSAL):
                client.moved_operation(binding)

    def test_never_published_pending_abandons_after_unenroll_with_current_pins(self):
        helper = runpy.run_path(str(SHARED / 'task-complete.py'))
        repo = self.home / 'repo'
        repo.mkdir()
        subprocess.run(['git', 'init', '-q', repo], check=True)
        common = repo / '.git'
        branch = 'task/never-published'
        key = hashlib.sha256(branch.encode()).hexdigest()[:24]
        receipt = common / 'devlyn-completion' / key / 'receipt.json'
        receipt.parent.mkdir(parents=True)
        saved = {'id': key, 'branch': branch, 'base': 'main', 'baseline': 'a'*40,
                 'common_gitdir': str(common), 'allocation': 'managed_pending', 'worktree': str(self.home / 'absent'),
                 'storage': {'decision': {'registration': self.record}, 'request': {
                    'operation_id': client.operation_id(), 'external_receipt': str(receipt)}}}
        receipt.write_text(json.dumps(saved))
        self.path.unlink()
        write_retirement(self.home)
        reference = {'release': {'package': 'devlyn-cli', 'version': '4.3.20', 'digest': 'a'*64, 'root': str(self.home)}}
        self.assertIn(str(receipt), client.queue_handoff(common, reference))
        with patch.dict(helper['recover_storage'].__globals__, storage_rpc=lambda *a: self.fail('authority RPC')), \
             patch.dict(helper['shared']('storage-checkout'), call=lambda *a: self.fail('adapter call')):
            result = helper['recover_storage'](SimpleNamespace(receipt=str(receipt), for_removal=True))
        self.assertEqual(result['status'], 'ABANDONED')
        self.assertEqual(Path(result['receipt']).parent.parent.name, 'retired')
        self.assertIsNone(client.queue_handoff(common, reference))

    def test_validate_closure_accepts_authority_migrated(self):
        adapter = runpy.run_path(str(SHARED / 'storage-checkout.py'))
        closure = {'established_by': 'authority_migrated', 'operation_id': client.operation_id()}
        self.assertEqual(adapter['validate_closure'](closure), closure)
        with self.assertRaises(adapter['StorageRefusal']):
            adapter['validate_closure']({'established_by': 'authority_migrated'})

    def test_current_pins_recovery_uses_only_retained_artifacts_and_maps_oserror(self):
        self.path.unlink()
        self.control.rename(self.root / 'archived-control')
        self.assertEqual(client.recovery_registration(), self.record)
        self.control.mkdir()
        self.assertEqual(client.recovery_registration(), self.record)
        with patch.object(client, 'package_digest', side_effect=PermissionError('denied')), self.assertRaises(REFUSAL):
            client.recovery_registration()
        changed = json.loads(json.dumps(self.record))
        changed['recovery_release']['root'] = str(self.root)
        write_recovery_pins(self.home, changed)
        with self.assertRaises(REFUSAL):
            client.recovery_registration()

    def test_windows_exe_cmd_path_stat_and_handle_stat_share_identity(self):
        import stat
        paths = [self.home / 'devlynd.exe', self.home / 'package' / 'run.cmd']
        paths[1].parent.mkdir()
        for path in paths:
            path.write_bytes(b'pinned artifact')
        expected = [client.regular_digest(paths[0]), client.package_digest(paths[1].parent)]
        lstat = Path.lstat
        def named_stat(path, *args, **kwargs):
            info = lstat(path, *args, **kwargs)
            values = {name: getattr(info, name) for name in ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns')}
            # A Windows path reports creation time as st_ctime; a handle reports the later change time.
            return SimpleNamespace(**values, st_mode=info.st_mode | 0o111, st_ctime_ns=info.st_ctime_ns - 1)
        # Natively these mismatches come from CPython (3.12, Windows Server 2025). Simulate them on POSIX too.
        with patch.object(Path, 'lstat', named_stat), patch.object(client, 'Path', type(self.home)), patch.object(client.os, 'name', 'nt'):
            self.assertEqual([client.regular_digest(paths[0]), client.package_digest(paths[1].parent)], expected)
            before = named_stat(paths[0])
            for field in ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns'):
                changed = SimpleNamespace(**{**vars(before), field: getattr(before, field) + 1})
                self.assertFalse(client._same_file(before, changed), field)

    def test_windows_hashing_refuses_a_handle_change_time_advance(self):
        path = self.home / 'devlynd.exe'
        path.write_bytes(b'pinned artifact')
        lstat, fstat = Path.lstat, os.fstat
        def named_stat(path, *args, **kwargs):
            info = lstat(path, *args, **kwargs)
            values = {name: getattr(info, name) for name in ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns')}
            return SimpleNamespace(**values, st_mode=info.st_mode | 0o111, st_ctime_ns=info.st_ctime_ns - 1)
        handle_stats = []
        def handle_stat(fd):
            info = fstat(fd)
            handle_stats.append(info)
            if len(handle_stats) == 1:
                return info
            # A same-size rewrite that restores mtime still advances the handle's change time.
            values = {name: getattr(info, name) for name in ('st_dev', 'st_ino', 'st_mode', 'st_size', 'st_mtime_ns')}
            return SimpleNamespace(**values, st_ctime_ns=info.st_ctime_ns + 1)
        with patch.object(Path, 'lstat', named_stat), patch.object(client, 'Path', type(self.home)), \
                patch.object(client.os, 'name', 'nt'), patch.object(client.os, 'fstat', handle_stat), \
                self.assertRaises(REFUSAL) as raised:
            client.regular_digest(path)
        self.assertIn('while hashing', raised.exception.diagnostic)

    def test_lost_or_invalid_enrollment_evidence_never_selects_unmanaged(self):
        self.assertEqual(client.enrollment()['mode'], 'managed')
        for bad in ({**self.record, 'schema': 2}, {**self.record, 'helper_release': {**self.record['helper_release'], 'sha256': '0'*64}}, []):
            self.path.write_text(json.dumps(bad))
            with self.subTest(record=bad), self.assertRaises(REFUSAL):
                client.enrollment()
        self.path.unlink()
        self.assertEqual(client.enrollment()["mode"], "standalone")
        self.control.rmdir()
        for discriminator in ({'mode': 'managed'}, {'allocation': 'managed_owned'}, {'allocation_state': 'managed_future'}):
            with self.subTest(discriminator=discriminator), self.assertRaises(REFUSAL):
                client.enrollment(receipt=discriminator)

    @unittest.skipIf(os.name == 'nt', 'directory symlink creation requires Windows privileges; enrollment checks still run')
    def test_canonical_lifecycle_root_alias_matches_rust(self):
        destination = self.home/'real-devlyn'
        self.root.rename(destination)
        self.root.symlink_to(destination, target_is_directory=True)
        # Records are canonical, independent of the alias used at the user boundary.
        for field in ('control_directory',):
            self.record[field] = str(destination/'control')
        self.record['recovery_release']['root'] = str(destination/'recovery')
        self.record['retained_recovery']['path'] = str(destination/'recovery')
        self.path.write_text(json.dumps(self.record))
        self.assertEqual(client.enrollment()['expectation'], str(destination/'storage-client.json'))

    def test_retained_recovery_byte_and_identity_changes_refuse(self):
        recovery = Path(self.record['retained_recovery']['path'])
        (recovery/'contract.json').write_text('{}')
        with self.assertRaises(REFUSAL):
            client.enrollment()

    def test_adapter_uncertain_output_never_becomes_success_or_refusal(self):
        adapter = runpy.run_path(str(SHARED/'storage-checkout.py'))
        for raw, code in ((b'', 0), (b'{"adapter_protocol":1', 0), (b'{}\n', 2), (b'{}\n', 1)):
            with self.subTest(raw=raw, code=code), self.assertRaises(adapter['StorageRefusal']) as raised:
                adapter['decode_reply'](raw, 'allocate', code)
            self.assertEqual(raised.exception.code, 'storage_unavailable')

    def test_empty_cache_reply_still_requires_closure(self):
        adapter = runpy.run_path(str(SHARED/'storage-checkout.py'))
        raw = json.dumps({'adapter_protocol': 1, 'op': 'reconcile-for-removal',
                         'result': {'operation_id': client.operation_id(), 'cache_ids': []}}).encode()+b'\n'
        with self.assertRaises(adapter['StorageRefusal']):
            adapter['decode_reply'](raw, 'reconcile-for-removal', 0)

    def test_retained_helper_invocation_is_independent_of_original_app(self):
        helper = runpy.run_path(str(SHARED / 'task-complete.py'))
        original = self.home / 'original-helper'
        shutil.copyfile(self.record['helper_path'], original)
        self.record['helper_path'] = str(original)
        self.path.write_text(json.dumps(self.record))
        receipt = {'allocation': 'managed_owned', 'storage': {'decision': {'registration': self.record}}}
        original.unlink()
        with self.assertRaises(REFUSAL):
            client.enrollment()
        self.path.unlink()
        registration = helper['managed_registration'](receipt, recovery=True)
        self.assertEqual(registration['helper_path'], self.record['retained_helper']['path'])
        adapter = runpy.run_path(str(SHARED / 'storage-checkout.py'))
        def invoke(argv, **kwargs):
            self.assertEqual(argv[0], self.record['retained_helper']['path'])
            value = json.loads((FIXTURES / 'storage-protocol-1/adapter-1/capabilities-result.json').read_bytes())
            kwargs['stdout'].write(json.dumps(value).encode()+b'\n')
            return SimpleNamespace(returncode=0)
        with patch.object(subprocess, 'run', invoke):
            self.assertTrue(adapter['call'](registration, 'capabilities', {})['cli_checkout_v1'])

    def test_retained_recovery_rejects_changed_pinned_package(self):
        helper = runpy.run_path(str(SHARED / 'task-complete.py'))
        receipt = {'allocation': 'managed_owned', 'storage': {'decision': {'registration': self.record}}}
        (Path(self.record['retained_recovery']['path']) / 'nested/runtime.txt').write_text('changed')
        with self.assertRaises(helper['CompletionError']):
            helper['managed_registration'](receipt, recovery=True)

    def test_recovery_republish_executes_new_pins_after_saved_helper_replaced(self):
        helper = runpy.run_path(str(SHARED / 'task-complete.py'))
        saved = json.loads(json.dumps(self.record))
        old = self.root / 'old-helper'
        old.write_bytes(b'old release')
        saved['retained_helper'] = {'path': str(old), 'identity': client.persistent_identity(old),
                                    'sha256': client.regular_digest(old)}
        saved['helper_release']['sha256'] = saved['retained_helper']['sha256']
        receipt = {'allocation': 'managed_owned', 'storage': {'decision': {'registration': saved}}}
        old.unlink()
        self.path.unlink()
        registration = helper['managed_registration'](receipt, recovery=True)
        self.assertNotEqual(saved['helper_release']['sha256'], registration['helper_release']['sha256'])
        adapter = runpy.run_path(str(SHARED / 'storage-checkout.py'))
        def invoke(argv, **kwargs):
            self.assertEqual(argv[0], self.record['retained_helper']['path'])
            value = json.loads((FIXTURES / 'storage-protocol-1/adapter-1/capabilities-result.json').read_bytes())
            kwargs['stdout'].write(json.dumps(value).encode() + b'\n')
            return SimpleNamespace(returncode=0)
        with patch.object(subprocess, 'run', invoke):
            adapter['call'](registration, 'capabilities', {})

    def test_recovery_pins_schema_paths_and_artifact_bindings_refuse(self):
        pins = json.loads(self.pins_path.read_text())
        changes = [('schema', 2), ('enrollment.schema', 2), ('node', str(self.home)),
                   ('enrollment.recovery_release.root', str(self.home)),
                   ('runtime.identity.file', 'changed'), ('runtime.sha256', 'changed'),
                   ('enrollment.retained_helper.identity.file', 'changed'),
                   ('enrollment.retained_helper.sha256', 'changed'),
                   ('enrollment.retained_recovery.identity.file', 'changed')]
        for field, value in changes:
            changed = json.loads(json.dumps(pins))
            keys = field.split('.')
            target = changed
            for key in keys[:-1]:
                target = target[key]
            target[keys[-1]] = value
            self.pins_path.write_text(json.dumps(changed))
            with self.subTest(field=field), self.assertRaises(REFUSAL):
                client.recovery_registration()

    @unittest.skipIf(os.name == 'nt', 'symlink privileges and FIFO semantics are POSIX-only')
    def test_recovery_pins_reader_refuses_symlinks_and_fifo(self):
        original = self.pins_path.with_name('original.json')
        self.pins_path.rename(original)
        self.pins_path.symlink_to(original)
        with self.assertRaises(REFUSAL):
            client.recovery_registration()
        self.pins_path.unlink()
        os.mkfifo(self.pins_path)
        with self.assertRaises(REFUSAL):
            client.recovery_registration()

    def test_recovery_missing_pins_or_binding_mismatch_retains(self):
        helper = runpy.run_path(str(SHARED / 'task-complete.py'))
        receipt = {'allocation': 'managed_owned', 'storage': {'decision': {'registration': self.record}}}
        pins = json.loads(self.pins_path.read_text())
        pins['enrollment']['control_identity']['file'] = 'another authority'
        self.pins_path.write_text(json.dumps(pins))
        with self.assertRaisesRegex(helper['CompletionError'], 'authority binding changed.*retain'):
            helper['managed_registration'](receipt, recovery=True)
        self.pins_path.unlink()
        with self.assertRaisesRegex(helper['CompletionError'], 'Retain.*repair Devlyn recovery pins'):
            helper['managed_registration'](receipt, recovery=True)

    def test_recovery_pins_reject_unknown_nested_fields_and_changed_runtime(self):
        pins = json.loads(self.pins_path.read_text())
        paths = [(), ('enrollment',), ('enrollment', 'control_identity'),
                 ('enrollment', 'helper_release'), ('enrollment', 'recovery_release'),
                 ('enrollment', 'retained_helper'), ('enrollment', 'retained_helper', 'identity'),
                 ('enrollment', 'retained_recovery'), ('enrollment', 'retained_recovery', 'identity'),
                 ('runtime',), ('runtime', 'identity')]
        for keys in paths:
            changed = json.loads(json.dumps(pins))
            target = changed
            for key in keys:
                target = target[key]
            target['unknown'] = True
            self.pins_path.write_text(json.dumps(changed))
            with self.subTest(keys=keys), self.assertRaises(REFUSAL):
                client.recovery_registration()
        self.pins_path.write_text(json.dumps(pins))
        Path(pins['node']).write_bytes(b'changed runtime')
        with self.assertRaises(REFUSAL):
            client.recovery_registration()

    def test_republishing_same_authority_does_not_strand_receipt(self):
        helper = runpy.run_path(str(SHARED / 'task-complete.py'))
        receipt = {'allocation': 'managed_owned', 'storage': {'decision': {'registration': self.record}}}
        updated = json.loads(json.dumps(self.record))
        updated['recovery_release']['version'] = '4.3.22'
        self.path.write_text(json.dumps(updated))
        with patch.dict(os.environ, HOME=str(self.home), USERPROFILE=str(self.home)):
            self.assertEqual(helper['managed_registration'](receipt)['recovery_release']['version'], '4.3.22')
        updated['control_identity']['file'] = 'changed'
        self.path.write_text(json.dumps(updated))
        with patch.dict(os.environ, HOME=str(self.home), USERPROFILE=str(self.home)), self.assertRaises(helper['CompletionError']):
            helper['managed_registration'](receipt)

    @unittest.skipIf(os.name == 'nt', 'fd-relative tree deletion is POSIX-only; Windows retains')
    def test_delivered_cacheless_tree_finishes_after_unenroll_with_retained_pins(self):
        helper = runpy.run_path(str(SHARED / 'task-complete.py'))
        fixture = helper['CompletionTests']('test_standalone_without_devlyn_keeps_existing_allocation_and_warm_behavior')
        self.addCleanup(fixture.doCleanups)
        fixture.setUp()
        result = fixture.allocate()
        path = Path(result['receipt'])
        receipt = json.loads(path.read_text())
        operation = client.operation_id()
        receipt.update(mode='managed', allocation='managed_owned', storage={
            'decision': {'registration': self.record},
            'request': {'operation_id': operation, 'external_receipt': str(path)},
            'result': {'closure_result': {'established_by': 'never_admitted', 'operation_id': operation}}})
        path.write_text(json.dumps(receipt))
        fixture.accept()
        self.path.unlink()
        (self.home / '.devlyn/storage-client-recovery').mkdir(exist_ok=True)
        call = helper['storage_call']
        pins = []
        def retained(name, *args, **kwargs):
            if name == 'call' and kwargs.get('adapter'):
                self.assertEqual(args[1], 'reconcile-for-removal')
                self.assertEqual(args[0]['helper_path'], self.record['retained_helper']['path'])
                pins.append(args[0])
                return {'operation_id': args[2]['removal_operation_id'], 'cache_ids': [],
                        'closure_result': {'established_by': 'never_admitted', 'operation_id': operation}}
            return call(name, *args, **kwargs)
        env = helper['complete'].__globals__
        with patch.dict(os.environ, fixture.env, clear=True), \
             patch.dict(os.environ, HOME=str(self.home), USERPROFILE=str(self.home)), \
             patch.dict(env, storage_call=retained, stopped_writers=lambda work: None, scratch_mounts=lambda: [],
                        storage_rpc=lambda *args: self.fail('cacheless removal used authority')):
            helper['accept'](SimpleNamespace(receipt=str(path), acceptance=str(fixture.acceptance)))
            completed = helper['complete'](SimpleNamespace(receipt=str(path), acceptance=None,
                mode='auto', local_only=False, writers_stopped=True))
            self.assertEqual(completed['status'], 'COMPLETE', completed)
            self.assertFalse(fixture.task.exists())
            self.assertTrue(pins)
            # Lost retirement output: the original saved direct command works.
            self.assertEqual(helper['complete'](SimpleNamespace(receipt=str(path), acceptance=None,
                mode='auto', local_only=False, writers_stopped=True))['status'], 'COMPLETE')

    @unittest.skipIf(os.name == 'nt', 'native Windows retains workspaces')
    def test_local_only_after_unenroll_has_terminal_owner_removal(self):
        self.accepted_owner_removal('LOCAL_ONLY')

    @unittest.skipIf(os.name == 'nt', 'native Windows retains workspaces')
    def test_failed_after_unenroll_has_terminal_owner_removal(self):
        self.accepted_owner_removal('FAILED')

    @unittest.skipIf(os.name == 'nt', 'native Windows retains workspaces')
    def test_queue_produced_failed_after_unenroll_has_terminal_owner_removal(self):
        self.accepted_owner_removal('FAILED', queued=True)

    @unittest.skipIf(os.name == 'nt', 'native Windows retains workspaces')
    def test_closed_pr_after_unenroll_has_terminal_owner_removal(self):
        self.accepted_owner_removal('CLOSED')

    @unittest.skipIf(os.name == 'nt', 'POSIX delivery fixture; native-Git manual-removal regression runs below')
    def test_unobservable_writers_names_manual_step_then_retires_with_scratch(self):
        self.accepted_owner_removal('LOCAL_ONLY', manual=True)

    @unittest.skipIf(os.name == 'nt', 'remote delivery fixture uses POSIX GitHub launchers')
    def test_standalone_reused_retired_key_completes_local_and_remote(self):
        helper = runpy.run_path(str(SHARED / 'task-complete.py'))
        for local in (True, False):
            with self.subTest(local=local):
                fixture = helper['CompletionTests']('test_standalone_without_devlyn_keeps_existing_allocation_and_warm_behavior')
                self.addCleanup(fixture.doCleanups)
                fixture.setUp()
                path = Path(fixture.allocate()['receipt'])
                saved = json.loads(path.read_text())
                fixture.g('worktree', 'remove', '--force', str(fixture.task))
                fixture.g('branch', '-D', saved['branch'])
                saved.update(status='ABANDONED', allocation='managed_pending', mode='managed', storage={
                    'decision': {'registration': {'fixture': True}}, 'removal_finished': True,
                    'request': {'operation_id': client.operation_id(), 'external_receipt': str(path)}})
                path.write_text(json.dumps(saved))
                with patch.dict(os.environ, fixture.env, clear=True), \
                     patch.dict(helper['complete'].__globals__, stopped_writers=lambda work: None, scratch_mounts=lambda: []):
                    args = fixture.allocation_args('fixture', fixture.task)
                    if local:
                        args.local_base = fixture.g('rev-parse', 'HEAD')
                    fresh = helper['allocate'](args)
                    self.assertNotIn('storage', json.loads(path.read_text()))
                    fixture.accept()
                    result = helper['complete'](SimpleNamespace(receipt=fresh['receipt'], acceptance=str(fixture.acceptance),
                        mode='auto', local_only=local, writers_stopped=True))
                    self.assertEqual(result['delivery_status'], 'LOCAL_ONLY' if local else 'COMPLETE', result)
                    self.assertEqual(len(list((path.parent.parent / 'retired').glob('*/receipt.json'))), 1)

    def accepted_owner_removal(self, outcome, *, queued=False, manual=False):
        helper = runpy.run_path(str(SHARED / 'task-complete.py'))
        fixture = helper['CompletionTests']('test_standalone_without_devlyn_keeps_existing_allocation_and_warm_behavior')
        self.addCleanup(fixture.doCleanups)
        fixture.setUp()
        result = fixture.allocate()
        path = Path(result['receipt'])
        receipt = json.loads(path.read_text())
        operation = client.operation_id()
        receipt.update(mode='managed', allocation='managed_owned', storage={
            'decision': {'registration': self.record},
            'request': {'operation_id': operation, 'external_receipt': str(path)},
            'result': {'closure_result': {'established_by': 'never_admitted', 'operation_id': operation}}})
        path.write_text(json.dumps(receipt))
        if outcome == 'FAILED':
            self.assertEqual(fixture.loop_result('FAILED')['status'], 'FAILED')
        else:
            fixture.accept()
        env, call = helper['complete'].__globals__, helper['storage_call']
        pins = []
        def retained(name, *args, **kwargs):
            if name == 'call' and kwargs.get('adapter'):
                self.assertEqual(args[1], 'reconcile-for-removal')
                self.assertEqual(args[0]['helper_path'], self.record['retained_helper']['path'])
                pins.append(args[0])
                return {'operation_id': args[2]['removal_operation_id'], 'cache_ids': [],
                        'closure_result': {'established_by': 'never_admitted', 'operation_id': operation}}
            return call(name, *args, **kwargs)
        with patch.dict(os.environ, fixture.env, clear=True), patch.dict(os.environ, HOME=str(self.home), USERPROFILE=str(self.home)), \
             patch.dict(env, storage_call=retained, stopped_writers=lambda work: None, scratch_mounts=lambda: [],
                        storage_rpc=lambda *args: self.fail('cacheless removal used authority')):
            helper['accept'](SimpleNamespace(receipt=str(path), acceptance=str(fixture.acceptance)))
            if queued:
                queue = runpy.run_path(str(ROOT / 'config/skills/devlyn-ideate/scripts/queue.py'))
                terminal = queue['commit_files'](fixture.task, receipt['branch'], fixture.sha,
                    {'queue.md': b'- [F] terminal failed task\n'}, 'terminal FAILED', checkout=False)
                helper['attach'](SimpleNamespace(receipt=str(path), commit=terminal, file='queue.md'))
                self.assertEqual(fixture.g('rev-parse', 'HEAD', work=fixture.task), terminal)
                self.assertEqual(fixture.g('write-tree', work=fixture.task), fixture.g('rev-parse', fixture.sha + '^{tree}'))
            opts = SimpleNamespace(receipt=str(path), acceptance=None, mode='pr' if outcome == 'CLOSED' else None,
                local_only=outcome != 'CLOSED', writers_stopped=False)

            self.assertEqual(helper['complete'](opts)['status'], 'PR' if outcome == 'CLOSED' else outcome)
            if outcome == 'CLOSED':
                gh_data = json.loads(fixture.data.read_text())
                gh_data['prs'][0]['state'] = 'CLOSED'
                fixture.data.write_text(json.dumps(gh_data))
            self.path.unlink()
            write_retirement(self.home)
            next_args = fixture.allocation_args('next', fixture.root / 'next')
            next_args.local_base = fixture.g('rev-parse', 'HEAD')
            self.assertEqual(helper['allocate'](next_args)['status'], 'ALLOCATED')
            with self.assertRaises(helper['CompletionError']) as blocked:
                helper['allocate'](fixture.allocation_args('fixture', fixture.task))
            self.assertIn('--for-removal', blocked.exception.storage_error['resume'])
            recovery = SimpleNamespace(receipt=str(path), for_removal=True, operation_id=operation)
            with self.assertRaisesRegex(helper['CompletionError'], 'release writers'):
                helper['recover_storage'](recovery)
            opts.writers_stopped = True
            self.assertEqual(helper['complete'](opts)['status'], outcome)
            if manual:
                scratch = path.parent / 'scratch'
                (scratch / 'retained-output').write_bytes(b'disposable output')
                unavailable = unittest.mock.Mock(side_effect=helper['WritersUnobservable']('cannot observe writers'))
                with patch.dict(env, stopped_writers=unavailable):
                    with self.assertRaisesRegex(helper['WritersUnobservable'], 'remove the task checkout by hand'):
                        helper['recover_storage'](recovery)
                    fixture.g('worktree', 'remove', '--force', str(fixture.task))
                    retired = helper['recover_storage'](recovery)
                audit = Path(retired['receipt'])
                self.assertEqual(audit.parent.parent.name, 'retired')
                self.assertEqual(retired['scratch_cleanup']['status'], 'RETAINED')
                self.assertEqual((audit.parent / 'scratch/retained-output').read_bytes(), b'disposable output')
                self.assertIn('--operation-id ' + operation, retired['scratch_cleanup']['resume'])
                self.assertIn(str(audit), retired['scratch_cleanup']['resume'])
                return
            (fixture.task / 'product').write_text('dirty failed source')
            with self.assertRaisesRegex(helper['CompletionError'], 'dirty'):
                helper['recover_storage'](recovery)
            self.assertEqual(pins, [])
            fixture.g('restore', 'product', work=fixture.task)
            saved = json.loads(path.read_text())
            recovery_ref = saved['recovery_ref']
            fixture.g('update-ref', recovery_ref, saved['baseline'])
            with self.assertRaisesRegex(helper['CompletionError'], 'reachability'):
                helper['recover_storage'](recovery)
            fixture.g('update-ref', recovery_ref, saved['publish_sha'])
            evidence = '.devlyn/loop/runs/1/cmd-0.stdout' if outcome == 'FAILED' else '.devlyn/checks.txt'
            custody = path.parent / 'custody' / evidence
            original = custody.read_bytes()
            custody.write_bytes(b'changed custody')
            with self.assertRaisesRegex(helper['CompletionError'], 'evidence'):
                helper['recover_storage'](recovery)
            custody.write_bytes(original)
            resolved = helper['recover_storage'](recovery)
            audit = Path(resolved['receipt'])
            self.assertEqual(audit.parent.parent.name, 'retired')
            self.assertEqual(resolved['status'], outcome)
            self.assertFalse(fixture.task.exists())
            self.assertTrue(pins)
            self.assertEqual(fixture.g('rev-parse', 'refs/heads/' + saved['branch']), saved['publish_sha'])
            if outcome == 'CLOSED':
                self.assertEqual(fixture.g('--git-dir', str(fixture.bare), 'rev-parse', 'refs/heads/' + saved['branch']), saved['publish_sha'])
            self.assertEqual(helper['recover_storage'](recovery)['receipt'], str(audit))
            self.assertEqual(helper['complete'](opts)['status'], outcome)
            self.assertTrue(Path(next_args.worktree).exists())

    @unittest.skipIf(os.name == 'nt', 'delivery/removal fixture needs POSIX writer observation')
    def test_reused_delivered_branch_accepts_with_legacy_recovery_ref_kept(self):
        helper = runpy.run_path(str(SHARED / 'task-complete.py'))
        fixture = helper['CompletionTests']('test_standalone_without_devlyn_keeps_existing_allocation_and_warm_behavior')
        self.addCleanup(fixture.doCleanups)
        fixture.setUp()
        result = fixture.allocate()
        path = Path(result['receipt'])
        fixture.accept()
        env = helper['complete'].__globals__
        with patch.dict(os.environ, fixture.env, clear=True), \
             patch.dict(env, stopped_writers=lambda work: None, scratch_mounts=lambda: []):
            old = json.loads(path.read_text())
            old.update(mode='managed', allocation='managed_owned', storage={
                'decision': {'registration': self.record}, 'request': {
                    'operation_id': client.operation_id(), 'external_receipt': str(path)},
                'result': {'closure_result': {'established_by': 'never_admitted', 'operation_id': client.operation_id()}}})
            path.write_text(json.dumps(old))
            helper['accept'](SimpleNamespace(receipt=str(path), acceptance=str(fixture.acceptance)))
            staged = helper['complete'](SimpleNamespace(receipt=str(path), acceptance=None,
                mode='auto', local_only=False, writers_stopped=False))
            self.assertEqual(staged['status'], 'CLEANUP_PENDING', staged)
            self.assertEqual(staged['delivery_status'], 'COMPLETE')
            # Simulate already-finished tree removal, retaining the legacy recovery ref.
            fixture.g('worktree', 'remove', '--force', str(fixture.task))
            old = json.loads(path.read_text())
            old['storage']['removal_finished'] = True
            path.write_text(json.dumps(old))
            completed = helper['complete'](SimpleNamespace(receipt=str(path), acceptance=None,
                mode='auto', local_only=False, writers_stopped=True))
            self.assertEqual(completed['status'], 'COMPLETE', completed)
            old_ref = old['recovery_ref']
            old_sha = fixture.g('rev-parse', old_ref)
            call = env['storage_call']
            def enrolled(name, *args, **kwargs):
                if name == 'operation_enrollment':
                    return {'mode': 'managed', 'registration': self.record}
                return call(name, *args, **kwargs)
            def checkout(receipt, receipt_path):
                fixture.g('worktree', 'add', '-b', receipt['branch'], receipt['worktree'], receipt['baseline'])
                work = Path(receipt['worktree'])
                helper['ignore_task_records'](work)
                receipt['worktree_gitdir'] = helper['git'](work, 'rev-parse', '--absolute-git-dir')
                receipt['worktree_identity'] = helper['workspace_identity'](work, Path(receipt['worktree_gitdir']))
                receipt['allocation'] = 'managed_owned'
                helper['atomic_json'](receipt_path, receipt)
            with patch.dict(env, storage_call=enrolled, finish_managed_allocation=checkout):
                allocated = helper['allocate'](fixture.allocation_args('fixture', fixture.task))
            new = json.loads(Path(allocated['receipt']).read_text())
            self.assertNotEqual(new['recovery_ref'], old_ref)
            (fixture.task / 'product').write_text('second task source\n')
            fixture.g('add', 'product', work=fixture.task)
            fixture.g('commit', '-m', 'second task', work=fixture.task)
            evidence = fixture.task / '.devlyn'
            evidence.mkdir(exist_ok=True)
            (evidence / 'checks.txt').write_text('second accepted check')
            fixture.acceptance.write_text(json.dumps({'kind': 'direct', 'task': 'fixture',
                'source_sha': fixture.g('rev-parse', 'HEAD', work=fixture.task),
                'checks': [{'command': 'second source check', 'evidence': '.devlyn/checks.txt'}]}))
            accepted = helper['accept'](SimpleNamespace(receipt=allocated['receipt'], acceptance=str(fixture.acceptance)))
            self.assertEqual(accepted['status'], 'ACCEPTED')
            self.assertEqual(fixture.g('rev-parse', old_ref), old_sha)
            self.assertNotEqual(fixture.g('rev-parse', new['recovery_ref']), old_sha)

    @unittest.skipIf(os.name == 'nt', 'deletion retains on Windows; digest tests run natively')
    def test_managed_receipt_survives_outage_upgrade_and_helper_replacement(self):
        helper = runpy.run_path(str(SHARED / 'task-complete.py'))
        fixture = helper['CompletionTests']('test_standalone_without_devlyn_keeps_existing_allocation_and_warm_behavior')
        self.addCleanup(fixture.doCleanups)
        fixture.setUp()
        result = fixture.allocate()
        path = Path(result['receipt'])
        original = self.home / 'old-helper'
        shutil.copyfile(self.record['helper_path'], original)
        saved = json.loads(json.dumps(self.record))
        saved['helper_path'] = str(original)
        receipt = json.loads(path.read_text())
        receipt.update(mode='managed', allocation='managed_owned', storage={
            'decision': {'registration': saved}, 'request': {'operation_id': client.operation_id(), 'external_receipt': str(path)},
            'result': {'closure_result': {'established_by': 'never_admitted', 'operation_id': client.operation_id()}}})
        path.write_text(json.dumps(receipt))
        fixture.accept()
        self.path.unlink()
        original.unlink()
        env = helper['complete'].__globals__
        opts = SimpleNamespace(receipt=str(path), acceptance=None, mode='auto', local_only=False, writers_stopped=True)
        with patch.dict(os.environ, fixture.env, clear=True), patch.dict(os.environ, HOME=str(self.home), USERPROFILE=str(self.home)), \
             patch.dict(env, stopped_writers=lambda work: None, scratch_mounts=lambda: []):
            self.assertEqual(helper['accept'](SimpleNamespace(receipt=str(path), acceptance=str(fixture.acceptance)))['status'], 'ACCEPTED')
            (fixture.task / 'QUEUE.md').write_text('terminal metadata')
            fixture.g('add', 'QUEUE.md', work=fixture.task)
            fixture.g('commit', '-m', 'queue terminal', work=fixture.task)
            terminal = fixture.g('rev-parse', 'HEAD', work=fixture.task)
            helper['attach'](SimpleNamespace(receipt=str(path), commit=terminal, file='QUEUE.md'))
            delivered = helper['complete'](opts)
            self.assertEqual((delivered['status'], delivered['delivery_status']), ('CLEANUP_PENDING', 'COMPLETE'))
            self.assertIn(str(path), delivered['workspace_cleanup']['resume'])
            self.assertEqual(json.loads(path.read_text())['delivery'], 'COMPLETE')
            replacement = self.home / 'new-helper'
            shutil.copyfile(self.record['helper_path'], replacement)
            with replacement.open('ab') as stream:
                stream.write(b'new release digest')
            updated = json.loads(json.dumps(self.record))
            digest = client.regular_digest(replacement)
            updated.update(helper_path=str(replacement), helper_release={**updated['helper_release'], 'version': '2.0.0', 'sha256': digest},
                           retained_helper={'path': str(replacement), 'identity': client.persistent_identity(replacement), 'sha256': digest})
            self.path.write_text(json.dumps(updated))
            seen = []
            def gate(receipt, receipt_path, **kwargs):
                selected = helper['managed_registration'](receipt)
                seen.append(selected['helper_release'])
                receipt['storage']['removal_request'] = {'worktree_identity': client.persistent_identity(fixture.task)}
                return selected
            repo_policy = env['repo_policy']
            def reference_outage(receipt, *args, **kwargs):
                if receipt.get('storage', {}).get('removal_finished'):
                    raise helper['CompletionError']('reference cleanup outage after storage removal')
                return repo_policy(receipt, *args, **kwargs)
            with patch.dict(env, managed_removal_gate=gate, repo_policy=reference_outage):
                finished = helper['complete'](opts)
            self.assertEqual((finished['status'], finished['delivery_status']), ('CLEANUP_PENDING', 'COMPLETE'), finished)
            self.assertEqual(seen, [updated['helper_release']])
            audit = Path(finished['receipt'])
            self.assertEqual(audit.parent.parent.name, 'retired')
            self.assertIn(str(audit), finished['workspace_cleanup']['resume'])
            self.assertFalse(path.exists())
            self.assertFalse(audit.with_name('tree-removal.json').exists())
            self.assertFalse(fixture.task.exists())
            # Replaying a terminal audit needs neither enrollment nor live helper.
            self.path.unlink()
            replacement.unlink()
            opts.receipt = str(path)  # Saved before retirement; its output was lost.
            with patch.dict(env, stopped_writers=unittest.mock.Mock(side_effect=helper['WritersUnobservable']('offline mount'))):
                resumed = helper['complete'](opts)
            self.assertEqual((resumed['status'], resumed['delivery_status']), ('COMPLETE', 'COMPLETE'))
            replay = helper['recover_storage'](SimpleNamespace(receipt=str(audit), for_removal=True))
            self.assertEqual(replay['status'], 'REMOVAL_RECONCILED')
            self.assertIn('complete --receipt', replay['resume'])

    def test_nested_package_digest_vector_native_paths_and_order(self):
        vector = json.loads((FIXTURES / 'storage-package-digest.json').read_text())
        recovery = self.home / 'digest-vector'
        recovery.mkdir()
        for name, contents in vector['files'].items():
            path = recovery / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(contents.encode())
        self.assertEqual(client.package_digest(recovery), vector['sha256']['windows' if os.name == 'nt' else 'posix'])

    def test_additive_closure_and_binding_fields_are_accepted(self):
        adapter = runpy.run_path(str(SHARED / 'storage-checkout.py'))
        value = {'adapter_protocol': 1, 'op': 'reconcile-for-removal', 'future': True,
                 'result': {'operation_id': client.operation_id(), 'cache_ids': [], 'extra': {},
                            'closure_result': {'established_by': 'never_admitted', 'operation_id': client.operation_id(), 'future': []}}}
        self.assertEqual(adapter['decode_reply'](json.dumps(value).encode()+b'\n', 'reconcile-for-removal', 0), value['result'])
        helper = runpy.run_path(str(SHARED / 'task-complete.py'))
        self.assertTrue(helper['reply_matches']({'owner': {'repository': {'volume': '1', 'file': '2', 'future': True}, 'extra': True}},
                                                {'owner': {'repository': {'volume': '1', 'file': '2'}}}))
        self.assertFalse(helper['reply_matches']({'owner': {'file': 'changed'}}, {'owner': {'file': '2'}}))



@unittest.skipIf(os.name == 'nt', 'fd-relative owner deletion requires native POSIX support; Windows retains')
class OwnerDeletionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='storage-delete-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.work = self.root/'owned'
        self.work.mkdir()
        self.helper = runpy.run_path(str(SHARED/'task-complete.py'))

    def test_fd_deletion_preserves_root_and_does_not_follow_links(self):
        outside = self.root/'retained'
        outside.mkdir()
        (outside/'data').write_text('retain')
        (self.work/'directory').mkdir()
        (self.work/'directory/data').write_text('owned')
        (self.work/'link').symlink_to(outside, target_is_directory=True)
        fd = os.open(self.work, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            self.helper['empty_owned_tree'](fd)
        finally:
            os.close(fd)
        self.assertEqual(list(self.work.iterdir()), [])
        self.assertEqual((outside/'data').read_text(), 'retain')

    def test_fd_deletion_rejects_cross_device_before_unlink(self):
        (self.work/'data').write_text('retain')
        fd = os.open(self.work, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        original = os.stat
        def changed(path, *args, **kwargs):
            info = original(path, *args, **kwargs)
            if kwargs.get('dir_fd') == fd and path == 'data':
                return SimpleNamespace(st_dev=info.st_dev+1)
            return info
        try:
            with patch.object(os, 'stat', changed), self.assertRaises(self.helper['CompletionError']):
                self.helper['empty_owned_tree'](fd)
        finally:
            os.close(fd)
        self.assertEqual((self.work/'data').read_text(), 'retain')


@unittest.skipIf(PACKAGED or os.name == 'nt', 'historical POSIX cost comparison uses the main CompletionTests fixture')
class StandaloneCostTests(unittest.TestCase):
    def baseline(self, name):
        source = subprocess.check_output(['git', 'show', '5a94e810:config/skills/_shared/' + name + '.py'], cwd=ROOT)
        namespace = {'__file__': str(SHARED / (name + '.py')), '__name__': 'round2b_baseline'}
        exec(compile(source, namespace['__file__'], 'exec'), namespace)
        return namespace

    def test_legacy_install_allocation_has_main_git_and_walk_cost(self):
        helper = runpy.run_path(str(SHARED / 'task-complete.py'))
        old = self.baseline('task-complete')
        counts = []
        for implementation in (old, helper):
            fixture = helper['CompletionTests']('test_standalone_without_devlyn_keeps_existing_allocation_and_warm_behavior')
            fixture.setUp()
            try:
                home = Path(fixture.env['HOME'])
                (home / '.devlyn/control').mkdir(parents=True)
                (home / '.devlyn/harness').mkdir()
                (home / '.devlyn/harness/state.json').write_text('{}')
                common = fixture.work / '.git'
                receipt_root = common / 'devlyn-completion'
                receipt_root.mkdir()
                (receipt_root / 'stray').write_text('not a receipt')
                args = SimpleNamespace(repo=str(fixture.work), task='cost', branch='task/cost', base=None,
                    remote='origin', repository=None, worktree=str(fixture.root / 'cost'), keep_root=None,
                    local_base=fixture.g('rev-parse', 'HEAD'), from_receipt=None, start=None)
                calls = {'rev_parse': 0, 'walk': 0, 'receipt_scan': 0}
                real_command, real_walk, real_iter = implementation['command'], os.walk, Path.iterdir
                def command(argv, **kwargs):
                    calls['rev_parse'] += 'rev-parse' in argv
                    return real_command(argv, **kwargs)
                def walk(*args, **kwargs):
                    calls['walk'] += 1
                    return real_walk(*args, **kwargs)
                def iterdir(path):
                    calls['receipt_scan'] += path.name == 'devlyn-completion'
                    return real_iter(path)
                with patch.dict(os.environ, fixture.env, clear=True), patch.dict(implementation['allocate'].__globals__, command=command), \
                     patch.object(os, 'walk', walk), patch.object(Path, 'iterdir', iterdir):
                    result = implementation['allocate'](args)
                self.assertEqual(result['status'], 'ALLOCATED')
                saved = json.loads(Path(result['receipt']).read_text())
                self.assertEqual(saved['allocation'], 'owned')
                self.assertNotIn('mode', saved)
                counts.append(calls)
            finally:
                fixture.doCleanups()
        self.assertEqual(counts[0], counts[1])
        self.assertEqual(counts[1]['receipt_scan'], 0)
        print('STANDALONE allocation main/current counters:', counts, file=sys.stderr)

    @unittest.skipIf(os.name == 'nt', 'warming is POSIX-only')
    def test_legacy_install_warming_has_main_git_and_walk_cost(self):
        warm = runpy.run_path(str(SHARED / 'warm-build-dirs.py'))
        old = self.baseline('warm-build-dirs')
        counts, outcomes = [], []
        for implementation in (old, warm):
            fixture = warm['WarmTests']('test_local_git_true_seeds_without_cargo_opt_in')
            fixture.setUp()
            try:
                home = Path.home()
                (home / '.devlyn/control').mkdir(parents=True)
                (home / '.devlyn/harness').mkdir()
                (home / '.devlyn/harness/state.json').write_text('{}')
                fixture.git(fixture.work, 'config', '--local', 'devlyn.warmBuildDirs', 'true')
                calls = {'rev_parse': 0, 'walk': 0, 'receipt_scan': 0}
                real_git, real_walk, real_iter = implementation['git'], os.walk, Path.iterdir
                def git(*args, **kwargs):
                    calls['rev_parse'] += 'rev-parse' in args
                    return real_git(*args, **kwargs)
                def walk(*args, **kwargs):
                    calls['walk'] += 1
                    return real_walk(*args, **kwargs)
                def iterdir(path):
                    calls['receipt_scan'] += path.name == 'devlyn-completion'
                    return real_iter(path)
                with patch.dict(implementation['warm'].__globals__, git=git, clone=implementation['clone']), \
                     patch.object(os, 'walk', walk), patch.object(Path, 'iterdir', iterdir):
                    result = implementation['warm'](fixture.work, fixture.anchor, fixture.staging)
                outcomes.append([entry['status'] for entry in result])
                counts.append(calls)
            finally:
                fixture.doCleanups()
        self.assertEqual(outcomes[0], outcomes[1])
        self.assertEqual(counts[0], counts[1])
        self.assertEqual(counts[1]['receipt_scan'], 0)
        print('STANDALONE warming main/current outcomes/counters:', outcomes, counts, file=sys.stderr)


class ReceiptLifecycleTests(unittest.TestCase):
    """Real lock/retirement boundary, without a running storage service."""
    def setUp(self):
        self.helper = runpy.run_path(str(SHARED / 'task-complete.py'))
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.branch = 'task/terminal'
        key = hashlib.sha256(self.branch.encode()).hexdigest()[:24]
        self.path = self.root / 'devlyn-completion' / key / 'receipt.json'
        self.path.parent.mkdir(parents=True)
        operation = client.operation_id()
        self.receipt = {'id': key, 'branch': self.branch, 'base': 'main', 'baseline': 'baseline',
            'common_gitdir': str(self.root), 'allocation': 'managed_pending', 'worktree': str(self.root / 'absent'),
            'storage': {'decision': {'registration': {'retained': True}},
                'request': {'operation_id': operation, 'external_receipt': str(self.path)}}}
        self.path.write_text(json.dumps(self.receipt))
        self.env = self.helper['recover_storage'].__globals__
        mocks = patch.dict(self.env, managed_registration=lambda *args, **kwargs: {},
                           ref_sha=lambda *args: None, registrations=lambda *args: {})
        mocks.start()
        self.addCleanup(mocks.stop)

    def recover(self, *, for_removal=True, path=None):
        return self.helper['recover_storage'](SimpleNamespace(receipt=str(path or self.path), for_removal=for_removal))

    def test_moved_receipt_releases_and_archives_without_deleting(self):
        work = Path(self.receipt['worktree'])
        work.mkdir()
        (work / 'source').write_bytes(b'keep copied edits')
        self.receipt['storage']['decision']['registration'] = {'control_directory': str(self.root / 'old-control'),
            'control_identity': {'volume': 'old', 'file': '1'}}
        self.path.write_text(json.dumps(self.receipt))
        move = client.operation_id()
        shared = self.helper['shared']('storage-client')
        with patch.dict(shared['moved_operation'].__globals__, moved_operation=lambda saved: move), \
             patch.dict(shared, moved_operation=lambda saved: move, recovery_registration=lambda: {'helper_path': 'helper',
                        'retained_helper': {'path': 'retained'}}):
            before = self.path.read_bytes()
            for flagged in (False, True):
                with self.subTest(flagged=flagged):
                    # Simulate a crash after durable disposition but before directory rename.
                    with patch.object(Path, 'rename', side_effect=OSError('rename interrupted')), self.assertRaises(OSError):
                        self.recover(for_removal=flagged)
                    saved = json.loads(self.path.read_text())
                    self.assertEqual(saved['storage']['moved'], {'operation_id': move, 'removal_result': None})
                    result = self.recover(for_removal=flagged)
                    audit = Path(result['receipt'])
                    self.assertEqual(audit.parent.parent.name, 'moved')
                    self.assertEqual(self.recover(for_removal=flagged), result)
                    self.assertEqual(self.recover(path=audit, for_removal=flagged), result)
                    self.assertEqual((work / 'source').read_bytes(), b'keep copied edits')
                    self.assertNotIn('status', json.loads(audit.read_text()))
                    self.assertNotIn('removal_finished', json.loads(audit.read_text())['storage'])
                    archived = json.loads(audit.read_text())
                    with patch.dict(self.env, storage_call=lambda *a, **kw: self.fail('reclassified saved moved disposition')):
                        with self.assertRaises(self.helper['CompletionError']) as raised:
                            self.helper['refuse_moved'](archived, audit)
                    self.assertNotIn('--for-removal', shlex.split(raised.exception.storage_error['resume']))
                    # Reset for the other accepted command spelling.
                    audit.parent.rename(self.path.parent)
                    self.path.write_bytes(before)
        with patch.dict(shared, moved_operation=lambda saved: move, recovery_registration=unittest.mock.Mock(
                side_effect=shared['StorageRefusal']('storage_unavailable', 'pins unavailable'))):
            with self.assertRaises(self.helper['CompletionError']) as raised:
                self.recover(for_removal=True)
            self.assertNotIn('--for-removal', shlex.split(raised.exception.storage_error['resume']))
        # A Rust subreceipt reconciles but cannot enter any deletion, Begin, Finish or custody path.
        (self.path.parent / 'storage-allocation.json').write_text('{}')
        calls = []
        original = self.env['storage_call']
        def call(name, *args, **kwargs):
            if name == 'moved_operation':
                return move
            if name == 'recovery_registration':
                return {'retained_helper': {'path': 'retained'}}
            if name == 'call':
                calls.append(args[1])
                return {'operation_id': args[2]['removal_operation_id'], 'cache_ids': [],
                        'closure_result': {'established_by': 'authority_migrated', 'operation_id': move}}
            return original(name, *args, **kwargs)
        with patch.dict(self.env, storage_call=call, verify_custody=lambda *a: self.fail('custody'),
                        storage_rpc=lambda *a: self.fail('authority RPC')):
            result = self.recover(for_removal=True)
            self.assertEqual(calls, ['reconcile-for-removal'])
            self.assertEqual(self.recover(), result)

    def test_retired_moved_receipt_replays_identical_argv(self):
        retired = Path(self.recover()['receipt'])
        (retired.parent / 'retained-note').write_bytes(b'keep audit files')
        operation = self.receipt['storage']['request']['operation_id']
        argv = ['task-complete.py', 'recover-storage', '--receipt', str(retired), '--operation-id', operation]
        shared = self.helper['shared']('storage-client')
        with patch.dict(shared, moved_operation=lambda saved: client.operation_id(),
                        replay_retirement=lambda registration: None,
                        recovery_registration=lambda: {'retained_helper': {'path': 'retained'}}), \
             patch.object(sys, 'argv', argv):
            # The first successful reply is lost; the caller repeats the exact saved argv.
            with contextlib.redirect_stdout(io.StringIO()) as lost:
                self.assertEqual(self.helper['main'](), 0)
            with contextlib.redirect_stdout(io.StringIO()) as replay:
                self.assertEqual(self.helper['main'](), 0)
        result = json.loads(lost.getvalue())
        self.assertEqual(json.loads(replay.getvalue()), result)
        audit = Path(result['receipt'])
        self.assertEqual(audit.parent.parent.name, 'moved')
        self.assertEqual((audit.parent / 'retained-note').read_bytes(), b'keep audit files')
        before = audit.read_bytes()
        for field in ('id', 'common_gitdir', 'operation_id', 'external_receipt', 'moved'):
            saved = json.loads(before)
            if field == 'id':
                saved['id'] = 'another-receipt'
            elif field == 'common_gitdir':
                saved['common_gitdir'] = str(self.root / 'other')
            elif field == 'moved':
                saved['storage'].pop('moved')
            else:
                saved['storage']['request'][field] = client.operation_id() if field == 'operation_id' else str(retired)
            audit.write_text(json.dumps(saved))
            with self.subTest(field=field), self.assertRaisesRegex(self.helper['CompletionError'], 'binding changed'):
                self.helper['resolve_receipt'](retired, operation_id=operation)
        audit.write_bytes(before)
        with self.assertRaisesRegex(self.helper['CompletionError'], 'operation ID differs'):
            self.helper['resolve_receipt'](retired, operation_id=client.operation_id())

    def test_retired_moved_rename_retries_source_durability_barrier(self):
        retired = Path(self.recover()['receipt'])
        root = retired.parent.parent.parent
        operation = self.receipt['storage']['request']['operation_id']
        args = SimpleNamespace(receipt=str(retired), operation_id=operation, for_removal=False)
        shared = self.helper['shared']('storage-client')
        real_sync = shared['sync_directory']
        synced = []
        def interrupted_sync(directory):
            synced.append(directory)
            if directory == root / 'retired' and not retired.exists():
                raise OSError('source parent barrier interrupted')
            real_sync(directory)
        with patch.dict(shared, moved_operation=lambda saved: client.operation_id(),
                        replay_retirement=lambda registration: None,
                        recovery_registration=lambda: {'retained_helper': {'path': 'retained'}},
                        sync_directory=interrupted_sync):
            with self.assertRaisesRegex(OSError, 'source parent barrier interrupted'):
                self.helper['recover_storage'](args)
        self.assertFalse(retired.exists())
        self.assertIn(root / 'retired', synced)
        synced.clear()
        def sync(directory):
            synced.append(directory)
            real_sync(directory)
        with patch.dict(shared, sync_directory=sync):
            result = self.helper['recover_storage'](args)
        self.assertEqual(result['status'], 'STORAGE_MOVED')
        self.assertEqual(set(synced), {root / 'retired', root / 'moved', root})

    def test_missing_recovery_pins_returns_owner_removal_resume(self):
        helper = runpy.run_path(str(SHARED / 'task-complete.py'))
        home = self.root / 'home'
        (home / '.devlyn/storage-client-recovery').mkdir(parents=True)
        operation = self.receipt['storage']['request']['operation_id']
        before = self.path.read_bytes()
        argv = ['task-complete.py', 'recover-storage', '--receipt', str(self.path),
                '--operation-id', operation, '--for-removal']
        with patch.dict(os.environ, HOME=str(home), USERPROFILE=str(home)), patch.object(sys, 'argv', argv), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(helper['main'](), 1)
        result = json.loads(output.getvalue())
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertIn('repair Devlyn recovery pins', result['reason'])
        self.assertIn('--for-removal', shlex.split(result['resume']))
        self.assertIn(operation, shlex.split(result['resume']))
        self.assertEqual(result['storage_error']['resume'], result['resume'])
        self.assertEqual(self.path.read_bytes(), before)

    def test_locked_abandonment_retires_and_original_locator_resumes(self):
        lock = self.helper['shared']('platform-support')['file_lock']
        held = []
        @contextlib.contextmanager
        def observe(path, **kwargs):
            held.append(path)
            with lock(path, **kwargs):
                yield
        with patch.dict(self.helper['shared']('platform-support'), file_lock=observe):
            result = self.recover()
        audit = Path(result['receipt'])
        self.assertEqual(held, [self.path.parent.with_suffix('.lock')])
        self.assertFalse(self.path.exists())
        self.assertEqual(self.recover()['receipt'], str(audit))
        self.assertEqual(json.loads(audit.read_text())['storage']['request'], self.receipt['storage']['request'])

    def test_original_locator_refuses_ambiguous_retired_operations(self):
        first = Path(self.recover()['receipt'])
        receipt = json.loads(first.read_text())
        receipt['storage']['request']['operation_id'] = client.operation_id()
        second = first.parent.parent / (receipt['id'] + '.' + receipt['storage']['request']['operation_id'])
        second.mkdir()
        (second / 'receipt.json').write_text(json.dumps(receipt))
        with self.assertRaisesRegex(self.helper['CompletionError'],
                                    'ambiguous; use the operation-specific archived receipt:'):
            self.recover()
        self.assertEqual(self.recover(path=first)['receipt'], str(first))

    def test_terminal_active_and_retired_receipts_never_allocate(self):
        self.receipt.update(status='ABANDONED')
        self.receipt['storage']['removal_finished'] = True
        self.path.write_text(json.dumps(self.receipt))
        with patch.dict(self.env, finish_managed_allocation=lambda *args: self.fail('terminal allocation replayed')):
            with self.assertRaisesRegex(self.helper['CompletionError'], '--for-removal'):
                self.recover(for_removal=False)
            audit = Path(self.recover()['receipt'])
            with self.assertRaisesRegex(self.helper['CompletionError'], '--for-removal'):
                self.recover(for_removal=False, path=audit)

    def test_finish_removal_interruption_finishes_abandonment(self):
        self.receipt['storage']['removal_finished'] = True
        self.receipt['storage']['removal_request'] = {'removal_operation_id': client.operation_id()}
        self.path.write_text(json.dumps(self.receipt))
        with patch.dict(self.env, managed_removal_gate=lambda *args, **kwargs: self.fail('finished removal restarted')):
            result = self.recover()
        self.assertEqual(result['status'], 'ABANDONED')
        saved = json.loads(Path(result['receipt']).read_text())
        self.assertEqual(saved['storage']['removal_request'], self.receipt['storage']['removal_request'])

    def test_absent_checkout_modules_veto_with_only_native_git_registration(self):
        admin = self.root / 'worktrees' / 'task'
        modules = admin / 'modules' / 'vendor' / 'lib'
        modules.mkdir(parents=True)
        precious = modules / 'only-copy'
        precious.write_bytes(b'unpushed source')
        (admin / 'gitdir').write_text((Path(self.receipt['worktree']) / '.git').as_posix() + '\n', encoding='utf-8')
        for operation in (lambda: self.helper['managed_removal_gate'](self.receipt, self.path, registration={'retained': True}),
                          lambda: self.helper['remove_managed_registration'](self.receipt)):
            with self.assertRaisesRegex(self.helper['CompletionError'], 'repositories block removal'):
                operation()
            self.assertNotIn('removal_request', self.receipt['storage'])
            self.assertEqual(precious.read_bytes(), b'unpushed source')

    def test_saved_resume_never_touches_reused_operation(self):
        old = self.receipt['storage']['request']['operation_id']
        saved_resume = self.helper['storage_resume'](self.path, for_removal=True)
        self.assertIn('--operation-id ' + old, saved_resume)
        saved_complete = self.helper['receipt_resume']('complete', self.path, self.receipt)
        self.assertIn('--operation-id ' + old, saved_complete)
        audit = Path(self.recover()['receipt'])
        self.path.parent.mkdir()
        replacement = json.loads(json.dumps(self.receipt))
        replacement['storage']['request']['operation_id'] = client.operation_id()
        self.path.write_text(json.dumps(replacement))
        before = self.path.read_bytes(), audit.read_bytes()
        for action in ('recover-storage', 'complete'):
            argv = ['task-complete.py', action, '--receipt', str(self.path), '--operation-id', old]
            if action == 'recover-storage':
                argv += ['--for-removal']
            with self.subTest(action=action), patch.object(sys, 'argv', argv), \
                 contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(self.helper['main'](), 0 if action == 'recover-storage' else 1)
                result = json.loads(output.getvalue())
                self.assertEqual(result.get('status'), 'ABANDONED' if action == 'recover-storage' else 'BLOCKED')
            self.assertEqual((self.path.read_bytes(), audit.read_bytes()), before)
        with self.helper['locked_receipt'](self.helper['resolve_receipt'](self.path), resume=True) as active:
            self.assertEqual(active['storage']['request']['operation_id'], replacement['storage']['request']['operation_id'])
        with self.assertRaisesRegex(self.helper['CompletionError'], 'operation'):
            self.helper['resolve_receipt'](self.path, operation_id=client.operation_id())

    def test_retired_complete_preserves_clean_scratch_without_observation(self):
        self.receipt.update(status='COMPLETE', delivery='COMPLETE', scratch_identity={},
                            scratch_cleanup={'status': 'CLEAN', 'bytes': 7})
        self.receipt['storage']['removal_finished'] = True
        self.path.write_text(json.dumps(self.receipt))
        audit = self.helper['retire_terminal'](self.receipt, self.path)
        before = audit.read_bytes()
        with patch.dict(self.env, clean_scratch=unittest.mock.Mock(side_effect=self.helper['WritersUnobservable']('offline mount'))):
            result = self.helper['completion_result'](self.receipt, audit, 'COMPLETE')
        self.assertEqual(result['scratch_cleanup'], {'status': 'CLEAN', 'bytes': 7})
        self.assertEqual(audit.read_bytes(), before)
        with self.helper['locked_receipt'](audit):
            pass

    @unittest.skipIf(os.name == 'nt', 'safe scratch deletion is unsupported on native Windows')
    def test_retired_complete_persists_new_writer_release_and_cleans_scratch(self):
        scratch = self.path.parent / 'scratch'
        scratch.mkdir()
        (scratch / 'output').write_bytes(b'disposable')
        self.receipt.update(allocation='managed_owned', linked=True, status='COMPLETE', delivery='COMPLETE',
            scratch_identity=self.helper['workspace_identity'](scratch, self.path.parent),
            scratch_cleanup={'status': 'RETAINED', 'reason': 'writers not released'})
        self.receipt['storage'].update(removal_finished=True, result={'closure_result': {
            'established_by': 'never_admitted', 'operation_id': self.receipt['storage']['request']['operation_id']}})
        self.path.write_text(json.dumps(self.receipt))
        audit = self.helper['retire_terminal'](self.receipt, self.path)
        argv = ['task-complete.py', 'complete', '--receipt', str(audit), '--writers-stopped']
        with patch.dict(self.env, stopped_writers=lambda work: None, scratch_mounts=lambda: [],
                        cleanup=lambda *args, **kwargs: self.fail('retired source cleanup attempted')), \
             patch.object(sys, 'argv', argv), contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(self.helper['main'](), 0)
        self.assertEqual(json.loads(output.getvalue())['status'], 'COMPLETE')
        saved = json.loads(audit.read_text())
        self.assertTrue(saved['writers_released'])
        self.assertEqual(saved['scratch_cleanup']['status'], 'CLEAN')
        self.assertEqual(list((audit.parent / 'scratch').iterdir()), [])

    @unittest.skipIf(os.name == 'nt', 'safe scratch deletion is unsupported on native Windows')
    def test_retired_complete_retries_retained_and_unrecorded_scratch(self):
        for retry in ('resume', 'reconcile', 'missing record'):
            with self.subTest(retry=retry):
                # Separate operations keep reconciliation and retired locators real.
                if not self.path.parent.exists():
                    self.path.parent.mkdir()
                scratch = self.path.parent / 'scratch'
                scratch.mkdir()
                (scratch / 'output').write_bytes(b'disposable')
                self.receipt.update(allocation='managed_owned', linked=True, status='PENDING' if retry == 'reconcile' else 'COMPLETE', delivery='COMPLETE',
                    writers_released=True, acceptance={'kind': 'direct'},
                    scratch_identity=self.helper['workspace_identity'](scratch, self.path.parent))
                self.receipt.pop('scratch_cleanup', None)
                self.receipt['storage']['request']['operation_id'] = client.operation_id()
                self.receipt['storage'].update(removal_finished=True, result={'closure_result': {
                    'established_by': 'never_admitted', 'operation_id': self.receipt['storage']['request']['operation_id']}})
                self.path.write_text(json.dumps(self.receipt))
                if retry == 'missing record':
                    audit = self.helper['retire_terminal'](self.receipt, self.path)
                else:
                    with patch.dict(self.env, stopped_writers=unittest.mock.Mock(side_effect=self.helper['WriterActive']('active cache writer')),
                                    scratch_mounts=lambda: []):
                        result = self.helper['completion_result'](self.receipt, self.path, 'COMPLETE')
                    self.assertEqual(result['status'], 'CLEANUP_PENDING')
                    audit = Path(result['receipt'])
                    self.assertEqual(audit.parent.parent.name, 'retired')
                with patch.dict(self.env, stopped_writers=lambda work: None, scratch_mounts=lambda: []):
                    if retry == 'reconcile':
                        results = self.helper['reconcile'](self.root, None, self.root)
                        self.assertEqual([r['status'] for r in results], ['COMPLETE'])
                    else:
                        saved = result['resume'] if retry == 'resume' else self.helper['receipt_resume'](
                            'complete', audit, self.receipt, flags=['--writers-stopped'])
                        with patch.object(sys, 'argv', shlex.split(saved)[1:]), contextlib.redirect_stdout(io.StringIO()) as output:
                            self.assertEqual(self.helper['main'](), 0)
                            self.assertEqual(json.loads(output.getvalue())['status'], 'COMPLETE')
                self.assertEqual(json.loads(audit.read_text())['scratch_cleanup']['status'], 'CLEAN')
                self.assertEqual(list((audit.parent / 'scratch').iterdir()), [])

    @unittest.skipIf(os.name == 'nt', 'safe scratch deletion is unsupported on native Windows')
    def test_saved_scratch_resume_cleans_retired_r1_after_r2_reuses_key(self):
        scratch = self.path.parent / 'scratch'
        scratch.mkdir()
        (scratch / 'r1-output').write_bytes(b'disposable R1')
        self.receipt.update(delivery='LOCAL_ONLY', scratch_identity=self.helper['workspace_identity'](scratch, self.path.parent))
        self.receipt['storage'].update(removal_finished=True,
            result={'closure_result': {'established_by': 'never_admitted',
                    'operation_id': self.receipt['storage']['request']['operation_id']}})
        saved = self.helper['receipt_resume']('clean-scratch', self.path, self.receipt, flags=['--writers-stopped'])
        self.receipt['scratch_cleanup'] = {'status': 'RETAINED', 'resume': saved}
        self.path.write_text(json.dumps(self.receipt))
        audit = self.helper['retire_terminal'](self.receipt, self.path)
        self.assertEqual((audit.parent / 'scratch/r1-output').read_bytes(), b'disposable R1')
        self.path.parent.mkdir()
        replacement = json.loads(json.dumps(self.receipt))
        replacement['storage']['request']['operation_id'] = client.operation_id()
        self.path.write_text(json.dumps(replacement))
        r2 = self.path.parent / 'scratch'
        r2.mkdir()
        (r2 / 'r2-output').write_bytes(b'R2 must survive')
        before = self.path.read_bytes()
        with patch.dict(self.env, stopped_writers=lambda work: None, scratch_mounts=lambda: []), \
             patch.object(sys, 'argv', shlex.split(saved)[1:]), contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(self.helper['main'](), 0, output.getvalue())
        self.assertEqual(json.loads(output.getvalue())['receipt'], str(audit))
        self.assertEqual(list((audit.parent / 'scratch').iterdir()), [])
        self.assertEqual((r2 / 'r2-output').read_bytes(), b'R2 must survive')
        self.assertEqual(self.path.read_bytes(), before)
        clean = audit.read_bytes()
        with patch.dict(self.env, stopped_writers=unittest.mock.Mock(side_effect=self.helper['WritersUnobservable']('no observation'))):
            result = self.helper['clean_scratch_command'](SimpleNamespace(receipt=str(audit), writers_stopped=True))
        self.assertEqual(result['scratch_cleanup']['status'], 'CLEAN')
        self.assertEqual(audit.read_bytes(), clean)

    def test_final_deliveries_retire_with_retained_scratch_without_deleting_it(self):
        scratch = self.path.parent / 'scratch'
        scratch.mkdir()
        (scratch / 'output').write_bytes(b'preserved')
        for delivery in ('COMPLETE', 'LOCAL_ONLY', 'FAILED', 'CLOSED'):
            with self.subTest(delivery=delivery):
                self.receipt.update(delivery=delivery, scratch_cleanup={'status': 'RETAINED', 'reason': 'unobservable'})
                self.receipt['storage']['removal_finished'] = True
                self.assertTrue(self.helper['managed_terminal'](self.receipt))
        self.path.write_text(json.dumps(self.receipt))
        audit = self.helper['retire_terminal'](self.receipt, self.path)
        self.assertEqual((audit.parent / 'scratch/output').read_bytes(), b'preserved')
        self.assertEqual(json.loads(audit.read_text())['scratch_cleanup']['status'], 'RETAINED')

    def test_unobservable_abandonment_names_by_hand_checkout_removal(self):
        with patch.dict(self.env, abandon_managed=unittest.mock.Mock(
                side_effect=self.helper['WritersUnobservable']('unobservable writer'))), \
             self.assertRaisesRegex(self.helper['WritersUnobservable'], 'remove the task checkout by hand') as raised:
            self.recover()
        self.assertIn('--operation-id ' + self.receipt['storage']['request']['operation_id'], str(raised.exception))
        self.assertIn('--for-removal', str(raised.exception))

    def test_cli_preserves_structured_removal_resume(self):
        for schedule in ('fenced', 'terminal', 'unenrolled', 'complete'):
            saved = json.loads(json.dumps(self.receipt))
            if schedule == 'terminal':
                saved['status'] = 'ABANDONED'
                saved['storage']['removal_finished'] = True
            elif schedule != 'unenrolled':
                saved['storage']['removal_request'] = {'removal_operation_id': client.operation_id()}
            self.path.write_text(json.dumps(saved))
            action = 'complete' if schedule == 'complete' else 'recover-storage'
            with self.subTest(schedule=schedule), patch.dict(os.environ, HOME=str(self.root), USERPROFILE=str(self.root)), \
                 patch.dict(self.env, managed_registration=self.helper['managed_registration'],
                     complete=lambda args: self.helper['allocation_replayable'](saved, self.path)), \
                 patch.object(sys, 'argv', ['task-complete.py', action, '--receipt', str(self.path)]), \
                 contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(self.helper['main'](), 1)
            result = json.loads(output.getvalue())
            self.assertEqual(result['resume'], result['storage_error']['resume'])
            self.assertIn('--for-removal', result['resume'])
            self.assertIn('--operation-id ' + saved['storage']['request']['operation_id'], result['resume'])

    def test_retired_locator_rejects_changed_operation_binding(self):
        audit = Path(self.recover()['receipt'])
        saved = json.loads(audit.read_text())
        saved['storage']['request']['operation_id'] = client.operation_id()
        audit.write_text(json.dumps(saved))
        with self.assertRaisesRegex(self.helper['CompletionError'], 'binding changed'):
            self.recover()


class ManagedOwnerTests(unittest.TestCase):
    def setUp(self):
        self.helper = runpy.run_path(str(SHARED / 'task-complete.py'))
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.work = self.root / 'tree'
        self.work.mkdir()
        self.path = self.root / 'receipt.json'
        self.receipt = {'worktree': str(self.work), 'storage': {'decision': {'registration': {'fixture': True}},
            'request': {'operation_id': client.operation_id()}}}
        self.closure = {'established_by': 'never_admitted', 'operation_id': client.operation_id()}
        self.env = self.helper['managed_removal_gate'].__globals__

    def gate(self, *, finished=False, not_found=False):
        def call(name, *args, **kwargs):
            if name == 'call':
                return {'operation_id': args[2]['removal_operation_id'], 'cache_ids': ['cache'], 'closure_result': self.closure}
            return getattr(client, name)(*args, **kwargs)
        def rpc(registration, request, path):
            if not_found:
                exc = self.helper['CompletionError']('compacted')
                exc.storage_error = {'code': 'storage_not_found'}
                raise exc
            return {'operation_id': request['operation_id'], 'removal_id': 'removal',
                    'entries': [{'cache_id': 'cache', 'generation': 1}], 'finished_at': 'done' if finished else None}
        with patch.dict(self.env, managed_registration=lambda receipt: {}, storage_call=call, storage_rpc=rpc):
            return self.helper['managed_removal_gate'](self.receipt, self.path)

    def test_accepted_recovery_reconciles_without_beginning_live_cache_removal(self):
        self.receipt.update(allocation='managed_owned', acceptance={'kind': 'direct'}, common_gitdir=str(self.root))
        self.path.write_text(json.dumps(self.receipt))
        def call(name, *args, **kwargs):
            if name == 'call':
                return {'operation_id': args[2]['removal_operation_id'], 'cache_ids': ['live-cache'], 'closure_result': self.closure}
            return getattr(client, name)(*args, **kwargs)
        with patch.dict(self.env, locked_receipt=lambda *args, **kwargs: contextlib.nullcontext(self.receipt),
                managed_registration=lambda *args, **kwargs: {'retained': True}, storage_call=call,
                storage_rpc=lambda *args, **kwargs: self.fail('reconciliation began removal of live caches')):
            result = self.helper['recover_storage'](SimpleNamespace(receipt=str(self.path), for_removal=True))
        self.assertEqual(result['status'], 'REMOVAL_RECONCILED')
        self.assertEqual(result['cache_ids'], ['live-cache'])
        self.assertNotIn('begin_removal', self.receipt['storage'])
        self.assertTrue(self.work.exists())

    def test_pending_without_rust_receipt_has_terminal_abandonment_without_adapter(self):
        self.work.rmdir()
        self.path = self.root / 'devlyn-completion/pending/receipt.json'
        self.path.parent.mkdir(parents=True)
        self.receipt.update(branch='task/pending', baseline='baseline', allocation='managed_pending', common_gitdir=str(self.root))
        with patch.dict(self.env, managed_registration=lambda *args, **kwargs: {}, ref_sha=lambda *args: None,
                        registrations=lambda receipt: {}, storage_call=lambda name, *args, **kwargs: getattr(client, name)(*args, **kwargs)):
            result = self.helper['abandon_managed'](self.receipt, self.path)
        self.assertEqual(result['status'], 'ABANDONED')
        self.assertFalse(self.path.exists())
        self.assertTrue(Path(result['receipt']).exists())

    def native_local_repository(self):
        # Native Git only: URL routing is Git config, never a PATH launcher.
        home = self.root / 'home'
        home.mkdir()
        environment = {**os.environ, 'HOME': str(home), 'USERPROFILE': str(home),
            'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_COUNT': '0',
            'GIT_AUTHOR_NAME': 'Fixture', 'GIT_AUTHOR_EMAIL': 'fixture@example.invalid',
            'GIT_COMMITTER_NAME': 'Fixture', 'GIT_COMMITTER_EMAIL': 'fixture@example.invalid', 'GIT_ALLOW_PROTOCOL': 'file'}
        for key in ('GIT_DIR', 'GIT_COMMON_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE'):
            environment.pop(key, None)
        git_bin = shutil.which('git')
        def git(*args):
            return subprocess.check_output([git_bin, '-C', str(self.work), *map(str, args)],
                env=environment, stderr=subprocess.PIPE, text=True, encoding='utf-8').strip()
        remote = self.root / 'remote.git'
        git('init', '--bare', '--initial-branch=main', remote)
        git('init', '--initial-branch=main')
        (self.work / '.gitignore').write_text('.devlyn/\n', encoding='utf-8')
        (self.work / 'source').write_text('baseline', encoding='utf-8')
        git('add', '.')
        git('commit', '-m', 'baseline')
        git('config', 'url.' + remote.as_uri() + '.insteadOf', 'https://github.com/test/project.git')
        git('remote', 'add', 'origin', 'https://github.com/test/project.git')
        git('push', 'origin', 'main')
        args = SimpleNamespace(repo=str(self.work), task='fixture', branch='task/fixture', base='main',
            remote='origin', repository=None, worktree=str(self.root / 'task'), local_base=git('rev-parse', 'HEAD'),
            from_receipt=None, start=None)
        return home, environment, git, args

    def test_active_abandoned_allocate_retires_before_fresh_allocation(self):
        home, environment, git, args = self.native_local_repository()
        with patch.dict(os.environ, environment, clear=True), patch.object(shutil, 'disk_usage',
                return_value=SimpleNamespace(total=100 * 1024**3, free=100 * 1024**3)):
            result = self.helper['allocate'](args)
            path = Path(result['receipt'])
            saved = json.loads(path.read_text(encoding='utf-8'))
            git('worktree', 'remove', '--force', args.worktree)
            git('branch', '-D', saved['branch'])
            saved.update(status='ABANDONED', allocation='managed_pending', mode='managed', storage={
                'decision': {'registration': {'fixture': True}}, 'removal_finished': True,
                'request': {'operation_id': client.operation_id(), 'external_receipt': str(path)}})
            path.write_text(json.dumps(saved), encoding='utf-8')
            with patch.dict(self.env, finish_managed_allocation=lambda *args: self.fail('abandoned operation admitted again')):
                fresh = self.helper['allocate'](args)
        self.assertEqual(fresh['status'], 'ALLOCATED')
        self.assertNotIn('storage', json.loads(path.read_text(encoding='utf-8')))
        retired, = (path.parent.parent / 'retired').glob('*/receipt.json')
        self.assertEqual(json.loads(retired.read_text(encoding='utf-8'))['storage']['request'], saved['storage']['request'])

    @unittest.skipIf(os.name == 'nt', 'safe scratch deletion is unsupported on native Windows')
    def test_next_allocation_cleans_retired_complete_scratch(self):
        fixture = self.helper['CompletionTests']('test_standalone_without_devlyn_keeps_existing_allocation_and_warm_behavior')
        self.addCleanup(fixture.doCleanups)
        fixture.setUp()
        allocated = fixture.allocate()
        path = Path(allocated['receipt'])
        saved = json.loads(path.read_text())
        operation = client.operation_id()
        saved.update(mode='managed', allocation='managed_owned', status='COMPLETE', delivery='COMPLETE',
            acceptance={'kind': 'direct'}, writers_released=True, storage={
                'decision': {'registration': {'fixture': True}},
                'removal_finished': True, 'request': {'operation_id': operation, 'external_receipt': str(path)},
                'result': {'closure_result': {'established_by': 'never_admitted', 'operation_id': operation}}})
        (path.parent / 'scratch/output').write_bytes(b'disposable cache')
        fixture.g('worktree', 'remove', '--force', allocated['worktree'])
        with patch.dict(os.environ, fixture.env, clear=True):
            with patch.dict(self.env, stopped_writers=unittest.mock.Mock(side_effect=self.helper['WriterActive']('cache writer')),
                            scratch_mounts=lambda: []):
                result = self.helper['completion_result'](saved, path, 'COMPLETE')
            self.assertEqual(result['status'], 'CLEANUP_PENDING')
            audit = Path(result['receipt'])
            args = fixture.allocation_args('next', fixture.root / 'next-task')
            with patch.dict(self.env, stopped_writers=lambda work: None, scratch_mounts=lambda: []):
                allocated = self.helper['allocate'](args)
        self.assertEqual(allocated['status'], 'ALLOCATED')
        self.assertEqual([r['status'] for r in allocated['reconciled']], ['COMPLETE'])
        self.assertEqual(json.loads(audit.read_text())['scratch_cleanup']['status'], 'CLEAN')
        self.assertEqual(list((audit.parent / 'scratch').iterdir()), [])

    def test_unsafe_platform_dirty_abandonment_retains_source_without_manual_advice(self):
        home, environment, git, args = self.native_local_repository()
        with patch.dict(os.environ, environment, clear=True), patch.object(shutil, 'disk_usage',
                return_value=SimpleNamespace(total=100 * 1024**3, free=100 * 1024**3)):
            allocated = self.helper['allocate'](args)
            path = Path(allocated['receipt'])
            work = Path(allocated['worktree'])
            saved = json.loads(path.read_text())
            operation = client.operation_id()
            saved.update(mode='managed', allocation='managed_owned', storage={
                'decision': {'registration': {'retained': True}},
                'request': {'operation_id': operation, 'external_receipt': str(path)}})
            path.write_text(json.dumps(saved))
            path.with_name('storage-allocation.json').write_text('Rust receipt marker')
            (work / 'source').write_text('uncommitted edit')
            (work / 'new-source').write_text('untracked new file')
            with patch.object(shutil.rmtree, 'avoids_symlink_attacks', False), \
                 patch.dict(self.env, managed_registration=lambda *args, **kwargs: {},
                    stopped_writers=lambda work: self.fail('writer observation preceded source verification')):
                with self.assertRaisesRegex(self.helper['CompletionError'], 'source changed; retain') as raised:
                    self.helper['recover_storage'](SimpleNamespace(receipt=str(path), operation_id=operation, for_removal=True))
                self.assertNotIn('by hand', str(raised.exception))
                self.assertEqual((work / 'source').read_text(), 'uncommitted edit')
                self.assertEqual((work / 'new-source').read_text(), 'untracked new file')
                (work / 'source').write_text('baseline')
                with self.assertRaisesRegex(self.helper['CompletionError'], 'new source; retain') as raised:
                    self.helper['recover_storage'](SimpleNamespace(receipt=str(path), operation_id=operation, for_removal=True))
                self.assertNotIn('by hand', str(raised.exception))
                # Interrupted deletion must verify its saved manifest before guidance too.
                sidecar = path.with_name('tree-removal.json')
                sidecar.write_text('{}')
                saved['storage']['tree_removal_digest'] = self.helper['file_record'](sidecar)['sha256']
                path.write_text(json.dumps(saved))
                with self.assertRaisesRegex(self.helper['CompletionError'], 'partial removal file changed or new source; retain') as raised:
                    self.helper['recover_storage'](SimpleNamespace(receipt=str(path), operation_id=operation, for_removal=True))
                self.assertNotIn('by hand', str(raised.exception))
            self.assertTrue(work.is_dir())
            self.assertTrue(path.exists())

    def test_native_manual_removal_retires_with_retained_scratch(self):
        home, environment, git, args = self.native_local_repository()
        with patch.dict(os.environ, environment, clear=True), patch.object(shutil, 'disk_usage',
                return_value=SimpleNamespace(total=100 * 1024**3, free=100 * 1024**3)):
            allocated = self.helper['allocate'](args)
            path = Path(allocated['receipt'])
            work = Path(allocated['worktree'])
            evidence = work / '.devlyn'
            evidence.mkdir(exist_ok=True)
            (evidence / 'checks.txt').write_text('native Git source verified')
            acceptance = evidence / 'acceptance.json'
            acceptance.write_text(json.dumps({'kind': 'direct', 'task': 'fixture', 'source_sha': git('rev-parse', 'HEAD'),
                'checks': [{'command': 'native fixture source check', 'evidence': '.devlyn/checks.txt'}]}))
            self.helper['accept'](SimpleNamespace(receipt=str(path), acceptance=str(acceptance)))
            saved = json.loads(path.read_text())
            operation = client.operation_id()
            saved.update(mode='managed', allocation='managed_owned', storage={
                'decision': {'registration': {'retained': True}},
                'request': {'operation_id': operation, 'external_receipt': str(path)},
                'result': {'closure_result': {'established_by': 'never_admitted', 'operation_id': operation}}})
            path.write_text(json.dumps(saved))
            (path.parent / 'scratch/output').write_bytes(b'keep disposable output')
            call = self.env['storage_call']
            fences = []
            def adapter(name, *values, **kwargs):
                if name == 'call' and kwargs.get('adapter'):
                    self.assertEqual(values[1], 'reconcile-for-removal')
                    fences.append(values[2])
                    return {'operation_id': values[2]['removal_operation_id'], 'cache_ids': [],
                            'closure_result': {'established_by': 'never_admitted', 'operation_id': operation}}
                return call(name, *values, **kwargs)
            unavailable = unittest.mock.Mock(side_effect=self.helper['WritersUnobservable']('cannot observe writers'))
            with patch.dict(self.env, managed_registration=lambda *args, **kwargs: {'retained': True},
                            storage_call=adapter, stopped_writers=unavailable, scratch_mounts=lambda: []):
                self.helper['complete'](SimpleNamespace(receipt=str(path), acceptance=None, mode=None,
                    local_only=True, writers_stopped=True))
                write_retirement(home)
                recovery = SimpleNamespace(receipt=str(path), operation_id=operation, for_removal=True)
                with self.assertRaisesRegex(self.helper['WritersUnobservable'], 'remove the task checkout by hand'):
                    self.helper['recover_storage'](recovery)
                self.assertEqual(fences, [])
                retained = json.loads(path.read_text())['storage']['records_custody']
                self.assertEqual((Path(retained['path']) / '.devlyn/checks.txt').read_text(), 'native Git source verified')
                self.assertEqual(self.helper['records_manifest'](Path(retained['path'])), retained['files'])
                git('worktree', 'remove', '--force', work)
                result = self.helper['recover_storage'](recovery)
            audit = Path(result['receipt'])
            self.assertEqual(audit.parent.parent.name, 'retired')
            self.assertEqual(result['scratch_cleanup']['status'], 'RETAINED')
            self.assertIn('--operation-id ' + operation, result['scratch_cleanup']['resume'])
            self.assertEqual((audit.parent / 'scratch/output').read_bytes(), b'keep disposable output')
            self.assertTrue(fences)
            self.assertEqual(git('rev-parse', 'refs/heads/' + saved['branch']), saved['publish_sha'])
            self.assertNotIn(str(work), self.helper['registrations'](saved))

    @unittest.skipIf(os.name == 'nt', 'Windows cannot observe writers')
    def test_empty_partial_checkout_checks_writers_before_gate(self):
        self.receipt.update(branch='task/pending', baseline='baseline', allocation='managed_pending', common_gitdir=str(self.root))
        self.path.with_name('storage-allocation.json').write_text('Rust marker')
        with patch.dict(self.env, managed_registration=lambda *args, **kwargs: {}, ref_sha=lambda *args: None,
                        registrations=lambda receipt: {}, managed_removal_gate=lambda *args, **kwargs: self.fail('fenced before writer check'),
                        stopped_writers=unittest.mock.Mock(side_effect=self.helper['WriterActive']('active writer'))), \
             self.assertRaisesRegex(self.helper['CompletionError'], 'active writer'):
            self.helper['abandon_managed'](self.receipt, self.path)
        self.assertNotIn('removal_request', self.receipt['storage'])

    @unittest.skipIf(os.name == 'nt', 'native POSIX deletion; Windows retains')
    def test_interrupted_checkout_can_be_abandoned_and_branch_reallocated_with_audit_retained(self):
        fixture = self.helper['CompletionTests']('test_standalone_without_devlyn_keeps_existing_allocation_and_warm_behavior')
        self.addCleanup(fixture.doCleanups)
        fixture.setUp()
        result = fixture.allocate()
        path, work = Path(result['receipt']), Path(result['worktree'])
        receipt = json.loads(path.read_text())
        receipt.update(mode='managed', allocation='managed_pending', storage={'decision': {'registration': {'fixture': True}}, 'request': {'operation_id': client.operation_id()}})
        path.with_name('storage-allocation.json').write_text('Rust-owned marker')
        def gate(receipt, path, **kwargs):
            receipt['storage'].setdefault('removal_request', {'worktree_identity': client.persistent_identity(work)})
            return {}
        with patch.dict(os.environ, fixture.env, clear=True), patch.dict(self.env,
                managed_registration=lambda *args, **kwargs: {}, managed_removal_gate=gate,
                stopped_writers=lambda work: None, scratch_mounts=lambda: []):
            (work / 'product').write_text('staged source')
            fixture.g('add', 'product', work=work)
            (work / 'product').write_text('baseline\n')
            with self.assertRaisesRegex(self.helper['CompletionError'], 'index changed'):
                self.helper['abandon_managed'](receipt, path)
            fixture.g('reset', '--', 'product', work=work)
            # An interrupted checkout may omit entries from its index.
            fixture.g('rm', '--cached', 'product', work=work)
            abandoned = self.helper['abandon_managed'](receipt, path)
            self.assertEqual(abandoned['status'], 'ABANDONED')
            self.assertFalse(work.exists())
            self.assertEqual(fixture.g('branch', '--list', receipt['branch']), '')
            self.assertFalse(path.exists())
            self.assertTrue(Path(abandoned['receipt']).exists())
            self.assertEqual(self.helper['recover_storage'](SimpleNamespace(receipt=abandoned['receipt'], for_removal=True))['status'], 'ABANDONED')
            replacement = self.helper['allocate'](fixture.allocation_args('fixture', work))
            self.assertEqual(replacement['status'], 'ALLOCATED')
            retired, = (path.parent.parent / 'retired').glob('*/storage-allocation.json')
            self.assertEqual(retired.read_text(), 'Rust-owned marker')
            self.assertNotIn('storage', json.loads(path.read_text()))

    def test_finished_removal_replay_never_authorizes_a_present_tree(self):
        with self.assertRaisesRegex(self.helper['CompletionError'], 'finished removal path is present'):
            self.gate(finished=True)
        self.work.rmdir()
        self.gate(finished=True)
        self.assertTrue(self.receipt['storage']['removal']['finished_at'])

    def test_compacted_notfound_requires_positive_tree_absence(self):
        with self.assertRaisesRegex(self.helper['CompletionError'], 'compacted'):
            self.gate(not_found=True)
        self.work.rmdir()
        self.gate(not_found=True)
        self.assertTrue(self.receipt['storage']['removal_compacted'])

    def test_compaction_cannot_treat_inaccessible_tree_as_absent(self):
        self.receipt['storage']['removal_request'] = {'removal_operation_id': client.operation_id(), 'worktree_identity': None}
        original = Path.lstat
        def observe(path, *args, **kwargs):
            if path == self.work:
                raise PermissionError('tree observation denied')
            return original(path, *args, **kwargs)
        with patch.object(Path, 'lstat', observe), self.assertRaises(PermissionError):
            self.gate(not_found=True)
        self.assertNotIn('removal_compacted', self.receipt['storage'])

    @unittest.skipIf(os.name == 'nt', 'native POSIX deletion; Windows retains')
    def test_partial_removal_resumes_after_ignore_deletion_but_rejects_unknown_or_changed_survivors(self):
        fixture = self.helper['CompletionTests']('test_standalone_without_devlyn_keeps_existing_allocation_and_warm_behavior')
        self.addCleanup(fixture.doCleanups)
        fixture.setUp()
        result = fixture.allocate()
        path = Path(result['receipt'])
        work = Path(result['worktree'])
        receipt = json.loads(path.read_text())
        receipt.update(mode='managed', allocation='managed_owned', files={}, publish_sha=receipt['baseline'])
        receipt['storage'] = {'removal_request': {'worktree_identity': client.persistent_identity(work)}}
        (work / '.devlyn').mkdir(exist_ok=True)
        (work / '.devlyn/.gitignore').write_text('*\n')
        (work / '.devlyn/acceptance.json').write_text('{}')
        (work / 'ignored').mkdir()
        (work / 'ignored/cache').write_text('cache')
        real_empty = self.helper['empty_owned_tree']
        def interrupted(fd):
            (work / '.devlyn/acceptance.json').unlink()
            (work / '.devlyn/.gitignore').unlink()
            (work / '.devlyn').rmdir()
            raise self.helper['CompletionError']('interrupted after ignore deletion')
        with patch.dict(os.environ, fixture.env, clear=True), patch.dict(self.env,
                managed_removal_gate=lambda *args, **kwargs: {}, stopped_writers=lambda work: None, scratch_mounts=lambda: []):
            with patch.dict(self.env, empty_owned_tree=interrupted), self.assertRaisesRegex(self.helper['CompletionError'], 'interrupted'):
                self.helper['remove_managed_tree'](receipt, path)
            (work / 'unexpected').write_text('new source')
            with self.assertRaises(self.helper['CompletionError']):
                self.helper['remove_managed_tree'](receipt, path)
            (work / 'unexpected').unlink()
            (work / 'product').write_text('changed')
            with self.assertRaisesRegex(self.helper['CompletionError'], 'source changed'):
                self.helper['remove_managed_tree'](receipt, path)
            (work / 'product').write_text('baseline\n')
            self.helper['remove_managed_tree'](receipt, path)
        self.assertFalse(work.exists())


@unittest.skipIf(os.name == 'nt', 'managed deletion retains on Windows')
class ManagedRemovalRegressions(unittest.TestCase):
    def setUp(self):
        self.helper = runpy.run_path(str(SHARED / 'task-complete.py'))
        self.fixture = self.helper['CompletionTests']('test_standalone_without_devlyn_keeps_existing_allocation_and_warm_behavior')
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.setUp()
        environment = patch.dict(os.environ, self.fixture.env, clear=True)
        environment.start()
        self.addCleanup(environment.stop)
        self.env = self.helper['remove_managed_tree'].__globals__
        self.calls = []

    def allocate(self):
        result = self.fixture.allocate()
        self.path, self.work = Path(result['receipt']), Path(result['worktree'])
        self.receipt = json.loads(self.path.read_text())
        self.receipt.update(mode='managed', allocation='managed_owned', publish_sha=self.receipt['baseline'], files={},
                            storage={'request': {'operation_id': client.operation_id()}})
        return self.receipt

    def gate(self, receipt, path, **kwargs):
        self.calls.append('gate')
        receipt['storage'].setdefault('removal_request', {'worktree_identity': client.persistent_identity(self.work)})
        return {}

    def remove(self, **kwargs):
        with patch.dict(self.env, managed_removal_gate=self.gate, stopped_writers=lambda work: None, scratch_mounts=lambda: []):
            self.helper['remove_managed_tree'](self.receipt, self.path, **kwargs)

    def test_populated_submodule_and_module_repository_retained_before_fence(self):
        source = self.fixture.root / 'module-source'
        source.mkdir()
        self.fixture.g('init', '-b', 'main', work=source)
        (source / 'precious').write_text('unpushed source')
        self.fixture.g('add', '.', work=source)
        self.fixture.g('commit', '-m', 'submodule source', work=source)
        self.fixture.g('-c', 'protocol.file.allow=always', 'submodule', 'add', str(source), 'vendor/lib')
        self.fixture.g('commit', '-am', 'gitlink')
        self.fixture.g('push', 'origin', 'main')
        self.allocate()
        self.fixture.g('-c', 'protocol.file.allow=always', 'submodule', 'update', '--init', work=self.work)
        module = self.work / 'vendor/lib'
        (module / 'precious').write_text('only copy of a new commit')
        self.fixture.g('add', '.', work=module)
        self.fixture.g('commit', '-m', 'local-only module commit', work=module)
        self.fixture.g('add', 'vendor/lib', work=self.work)
        self.fixture.g('commit', '-m', 'new gitlink', work=self.work)
        self.receipt['publish_sha'] = self.fixture.g('rev-parse', 'HEAD', work=self.work)
        self.receipt['baseline'] = self.receipt['publish_sha']
        module_gitdir = Path(self.fixture.g('rev-parse', '--absolute-git-dir', work=module))
        head = self.fixture.g('rev-parse', 'HEAD', work=module)
        # Hidden submodule dirt must not turn the removal guard off.
        self.fixture.g('config', 'submodule.vendor/lib.ignore', 'all', work=self.work)
        (module / 'precious').write_text('hidden local edits')
        for abandonment in (False, True):
            with self.subTest(abandonment=abandonment), self.assertRaisesRegex(
                    self.helper['CompletionError'], 'populated submodules'):
                self.remove(abandonment=abandonment)
            self.assertEqual(self.calls, [])
            self.assertNotIn('removal_request', self.receipt['storage'])
            self.assertNotIn('tree_removal_digest', self.receipt['storage'])
            self.assertEqual((module / 'precious').read_text(), 'hidden local edits')
            self.assertTrue(module_gitdir.is_dir())
            self.assertEqual(self.fixture.g('rev-parse', 'HEAD', work=module), head)

        shutil.rmtree(self.work)
        self.path.with_name('storage-allocation.json').write_text('retained Rust marker')
        self.receipt['storage']['decision'] = {'registration': {'fixture': True}}
        for finished in (False, True):
            for known_gitdir in (True, False):
                saved_gitdir = self.receipt.pop('worktree_gitdir')
                if known_gitdir:
                    self.receipt['worktree_gitdir'] = saved_gitdir
                self.receipt['storage']['removal_finished'] = finished
                with patch.dict(self.env, managed_registration=lambda *args, **kwargs: {},
                        storage_rpc=lambda *args: self.fail('module repository reached authority')):
                    for remove in (lambda: self.helper['cleanup_workspace'](self.receipt, self.path, warnings=[]),
                                   lambda: self.helper['abandon_managed'](self.receipt, self.path)):
                        with self.subTest(finished=finished, known_gitdir=known_gitdir), self.assertRaisesRegex(
                                self.helper['CompletionError'], 'repositories block removal'):
                            remove()
                        self.assertNotIn('removal_request', self.receipt['storage'])
                        self.assertEqual(self.fixture.g('--git-dir', str(module_gitdir), '--work-tree', str(self.fixture.work), 'rev-parse', 'HEAD'), head)
                        self.assertIn(str(self.work), self.helper['registrations'](self.receipt))
                self.receipt['worktree_gitdir'] = saved_gitdir

    def test_finish_removal_checkpoint_resumes_remaining_tree_under_original_fence(self):
        self.allocate()
        real_delete = self.env['empty_owned_tree']
        def interrupt(fd):
            os.unlink('product', dir_fd=fd)
            raise OSError('interrupted deletion')
        with patch.dict(self.env, empty_owned_tree=interrupt), self.assertRaisesRegex(OSError, 'interrupted'):
            self.remove(abandonment=True)
        fence = dict(self.receipt['storage']['removal_request'])
        self.receipt['storage']['removal_finished'] = True
        self.receipt['storage']['decision'] = {'registration': {'fixture': True}}
        with patch.dict(self.env, managed_registration=lambda *args, **kwargs: {},
                        managed_removal_gate=lambda *args, **kwargs: self.fail('replaced finished fence'),
                        stopped_writers=lambda work: None, scratch_mounts=lambda: [], empty_owned_tree=real_delete):
            result = self.helper['abandon_managed'](self.receipt, self.path)
        self.assertEqual(result['status'], 'ABANDONED')
        self.assertFalse(self.work.exists())
        self.assertEqual(self.receipt['storage']['removal_request'], fence)

    def test_tracked_file_directory_symlinks_and_ignored_bin_links_are_leaves(self):
        repo = self.fixture.work
        (repo / 'file-link').symlink_to('product')
        (repo / 'directory-link').symlink_to('../', target_is_directory=True)
        self.fixture.g('add', '.')
        self.fixture.g('commit', '-m', 'tracked symlinks')
        self.fixture.g('push', 'origin', 'main')
        self.allocate()
        outside = self.fixture.root / 'must-survive'
        outside.write_text('retained')
        links = self.work / 'node_modules/.bin'
        links.mkdir(parents=True)
        (links / 'command').symlink_to(outside)
        self.remove(abandonment=True)
        self.assertEqual(outside.read_text(), 'retained')
        self.assertFalse(self.work.exists())

    def test_crlf_baseline_uses_git_normalization_in_abandonment(self):
        repo = self.fixture.work
        (repo / '.gitattributes').write_text('*.txt text eol=crlf\n')
        (repo / 'windows.txt').write_bytes(b'first\nsecond\n')
        self.fixture.g('add', '.')
        self.fixture.g('commit', '-m', 'crlf baseline')
        self.fixture.g('push', 'origin', 'main')
        self.allocate()
        self.assertEqual((self.work / 'windows.txt').read_bytes(), b'first\r\nsecond\r\n')
        self.remove(abandonment=True)
        self.assertFalse(self.work.exists())

    def test_all_first_pass_vetoes_precede_fence_and_abandonment_flag(self):
        self.allocate()
        with patch.object(shutil.rmtree, 'avoids_symlink_attacks', False), self.assertRaises(self.helper['CompletionError']):
            self.remove(abandonment=True)
        (self.work / 'product').write_text('new source')
        with self.assertRaises(self.helper['CompletionError']):
            self.remove(abandonment=True)
        (self.work / 'product').write_text('baseline\n')
        with patch.dict(self.env, managed_removal_gate=self.gate, stopped_writers=unittest.mock.Mock(side_effect=self.helper['WriterActive']('writer'))), self.assertRaises(self.helper['CompletionError']):
            self.helper['remove_managed_tree'](self.receipt, self.path, abandonment=True)
        self.assertEqual(self.calls, [])
        self.assertNotIn('abandonment', self.receipt['storage'])
        self.assertNotIn('removal_request', self.receipt['storage'])

    def test_50k_ignored_files_never_read_and_receipt_stays_small(self):
        self.allocate()
        target = self.work / 'ignored/target'
        target.mkdir(parents=True)
        for number in range(50000):
            (target / str(number)).touch()
        opened = Path.open
        def checked(path, *args, **kwargs):
            self.assertFalse(path.is_relative_to(target), 'ignored file was opened: ' + str(path))
            return opened(path, *args, **kwargs)
        with patch.object(Path, 'open', checked):
            self.remove()
        self.assertLess(self.path.stat().st_size, 8192)
        self.assertEqual(json.loads(self.path.with_name('tree-removal.json').read_text()), {})
        self.helper['finish_managed_removal'](self.receipt, self.path, {})
        self.assertFalse(self.path.with_name('tree-removal.json').exists())

    def test_revalidation_rejects_replaced_git_pointer_before_deletion(self):
        self.allocate()
        original_gate = self.gate
        def redirected(receipt, path, **kwargs):
            result = original_gate(receipt, path, **kwargs)
            (self.work / '.git').unlink()
            (self.work / '.git').mkdir()
            (self.work / '.git/foreign-data').write_text('must survive')
            return result
        self.gate = redirected
        with self.assertRaisesRegex(self.helper['CompletionError'], 'Git pointer changed'):
            self.remove()
        self.assertEqual((self.work / '.git/foreign-data').read_text(), 'must survive')

    def test_revalidation_keeps_the_pinned_manifest_across_the_gate(self):
        self.allocate()
        original_gate = self.gate
        def changed(receipt, path, **kwargs):
            result = original_gate(receipt, path, **kwargs)
            source = self.work / 'unexpected-source'
            source.write_text('must survive')
            self.helper['atomic_json'](path.with_name('tree-removal.json'), {
                'unexpected-source': self.helper['removal_file_record'](source)})
            return result
        self.gate = changed
        with self.assertRaisesRegex(self.helper['CompletionError'], 'file changed or new source'):
            self.remove()
        self.assertEqual((self.work / 'unexpected-source').read_text(), 'must survive')

    def test_resume_verifies_nonignored_untracked_file_mode_and_symlink_target(self):
        self.allocate()
        leaf = self.work / 'untracked-file'
        leaf.write_bytes(b'recorded bytes')
        leaf.chmod(0o640)
        link = self.work / 'untracked-link'
        link.symlink_to('../outside')
        manifest = {name: self.helper['removal_file_record'](self.work / name)
                    for name in ('untracked-file', 'untracked-link')}
        sidecar = self.path.with_name('tree-removal.json')
        self.helper['atomic_json'](sidecar, manifest)
        self.receipt['storage']['tree_removal_digest'] = hashlib.sha256(sidecar.read_bytes()).hexdigest()
        for change in ('mode', 'target'):
            if change == 'mode':
                leaf.chmod(0o600)
            else:
                link.unlink()
                link.symlink_to('../different-outside')
            with self.subTest(change=change), self.assertRaises(self.helper['CompletionError']):
                self.remove()
            leaf.chmod(0o640)
            link.unlink()
            link.symlink_to('../outside')
        self.assertEqual(self.calls, [])
        self.remove()
        self.assertFalse(self.work.exists())

    def test_ordered_deletion_preserves_ignore_rules_and_git_pointer_until_last(self):
        self.allocate()
        records = self.work / '.devlyn'
        records.mkdir(exist_ok=True)
        (records / '.gitignore').write_text('*\n')
        (records / 'acceptance.json').write_text('{}')
        ignored = self.work / 'ignored'
        ignored.mkdir()
        (ignored / 'cache').write_text('disposable')
        unlink = os.unlink
        def checked(name, *args, **kwargs):
            if name == '.gitignore':
                names = os.listdir(kwargs['dir_fd'])
                self.assertTrue(set(names) <= {'.gitignore', '.git'}, names)
            if name == '.git':
                self.assertEqual(os.listdir(kwargs['dir_fd']), ['.git'])
            return unlink(name, *args, **kwargs)
        with patch.object(os, 'unlink', checked):
            self.remove()
        self.assertFalse(self.work.exists())


if __name__ == "__main__":
    if sys.argv[1:] == ["--golden-vectors"]:
        try:
            load_cross_language_golden_vectors()
        except REFUSAL as exc:
            print(json.dumps(exc.result()), file=sys.stderr)
            sys.exit(1)
        unittest.main(argv=[sys.argv[0], "SharedVectorTests"], verbosity=2)
    else:
        unittest.main(verbosity=2)
