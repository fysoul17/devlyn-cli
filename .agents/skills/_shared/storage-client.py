#!/usr/bin/env python3
"""Authenticated storage protocol 1. No registry access or allocation side effects.

Source of record: devlyn-os/storage-reservations/crates/devlynd/src/:
 storage/rpc.rs:21-119 (wire), 798-835 (busy), 870-933 (authentication/errors);
 storage/model.rs:9-350 (all records and decimal fields);
 control_service/protocol.rs:71-74 (limits), unix.rs:19-27 (endpoint);
 control_service/windows.rs:91-106 (pipe digest);
 tool_channel/peer.rs:188-249 (peer credentials);
 supervisor.rs:253-271,3753-3886,3933-3957 (process identities);
 util/windows.rs:65-112,308-326,876-901,977-1000 (SID/canonical path).

Connections carry one request. Hello is negotiated on a separate authenticated
connection; the operation connection must have that same server incarnation.
No transport error authorizes downgrade, a new operation ID, or an automatic
retry. Only an explicit busy reply permits bounded replay of identical bytes.
"""
from __future__ import annotations

import contextlib
import ctypes
import errno
import hashlib
import json
import math
import os
from pathlib import Path
import re
import runpy
import shlex
import selectors
import socket
import stat
import struct
import subprocess
import sys
import tempfile
import threading
import time
import uuid

MAX_REQUEST = 128 * 1024
MAX_REPLY = 4 * 1024 * 1024
EXCHANGE_SECONDS = 15.0
BUSY_SECONDS = 2.0
MANAGED_PENDING = "managed_pending"
MANAGED_OWNED = "managed_owned"
MANAGED_STATES = frozenset({MANAGED_PENDING, MANAGED_OWNED})

# Quoted sentences are exactly plan §4. Rows without a quoted sentence use
# conservative receipt-based reconciliation instructions, never raw diagnostics.
REFUSAL_TEXT = {
    "storage_insufficient": "Not enough disk space to complete this operation safely. Free up space and retry.",
    "allocation_size_unknown": "Devlyn can't check the space needed to create a separate workspace. You can work in an existing project folder instead.",
    "storage_io": "Couldn't verify available disk space. Retry the operation.",
    "storage_unavailable": "Devlyn storage is unavailable. Open Devlyn and retry using this receipt.",
    "storage_unsupported": "Update Devlyn and devlyn-cli, then resume using this receipt.",
    "storage_exhausted": "Finish outstanding work, then retry using this receipt. If this continues, repair Devlyn.",
    "storage_expired": "This attempt needs reconciliation; retain the workspace and resume from its receipt.",
    "storage_busy": "Devlyn storage is busy. Retry using this receipt.",
    "storage_in_use": "This cache is still in use. Stop the processes using this cache. Then resume cleanup.",
    "storage_protected": "Ownership or identity changed. Retain the workspace and inspect using this receipt.",
    "storage_missing": "Ownership or identity changed. Retain the workspace and inspect using this receipt.",
    "storage_conflict": "Ownership or identity changed. Retain the workspace and inspect using this receipt.",
    "storage_invalid": "The storage request needs repair. Retain the workspace and inspect using this receipt.",
    "storage_not_found": "This attempt needs reconciliation; retain the workspace and resume from its receipt.",
}


class StorageRefusal(Exception):
    """Safe prose in str(); untrusted details only in diagnostic."""

    def __init__(self, code, diagnostic="", *, operation=None, phase=None, message=None, resume=None):
        self.code = "storage_busy" if code == "busy" else code
        if self.code not in REFUSAL_TEXT:
            diagnostic = f"unknown refusal {self.code!r}: {diagnostic}"
            self.code = "storage_unavailable"
        self.diagnostic = diagnostic
        self.operation = operation
        self.phase = phase
        self.resume = resume
        self.retryable = self.code == "storage_busy"
        super().__init__(message or REFUSAL_TEXT[self.code])

    def result(self, *, receipt=None, resume=None):
        # Callers construct resume from their saved receipt and verified helper;
        # no path, shell command or instruction from the server is interpolated.
        return {"code": self.code, "message": str(self), "diagnostic": self.diagnostic,
                "operation": self.operation, "phase": self.phase,
                "retryable": self.retryable, "receipt": receipt, "resume": resume or self.resume}


def require(condition, diagnostic, code="storage_unavailable"):
    if not condition:
        raise StorageRefusal(code, diagnostic)


def _pairs(pairs):
    value = {}
    for key, item in pairs:
        require(key not in value, f"duplicate JSON key {key!r}")
        value[key] = item
    return value


def _constant(value):
    raise StorageRefusal("storage_unavailable", f"nonfinite JSON constant {value}")


def loads(data):
    try:
        value = json.loads(data.decode("utf-8", "strict"), object_pairs_hook=_pairs,
                           parse_constant=_constant)
        _json_values(value)
        return value
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise StorageRefusal("storage_unavailable", f"invalid JSON: {exc}") from exc


def _json_values(value):
    if isinstance(value, str):
        value.encode("utf-8", "strict")  # Reject escaped unpaired surrogates too.
    elif isinstance(value, float):
        require(math.isfinite(value), "overflowing JSON float")
    elif isinstance(value, dict):
        for key, item in value.items():
            require(isinstance(key, str), "JSON key must be text")
            _json_values(key)
            _json_values(item)
    elif isinstance(value, list):
        for item in value:
            _json_values(item)


# Declarative required shapes are deliberately separate from policy. Replies
# allow additive fields; requests reject misspelled/unknown fields before I/O.
# '?' marks serde Option/default fields. Decimal is ONLY used at Rust #[with].
SHAPES = {
    "identity": {"volume": "str", "file": "str"},
    "stamp": {"pid": "i64", "start": "str"},
    "owner": {"repository": "identity", "allocation_id": "str", "receipt": "str"},
    "creator": {"product": "str", "protocol_version": "u32", "operation_id": "str"},
    "declaration": {"creator": "creator", "owner": "owner", "parent": "str", "entry": "str"},
    "location": {"parent": "str", "parent_identity": "identity", "entry": "str",
                 "directory_identity?": "identity?", "volume_id": "str", "pool_id?": "str?"},
    "cache": {"schema_version": "u32", "cache_id": "str", "kind": ("cargo_build_cache",),
              "disposable": "bool", "creator": "creator", "owner": "owner", "location": "location",
              "created_at": "str", "last_release_at?": "str?", "coverage": ("unproven", "managed"),
              "state": ("preparing", "active", "retired", "removing", "evicting", "partial", "deleted", "protected"),
              "reason?": "str?", "protection?": (None, "missing", "io"), "supervisor": "stamp",
              "removal_generation?": "u64", "removal_id?": "str?", "retire_intent": "bool",
              "retirement_authorized_by?": "stamp?"},
    "lease": {"lease_id": "str", "cache_id": "str", "operation_id": "str", "supervisor": "stamp",
              "consumers": ["consumer"], "acquired_at": "str", "leaf?": "bool",
              "descendants_reconciled": "bool", "released_at?": "str?"},
    "snapshot": {"cache": "cache", "leases": ["lease"]},
    "removal_entry": {"cache_id": "str", "generation": "u64"},
    "removal": {"removal_id": "str", "operation_id": "str", "supervisor": "stamp",
                "entries": ["removal_entry"], "finished_at?": "str?"},
    "write": {"parent": "str", "relative": "str", "phase": "str", "bytes": "decimal"},
    "charge": {"id": "str", "bytes": "decimal"},
    "destination": {"parent_identity": "identity", "existing_ancestors": ["identity"],
                    "volume_id": "str", "pool_id": "str"},
    "worker": {"operation_id": "str", "consumer": "consumer", "containment": "containment",
               "descendants_reconciled": "bool"},
    "reservation": {"reservation_id": "str", "operation_id": "str", "generation": "decimal",
                    "boot_id?": "str?", "owner": "owner", "holder": "stamp", "plan": "plan",
                    "destinations": ["destination"], "pools": ["charge"], "volumes": ["charge"],
                    "workers": ["worker"], "granted_at": "str", "released_at?": "str?"},
    "hello": {"storage_protocol": "u32", "capabilities": ["str"], "schema": "u32"},
    "containment": ("unix_group", "unix_checkout", "windows_job", "supervised"),
}
REQUESTS = {
    "hello": ({}, "hello"),
    "reserve": ({"operation_id": "str", "owner": "owner", "plan": "plan"}, "reservation"),
    "enroll_reservation_worker": ({"operation_id": "str", "reservation_id": "str", "generation": "decimal",
                                   "consumer": "consumer", "containment": "containment"}, "reservation"),
    "release_reservation": ({"reservation_id": "str", "generation": "decimal", "descendants_reconciled": "bool"}, "reservation"),
    "record_reservation_completion": ({"reservation_id": "str", "generation": "decimal"}, "reservation"),
    "query_reservation": ({"operation_id": "str"}, "reservation"),
    "locate": ({"parent": "str", "entry": "str"}, "cache"),
    "begin_removal": ({"operation_id": "str", "cache_ids": ["str"]}, "removal"),
    "finish_removal": ({"removal_id": "str"}, "removal"),
    "declare": ({"declaration": "declaration"}, "cache"),
    "bind": ({"cache_id": "str", "consumers": ["consumer"]}, "published"),
    "bind_publication": ({"cache_id": "str"}, "published"),
    "lease": ({"cache_id": "str", "operation_id": "str", "consumers": ["consumer"], "leaf?": "bool"}, "published"),
    "release": ({"lease_id": "str", "descendants_reconciled": "bool"}, "released"),
    "retire_intent": ({"cache_id": "str"}, "cache"),
    "query": ({"cache_id": "str"}, "snapshot"),
}
SHAPES["published"] = {"cache": "cache", "lease": "lease"}
SHAPES["released"] = SHAPES["lease"]
SHAPES["parent_evidence"] = {"identity": "identity", "mount": "str"}
SHAPES["declaration"]["parent_evidence?"] = "parent_evidence?"
SHAPES["location"]["parent_evidence?"] = "parent_evidence?"
SHAPES["warning"] = {"code": ("exclusion_failed", "cargo_ineligible", "cargo_unverifiable", "no_cargo_manifest"),
                     "diagnostic": "str"}
SHAPES["cache"]["warnings?"] = ["warning"]
SHAPES["outcome"] = {"attempt": "str", "resolves?": "str?", "project": "str", "taskId": "str",
                     "code?": (None, "storage_insufficient", "allocation_size_unknown", "storage_io",
                               "storage_unavailable", "storage_unsupported", "storage_exhausted", "storage_protected"),
                     "retryable": "bool"}
SHAPES["storage_refused"] = {"generation": "i64", "revision": "str", "outcome": "outcome"}
SHAPES["allocation_outcome"] = "storage_refused?"
REQUESTS.update({"allocation_outcome": ({}, "allocation_outcome"),
                 "report_allocation_outcome": ({"outcome": "outcome"}, "reported")})


def validate(value, shape, *, exact=False, windows=None):
    if windows is None:
        windows = os.name == "nt"
    if isinstance(shape, dict):
        require(type(value) is dict, "expected JSON object")
        for key, child in shape.items():
            name = key.removesuffix("?")
            if name not in value and key.endswith("?"):
                continue
            require(name in value, f"missing field {name}")
            validate(value[name], child, exact=exact, windows=windows)
        if exact:
            require(not value.keys() - {k.removesuffix('?') for k in shape}, "unknown request field")
    elif isinstance(shape, list):
        require(type(value) is list, "expected JSON array")
        for item in value:
            validate(item, shape[0], exact=exact, windows=windows)
    elif isinstance(shape, tuple):
        require(value in shape and (value is None or type(value) is str), "invalid enum")
    elif shape.endswith("?"):
        if value is not None:
            validate(value, shape[:-1], exact=exact, windows=windows)
    elif shape == "str":
        require(type(value) is str, "expected string")
    elif shape == "bool":
        require(type(value) is bool, "expected boolean")
    elif shape in {"u32", "u64", "i64"}:
        lo, hi = {"u32": (0, 2**32-1), "u64": (0, 2**64-1), "i64": (-2**63, 2**63-1)}[shape]
        require(type(value) is int and lo <= value <= hi, f"expected {shape} integer")
    elif shape == "decimal":
        require(type(value) is str and re.fullmatch(r"0|[1-9][0-9]{0,19}", value) is not None
                and int(value) <= 2**64-1, "expected canonical decimal u64 string")
    elif shape == "consumer":
        fields = {"pid": "i64", "created": "u64"} if windows else {"pid": "i64", "pgid": "i64", "start?": "str?"}
        validate(value, fields, exact=exact, windows=windows)
    elif shape == "plan":
        require(type(value) is dict, "expected write plan")
        if value.get("kind") == "known":
            fields = {"kind": ("known",), "writes": ["write"], "digest": "str"}
        else:
            fields = {"kind": ("unknown",), "reason": ("external_filter", "lfs_extension", "encoding", "attributes",
                      "lfs_transfer", "missing_object", "plan_changed", "unsupported_git", "overflow")}
        validate(value, fields, exact=exact, windows=windows)
    else:
        validate(value, SHAPES[shape], exact=exact, windows=windows)


def encode_request(request):
    try:
        require(type(request) is dict and request.get("op") in REQUESTS, "unsupported request operation", "storage_invalid")
        fields, _ = REQUESTS[request["op"]]
        validate(request, {"op": (request["op"],), **fields}, exact=True)
        _json_values(request)
        data = json.dumps({"storage_protocol": 1, "request": request}, ensure_ascii=False,
                          allow_nan=False, separators=(",", ":")).encode("utf-8")
        require(len(data) <= MAX_REQUEST, "request exceeds 128 KiB", "storage_invalid")
        return data + b"\n"
    except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
        raise StorageRefusal("storage_invalid", str(exc)) from exc


def decode_reply(frame, expected):
    require(frame.endswith(b"\n") and b"\n" not in frame[:-1], "truncated or multiple reply frames")
    require(len(frame) <= MAX_REPLY, "reply exceeds 4 MiB including LF")
    response = loads(frame[:-1])
    require(type(response) is dict and ("ok" in response) != ("error" in response), "invalid response envelope")
    if "error" in response:
        validate(response["error"], {"code": "str", "message": "str"})
        raise StorageRefusal(response["error"]["code"], response["error"]["message"])
    reply = response["ok"]
    require(type(reply) is dict and reply.get("kind") == expected, "unexpected reply kind")
    if expected == "reported":
        return None
    require("value" in reply, "missing reply value")
    validate(reply["value"], expected)
    return reply["value"]


def remaining(deadline):
    left = deadline - time.monotonic()
    require(left > 0, "storage exchange deadline exceeded")
    return left


def unix_start(pid):
    require(type(pid) is int and 0 < pid < 2**31, "invalid peer pid")
    if sys.platform.startswith("linux"):
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(") ", 1)[1].split()
        require(fields[0] not in {"Z", "X"}, "peer exited")
        ticks = int(fields[19])
        boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
        require(re.fullmatch(r"[0-9a-f-]{36}", boot) is not None and ticks >= 0, "invalid Linux process identity")
        return f"linux:{boot}:{ticks}"
    require(sys.platform == "darwin" and struct.calcsize("P") == 8, "unsupported process identity", "storage_unsupported")
    # Same size/offsets as supervisor.rs:3810-3886; no ps/libproc approximation.
    libc = ctypes.CDLL(None, use_errno=True)
    libc.sysctl.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.c_uint, ctypes.c_void_p,
                           ctypes.POINTER(ctypes.c_size_t), ctypes.c_void_p, ctypes.c_size_t]
    libc.sysctl.restype = ctypes.c_int
    mib = (ctypes.c_int * 4)(1, 14, 1, pid)
    record = ctypes.create_string_buffer(648)
    size = ctypes.c_size_t(648)
    require(libc.sysctl(mib, 4, record, ctypes.byref(size), None, 0) == 0,
            f"sysctl failed: errno {ctypes.get_errno()}")
    require(size.value == 648, f"unexpected kinfo_proc size {size.value}")
    raw = record.raw
    seconds, micros = struct.unpack_from("=qi", raw)
    require(struct.unpack_from("=i", raw, 40)[0] == pid and raw[36] != 5
            and seconds >= 0 and 0 <= micros < 1_000_000, "invalid macOS process identity")
    return f"macos:{seconds}:{micros}"


def unix_peer(stream):
    if sys.platform.startswith("linux"):
        raw = stream.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("=iII"))
        pid, uid, _ = struct.unpack("=iII", raw)
    else:
        require(sys.platform == "darwin", "unsupported peer credentials", "storage_unsupported")
        libc = ctypes.CDLL(None, use_errno=True)
        libc.getpeereid.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_uint), ctypes.POINTER(ctypes.c_uint)]
        libc.getpeereid.restype = ctypes.c_int
        uid_out, gid_out = ctypes.c_uint(), ctypes.c_uint()
        require(libc.getpeereid(stream.fileno(), ctypes.byref(uid_out), ctypes.byref(gid_out)) == 0,
                f"getpeereid failed: errno {ctypes.get_errno()}")
        uid = uid_out.value
        pid = struct.unpack("=i", stream.getsockopt(0, 2, 4))[0]  # SOL_LOCAL / LOCAL_PEERPID
    require(uid == os.geteuid(), f"foreign endpoint uid {uid}")
    return pid, uid, unix_start(pid)


class UnixStream:
    def __init__(self, directory, deadline):
        self.stream = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            directory = Path(directory).resolve(strict=True)
            self.directory = directory
            self.directory_stat = directory.lstat()
            require(stat.S_ISDIR(self.directory_stat.st_mode) and self.directory_stat.st_uid == os.geteuid()
                    and self.directory_stat.st_mode & 0o077 == 0, "control directory is not private")
            self.path = directory / "control.sock"
            self.socket_stat = self.path.lstat()
            require(stat.S_ISSOCK(self.socket_stat.st_mode) and self.socket_stat.st_uid == os.geteuid(), "invalid control socket")
            self.stream.setblocking(False)
            while True:
                remaining(deadline)
                result = self.stream.connect_ex(str(self.path))
                if result in (0, errno.EISCONN):
                    break
                if result == errno.EAGAIN:  # Linux's full Unix backlog: retry connect itself.
                    time.sleep(min(0.02, remaining(deadline)))
                    continue
                if result in (errno.EINPROGRESS, errno.EALREADY, errno.EINTR):
                    with selectors.DefaultSelector() as selector:
                        selector.register(self.stream, selectors.EVENT_WRITE)
                        require(selector.select(remaining(deadline)), "connect deadline exceeded")
                    result = self.stream.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
                    if result == 0:
                        break
                raise OSError(result, os.strerror(result))
            self.identity = self.authenticate()
        except BaseException:
            self.close()
            raise

    def authenticate(self):
        directory, endpoint = self.directory.lstat(), self.path.lstat()
        require((directory.st_dev, directory.st_ino) == (self.directory_stat.st_dev, self.directory_stat.st_ino)
                and directory.st_uid == os.geteuid() and directory.st_mode & 0o077 == 0
                and (endpoint.st_dev, endpoint.st_ino) == (self.socket_stat.st_dev, self.socket_stat.st_ino)
                and stat.S_ISSOCK(endpoint.st_mode), "control endpoint changed")
        first = unix_peer(self.stream)
        require(first == unix_peer(self.stream), "server incarnation changed during authentication")
        return first

    def exchange(self, data, deadline):
        require(self.authenticate() == self.identity, "server incarnation changed before first byte")
        sent, reply = 0, bytearray()
        write_error = None
        with selectors.DefaultSelector() as selector:
            selector.register(self.stream, selectors.EVENT_READ | selectors.EVENT_WRITE)
            while True:
                events = selector.select(remaining(deadline))
                require(events, "exchange deadline exceeded")
                mask = 0
                for _, ready in events:  # kqueue may emit read/write separately.
                    mask |= ready
                # Read first: an early busy reply survives a concurrent EPIPE.
                if mask & selectors.EVENT_READ:
                    try:
                        chunk = self.stream.recv(min(65536, MAX_REPLY + 2 - len(reply)))
                    except BlockingIOError:
                        chunk = None
                    if chunk is not None:
                        require(chunk, f"reply truncated; write error={write_error}")
                        reply.extend(chunk)
                        require(len(reply) <= MAX_REPLY, "oversized reply")
                        if b"\n" in reply:
                            return bytes(reply)
                if mask & selectors.EVENT_WRITE and sent < len(data) and write_error is None:
                    try:
                        count = self.stream.send(data[sent:])
                        require(count > 0, "zero-byte write")
                        sent += count
                    except BlockingIOError:
                        continue
                    except OSError as exc:
                        write_error = exc
                    if sent == len(data) or write_error is not None:
                        selector.modify(self.stream, selectors.EVENT_READ)

    def close(self):
        self.stream.close()


def pipe_name(sid, canonical_directory):
    digest = hashlib.sha256((sid + "\0" + canonical_directory).encode("utf-8")).hexdigest()[:32]
    return "\\\\.\\pipe\\devlyn-control-" + digest


def rust_windows_path(path):
    """Rust util/windows.rs:876-901 strips ONLY safe verbatim disk prefixes."""
    if re.match(r"^\\\\\?\\[A-Za-z]:\\", path):
        names = path[7:].split("\\")
        reserved = re.compile(r"^(CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])(?:\.|$)", re.I | re.ASCII)
        if all(not reserved.match(name) and not name.endswith((".", " "))
               and not any(c in '<>:"|?*' or ord(c) < 32 or 127 <= ord(c) <= 159 for c in name)
               for name in names if name):
            return path[4:]
    return path


class Overlapped(ctypes.Structure):
    _fields_ = [("Internal", ctypes.c_size_t), ("InternalHigh", ctypes.c_size_t),
                ("Offset", ctypes.c_uint32), ("OffsetHigh", ctypes.c_uint32), ("hEvent", ctypes.c_void_p)]


class WindowsAPI:
    """Typed Win32 boundary; constructed only on native Windows."""

    def __init__(self):
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.advapi = ctypes.WinDLL("advapi32", use_last_error=True)
        self.cleanup_diagnostics = []
        H, D, B, P, W = ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int32, ctypes.c_void_p, ctypes.c_wchar_p
        self._bind(self.kernel, "CreateFileW", H, [W, D, D, P, D, D, H])
        self._bind(self.kernel, "CloseHandle", B, [H])
        self._bind(self.kernel, "DuplicateHandle", B, [H, H, H, ctypes.POINTER(H), D, B, D])
        self._bind(self.kernel, "GetCurrentProcess", H, [])
        self._bind(self.kernel, "OpenProcess", H, [D, B, D])
        self._bind(self.kernel, "GetProcessTimes", B, [H, P, P, P, P])
        self._bind(self.kernel, "GetNamedPipeServerProcessId", B, [H, ctypes.POINTER(D)])
        self._bind(self.kernel, "GetFinalPathNameByHandleW", D, [H, W, D, D])
        self._bind(self.kernel, "GetFileInformationByHandleEx", B, [H, ctypes.c_int, P, D])
        self._bind(self.kernel, "LocalFree", H, [H])
        self._bind(self.kernel, "WaitNamedPipeW", B, [W, D])
        self._bind(self.kernel, "CreateEventW", H, [P, B, B, W])
        self._bind(self.kernel, "WaitForSingleObject", D, [H, D])
        self._bind(self.kernel, "ReadFile", B, [H, P, D, ctypes.POINTER(D), ctypes.POINTER(Overlapped)])
        self._bind(self.kernel, "WriteFile", B, [H, P, D, ctypes.POINTER(D), ctypes.POINTER(Overlapped)])
        self._bind(self.kernel, "GetOverlappedResult", B, [H, ctypes.POINTER(Overlapped), ctypes.POINTER(D), B])
        self._bind(self.kernel, "CancelIoEx", B, [H, ctypes.POINTER(Overlapped)])
        self._bind(self.advapi, "OpenProcessToken", B, [H, D, ctypes.POINTER(H)])
        self._bind(self.advapi, "GetTokenInformation", B, [H, ctypes.c_int, P, D, ctypes.POINTER(D)])
        self._bind(self.advapi, "ConvertSidToStringSidW", B, [P, ctypes.POINTER(H)])

    @staticmethod
    def _bind(library, name, result, args):
        function = getattr(library, name)
        function.restype, function.argtypes = result, args

    @staticmethod
    def check(value):
        if not value:
            raise ctypes.WinError(ctypes.get_last_error())
        return value

    def close(self, handle):
        self.check(self.kernel.CloseHandle(handle))

    def sid(self, process=None):
        token = ctypes.c_void_p()
        self.check(self.advapi.OpenProcessToken(process or self.kernel.GetCurrentProcess(), 8, ctypes.byref(token)))
        try:
            size = ctypes.c_uint32()
            self.advapi.GetTokenInformation(token, 1, None, 0, ctypes.byref(size))
            require(0 < size.value <= 65536, "invalid token information size")
            buffer = (ctypes.c_uint64 * ((size.value + 7)//8))()
            self.check(self.advapi.GetTokenInformation(token, 1, buffer, size, ctypes.byref(size)))
            sid_pointer = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_void_p))[0]
            text = ctypes.c_void_p()
            self.check(self.advapi.ConvertSidToStringSidW(sid_pointer, ctypes.byref(text)))
            try:
                return ctypes.wstring_at(text)
            finally:
                self.kernel.LocalFree(text)
        finally:
            self.close(token)

    def directory(self, path):
        handle = self.kernel.CreateFileW(str(path), 0, 7, None, 3, 0x02000000, None)
        require(handle not in (None, ctypes.c_void_p(-1).value), "cannot open control directory")
        try:
            buffer = ctypes.create_unicode_buffer(32768)
            count = self.check(self.kernel.GetFinalPathNameByHandleW(handle, buffer, len(buffer), 0))
            require(count < len(buffer), "canonical directory path exceeds buffer")
            # FileIdInfo: volume serial + 128-bit file ID. Never coerce ID to float.
            identity = ctypes.create_string_buffer(24)
            self.check(self.kernel.GetFileInformationByHandleEx(handle, 18, identity, 24))
            volume = struct.unpack_from("=Q", identity.raw)[0]
            file_id = identity.raw[8:24].hex()
            return rust_windows_path(buffer.value), (str(volume), file_id)
        finally:
            self.close(handle)

    def server(self, pipe):
        pid = ctypes.c_uint32()
        self.check(self.kernel.GetNamedPipeServerProcessId(pipe, ctypes.byref(pid)))
        process = self.check(self.kernel.OpenProcess(0x1000 | 0x100000, False, pid))
        try:
            times = [ctypes.c_uint64() for _ in range(4)]
            self.check(self.kernel.GetProcessTimes(process, *(ctypes.byref(t) for t in times)))
            require(self.kernel.WaitForSingleObject(process, 0) == 258, "server process exited")
            return pid.value, self.sid(process), f"windows:{times[0].value}"
        finally:
            self.close(process)

    def open_pipe(self, name, deadline):
        while True:
            remaining(deadline)
            # FILE_FLAG_OVERLAPPED | SECURITY_SQOS_PRESENT | SECURITY_ANONYMOUS
            handle = self.kernel.CreateFileW(name, 0xC0000000, 0, None, 3, 0x40000000 | 0x00100000, None)
            if handle not in (None, ctypes.c_void_p(-1).value):
                return handle
            error = ctypes.get_last_error()
            if error != 231:  # ERROR_PIPE_BUSY only; absent/access-denied never downgrades.
                raise ctypes.WinError(error)
            wait = max(1, min(50, int(remaining(deadline)*1000)))
            if not self.kernel.WaitNamedPipeW(name, wait) and ctypes.get_last_error() not in (121, 231):
                raise ctypes.WinError(ctypes.get_last_error())

    def start_io(self, handle, data=None):
        event = self.check(self.kernel.CreateEventW(None, True, False, None))
        overlap = Overlapped(hEvent=event)
        buffer = ctypes.create_string_buffer(data, len(data)) if data is not None else ctypes.create_string_buffer(65536)
        operation = [overlap, buffer, event, False]
        function = self.kernel.WriteFile if data is not None else self.kernel.ReadFile
        if not function(handle, buffer, len(buffer), None, ctypes.byref(overlap)):
            error = ctypes.get_last_error()
            if error != 997:  # ERROR_IO_PENDING
                self.close(event)
                raise ctypes.WinError(error)
        return operation

    def poll_io(self, handle, operation):
        count = ctypes.c_uint32()
        if not self.kernel.GetOverlappedResult(handle, ctypes.byref(operation[0]), ctypes.byref(count), False):
            error = ctypes.get_last_error()
            if error == 996:  # ERROR_IO_INCOMPLETE
                return None
            if error in (995, 109, 232, 234):
                operation[3] = True
            raise ctypes.WinError(error)
        operation[3] = True
        return count.value, operation[1].raw[:count.value]

    def _cancel_completed(self, handle, operation, wait):
        count = ctypes.c_uint32()
        success = self.kernel.GetOverlappedResult(handle, ctypes.byref(operation[0]), ctypes.byref(count), wait)
        if success or ctypes.get_last_error() in (995, 109, 232):
            operation[3] = True
        return operation[3]

    def _drain_cancelled(self, handle, operation, close_handle=True):
        # Unexpected errors are not positive completion. Keep all native state
        # alive and retry; never free a buffer the kernel may still reference.
        while not operation[3]:
            try:
                if not self._cancel_completed(handle, operation, True):
                    time.sleep(0.01)
            except OSError as exc:
                self.cleanup_diagnostics.append(str(exc))
                time.sleep(0.01)
        try:
            self.close(operation[2])
        finally:
            if close_handle:
                self.close(handle)

    def _retain_cancelled(self, handle, operation):
        duplicate = ctypes.c_void_p()
        try:
            process = self.kernel.GetCurrentProcess()
            self.check(self.kernel.DuplicateHandle(process, handle, process, ctypes.byref(duplicate), 0, False, 2))
        except BaseException:
            # No duplicate exists to own a background wait. The caller must
            # retain the original handle and synchronously await completion.
            self._drain_cancelled(handle, operation, False)
            raise
        cleanup = None
        try:
            lock = threading.Lock()
            reclaimed = False
            def cleanup():
                nonlocal reclaimed
                # start() may launch a worker and then be interrupted. Both
                # paths share one owner of the event and duplicated handle.
                with lock:
                    if not reclaimed:
                        try:
                            self._drain_cancelled(duplicate, operation)
                        finally:
                            reclaimed = operation[3]
            worker = threading.Thread(target=cleanup, daemon=True)
            worker.start()
        except BaseException:
            if cleanup is None:
                self._drain_cancelled(duplicate, operation)
            else:
                cleanup()
            raise
        self.cleanup_diagnostics.append('cancellation completion pending; native I/O resources retained until completion')

    def finish_io(self, handle, operation, deadline):
        try:
            if not operation[3]:
                if not self.kernel.CancelIoEx(handle, ctypes.byref(operation[0])):
                    require(ctypes.get_last_error() == 1168, 'CancelIoEx failed')
                wait_ms = max(0, int((deadline-time.monotonic())*1000))
                result = self.kernel.WaitForSingleObject(operation[2], wait_ms)
                require(result in (0, 258), 'cancellation wait failed')
                if result == 0:
                    self._cancel_completed(handle, operation, False)
        finally:
            if operation[3]:
                self.close(operation[2])
            else:
                self._retain_cancelled(handle, operation)


class WindowsStream:
    def __init__(self, directory, deadline, *, api=None):
        self.api = api or WindowsAPI()
        self.directory, self.directory_identity = self.api.directory(directory)
        self.sid = self.api.sid()
        self.handle = self.api.open_pipe(pipe_name(self.sid, self.directory), deadline)
        try:
            self.identity = self.authenticate()
        except BaseException:
            self.close()
            raise

    def authenticate(self):
        require(self.api.directory(self.directory) == (self.directory, self.directory_identity), "control directory changed")
        first = self.api.server(self.handle)
        require(first[1] == self.sid and first == self.api.server(self.handle), "foreign or reused pipe server")
        return first

    def exchange(self, data, deadline):
        require(self.authenticate() == self.identity, "pipe server changed before first byte")
        reply, sent, write_error = bytearray(), 0, None
        with contextlib.ExitStack() as pending:
            read = self.api.start_io(self.handle)
            read_cleanup = pending.enter_context(contextlib.ExitStack())
            read_cleanup.callback(self.api.finish_io, self.handle, read, deadline)
            write_cleanup = pending.enter_context(contextlib.ExitStack())
            write = None
            while True:
                remaining(deadline)
                try:
                    result = self.api.poll_io(self.handle, read)
                except OSError as exc:
                    raise StorageRefusal("storage_unavailable", f"pipe reply failed: {exc}; write={write_error}") from exc
                if result is not None:
                    count, chunk = result
                    require(count, "pipe reply truncated")
                    reply.extend(chunk)
                    require(len(reply) <= MAX_REPLY, "oversized reply")
                    if b"\n" in reply:
                        return bytes(reply)
                    read_cleanup.close()
                    read = self.api.start_io(self.handle)
                    read_cleanup.callback(self.api.finish_io, self.handle, read, deadline)
                if sent < len(data) and write_error is None:
                    try:
                        if write is None:
                            write = self.api.start_io(self.handle, data[sent:])
                            write_cleanup.callback(self.api.finish_io, self.handle, write, deadline)
                        result = self.api.poll_io(self.handle, write)
                        if result is not None:
                            require(result[0] > 0, "pipe zero-byte write")
                            sent += result[0]
                            write_cleanup.close()
                            write = None
                    except OSError as exc:
                        write_error = exc  # Continue reading an early busy reply.
                time.sleep(min(0.005, remaining(deadline)))

    def close(self):
        self.api.close(self.handle)


def connect(directory, deadline):
    return WindowsStream(directory, deadline) if os.name == "nt" else UnixStream(directory, deadline)


class Client:
    def __init__(self, control_directory, *, required_capabilities=("reserve",)):
        self.directory = control_directory
        self.required = frozenset(required_capabilities)

    def _exchange(self, data, expected, deadline, server=None):
        with contextlib.closing(connect(self.directory, deadline)) as stream:
            require(server is None or stream.identity == server, "server changed after hello")
            value = decode_reply(stream.exchange(data, deadline), expected)
            return value, stream.identity

    def call(self, request):
        data = encode_request(request)  # Freeze validated bytes before retry.
        expected = REQUESTS[request["op"]][1]
        busy_deadline, backoff = time.monotonic()+BUSY_SECONDS, 0.01
        try:
            while True:
                try:
                    # A new server incarnation always gets fresh hello. Never
                    # send an operation to a successor without renegotiation.
                    hello, server = self._exchange(encode_request({"op": "hello"}), "hello", time.monotonic()+EXCHANGE_SECONDS)
                    required = self.required | ({"leaf_leases"} if request.get("leaf") is True else set())
                    require(hello["storage_protocol"] == 1 and required <= set(hello["capabilities"]),
                            "incompatible protocol or missing capabilities", "storage_unsupported")
                    if request["op"] == "hello":
                        return hello
                    return self._exchange(data, expected, time.monotonic()+EXCHANGE_SECONDS, server)[0]
                except StorageRefusal as exc:
                    if exc.code != "storage_busy" or time.monotonic() >= busy_deadline:
                        raise
                    time.sleep(max(0.0, min(backoff, busy_deadline-time.monotonic())))
                    backoff = min(backoff*2, 0.2)
                    require(time.monotonic() < busy_deadline, "busy retry window exhausted", "storage_busy")
        except (OSError, ValueError, IndexError, struct.error) as exc:
            raise StorageRefusal("storage_unavailable", str(exc), operation=request["op"], phase="exchange") from exc
        except StorageRefusal as exc:
            exc.operation, exc.phase = request["op"], "exchange"
            raise


def _evidence(path):
    """Only ENOENT is absence; reject redirected evidence below the canonical root."""
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None
    require(not stat.S_ISLNK(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400,
            f"redirected enrollment evidence: {path}")
    return info


def _same_file(left, right, handles=False):
    def identity(info):
        if os.name == 'nt' and not handles:
            # Windows path stat synthesizes executable bits from the extension, and its
            # st_ctime is the creation time while handle stat reports the change time
            # (CPython 3.12, Windows Server 2025). Neither compares across the two;
            # two stats of one handle (`handles`) compare every field.
            return (info.st_dev, info.st_ino, stat.S_IFMT(info.st_mode), info.st_size, info.st_mtime_ns)
        return (info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
    return right is not None and identity(left) == identity(right)


def managed_receipt(receipt):
    """Rust obligations::Discriminators, including future managed custody states."""
    require(type(receipt) is dict, "invalid saved receipt")
    for name in ("mode", "allocation", "allocation_state"):
        require(receipt.get(name) is None or type(receipt[name]) is str, "invalid receipt discriminator")
    return receipt.get("mode") == "managed" or any(
        (receipt.get(name) or "").startswith("managed") for name in ("allocation", "allocation_state"))


def operation_id():
    # RFC 9562 UUIDv7, also on Python versions without uuid.uuid7.
    bits = (int(time.time()*1000) << 80) | (int.from_bytes(os.urandom(10), "big") & ((1 << 80)-1))
    return str(uuid.UUID(int=(bits & ~(15 << 76) & ~(3 << 62)) | (7 << 76) | (2 << 62)))


def canonical_operation(value, *, now=None):
    try:
        parsed = uuid.UUID(value)
    except (ValueError, TypeError, AttributeError) as exc:
        raise StorageRefusal("storage_invalid", "operation ID must be canonical UUIDv7") from exc
    require(parsed.version == 7 and str(parsed) == value, "operation ID must be canonical UUIDv7", "storage_invalid")
    if now is not None:
        seconds = (parsed.int >> 80)//1000
        require(now-604800 <= seconds <= now+300, "operation ID outside replay window", "storage_expired")
    return parsed


def persistent_identity(path):
    """Same persistent identity as Rust, without boot-dependent device spelling."""
    path = Path(path)
    info = _evidence(path)
    require(info is not None, "identity path absent")
    if os.name == "nt":
        api = WindowsAPI()
        handle = api.kernel.CreateFileW(str(path), 0, 7, None, 3, 0x02200000, None)
        require(handle not in (None, ctypes.c_void_p(-1).value), "identity open failed")
        try:
            identity = ctypes.create_string_buffer(24)
            api.check(api.kernel.GetFileInformationByHandleEx(handle, 18, identity, 24))
            return {"volume": str(struct.unpack_from("=Q", identity.raw)[0]),
                    "file": str(int.from_bytes(identity.raw[8:24], "little"))}
        finally:
            api.close(handle)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        require(_same_file(info, os.fstat(fd)), "identity changed during open")
        volume = str(info.st_dev)
        if sys.platform == "darwin":
            class AttrList(ctypes.Structure):
                _fields_ = [("count", ctypes.c_uint16), ("reserved", ctypes.c_uint16),
                            ("common", ctypes.c_uint32), ("volume", ctypes.c_uint32),
                            ("directory", ctypes.c_uint32), ("file", ctypes.c_uint32), ("fork", ctypes.c_uint32)]
            libc = ctypes.CDLL(None, use_errno=True)
            mount = ctypes.create_string_buffer(2168)  # Darwin statfs64, SDK sys/mount.h.
            if libc.fstatfs64(fd, mount) != 0:
                raise OSError(ctypes.get_errno(), "mount observation failed")
            require(not struct.unpack_from("=I", mount.raw, 64)[0] & 0x40000000,
                    "snapshot volume identity unsupported", "storage_unsupported")
            asked = AttrList(5, 0, 0x80000000, 0x80040000, 0, 0, 0)
            answer = ctypes.create_string_buffer(40)
            if libc.fgetattrlist(fd, ctypes.byref(asked), answer, 40, 0) != 0:
                raise OSError(ctypes.get_errno(), "volume UUID observation failed")
            require(struct.unpack("=6I", answer.raw[:24]) == (40, 0x80000000, 0x40000, 0, 0, 0)
                    and any(answer.raw[24:]), "volume UUID unavailable")
            volume = str(uuid.UUID(bytes=answer.raw[24:]))
        return {"volume": volume, "file": str(info.st_ino)}
    finally:
        os.close(fd)


def regular_digest(path):
    path = Path(path)
    before = _evidence(path)
    require(before is not None and stat.S_ISREG(before.st_mode), "retained artifact is not a regular file")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0))
    with os.fdopen(fd, "rb") as stream:
        opened = os.fstat(stream.fileno())
        require(_same_file(before, opened), "retained artifact changed")
        digest = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1024*1024), b""):
            digest.update(chunk)
        require(_same_file(opened, os.fstat(stream.fileno()), handles=True) and _same_file(before, _evidence(path)),
                "retained artifact changed while hashing")
        return digest.hexdigest()


def package_digest(root, *, excluded=()):
    digest = hashlib.sha256()
    root = Path(root)
    def visit(directory):
        directory_info = _evidence(directory)
        require(directory_info is not None and stat.S_ISDIR(directory_info.st_mode), "invalid retained package directory")
        for path in sorted(directory.iterdir(), key=lambda p: p.name.encode("utf-8")):
            info = _evidence(path)
            require(info is not None, "retained package entry disappeared")
            if stat.S_ISREG(info.st_mode) and path.relative_to(root).as_posix() in excluded:
                continue
            name = str(path.relative_to(root)).encode()
            digest.update(struct.pack("<Q", len(name)))
            digest.update(name)
            if stat.S_ISDIR(info.st_mode):
                digest.update(b"directory")
                visit(path)
            else:
                require(stat.S_ISREG(info.st_mode), "special retained package entry")
                digest.update(b"file")
                digest.update(regular_digest(path).encode())
    visit(root)
    return digest.hexdigest()


ARTIFACT_SHAPE = {"path": "str", "identity": "identity", "sha256": "str"}
ENROLLMENT_SHAPE = {"schema": "u32", "control_directory": "str", "control_identity": "identity",
    "helper_path": "str", "helper_release": {"version": "str", "target": "str", "sha256": "str"},
    "recovery_release": {"package": "str", "version": "str", "digest": "str", "root": "str"},
    "retained_helper": ARTIFACT_SHAPE, "retained_recovery": ARTIFACT_SHAPE}


def verify_artifact(artifact, *, package=False, identity=True):
    path = Path(artifact['path'])
    require(path.is_absolute() and str(path.resolve(strict=True)) == artifact['path'], 'noncanonical retained path')
    if identity:
        require(persistent_identity(artifact['path']) == artifact['identity'], 'retained identity changed')
    digest = package_digest(artifact['path']) if package else regular_digest(artifact['path'])
    require(digest == artifact['sha256'], 'retained digest changed')


def verify_registration(record):
    try:
        return _verify_registration(record)
    except OSError as exc:
        raise StorageRefusal('storage_unavailable', f'registration inspection failed: {exc}', phase='enrollment') from exc


def validate_registration_shape(record):
    """Rust evidence::validate_shape without reading any copied identity."""
    validate(record, ENROLLMENT_SHAPE, exact=True)
    helper, recovery = record["helper_release"], record["recovery_release"]
    require(record["schema"] == 1 and re.fullmatch(
        r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-(?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*)(?:\.(?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*))*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?", helper["version"])
        and 0 < len(helper["target"].encode()) <= 128 and recovery["package"] == "devlyn-cli"
        and recovery["version"] and recovery["digest"], "unsupported or incomplete enrollment", "storage_unsupported")
    require(record["retained_helper"]["sha256"] == helper["sha256"]
            and record["retained_recovery"]["path"] == recovery["root"], "retained release binding changed")
    for value in (record['control_directory'], record['helper_path'], recovery['root'],
                  record['retained_helper']['path'], record['retained_recovery']['path']):
        path = Path(value)
        require(path.is_absolute() and str(path) == value and '..' not in path.parts, 'noncanonical enrollment path')


def _verify_registration(record):
    validate_registration_shape(record)
    helper = record['helper_release']
    for value in (record['control_directory'], record['helper_path']):
        path = Path(value)
        require(path.is_absolute() and str(path.resolve(strict=True)) == value, "noncanonical enrollment path")
    require(persistent_identity(record["control_directory"]) == record["control_identity"], "control identity changed")
    require(regular_digest(record["helper_path"]) == helper["sha256"], "helper digest changed")
    verify_artifact(record['retained_helper'])
    verify_artifact(record['retained_recovery'], package=True)
    return record


def read_evidence_json(path, observed, *, limit=MAX_REQUEST):
    info = _evidence(path)
    require(info is not None and stat.S_ISREG(info.st_mode), f'missing/invalid {path}')
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
                 | getattr(os, 'O_BINARY', 0))
    with os.fdopen(fd, 'rb') as stream:
        require(_same_file(info, os.fstat(stream.fileno())), f'{path} changed while opening')
        raw = stream.read() if limit is None else stream.read(limit + 1)
    require(limit is None or len(raw) <= limit, f'oversized {path}')
    observed.append((path, info))
    return loads(raw)


def lifecycle_evidence(root, path, observed):
    """Optional no-follow evidence, including every ancestor under the root."""
    current = root
    for part in path.relative_to(root).parts:
        current = current / part
        info = _evidence(current)
        observed.append((current, info))
        if info is None:
            return None
        require(stat.S_ISREG(info.st_mode) if current == path else stat.S_ISDIR(info.st_mode),
                f'invalid lifecycle evidence kind: {current}')
    return read_evidence_json(path, observed)


def retirement_evidence(root, observed):
    shape = {'schema': 'u32', 'operation_id': 'str', 'root_identity': 'identity', 'lock_identity': 'identity'}
    fence = lifecycle_evidence(root, root / 'storage-client-fence.json', observed)
    journal = lifecycle_evidence(root, root / 'storage-client-unenroll.json', observed)
    if fence is not None:
        validate(fence, shape, exact=True)
        require(fence['schema'] == 1, 'unsupported retirement fence')
        canonical_operation(fence['operation_id'])
    if journal is not None:
        validate(journal, {**shape, 'retired': 'bool', 'archives': [
            {'source': 'str', 'destination': 'str', 'identity': 'identity', 'sha256': 'str'}]}, exact=True)
        require(fence is not None and all(journal[key] == fence[key] for key in shape),
                'retirement journal/fence differs')
        sources = ('storage', 'control', 'harness/state.json', 'storage-client.json')
        names = ('storage', 'control', 'harness-state.json', 'enrollment.json')
        previous = -1
        for archive in journal['archives']:
            require(archive['source'] in [str(root / name) for name in sources], 'invalid retirement source')
            index = sources.index(str(Path(archive['source']).relative_to(root)))
            require(index > previous and Path(archive['destination']) == root / 'storage-client-retired'
                    / fence['operation_id'] / names[index], 'invalid retirement archive path/order')
            previous = index
        if not journal['retired']:
            for name in sources:
                if str(root / name) not in [entry['source'] for entry in journal['archives']]:
                    require(_evidence(root / name) is None, 'uninventoried retirement evidence')
    return fence, journal


def _retirement_move(root, pins, observed):
    """Establish a copied retirement before allowing digest-only bootstrap.

    Compare all identities in the evidence this client reads, never merely a
    failed retained-artifact identity. Same-volume replacements cannot qualify.
    """
    fence, journal = retirement_evidence(root, observed)
    if fence is None:
        return False
    identities = []
    def record_identities(record):
        validate_registration_shape(record)
        identities.extend([record['control_identity'], record['retained_helper']['identity'],
                           record['retained_recovery']['identity']])
    record_identities(pins['enrollment'])
    identities.append(pins['runtime']['identity'])
    record = lifecycle_evidence(root, root / 'storage-client.json', observed)
    if record is not None:
        record_identities(record)
        require(all(record[key] == pins['enrollment'][key] for key in ('control_directory', 'control_identity')),
                'move record/pins binding differs')
    identities.extend([fence['root_identity'], fence['lock_identity']])
    if journal is not None:
        identities.extend([journal['root_identity'], journal['lock_identity']])
        for archive in journal['archives']:
            identities.append(archive['identity'])
            paths = [Path(archive[key]) for key in ('source', 'destination')]
            existing = []
            for path in paths:
                # Check every ancestor without interpreting a directory as JSON.
                current = root
                for part in path.relative_to(root).parts:
                    current /= part
                    info = _evidence(current)
                    observed.append((current, info))
                    if info is None:
                        break
                    require(current == path or stat.S_ISDIR(info.st_mode), 'invalid archive ancestor')
                else:
                    existing.append(path)
            require(len(existing) == 1, 'incomplete/ambiguous retirement archive')
            path = existing[0]
            digest = (package_digest(path, excluded=('service/serve.log', 'service/serve.log.1')
                                     if path.name == 'control' else ()) if path.is_dir() else regular_digest(path))
            require(digest == archive['sha256'], 'retirement archive digest changed')
            if archive['source'] == str(root / 'storage-client.json'):
                record_identities(read_evidence_json(path, observed))
    old = identities[0]['volume']
    require(old and all(identity['volume'] == old and identity['file'] for identity in identities),
            'mixed or malformed moved identities')
    current_volume = persistent_identity(root)['volume']
    if current_volume == old:
        return False
    for path, directory in ((root / 'storage-client.lock', False), (root / 'control', True)):
        info = _evidence(path)
        if info is not None:
            require((stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
                    and persistent_identity(path)['volume'] == current_volume, 'mixed current move identities')
    return True


def retirement_move(root, pins, observed):
    try:
        return _retirement_move(root, pins, observed)
    except StorageRefusal:
        # Rust Established::NotMoved: malformed/mixed evidence cannot authorize
        # bootstrap. The caller must still pass every ordinary identity check.
        return False


def moved_operation(saved):
    """A committed manifest or established retirement, never registry membership."""
    home = user_home()
    if home is None:
        return None
    root = (home / '.devlyn').resolve(strict=False)
    observed = []
    marker = root / 'storage-client-moved'
    info = _evidence(marker)
    journal_info = _evidence(root / 'storage-client-unenroll.json')
    if info is None and journal_info is None:
        return None
    require(type(saved) is dict, 'invalid saved authority binding')
    current = lifecycle_evidence(root, root / 'storage-client.json', observed)
    require(current is None or type(current) is dict, 'invalid current enrollment')
    if current is not None and all(key in current and key in saved and current[key] == saved[key]
                                   for key in ('control_directory', 'control_identity')):
        control = Path(current['control_directory'])
        if _evidence(control) is not None and persistent_identity(control) == current['control_identity']:
            return None
    if info is not None:
        require(stat.S_ISDIR(info.st_mode), 'redirected move archive')
        for directory in sorted(marker.iterdir()):
            # Like Rust, non-operation archive names are not manifests.
            try:
                canonical_operation(directory.name)
            except StorageRefusal:
                continue
            manifest = lifecycle_evidence(root, directory / 'storage-client-move.json', observed)
            if manifest is None:
                continue
            require(type(manifest) is dict, 'invalid move manifest')
            validate(manifest, {'schema': 'u32', 'operation_id': 'str', 'from_volume': 'str', 'to_volume': 'str',
                     'old_binding': {'control_directory': 'str', 'control_identity': 'identity'} if manifest.get('old_binding') is not None else (None,)}, exact=True)
            require(manifest['schema'] == 1 and manifest['operation_id'] == directory.name
                    and manifest['from_volume'] and manifest['to_volume']
                    and manifest['from_volume'] != manifest['to_volume'], 'invalid move manifest')
            binding = manifest['old_binding']
            if binding is not None:
                path = Path(binding['control_directory'])
                require(path.is_absolute() and str(path) == binding['control_directory'] and '..' not in path.parts
                        and binding['control_identity']['volume'] == manifest['from_volume']
                        and binding['control_identity']['file'], 'invalid moved binding')
            if binding is not None and all(saved.get(key) == binding[key] for key in binding):
                return manifest['operation_id']
    if _evidence(root / 'storage-client-unenroll.json') is not None:
        pins = lifecycle_evidence(root, root / 'storage-client-recovery/pins.json', observed)
        if pins is None:
            return None  # No retained binding can establish a moved receipt.
        validate(pins, {'schema': 'u32', 'enrollment': ENROLLMENT_SHAPE, 'runtime': ARTIFACT_SHAPE, 'node': 'str'}, exact=True)
        require(pins['schema'] == pins['enrollment']['schema'] == 1, 'unsupported recovery pins')
        if (all(saved.get(key) == pins['enrollment'][key] for key in ('control_directory', 'control_identity'))
                and retirement_move(root, pins, observed)):
            return read_evidence_json(root / 'storage-client-unenroll.json', observed)['operation_id']
    return None


def unenroll_resume(record, operation, *, cancel=False):
    request = json.dumps({'adapter_protocol': 1, 'operation_id': operation}, separators=(',', ':'))
    return (shlex.join(['printf', '%s\\n', request]) + ' | '
            + shlex.join([record['retained_helper']['path'], 'storage-client', 'unenroll',
                          '--cancel' if cancel else '--reconcile', '--json']))


def replay_retirement(record):
    root = (user_home() / '.devlyn').resolve(strict=True)
    fence, journal = retirement_evidence(root, [])
    if journal is None or journal['retired']:
        return
    helper = record['retained_helper']['path']
    require(regular_digest(helper) == record['helper_release']['sha256'], 'retained helper changed')
    request = {'adapter_protocol': 1, 'operation_id': fence['operation_id']}
    adapter = runpy.run_path(str(Path(__file__).with_name('storage-checkout.py')))
    try:
        with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as diagnostic:
            process = subprocess.run([helper, 'storage-client', 'unenroll', '--reconcile', '--json'],
                                     input=json.dumps(request).encode()+b'\n', stdout=output, stderr=diagnostic)
            output.seek(0)
            reply = output.read(MAX_REPLY+1)
        result = adapter['decode_reply'](reply, 'unenroll', process.returncode)
        require(type(result) is dict and result.get('operation_id') == fence['operation_id']
                and result.get('retired') is True, 'retirement replay not complete')
        _, journal = retirement_evidence(root, [])
        require(journal is not None and journal['retired'], 'retirement replay did not commit')
    except (OSError, StorageRefusal, adapter['StorageRefusal']) as exc:
        resume = unenroll_resume(record, fence['operation_id'])
        detail = exc.diagnostic if isinstance(exc, StorageRefusal) else str(exc)
        raise StorageRefusal('storage_unavailable', detail, phase='retirement',
                             message='Finish this storage retirement; resume ' + resume, resume=resume) from exc


def retirement_refusal(root=None):
    """An interrupted retirement has a headless exit through its retained helper."""
    if root is None:
        home = user_home()
        if home is None:
            return
        root = (home / '.devlyn').resolve(strict=False)
    if _evidence(root / 'storage-client-fence.json') is None and _evidence(root / 'storage-client-unenroll.json') is None:
        return
    try:
        # Completed retirement keeps operation_enrollment's existing validation,
        # including stale same-disk archive paths. Only an unfinished one exits here.
        journal = lifecycle_evidence(root, root / 'storage-client-unenroll.json', [])
        if type(journal) is dict and journal.get('retired') is True:
            return
        fence, journal = retirement_evidence(root, [])
        require(fence is not None, 'retirement fence missing')
        record = recovery_registration()
    except (StorageRefusal, OSError, ValueError, RuntimeError) as exc:
        detail = exc.diagnostic if isinstance(exc, StorageRefusal) else str(exc)
        repair = 'Open Devlyn to repair its storage registration'
        raise StorageRefusal('storage_unavailable', detail, phase='enrollment', message=repair, resume=repair) from exc
    resume = unenroll_resume(record, fence['operation_id'], cancel=journal is None)
    alternative = ''
    if journal is None:
        pins = read_evidence_json(root / 'storage-client-recovery/pins.json', [])
        if not retirement_move(root, pins, []):
            alternative = '; or cancel before retirement starts: ' + resume
            resume = unenroll_resume(record, fence['operation_id'])
    raise StorageRefusal('storage_unavailable', 'retirement is not complete', phase='enrollment',
                         message='Finish this storage retirement; resume ' + resume + alternative, resume=resume)


def recovery_registration():
    """Current retained pins survive replacement of the app and unenrollment."""
    try:
        home = user_home()
        require(home is not None, 'recovery home unavailable')
        root = (home / '.devlyn').resolve(strict=True)
        marker = root / 'storage-client-recovery'
        info = _evidence(marker)
        require(info is not None and stat.S_ISDIR(info.st_mode), 'recovery pins directory missing/invalid')
        observed = [(marker, info)]
        pins = read_evidence_json(marker / 'pins.json', observed)
        validate(pins, {'schema': 'u32', 'enrollment': ENROLLMENT_SHAPE,
                        'runtime': ARTIFACT_SHAPE, 'node': 'str'}, exact=True)
        record = pins['enrollment']
        node, runtime = Path(pins['node']), Path(pins['runtime']['path'])
        require(pins['schema'] == record['schema'] == 1
                and record['recovery_release']['root'] == record['retained_recovery']['path']
                and node.is_absolute() and str(node.resolve(strict=True)) == pins['node']
                and node.is_relative_to(runtime), 'invalid recovery pin paths')
        moved = retirement_move(root, pins, observed)
        verify_artifact(record['retained_helper'], identity=not moved)
        verify_artifact(record['retained_recovery'], package=True, identity=not moved)
        verify_artifact(pins['runtime'], package=True, identity=not moved)
        for path, before in observed:
            after = _evidence(path)
            require(after is None if before is None else _same_file(before, after), f'recovery pins changed: {path}')
        return record
    except (StorageRefusal, OSError, ValueError, RuntimeError) as exc:
        detail = exc.diagnostic if isinstance(exc, StorageRefusal) else str(exc)
        raise StorageRefusal('storage_unavailable', f'recovery pins invalid: {detail}', phase='enrollment',
                             message='Retain the workspace and receipt; repair Devlyn recovery pins and retry') from exc


def windows_profile():
    """The known-folder fallback used by Rust dirs::home_dir on Windows."""
    import uuid
    class GUID(ctypes.Structure):
        _fields_ = [('bytes', ctypes.c_ubyte * 16)]
    profile = GUID((ctypes.c_ubyte * 16).from_buffer_copy(
        uuid.UUID('5e6c858f-0e22-4760-9afe-ea3317b67173').bytes_le))
    shell = ctypes.WinDLL('shell32', use_last_error=True)
    ole = ctypes.WinDLL('ole32', use_last_error=True)
    shell.SHGetKnownFolderPath.argtypes = [ctypes.POINTER(GUID), ctypes.c_uint32, ctypes.c_void_p,
                                          ctypes.POINTER(ctypes.c_wchar_p)]
    shell.SHGetKnownFolderPath.restype = ctypes.c_long
    ole.CoTaskMemFree.argtypes = [ctypes.c_void_p]
    ole.CoTaskMemFree.restype = None
    value = ctypes.c_wchar_p()
    try:
        result = shell.SHGetKnownFolderPath(ctypes.byref(profile), 0, None, ctypes.byref(value))
        require(result == 0 and bool(value.value), 'Windows profile unavailable; repair the user profile')
        return Path(value.value)
    finally:
        if value:
            ole.CoTaskMemFree(ctypes.cast(value, ctypes.c_void_p))


def user_home():
    """Mirror devlynd util::home_dir; HOMEDRIVE/HOMEPATH are not authority."""
    try:
        if os.name == 'nt':
            profile = os.environ.get('USERPROFILE')
            return Path(profile) if profile else windows_profile()
        home = os.environ.get('HOME')
        if home:
            return Path(home)
        import pwd
        try:
            home = pwd.getpwuid(os.getuid()).pw_dir
        except KeyError:
            return None
        return Path(home) if home else None
    except (OSError, ValueError, RuntimeError, ImportError, AttributeError) as exc:
        raise StorageRefusal('storage_unavailable', f'home resolution failed; repair the user profile: {exc}',
                             phase='enrollment') from exc


def enrollment(*, receipt=None, verify_registration=verify_registration):
    """Three-state read: absent/standalone, enrolled/managed, or invalid/refusal.

    Canonical lifecycle root and retained artifact checks mirror Rust evidence.rs.
    Registry contents never participate. Receipt custody cannot downgrade.
    """
    try:
        # A positively absent home has no record. Invalid/inaccessible evidence
        # still fails below; receipt custody must never downgrade.
        home = user_home()
        if home is None:
            require(not managed_receipt(receipt or {}), 'managed receipt has no home; restore the user profile')
            return {'mode': 'standalone', 'evidence': []}
        home = home.resolve(strict=False)
        # Rust canonical_root resolves the lifecycle root at the user boundary.
        named_root = home / ".devlyn"
        try:
            named_root.lstat()
        except FileNotFoundError:
            root = named_root
        else:
            root = named_root.resolve(strict=True)
        retirement_refusal(root)
        evidence = []
        observations = []

        def probe(path):
            info = _evidence(path)
            observations.append((path, info))
            return info

        def finish(result):
            for path, before in observations:
                after = _evidence(path)
                require(after is None if before is None else _same_file(before, after),
                        f"enrollment evidence changed during inspection: {path}")
            return result

        managed = False
        if receipt is not None:
            require(type(receipt) is dict, "invalid saved receipt")
            managed = managed_receipt(receipt)
        if managed:
            evidence.append("managed_receipt")
        expectation = root / "storage-client.json"
        info = probe(expectation)
        if info is not None:
            evidence.append("storage-client.json")
            require(stat.S_ISREG(info.st_mode), "expectation is not a regular file")
            fd = os.open(expectation, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
                         | getattr(os, "O_BINARY", 0))
            with os.fdopen(fd, "rb") as stream:
                require(_same_file(info, os.fstat(stream.fileno())), "expectation changed while opening")
                raw = stream.read(MAX_REQUEST+1)
            require(len(raw) <= MAX_REQUEST, "oversized expectation")
            record = loads(raw)
            require(type(record) is dict and type(record.get("schema")) is int, "malformed expectation schema")
            require(record["schema"] == 1, "unsupported expectation schema", "storage_unsupported")
            require(verify_registration is not None, "enrollment registration verifier unavailable", "storage_unsupported")
            registration = verify_registration(record)
            require(type(registration) is dict and bool(registration), "registration verification failed")
            return finish({"mode": "managed", "evidence": evidence, "evidence_version": 1,
                           "expectation": str(expectation), "registration": registration})
        require(not evidence, "Devlyn enrollment evidence exists without a valid helper registration")
        return finish({"mode": "standalone", "evidence": []})
    except (OSError, ValueError, RuntimeError) as exc:
        raise StorageRefusal("storage_unavailable", f"enrollment inspection failed: {exc}", phase="enrollment") from exc


def recovery_marker():
    # Marker existence (including a redirected marker) matches Rust retained().
    try:
        home = user_home()
        if home is None:
            return False
        (home / '.devlyn/storage-client-recovery').lstat()
        return True
    except FileNotFoundError:
        return False
    except (OSError, ValueError, RuntimeError) as exc:
        raise StorageRefusal('storage_unavailable', f'recovery marker inspection failed; repair the user profile: {exc}',
                             phase='enrollment') from exc


def operation_enrollment():
    """New operations use enrollment alone; existing receipts keep their mode."""
    decision = enrollment()
    if decision['mode'] == 'managed' or not recovery_marker():
        return decision
    repair = 'Open Devlyn to repair its storage registration'
    try:
        root = (user_home() / '.devlyn').resolve(strict=True)
        observed = []

        journal = read_evidence_json(root / 'storage-client-unenroll.json', observed)
        fence = read_evidence_json(root / 'storage-client-fence.json', observed)
        binding = {'schema': 'u32', 'operation_id': 'str', 'root_identity': 'identity', 'lock_identity': 'identity'}
        validate(journal, {**binding, 'archives': [{'source': 'str', 'destination': 'str',
                 'identity': 'identity', 'sha256': 'str'}], 'retired': 'bool'})
        validate(fence, binding)
        # Journal, Fence and Archive deny unknown fields in Rust; Identity does not.
        require(set(journal) == set(binding) | {'archives', 'retired'} and set(fence) == set(binding),
                'unknown retirement field')
        require(journal['schema'] == fence['schema'] == 1 and journal['retired'] is True,
                'unenrollment is not complete')
        operation = journal['operation_id']
        parsed = uuid.UUID(operation)
        require(parsed.version == 7 and str(parsed) == operation and fence['operation_id'] == operation,
                'retirement operation ID differs')
        stale = False
        for key, path in (('root_identity', root), ('lock_identity', root / 'storage-client.lock')):
            info = _evidence(path)
            require(info is not None and (stat.S_ISDIR(info.st_mode) if path == root else stat.S_ISREG(info.st_mode)),
                    'invalid retirement root/lock kind')
            identities = [{field: record[key][field] for field in ('volume', 'file')} for record in (journal, fence)]
            require(identities[0] == identities[1], 'retirement journal/fence identity differs')
            stale |= identities[0] != persistent_identity(path)
        sources = ('storage', 'control', 'harness/state.json', 'storage-client.json')
        names = ('storage', 'control', 'harness-state.json', 'enrollment.json')
        previous = -1
        archive_root = None
        for entry in journal['archives']:
            require(set(entry) == {'source', 'destination', 'identity', 'sha256'}, 'unknown retirement archive field')
            source = Path(entry['source'])
            matches = [i for i, name in enumerate(sources) if source.parts[-len(Path(name).parts):] == Path(name).parts]
            require(source.is_absolute() and '..' not in source.parts and len(matches) == 1, 'invalid retirement source')
            index = matches[0]
            origin = source.parents[len(Path(sources[index]).parts) - 1]
            require(archive_root is None or origin == archive_root, 'retirement archive roots differ')
            archive_root = origin
            require(index > previous, 'duplicate or reordered retirement archive')
            previous = index
            require(Path(entry['destination']) == origin / 'storage-client-retired' / operation / names[index],
                    'invalid retirement archive path')
            stale |= origin != root
        if stale:
            for name in sources:
                try:
                    (root / name).lstat()
                except FileNotFoundError:
                    continue
                raise StorageRefusal('storage_unavailable', 'stale retirement evidence has live inventory')
        for path, info in observed:
            require(_same_file(info, _evidence(path)), f'retirement evidence changed: {path}')
        require(_evidence(root / 'storage-client.json') is None, 'enrollment appeared during retirement inspection')
        return decision
    except (StorageRefusal, OSError, ValueError, RuntimeError) as exc:
        detail = exc.diagnostic if isinstance(exc, StorageRefusal) else str(exc)
        raise StorageRefusal('storage_unavailable', f'registration repair required: {detail}', phase='enrollment',
                             message=repair, resume=repair) from exc


def queue_handoff(common, binding):
    """Follow Devlyn's pre-contract hold without changing enrollment or bindings."""
    try:
        decision = operation_enrollment()
        managed = decision['mode'] == 'managed'
        if not managed and not recovery_marker():
            return None
    except StorageRefusal as exc:
        return str(exc)
    reference = binding['release']
    listed = False
    try:
        manifest = read_evidence_json(Path(reference['root']) / 'release.json', [], limit=4*1024*1024)
        listed = (type(manifest) is dict and type(manifest.get('schemaVersion')) is int
                  and manifest['schemaVersion'] == 1
                  and all(manifest.get(key) == reference[key] for key in ('package', 'version'))
                  and type(manifest.get('digest')) is dict
                  and manifest['digest'].get('algorithm') == 'sha256'
                  and manifest['digest'].get('value') == reference['digest']
                  and type(manifest.get('files')) is list
                  and sum(type(entry) is dict and entry.get('path') == 'config/storage-client-contract.json'
                          for entry in manifest['files']) == 1)
    except (StorageRefusal, OSError, ValueError):
        listed = False  # An unreadable manifest is pre-contract, never positive absence.
    drain = 'Devlyn runs this queue on this computer: start it with Drain in Devlyn'
    if listed:
        return drain if managed else None
    holders = []
    def unreadable(path):
        holders.append(f'{path} cannot be read; repair it so this release can read it')
    root = Path(common) / 'devlyn-completion'
    try:
        info = _evidence(root)
        if info is not None:
            require(stat.S_ISDIR(info.st_mode), 'invalid receipt root')
            for entry in sorted(root.iterdir()):
                receipt = entry / 'receipt.json'
                adapter_marker = False
                info = None
                try:
                    info = _evidence(entry)
                    require(info is not None, 'receipt entry disappeared')
                    if not stat.S_ISDIR(info.st_mode):
                        continue
                    try:
                        (entry / 'storage-allocation.json').lstat()
                        adapter_marker = True  # Any Rust marker kind is positive presence.
                    except FileNotFoundError:
                        adapter_marker = False
                    if _evidence(receipt) is None:
                        if adapter_marker:
                            holders.append(str(receipt))
                        continue
                    saved = read_evidence_json(receipt, [], limit=None)
                    if adapter_marker or managed_receipt(saved):
                        text = str(receipt)
                        registration = saved.get('storage', {}).get('decision', {}).get('registration')
                        if registration and moved_operation(registration):
                            canonical_operation(saved['storage']['request']['operation_id'])
                            # Share the operation-specific resume builder with task completion.
                            helper = runpy.run_path(str(Path(__file__).with_name('task-complete.py')))
                            text += ' resume ' + helper['receipt_resume']('recover-storage', receipt, saved)
                        holders.append(text)
                except (StorageRefusal, OSError, ValueError, TypeError, AttributeError, KeyError):
                    if adapter_marker:
                        holders.append(str(receipt))
                        continue
                    unreadable(receipt if info is not None and stat.S_ISDIR(info.st_mode) else entry)
    except (StorageRefusal, OSError, ValueError):
        unreadable(root)
    if not holders:
        return drain if managed else None
    return ('this queue waits for the tasks in progress here: ' + '; '.join(holders)
            + ". Finish each with this release, and follow any resume a refusal names; a moved task's resume releases it and keeps its files; "
            + '`recover-storage --for-removal` removes one only when the owner says so (task-completion.md); '
            + ('then start it with Drain in Devlyn' if managed else 'then run this again'))


def sync_directory(path):
    """Native durability barrier; failure is visible, never treated as success."""
    path = Path(path)
    if os.name != 'nt':
        fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    else:
        api = WindowsAPI()
        api._bind(api.kernel, 'FlushFileBuffers', ctypes.c_int, [ctypes.c_void_p])
        handle = api.kernel.CreateFileW(str(path), 0xC0000000, 3, None, 3, 0x02200000, None)
        require(handle not in (None, ctypes.c_void_p(-1).value), 'directory durability open failed')
        try:
            api.check(api.kernel.FlushFileBuffers(handle))
        finally:
            api.close(handle)
