#!/usr/bin/env python3
"""Legacy cleanup fixtures: real installs made by this package's installer in temporary homes and
repositories, then `devlyn cleanup --plan` and `--apply`. No model calls; GitHub is task-complete's
own fake gh over a local bare repository."""
import hashlib
import json
import os
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "bin" / "devlyn.js"
HELPER = ROOT / "config" / "skills" / "_shared" / "task-complete.py"


class CleanupFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="devlyn cleanup ✓ ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.home = self.root / "home"
        self.home.mkdir()
        self.env = {**os.environ, "HOME": str(self.home), "USERPROFILE": str(self.home), "GIT_CONFIG_NOSYSTEM": "1",
                    "GIT_AUTHOR_NAME": "Fixture", "GIT_AUTHOR_EMAIL": "fixture@example.com",
                    "GIT_COMMITTER_NAME": "Fixture", "GIT_COMMITTER_EMAIL": "fixture@example.com",
                    "CODEX_HOME": str(self.home / ".codex"), "PYTHONDONTWRITEBYTECODE": "1"}
        self.snapshots = self.root / "tmp"
        self.snapshots.mkdir()
        self.env["TMPDIR"] = str(self.snapshots)
        self.env["TMP"] = str(self.snapshots)
        self.env["TEMP"] = str(self.snapshots)
        self.repos = []
        self.env.pop("CLAUDE_CONFIG_DIR", None)
        self.env["GIT_CONFIG_GLOBAL"] = os.devnull
        # These fixtures own every process using their temporary installs. Use a deterministic process
        # listing so host privacy/sandbox restrictions cannot turn every fixture into an in-use skip.
        if os.name != "nt":
            bins = self.root / "process-bin"
            bins.mkdir()
            ps = bins / "ps"
            ps.write_text(f"#!{sys.executable}\nimport os\nprint(os.environ.get('FIXTURE_PROCESSES', ''))\n")
            ps.chmod(0o755)
            self.env["PATH"] = str(bins) + os.pathsep + self.env["PATH"]

    def run_ok(self, argv, cwd=None, code=0, input=None):
        result = subprocess.run([str(part) for part in argv], cwd=cwd or self.root, env=self.env, capture_output=True,
                                text=True, encoding="utf-8", input=input)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return result

    def cli(self, *args, cwd=None, code=0):
        result = self.run_ok(["node", getattr(self, "cli_path", CLI), *args, "--json"], cwd=cwd, code=code)
        if args[0] == "cleanup":
            # Prediction: every command releases all snapshot directories, registrations and owned refs.
            self.assertEqual(list(self.snapshots.glob("dc-*")), [])
            for repo in self.repos:
                self.assertEqual(self.run_ok(["git", "for-each-ref", "refs/devlyn/cleanup/"], cwd=repo).stdout, "")
                trees = self.run_ok(["git", "worktree", "list", "--porcelain"], cwd=repo).stdout
                self.assertNotIn(str(self.snapshots), trees)
        envelope = json.loads(result.stdout.strip().splitlines()[-1])
        return envelope["data"] if envelope["ok"] else envelope["error"]

    def repo(self, name):
        repo = self.root / name
        repo.mkdir()
        self.run_ok(["git", "init", "-q", "--initial-branch=main"], cwd=repo)
        (repo / "README.md").write_text("# project\n", encoding="utf-8")
        self.run_ok(["git", "add", "README.md"], cwd=repo)
        self.run_ok(["git", "commit", "-qm", "init"], cwd=repo)
        self.repos.append(repo)
        return repo

    def install(self, cwd, *flags):
        self.run_ok(["node", CLI, "-y", *flags], cwd=cwd)

    def plan(self, *args):
        registrations = lambda repo: [line for line in self.run_ok(["git", "worktree", "list", "--porcelain"], cwd=repo).stdout.splitlines()
                                      if line.startswith("worktree ")]
        trees = {repo: registrations(repo) for repo in self.repos}
        plan = self.cli("cleanup", "--plan", *args)
        for repo, before in trees.items():
            self.assertEqual(registrations(repo), before)
        path = self.root / f"plan-{plan['digest'][:8]}.json"
        # As the app stores a reviewed plan: serde_json writes object keys sorted.
        path.write_text(json.dumps(plan, sort_keys=True), encoding="utf-8")
        return plan, path

    def apply(self, plan, path, code=0, include=()):
        return self.cli("cleanup", "--apply", "--plan-file", path, "--digest", plan["digest"],
                        *[arg for item in include for arg in ("--include", item)], code=code)

    def historical_skill(self, dest, tag="v3.0.1", name="devlyn:ideate"):
        source = f"config/skills/{name}"
        files = self.run_ok(["git", "ls-tree", "-r", "--name-only", tag, "--", source], cwd=ROOT).stdout.splitlines()
        self.assertTrue(files)
        for file in files:
            target = dest / Path(file).relative_to(source)
            target.parent.mkdir(parents=True, exist_ok=True)
            data = subprocess.check_output(["git", "show", f"{tag}:{file}"], cwd=ROOT)
            target.write_bytes(data)

    def fake_github(self, repo):
        """task-complete's own fake gh and transport wrappers over a local bare repository holding main."""
        helper = runpy.run_path(str(HELPER))
        bare = self.root / f"{repo.name}.git"
        self.run_ok(["git", "init", "-q", "--bare", "--initial-branch=main", bare])
        self.run_ok(["git", "push", "-q", bare, "main"], cwd=repo)
        bin_dir = self.root / "bin"
        bin_dir.mkdir(exist_ok=True)
        for name, body in (("gh", helper["FAKE_GH"]), ("git.py", helper["GIT_WRAPPER"]), ("git", helper["GIT_DISPATCH"])):
            (bin_dir / name).write_text(body, encoding="utf-8")
            (bin_dir / name).chmod(0o755)
        data = self.root / "gh.json"
        data.write_text(json.dumps({"bare": str(bare), "pending": False}), encoding="utf-8")
        self.env.update(PATH=str(bin_dir) + os.pathsep + self.env["PATH"], FIXTURE_GH=str(data), REAL_GIT=shutil.which("git"))
        self.run_ok(["git", "remote", "add", "origin", "https://github.com/test/project.git"], cwd=repo)
        return bare

    @staticmethod
    def actions(scope):
        return sorted((item["kind"], item["action"], Path(item["path"]).name, item["route"],
                       (item["reasons"] or [{}])[0].get("code")) for item in scope["items"])

    def checkout_state(self, repo):
        gitdir = Path(self.run_ok(["git", "rev-parse", "--absolute-git-dir"], cwd=repo).stdout.strip())
        return {"head": self.run_ok(["git", "rev-parse", "HEAD"], cwd=repo).stdout,
                "index": (gitdir / "index").read_bytes(),
                "fetch": (gitdir / "FETCH_HEAD").read_bytes() if (gitdir / "FETCH_HEAD").exists() else None,
                "files": {str(p.relative_to(repo)): os.readlink(p) if p.is_symlink() else p.read_bytes()
                          for p in repo.rglob("*") if ".git" not in p.relative_to(repo).parts and (p.is_file() or p.is_symlink())},
                "worktrees": self.run_ok(["git", "worktree", "list", "--porcelain"], cwd=repo).stdout}

    def ai_os_package(self):
        """Synthetic public fixtures, made known only in this copied package's ordinary history JSON."""
        package = self.root / "package"
        package.mkdir()
        for name in ("bin", "config"):
            shutil.copytree(ROOT / name, package / name)
        for name in ("package.json", "CLAUDE.md", "AGENTS.md"):
            shutil.copyfile(ROOT / name, package / name)
        shutil.copytree(ROOT / "node_modules", package / "node_modules", symlinks=True)
        self.cli_path = package / "bin/devlyn.js"
        history_path = package / "bin/cleanup-history.json"
        history = json.loads(history_path.read_text())
        self.ai_command = b"# Synthetic retired command\nFixture only.\n"
        self.ai_script = b"#!/usr/bin/env node\n// Synthetic retired hook fixture.\n"
        self.ai_hook = {"type": "command", "command": "node .claude/hooks/hook-to-file.mjs", "timeout": 10}
        self.ai_events = ["PreToolUse", "PostToolUse", "PostToolUseFailure", "Notification", "UserPromptSubmit",
                          "SessionStart", "Stop", "SubagentStart", "SubagentStop", "PreCompact", "SessionEnd", "PermissionRequest"]
        history["commands"]["devlyn.fixture.md"] = [hashlib.sha256(self.ai_command).hexdigest()]
        history["hooks"][".claude/hooks/hook-to-file.mjs"] = {
            "hashes": [hashlib.sha256(self.ai_script).hexdigest()],
            "entries": [hashlib.sha256(json.dumps([event, "*", self.ai_hook], sort_keys=True,
                        separators=(",", ":")).encode()).hexdigest() for event in self.ai_events]}
        history_path.write_text(json.dumps(history))
        return history

    def ai_os_install(self, repo, edited=False):
        script = repo / ".claude/hooks/hook-to-file.mjs"
        script.parent.mkdir(parents=True)
        script.write_bytes(self.ai_script + (b"// Owner edit.\n" if edited else b""))
        settings = repo / ".claude/settings.json"
        data = {"env": {"OWNER": "kept ✓"}, "permissions": {"allow": ["Read(*)"]},
                "hooks": {event: [{"matcher": "*", "hooks": [self.ai_hook]}] for event in self.ai_events}}
        data["hooks"]["PostToolUse"][0]["hooks"].append({"type": "command", "command": "echo owner"})
        data["hooks"]["Notification"][0]["ownerKey"] = "keep wrapper"
        settings.write_text(json.dumps(data, ensure_ascii=False))
        return script, settings, data

    def test_ai_os_commands_all_providers_and_local_hook_pair(self):
        # Prediction: known CRLF commands in every provider directory and the hook/settings pair go;
        # edited/unknown commands and every owner settings key survive. A second plan has no edits.
        history = self.ai_os_package()
        repo = self.repo("ai-os-local")
        script, settings, original = self.ai_os_install(repo)
        for directory in history["commandDirectories"]:
            folder = repo / directory
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "devlyn.fixture.md").write_bytes(self.ai_command.replace(b"\n", b"\r\n"))
            (folder / "owner.md").write_text("owner")
        edited = repo / ".claude/commands/devlyn.recommend.md"
        edited.write_text("owner edited command")
        plan, file = self.plan("--project", repo)
        items = plan["scopes"][0]["items"]
        self.assertEqual(sum(i["kind"] == "legacy-command" and i["action"] == "remove" for i in items), 4)
        self.assertIn(("legacy-hook", "remove", script.name, "local", None), self.actions(plan["scopes"][0]))
        self.assertEqual(self.apply(plan, file)["state"], "succeeded")
        self.assertFalse(script.exists())
        expected = {**original, "hooks": {}}
        expected["hooks"]["PostToolUse"] = [{"matcher": "*", "hooks": [{"type": "command", "command": "echo owner"}]}]
        expected["hooks"]["Notification"] = [{"matcher": "*", "hooks": [], "ownerKey": "keep wrapper"}]
        self.assertEqual(json.loads(settings.read_text()), expected)
        self.assertEqual(edited.read_text(), "owner edited command")
        again, _ = self.plan("--project", repo)
        self.assertTrue(all(i["action"] == "skip" for i in again["scopes"][0]["items"]))

    def test_ai_os_edited_hook_requires_include_and_carries_settings(self):
        # Prediction: an edited script and its settings stay by default; explicit --include removes
        # that reviewed script and only its proven settings entries, without a production test switch.
        self.ai_os_package()
        repo = self.repo("ai-os-edited")
        script, settings, _ = self.ai_os_install(repo, edited=True)
        before = settings.read_bytes()
        plan, file = self.plan("--project", repo)
        self.assertIn(("legacy-hook", "skip", script.name, "local", "modified-copy"), self.actions(plan["scopes"][0]))
        self.apply(plan, file)
        self.assertEqual(settings.read_bytes(), before)
        self.assertTrue(script.exists())
        selected = next(i["id"] for i in plan["scopes"][0]["items"] if i["kind"] == "legacy-hook")
        self.assertEqual(self.apply(plan, file, include=[selected])["state"], "succeeded")
        self.assertFalse(script.exists())
        self.assertNotIn(script.name, settings.read_text())

    def test_ai_os_unknown_references_and_unsafe_settings_keep_hook(self):
        # Prediction: modified command objects, wrappers, absolute/shell references, malformed JSON,
        # invalid UTF-8, symlinks and mixed tracking routes never strand a live hook entry.
        self.ai_os_package()
        for variant in ("timeout", "extra", "matcher", "shell", "absolute", "json", "utf8", "link", "local", "duplicate-hooks", "tracked-script", "tracked-settings"):
            if variant == "link" and os.name == "nt":
                continue  # Windows symlink creation requires privileges; POSIX exercises this refusal.
            with self.subTest(variant=variant):
                repo = self.repo("ai-os-" + variant)
                script, settings, data = self.ai_os_install(repo)
                hook = data["hooks"]["PreToolUse"][0]["hooks"][0]
                if variant == "timeout": hook["timeout"] = 11
                if variant == "extra": hook["async"] = True
                if variant == "matcher": data["hooks"]["PreToolUse"][0]["matcher"] = "Read"
                if variant == "shell": hook["command"] += " && echo owner"
                if variant == "absolute": hook["command"] = "node " + str(script)
                settings.write_text(json.dumps(data))
                # The fixture hook object is shared in Python; restore it before the next variant.
                self.ai_hook = {"type": "command", "command": "node .claude/hooks/hook-to-file.mjs", "timeout": 10}
                if variant == "json": settings.write_text("{broken")
                if variant == "utf8": settings.write_bytes(b'{"owner":"\xff"}')
                if variant == "local": (settings.parent / "settings.local.json").write_text(json.dumps(data))
                if variant == "duplicate-hooks":
                    settings.write_text('{"hooks":{},"hooks":' + json.dumps(data["hooks"]) + '}')
                if variant == "link":
                    target = repo / "owner-settings.json"
                    settings.rename(target)
                    settings.symlink_to(target)
                if variant.startswith("tracked-"):
                    self.run_ok(["git", "add", script if variant == "tracked-script" else settings], cwd=repo)
                before = settings.read_bytes()
                plan, file = self.plan("--project", repo)
                item = next(i for i in plan["scopes"][0]["items"] if i["kind"] == "legacy-hook")
                self.assertEqual((item["action"], item["reasons"][0]["code"]), ("skip", "dependent-copy"))
                self.apply(plan, file)
                self.assertTrue(script.exists())
                self.assertEqual(settings.read_bytes(), before)

    def test_ai_os_stale_or_narrowed_pair_preserves_both(self):
        # Prediction: changing either reviewed preimage or narrowing either half out refuses both.
        self.ai_os_package()
        for variant in ("script", "settings", "omit-script", "omit-settings"):
            with self.subTest(variant=variant):
                repo = self.repo("ai-os-stale-" + variant)
                script, settings, _ = self.ai_os_install(repo)
                plan, file = self.plan("--project", repo)
                if variant == "script": script.write_bytes(script.read_bytes() + b"// changed\n")
                if variant == "settings": settings.write_text(settings.read_text() + "\n")
                if variant.startswith("omit-"):
                    kind = "legacy-hook" if variant == "omit-script" else "settings-entry"
                    plan["scopes"][0]["items"] = [i for i in plan["scopes"][0]["items"] if i["kind"] != kind]
                    body = {k: v for k, v in plan.items() if k != "digest"}
                    plan["digest"] = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
                    file.write_text(json.dumps(plan))
                before = settings.read_bytes()
                self.assertEqual(self.apply(plan, file)["state"], "failed")
                self.assertTrue(script.exists())
                self.assertEqual(settings.read_bytes(), before)

    def test_ai_os_settings_write_failure_restores_script(self):
        # Prediction: a failed settings replacement after staging a script restores its original
        # bytes/path and leaves settings intact. Inject at Node's filesystem boundary, not a CLI flag.
        self.ai_os_package()
        repo = self.repo("ai-os-write-failure")
        script, settings, _ = self.ai_os_install(repo)
        before = settings.read_bytes()
        plan, file = self.plan("--project", repo)
        preload = self.root / "fail-settings.cjs"
        preload.write_text("const fs = require('fs'); const rename = fs.renameSync;\n"
                           "fs.renameSync = (a, b) => {\n"
                           f"if (b === {json.dumps(str(settings))}) throw new Error('fixture settings rename failure');\n"
                           "return rename(a, b); };\n")
        self.env["NODE_OPTIONS"] = "--require " + json.dumps(str(preload), ensure_ascii=False)
        result = self.apply(plan, file)
        self.assertEqual(result["state"], "failed")
        self.assertIn("fixture settings rename failure", result["scopes"][0]["error"]["params"]["detail"])
        self.assertEqual(script.read_bytes(), self.ai_script)
        self.assertEqual(settings.read_bytes(), before)
        self.assertEqual(list(script.parent.glob("*.tmp")), [])

    def test_ai_os_settings_edit_preserves_owner_bytes(self):
        # Prediction (review HIGH): only proven array elements disappear. BOM, CRLF, duplicate owner
        # keys, large numbers, escapes and remaining hook objects keep their exact original bytes.
        self.ai_os_package()
        repo = self.repo("ai-os-owner-bytes")
        script, settings, _ = self.ai_os_install(repo)
        prefix = '\ufeff{\r\n  "ownerNumber":9007199254740993,"duplicate":1,"duplicate":2,\r\n'
        suffix = ',\r\n  "ownerEscape":"\\u0061"\r\n}\r\n'
        owner = '{"type":"command", "command":"echo owner", "number":9007199254740993}'
        retired = json.dumps(self.ai_hook)
        middle = '"hooks":{"PreToolUse":[{"matcher":"*","hooks":[' + retired + ',' + owner + ',' + retired + ']}]}'
        settings.write_bytes((prefix + middle + suffix).encode())
        plan, file = self.plan("--project", repo)
        self.assertEqual(self.apply(plan, file)["state"], "succeeded")
        expected = prefix + '"hooks":{"PreToolUse":[{"matcher":"*","hooks":[' + owner + ']}]}' + suffix
        self.assertEqual(settings.read_bytes(), expected.encode())
        self.assertFalse(script.exists())

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_only_retired_hooks_remove_settings_through_delivery(self):
        # Prediction: the templer-landing shape (12 Jarvis-only events), and the retired Stop-only
        # shape, delete settings through the existing settings-entry item and PR route. Both the
        # merged tree and caller lose the file; the caller reaches main with a clean checkout.
        self.ai_os_package()
        for generation in ("jarvis", "stop"):
            with self.subTest(generation=generation):
                repo = self.repo("only-hooks-" + generation)
                script, settings, _ = self.ai_os_install(repo)
                hooks = {event: [{"matcher": "*", "hooks": [self.ai_hook]}] for event in self.ai_events}
                if generation == "stop":
                    hooks = {"Stop": [{"hooks": [{"type": "command", "command":
                        'python3 "$CLAUDE_PROJECT_DIR/.claude/skills/_shared/resolve-stop-hook.py"'}]}]}
                settings.write_bytes(('\ufeff \r\n' + json.dumps({"hooks": hooks}, indent=2) + '\r\n ').encode())
                self.run_ok(["git", "add", "."], cwd=repo)
                self.run_ok(["git", "commit", "-qm", "only retired hooks"], cwd=repo)
                bare = self.fake_github(repo)
                plan, file = self.plan("--project", repo)
                [item] = [i for i in plan["scopes"][0]["items"] if i["kind"] == "settings-entry"]
                self.assertEqual((item["action"], item["route"]), ("edit", "delivery"))
                self.assertEqual(item["before"]["sha256"], hashlib.sha256(settings.read_bytes()).hexdigest())
                result = self.apply(plan, file)
                self.assertEqual(result["state"], "succeeded", result)
                self.assertEqual(result["scopes"][0]["delivery"]["state"], "merged", result)
                self.assertTrue(json.loads((self.root / "gh.json").read_text())["prs"])
                self.assertFalse(settings.exists())
                self.assertFalse(script.exists())
                listed = self.run_ok(["git", "--git-dir", bare, "ls-tree", "-r", "--name-only", "main"]).stdout.splitlines()
                self.assertNotIn(".claude/settings.json", listed)
                self.assertEqual(self.run_ok(["git", "rev-parse", "HEAD"], cwd=repo).stdout,
                                 self.run_ok(["git", "--git-dir", bare, "rev-parse", "main"]).stdout)
                self.assertEqual(self.run_ok(["git", "status", "--porcelain"], cwd=repo).stdout, "")

    def test_emptied_settings_keys_preserve_surrounding_owner_bytes(self):
        # Prediction: first/middle/last event keys emptied by either hook generation disappear;
        # owner hooks, empty events, BOM, CRLF, duplicate keys, escapes and large numbers retain bytes.
        # When only hooks is emptied, its first/middle/last property disappears with its comma.
        self.ai_os_package()
        for generation in ("jarvis", "stop"):
            entry = json.dumps({"matcher": "*", "hooks": [self.ai_hook]} if generation == "jarvis" else
                {"hooks": [{"type": "command", "command":
                    'python3 "$CLAUDE_PROJECT_DIR/.claude/skills/_shared/resolve-stop-hook.py"'}]})
            for position in range(3):
                for owner_events in (False, True):
                    with self.subTest(generation=generation, position=position, owner_events=owner_events):
                        repo = self.repo(f"keys-{generation}-{position}-{owner_events}")
                        script, settings, _ = self.ai_os_install(repo)
                        owner = '"OwnerEvent" : [{"hooks":[{"type":"command", "command":"echo owner"}]}]'
                        events = [owner, '"EmptyEvent" : [ ]'] if owner_events else []
                        events.insert(position, '"Stop" : [' + entry + ']')
                        owned = ['"duplicate":9007199254740993', '"duplicate":"\\u0061"']
                        original = owned.copy()
                        original.insert(position, '"hooks" : {' + ',\r\n'.join(events) + '}')
                        if owner_events:
                            owned.insert(position, '"hooks" : {' + owner + ',\r\n"EmptyEvent" : [ ]}')
                        before = '\ufeff{\r\n' + ',\r\n'.join(original) + '\r\n}\r\n'
                        expected = '\ufeff{\r\n' + ',\r\n'.join(owned) + '\r\n}\r\n'
                        settings.write_bytes(before.encode())
                        plan, file = self.plan("--project", repo)
                        self.assertEqual(self.apply(plan, file)["state"], "succeeded")
                        self.assertEqual(settings.read_bytes(), expected.encode())
                        self.assertFalse(script.exists())

    def test_preexisting_empty_settings_containers_stay(self):
        # Prediction: owner-created empty document/hooks/event containers are unchanged, even when
        # the unreferenced Jarvis script is removed. An empty event beside a removed event stays.
        self.ai_os_package()
        entry = json.dumps({"matcher": "*", "hooks": [self.ai_hook]})
        for index, (before, after) in enumerate([
            ('\ufeff { }\r\n', '\ufeff { }\r\n'),
            ('{ "hooks" : { } }\n', '{ "hooks" : { } }\n'),
            ('{ "hooks" : { "Stop" : [ ] } }', '{ "hooks" : { "Stop" : [ ] } }'),
            ('{ "hooks" : { "Stop" : [ ], "PreToolUse":[' + entry + '] } }',
             '{ "hooks" : { "Stop" : [ ] } }'),
        ]):
            with self.subTest(index=index):
                repo = self.repo(f"owner-empty-{index}")
                script, settings, _ = self.ai_os_install(repo)
                settings.write_bytes(before.encode())
                plan, file = self.plan("--project", repo)
                self.assertEqual(self.apply(plan, file)["state"], "succeeded")
                self.assertEqual(settings.read_bytes(), after.encode())
                self.assertFalse(script.exists())

    def test_settings_deletion_binds_preimage_and_restores_script_on_failure(self):
        # Prediction: a stale preimage or filesystem deletion failure keeps both files intact;
        # an unchanged review removes both locally. No temporary staged scripts survive failure.
        self.ai_os_package()
        for variant in ("stale", "failure", "success"):
            with self.subTest(variant=variant):
                repo = self.repo("delete-settings-" + variant)
                script, settings, _ = self.ai_os_install(repo)
                settings.write_text(json.dumps({"hooks": {"Stop": [{"matcher": "*", "hooks": [self.ai_hook]}]}}))
                plan, file = self.plan("--project", repo)
                if variant == "stale":
                    settings.write_text(settings.read_text() + "\n")
                before = settings.read_bytes()
                if variant == "failure":
                    preload = self.root / "fail-settings-delete.cjs"
                    preload.write_text("const fs = require('fs'); const unlink = fs.unlinkSync;\n"
                        "fs.unlinkSync = (file) => {\n"
                        f"if (file === {json.dumps(str(settings))}) throw new Error('fixture settings unlink failure');\n"
                        "return unlink(file); };\n")
                    self.env["NODE_OPTIONS"] = "--require " + json.dumps(str(preload), ensure_ascii=False)
                result = self.apply(plan, file)
                self.env.pop("NODE_OPTIONS", None)
                self.assertEqual(result["state"], "succeeded" if variant == "success" else "failed", result)
                if variant == "success":
                    self.assertFalse(settings.exists())
                    self.assertFalse(script.exists())
                else:
                    self.assertEqual(settings.read_bytes(), before)
                    self.assertEqual(script.read_bytes(), self.ai_script)
                    self.assertEqual(list(script.parent.glob("*.tmp")), [])
                    if variant == "failure":
                        self.assertIn("fixture settings unlink failure", result["scopes"][0]["error"]["params"]["detail"])

    def test_ai_os_legacy_hook_generations_share_one_settings_edit(self):
        # Prediction: shell, HTTP mjs and file mjs generations can coexist; all proven scripts and
        # their settings are removed together, including first/middle/last array deletions.
        history = self.ai_os_package()
        repo = self.repo("ai-os-generations")
        script, settings, _ = self.ai_os_install(repo)
        scripts = [script]
        hooks = [self.ai_hook]
        for name, command in (("post-to-jarvis.sh", "./.claude/hooks/post-to-jarvis.sh"),
                              ("post-to-jarvis.mjs", "node .claude/hooks/post-to-jarvis.mjs")):
            file = script.with_name(name)
            file.write_bytes(self.ai_script)
            hook = {"type": "command", "command": command, "timeout": 10}
            history["hooks"][str(file.relative_to(repo)).replace(os.sep, "/")] = {
                "hashes": [hashlib.sha256(self.ai_script).hexdigest()],
                "entries": [hashlib.sha256(json.dumps(["PostToolUse", "*", hook], sort_keys=True,
                            separators=(",", ":")).encode()).hexdigest()]}
            scripts.append(file)
            hooks.append(hook)
        (self.cli_path.parent / "cleanup-history.json").write_text(json.dumps(history))
        owner = {"type": "command", "command": "echo owner"}
        settings.write_text(json.dumps({"hooks": {"PostToolUse": [{"matcher": "*", "hooks": [hooks[0], owner, *hooks[1:]]}]}}))
        plan, file = self.plan("--project", repo)
        self.assertEqual(sum(i["kind"] == "legacy-hook" and i["action"] == "remove" for i in plan["scopes"][0]["items"]), 3)
        self.assertEqual(self.apply(plan, file)["state"], "succeeded")
        self.assertTrue(all(not p.exists() for p in scripts))
        self.assertEqual(json.loads(settings.read_text()), {"hooks": {"PostToolUse": [{"matcher": "*", "hooks": [owner]}]}})

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_ai_os_tracked_hook_and_commands_use_delivery(self):
        # Prediction: tracked AI OS commands and hook/settings travel in one PR; its merge removes
        # the script and references together and keeps unrelated settings in the reconciled checkout.
        self.ai_os_package()
        repo = self.repo("ai-os-delivery")
        script, settings, _ = self.ai_os_install(repo)
        commands = repo / ".agent/workflows"
        commands.mkdir(parents=True)
        command = commands / "devlyn.fixture.md"
        command.write_bytes(self.ai_command)
        self.run_ok(["git", "add", "."], cwd=repo)
        self.run_ok(["git", "commit", "-qm", "legacy AI OS"], cwd=repo)
        self.fake_github(repo)
        plan, file = self.plan("--project", repo)
        self.assertTrue(all(i["route"] == "delivery" for i in plan["scopes"][0]["items"]))
        result = self.apply(plan, file)
        self.assertEqual(result["scopes"][0]["delivery"]["state"], "merged", result)
        self.assertFalse(script.exists())
        self.assertFalse(command.exists())
        self.assertNotIn(script.name, settings.read_text())
        self.assertEqual(json.loads(settings.read_text())["env"], {"OWNER": "kept ✓"})

    def test_machine_copies_go_and_the_owner_skill_and_an_edited_copy_stay(self):
        # Prediction: a global install's three roots list devlyn-ideate, devlyn-engines, _shared and the marker; an owner
        # skill is not listed; an edited devlyn-ideate in one root is kept with its marker. Apply removes the rest and
        # the roots it emptied; the owner skill keeps its bytes.
        self.install(self.root, "--global", "--claude")
        own = self.home / ".claude/skills/my-skill"
        own.mkdir()
        (own / "SKILL.md").write_text("---\nname: my-skill\ndescription: mine\n---\nMine.\n", encoding="utf-8")
        edited = self.home / ".codex/skills/devlyn-ideate/SKILL.md"
        edited.write_text(edited.read_text(encoding="utf-8") + "\nMy own note.\n", encoding="utf-8")
        plan, path = self.plan("--machine")
        [machine] = plan["scopes"]
        items = self.actions(machine)
        self.assertNotIn("my-skill", [item[2] for item in items])
        self.assertIn(("core-skill", "skip", "devlyn-ideate", "local", "modified-copy"), items)
        markers = [item for item in machine["items"] if item["kind"] == "install-marker"]
        self.assertEqual(sorted(Path(item["path"]).parent.parent.name for item in markers), [".agents", ".claude"])
        result = self.apply(plan, path)
        self.assertEqual(result["state"], "succeeded")
        self.assertFalse((self.home / ".agents/skills").exists())
        self.assertFalse((self.home / ".claude/skills/devlyn-ideate").exists())
        self.assertTrue((own / "SKILL.md").read_text(encoding="utf-8").endswith("Mine.\n"))
        self.assertTrue(edited.exists())
        self.assertTrue((self.home / ".codex/skills/.devlyn-install.json").exists())
        # A second plan finds only what was kept on purpose.
        again, _ = self.plan("--machine")
        self.assertEqual([item["action"] for item in again["scopes"][0]["items"]], ["skip"])

    def test_project_copies_not_in_git_go_in_place_and_principles_stay(self):
        # Prediction: an uncommitted project install is local: its skill copies and markers go in place; the current
        # managed blocks in AGENTS.md and CLAUDE.md are not items and keep every byte, owner text included.
        repo = self.repo("plain")
        (repo / "AGENTS.md").write_text("# Team rules\n\nAlways write tests.\n", encoding="utf-8")
        self.install(repo, "--claude")
        before = {name: (repo / name).read_bytes() for name in ("AGENTS.md", "CLAUDE.md")}
        plan, path = self.plan("--project", repo)
        [project] = plan["scopes"]
        self.assertTrue(all(item["route"] == "local" for item in project["items"]))
        self.assertEqual({item["kind"] for item in project["items"]}, {"core-skill", "install-marker"})
        self.assertEqual(self.apply(plan, path)["state"], "succeeded")
        self.assertFalse((repo / ".agents/skills").exists())
        self.assertFalse((repo / ".claude/skills").exists())
        self.assertEqual({name: (repo / name).read_bytes() for name in before}, before)

    def test_source_repository_and_linked_roots_are_left_as_they_are(self):
        # Prediction: the devlyn-cli source checkout is skipped whole; a skill root that is a link is skipped with its
        # reason, and nothing behind the link is read as owned.
        source = self.repo("source")
        (source / "bin").mkdir()
        (source / "bin/devlyn.js").write_text("// cli\n", encoding="utf-8")
        (source / "package.json").write_text(json.dumps({"name": "devlyn-cli"}), encoding="utf-8")
        self.run_ok(["git", "add", "."], cwd=source)
        self.run_ok(["git", "commit", "-qm", "source"], cwd=source)
        linked = self.repo("linked")
        shared = self.root / "shared-skills"
        (shared / "devlyn-ideate").mkdir(parents=True)
        (linked / ".claude").mkdir()
        os.symlink(shared, linked / ".claude/skills", target_is_directory=True)
        plan, _ = self.plan("--project", source, "--project", linked)
        reasons = {scope["name"]: [(item["action"], item["reasons"][0]["code"]) for item in scope["items"]] for scope in plan["scopes"]}
        self.assertEqual(reasons, {"source": [("skip", "source-repository")], "linked": [("skip", "outside-link")]})

    @unittest.skipIf(os.name == "nt", "skill-root symlinks require POSIX")
    def test_local_linked_roots_keep_their_empty_target(self):
        # Prediction: two roots sharing a real target remove its copies once locally and keep both links
        # and the empty directory, even when the real root is itself a conventional agent skill root.
        for target in ("skills", ".agents/skills"):
            with self.subTest(target=target):
                repo = self.repo("local-linked-" + target.replace("/", "-"))
                self.install(repo, "--claude")
                if target == "skills":
                    (repo / ".agents/skills").rename(repo / target)
                    (repo / ".agents/skills").symlink_to("../skills", target_is_directory=True)
                shutil.rmtree(repo / ".claude/skills")
                (repo / ".claude/skills").symlink_to("../" + target, target_is_directory=True)
                plan, path = self.plan("--project", repo)
                self.assertEqual(len(plan["scopes"][0]["items"]), 4)
                self.assertTrue(all(i["action"] == "remove" and i["route"] == "local"
                                    and i["relative"].startswith(target + "/") for i in plan["scopes"][0]["items"]))
                self.assertEqual(self.apply(plan, path)["state"], "succeeded")
                self.assertEqual(list((repo / target).iterdir()), [])
                self.assertTrue((repo / ".claude/skills").is_symlink())
                if target == "skills":
                    self.assertTrue((repo / ".agents/skills").is_symlink())

    @unittest.skipIf(os.name == "nt", "skill-root symlinks require POSIX")
    def test_machine_linked_roots_are_deduplicated_within_their_base(self):
        # Prediction: a machine root and its alias are planned once at the real path; account links
        # are bounded by their paired base, and empty targets still named by links stay.
        self.install(self.root, "--global")
        shutil.rmtree(self.home / ".codex/skills")
        (self.home / ".codex/skills").symlink_to("../.agents/skills", target_is_directory=True)
        accounts = self.root / "accounts"
        account = accounts / "one"
        account.mkdir(parents=True)
        shutil.copytree(self.home / ".agents/skills", accounts / "shared")
        (account / "skills").symlink_to("../shared", target_is_directory=True)
        plan, path = self.plan("--machine", "--account-home", account)
        items = plan["scopes"][0]["items"]
        self.assertEqual(len(items), 8)
        self.assertEqual(len({i["path"] for i in items}), 8)
        self.assertTrue(all(i["action"] == "remove" for i in items))
        self.assertEqual(self.apply(plan, path)["state"], "succeeded")
        self.assertEqual(list((self.home / ".agents/skills").iterdir()), [])
        self.assertEqual(list((accounts / "shared").iterdir()), [])
        self.assertTrue((account / "skills").is_symlink())
        self.assertTrue((self.home / ".codex/skills").is_symlink())

    @unittest.skipIf(os.name == "nt", "skill-root symlinks require POSIX")
    def test_root_deduplication_uses_resolved_spelling(self):
        # Prediction: a real root and its link resolve to one canonical directory even when its
        # stored case differs from the configured path on a case-insensitive filesystem.
        repo = self.repo("linked-case")
        self.install(repo)
        if not (repo / ".AGENTS/skills").is_dir():
            self.skipTest("case-insensitive filesystem required")
        (repo / ".agents/skills").rename(repo / ".agents/moving")
        (repo / ".agents/moving").rename(repo / ".agents/SKILLS")
        (repo / ".claude").mkdir()
        (repo / ".claude/skills").symlink_to("../.agents/SKILLS", target_is_directory=True)
        plan, path = self.plan("--project", repo)
        self.assertEqual(len(plan["scopes"][0]["items"]), 4)
        self.assertTrue(all(i["relative"].startswith(".agents/SKILLS/") for i in plan["scopes"][0]["items"]))
        self.assertEqual(self.apply(plan, path)["state"], "succeeded")
        self.assertEqual(list((repo / ".agents/SKILLS").iterdir()), [])

    @unittest.skipIf(os.name == "nt", "skill-root symlinks require POSIX")
    def test_roots_reached_through_another_link_stay_outside_link(self):
        # Prediction: a link to a link, a linked parent, and a link hidden by `..` are all refused,
        # even when their eventual directory is inside the project.
        repo = self.repo("indirect-links")
        self.install(repo)
        (repo / ".agents/skills").rename(repo / "skills")
        (repo / "alias").symlink_to("skills", target_is_directory=True)
        (repo / "parent").mkdir()
        (repo / "parent/alias").symlink_to("../skills", target_is_directory=True)
        for target in ("../alias", "../alias/../skills", "../parent/alias"):
            with self.subTest(target=target):
                link = repo / ".agents/skills"
                link.symlink_to(target, target_is_directory=True)
                plan, _ = self.plan("--project", repo)
                self.assertEqual([(i["action"], i["reasons"][0]["code"]) for i in plan["scopes"][0]["items"]],
                                 [("skip", "outside-link")])
                link.unlink()

    def test_included_local_modified_copies_leave_support_for_a_later_plan(self):
        # Prediction: repeatable --include removes only the chosen modified copies; their kept support
        # stays byte-identical this run and is offered by the next plan.
        repo = self.repo("chosen-local")
        self.install(repo)
        root = repo / ".agents/skills"
        edited = root / "devlyn-ideate/SKILL.md"
        edited.write_text(edited.read_text() + "\nOwner note.\n")
        standard = root / "workflow-routing"
        standard.mkdir()
        (standard / "SKILL.md").write_text("Owner's edited workflow.\n")
        marker = (root / ".devlyn-install.json").read_bytes()
        plan, path = self.plan("--project", repo)
        chosen = [i["id"] for i in plan["scopes"][0]["items"] if i["reasons"] == [{"code": "modified-copy", "params": {}}]]
        self.assertEqual(len(chosen), 2)
        self.assertEqual(self.apply(plan, path, include=chosen)["state"], "succeeded")
        self.assertEqual(sorted(p.name for p in root.iterdir()), [".devlyn-install.json", "_shared"])
        self.assertEqual((root / ".devlyn-install.json").read_bytes(), marker)
        later, _ = self.plan("--project", repo)
        self.assertEqual({Path(i["path"]).name for i in later["scopes"][0]["items"] if i["action"] == "remove"},
                         {"_shared", ".devlyn-install.json"})

    def test_included_copy_changed_after_review_is_refused(self):
        # Prediction: an included modified copy whose bytes changed after review is stale, even though
        # it is still modified-copy; no copy or support is removed.
        repo = self.repo("chosen-stale")
        self.install(repo)
        root = repo / ".agents/skills"
        shutil.rmtree(root / "devlyn-engines")
        edited = root / "devlyn-ideate/SKILL.md"
        edited.write_text(edited.read_text() + "\nOwner note.\n")
        plan, path = self.plan("--project", repo)
        [item] = plan["scopes"][0]["items"]
        edited.write_text(edited.read_text() + "\nAnother edit.\n")
        before = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
        result = self.apply(plan, path, include=[item["id"]])
        self.assertEqual(result["scopes"][0]["error"]["code"], "stale-plan")
        self.assertEqual({p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}, before)

    def test_invalid_included_ids_refuse_the_whole_command(self):
        # Prediction: unknown ids, remove actions, other skip reasons and modified support fail exit 2
        # before any change, including a valid include earlier in the same command.
        repo = self.repo("chosen-invalid")
        self.install(repo, "--claude")
        root = repo / ".agents/skills"
        edited = root / "devlyn-ideate/SKILL.md"
        edited.write_text(edited.read_text() + "\nOwner note.\n")
        marker = repo / ".claude/skills/.devlyn-install.json"
        marker.write_text(marker.read_text() + " ")
        optional = root / "devlyn\uf03apencil-pull"
        optional.mkdir()
        (optional / "SKILL.md").write_text("Optional.\n")
        plan, path = self.plan("--project", repo)
        items = plan["scopes"][0]["items"]
        chosen = next(i["id"] for i in items if i["path"] == str(edited.parent))
        invalid = ["missing", next(i["id"] for i in items if i["action"] == "remove"),
                   next(i["id"] for i in items if i["path"] == str(optional)),
                   next(i["id"] for i in items if i["path"] == str(marker))]
        before = {p.relative_to(repo): p.read_bytes() for p in repo.rglob("*") if p.is_file()}
        for item_id in invalid:
            with self.subTest(item_id=item_id):
                self.assertEqual(self.apply(plan, path, code=2, include=[chosen, item_id])["code"], "invalid-arguments")
                self.assertEqual({p.relative_to(repo): p.read_bytes() for p in repo.rglob("*") if p.is_file()}, before)

    @unittest.skipIf(os.name == "nt", "interior symlinks require POSIX")
    def test_included_copy_without_a_readable_preimage_stays(self):
        # Prediction: a modified copy with an interior link has no usable fingerprint; two null hashes
        # cannot prove unchanged bytes, so the plan exposes outside-link and --include is invalid.
        repo = self.repo("chosen-null-proof")
        self.install(repo)
        root = repo / ".agents/skills"
        shutil.rmtree(root / "devlyn-engines")
        skill = root / "devlyn-ideate"
        (skill / "link").symlink_to("SKILL.md")
        plan, path = self.plan("--project", repo)
        [item] = plan["scopes"][0]["items"]
        self.assertIsNone(item["before"]["sha256"])
        (skill / "SKILL.md").write_text("Changed after review.\n")
        self.assertEqual(item["reasons"][0]["code"], "outside-link")
        result = self.apply(plan, path, code=2, include=[item["id"]])
        self.assertEqual(result["code"], "invalid-arguments")
        self.assertEqual((skill / "SKILL.md").read_text(), "Changed after review.\n")
        self.assertTrue((skill / "link").is_symlink())

    def test_included_copy_proof_does_not_normalize_owner_bytes(self):
        # Prediction: include proofs cover exact owner bytes, including line endings and generated
        # metadata that installer ownership deliberately normalizes or ignores.
        repo = self.repo("chosen-exact-proof")
        self.install(repo)
        root = repo / ".agents/skills"
        shutil.rmtree(root / "devlyn-engines")
        skill = root / "devlyn-ideate"
        edited = skill / "SKILL.md"
        edited.write_bytes(edited.read_bytes() + b"\nOwner note.\n")
        for change in ("line-endings", "metadata"):
            with self.subTest(change=change):
                plan, path = self.plan("--project", repo)
                [item] = plan["scopes"][0]["items"]
                if change == "line-endings":
                    edited.write_bytes(edited.read_bytes().replace(b"\n", b"\r\n"))
                else:
                    (skill / ".DS_Store").write_bytes(b"changed metadata")
                result = self.apply(plan, path, include=[item["id"]])
                self.assertEqual(result["scopes"][0]["error"]["code"], "stale-plan")
                self.assertTrue(edited.exists())

    @unittest.skipIf(os.name == "nt", "process-list fixture and skill-root links require POSIX")
    def test_running_copies_are_kept_through_aliases_and_include(self):
        # Prediction: a process naming either the original skill-root alias or a chosen modified copy
        # keeps that copy; inclusion cannot bypass a running process or an occupied install lock.
        repo = self.repo("running-linked")
        self.install(repo)
        (repo / ".agents/skills").rename(repo / "skills")
        (repo / ".agents/skills").symlink_to("../skills", target_is_directory=True)
        self.env["FIXTURE_PROCESSES"] = f"python {repo}/.agents/skills/devlyn-ideate/scripts/queue.py drain"
        plan, path = self.plan("--project", repo)
        self.assertTrue(all(i["reasons"] == [{"code": "in-use", "params": {}}] for i in plan["scopes"][0]["items"]))
        self.assertEqual(self.apply(plan, path)["state"], "succeeded")
        edited = repo / "skills/devlyn-ideate/SKILL.md"
        edited.write_text(edited.read_text() + "\nOwner note.\n")
        for blocker in ("process", "lock"):
            with self.subTest(blocker=blocker):
                if blocker == "lock":
                    self.env.pop("FIXTURE_PROCESSES")
                    (repo / "skills/.devlyn-install.lock").write_text("occupied")
                plan, path = self.plan("--project", repo)
                chosen = next(i for i in plan["scopes"][0]["items"] if i["path"] == str(edited.parent))
                self.assertEqual(chosen["reasons"][0]["code"], "in-use" if blocker == "process" else "occupied-lock")
                result = self.apply(plan, path, code=2, include=[chosen["id"]])
                self.assertEqual(result["code"], "invalid-arguments")
                self.assertTrue(edited.exists())

    @unittest.skipIf(os.name == "nt", "skill-root symlinks require POSIX")
    def test_a_linked_target_inside_a_copy_is_never_removed(self):
        # Prediction: a recognized copy that is itself a linked skill root (or contains one) stays;
        # deleting an ancestor must never remove a directory another configured root names.
        repo = self.repo("overlapping-linked")
        self.install(repo)
        (repo / ".claude").mkdir()
        for target in ("devlyn-ideate", "devlyn-ideate/scripts"):
            with self.subTest(target=target):
                link = repo / ".claude/skills"
                link.symlink_to("../.agents/skills/" + target, target_is_directory=True)
                plan, path = self.plan("--project", repo)
                self.assertEqual(self.apply(plan, path)["state"], "succeeded")
                self.assertTrue(link.is_dir())
                self.assertTrue((repo / ".agents/skills/devlyn-ideate/SKILL.md").exists())
                link.unlink()

    def test_a_plan_cannot_embed_include_authorization(self):
        # Prediction: even a correctly digested plan with duplicate ids cannot smuggle the internal
        # include choice into an apply without --include; the edited copy stays.
        repo = self.repo("forged-include")
        self.install(repo)
        edited = repo / ".agents/skills/devlyn-ideate/SKILL.md"
        edited.write_text(edited.read_text() + "\nOwner note.\n")
        plan, path = self.plan("--project", repo)
        items = plan["scopes"][0]["items"]
        item = next(i for i in items if i["path"] == str(edited.parent))
        items.append(dict(item))
        item["included"] = True
        del plan["digest"]
        plan["digest"] = hashlib.sha256(json.dumps(plan, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
        path.write_text(json.dumps(plan))
        self.assertEqual(self.apply(plan, path)["state"], "succeeded")
        self.assertTrue(edited.read_text().endswith("Owner note.\n"))

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_included_tracked_modified_copy_is_delivered_with_support_kept(self):
        # Prediction: an explicitly chosen tracked modified standard is removed through one merged PR;
        # the support it kept out of the review remains both upstream and in the checkout.
        repo = self.repo("chosen-delivery")
        self.install(repo)
        root = repo / ".agents/skills"
        standard = root / "workflow-routing"
        standard.mkdir()
        (standard / "SKILL.md").write_text("Owner's edited workflow.\n")
        self.run_ok(["git", "add", "-A"], cwd=repo)
        self.run_ok(["git", "commit", "-qm", "edited install"], cwd=repo)
        bare = self.fake_github(repo)
        plan, path = self.plan("--project", repo)
        chosen = next(i for i in plan["scopes"][0]["items"] if i["path"] == str(standard))
        self.assertEqual((chosen["action"], chosen["route"]), ("skip", "delivery"))
        result = self.apply(plan, path, include=[chosen["id"]])
        self.assertEqual((result["state"], result["scopes"][0]["delivery"]["state"]), ("succeeded", "merged"))
        self.assertEqual(sorted(p.name for p in root.iterdir()), [".devlyn-install.json", "_shared"])
        listed = self.run_ok(["git", "--git-dir", bare, "ls-tree", "-r", "--name-only", "main"]).stdout
        self.assertNotIn("workflow-routing", listed)
        self.assertIn(".agents/skills/.devlyn-install.json", listed)

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_included_copy_changed_on_the_base_refuses_delivery(self):
        # Prediction: even another modified-copy on the base fails the reviewed preimage; the whole
        # delivery is refused before deletion or PR; only the next plan takes those upstream bytes.
        repo = self.repo("chosen-base-stale")
        self.install(repo)
        edited = repo / ".agents/skills/devlyn-ideate/SKILL.md"
        edited.write_text(edited.read_text() + "\nOwner note.\n")
        self.run_ok(["git", "add", "-A"], cwd=repo)
        self.run_ok(["git", "commit", "-qm", "edited install"], cwd=repo)
        bare = self.fake_github(repo)
        plan, path = self.plan("--project", repo)
        chosen = next(i for i in plan["scopes"][0]["items"] if i["path"] == str(edited.parent))
        upstream = self.root / "changed-base"
        self.run_ok(["git", "clone", "-q", bare, upstream])
        (upstream / chosen["relative"] / "SKILL.md").write_text("Another owner's edit.\n")
        self.run_ok(["git", "commit", "-qam", "edit again"], cwd=upstream)
        self.run_ok(["git", "push", "-q", "origin", "main"], cwd=upstream)
        result = self.apply(plan, path, include=[chosen["id"]])
        self.assertEqual(result["scopes"][0]["error"]["code"], "stale-plan")
        self.assertTrue(edited.read_text().endswith("Owner note.\n"))
        self.plan("--project", repo)
        self.assertEqual(edited.read_text(), "Another owner's edit.\n")
        self.assertTrue((edited.parent.parent / "devlyn-engines").is_dir())
        self.assertEqual(self.run_ok(["git", "branch", "--list", "devlyn/cleanup-*"], cwd=repo).stdout, "")

    def test_include_keeps_dependent_local_support_and_refuses_no_remote(self):
        # Prediction: local support retained for a tracked copy remains dependent-copy when that
        # modified copy is skipped; without a remote the plan exposes no-remote and cannot offer include.
        repo = self.repo("chosen-no-remote")
        self.install(repo)
        root = repo / ".agents/skills"
        self.run_ok(["git", "add", ".agents/skills/devlyn-ideate"], cwd=repo)
        self.run_ok(["git", "commit", "-qm", "tracked copy"], cwd=repo)
        plan, path = self.plan("--project", repo)
        support = [i for i in plan["scopes"][0]["items"] if Path(i["path"]).name in ("_shared", ".devlyn-install.json")]
        self.assertEqual(len(support), 2)
        self.assertTrue(all(i["reasons"] == [{"code": "dependent-copy", "params": {}}] for i in support))
        for item in support:
            self.assertEqual(self.apply(plan, path, code=2, include=[item["id"]])["code"], "invalid-arguments")
        shutil.rmtree(root / "devlyn-engines")
        edited = root / "devlyn-ideate/SKILL.md"
        edited.write_text(edited.read_text() + "\nOwner note.\n")
        plan, path = self.plan("--project", repo)
        [chosen] = plan["scopes"][0]["items"]
        self.assertEqual(chosen["reasons"][0]["code"], "no-remote")
        result = self.apply(plan, path, code=2, include=[chosen["id"]])
        self.assertEqual(result["code"], "invalid-arguments")
        self.assertTrue(edited.exists())
        self.assertTrue((root / "_shared").is_dir())
        self.assertTrue((root / ".devlyn-install.json").is_file())

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_included_copy_already_removed_on_the_base_is_settled(self):
        # Prediction: a reviewed modified copy already removed upstream is settled under --include;
        # main takes the base without a new PR, and the support omitted from the review stays.
        repo = self.repo("chosen-settled")
        self.install(repo)
        edited = repo / ".agents/skills/devlyn-ideate/SKILL.md"
        edited.write_text(edited.read_text() + "\nOwner note.\n")
        self.run_ok(["git", "add", "-A"], cwd=repo)
        self.run_ok(["git", "commit", "-qm", "edited install"], cwd=repo)
        bare = self.fake_github(repo)
        plan, path = self.plan("--project", repo)
        chosen = next(i for i in plan["scopes"][0]["items"] if i["path"] == str(edited.parent))
        removed = json.loads(json.dumps(plan))
        for item in removed["scopes"][0]["items"]:
            if item["id"] == chosen["id"]:
                item["action"] = "remove"
        self.removed_upstream(repo, bare, removed)
        result = self.apply(plan, path, include=[chosen["id"]])
        self.assertEqual(result["state"], "succeeded")
        self.assertIsNone(result["scopes"][0]["delivery"])
        self.assertFalse(edited.exists())
        self.assertTrue((edited.parent.parent / "_shared").is_dir())
        self.assertTrue((edited.parent.parent / ".devlyn-install.json").is_file())
        self.assertEqual(self.run_ok(["git", "branch", "--list", "devlyn/cleanup-*"], cwd=repo).stdout, "")

    def test_tracked_copies_without_a_github_remote_are_not_touched(self):
        # Prediction: committed copies route through delivery; without a GitHub origin they are skipped as no-remote.
        repo = self.repo("tracked")
        self.install(repo)
        self.run_ok(["git", "add", "-A"], cwd=repo)
        self.run_ok(["git", "commit", "-qm", "install"], cwd=repo)
        plan, _ = self.plan("--project", repo)
        codes = {(item["route"], item["action"], (item["reasons"] or [{}])[0].get("code")) for item in plan["scopes"][0]["items"]}
        self.assertEqual(codes, {("delivery", "skip", "no-remote")})

    def test_a_changed_or_forged_plan_is_refused(self):
        # Prediction: a digest that does not match the plan file exits 3 (stale-plan) with nothing removed; an item that
        # changed after review is reported stale and kept.
        self.install(self.root, "--global")
        plan, path = self.plan("--machine")
        forged = self.cli("cleanup", "--apply", "--plan-file", path, "--digest", "0" * 64, code=3)
        self.assertEqual(forged["code"], "stale-plan")
        self.assertTrue((self.home / ".agents/skills/devlyn-ideate").exists())
        (self.home / ".agents/skills/devlyn-ideate/SKILL.md").write_text("changed\n", encoding="utf-8")
        result = self.apply(plan, path)
        self.assertEqual(result["state"], "failed")
        self.assertEqual(result["scopes"][0]["error"]["code"], "stale-plan")
        self.assertTrue((self.home / ".agents/skills/devlyn-ideate").exists())

    def test_a_forged_plan_cannot_widen_what_is_removed(self):
        # Prediction (review HIGH): a hand-written plan naming an unproven folder with a valid digest removes nothing:
        # apply plans again from disk and acts only on items both plans name the same way.
        victim = self.root / "victim/precious"
        victim.mkdir(parents=True)
        (victim / "notes.txt").write_text("keep\n", encoding="utf-8")
        plan = {"schemaVersion": 1, "version": json.loads((ROOT / "package.json").read_text())["version"],
                "inputs": {"machine": True, "projects": [], "accountHomes": []},
                "scopes": [{"id": "machine", "kind": "machine", "root": "/", "name": None, "remote": None, "items": [
                    {"id": "machine:0", "kind": "retired-skill", "path": str(victim), "base": "/", "relative": None,
                     "route": "local", "action": "remove", "reasons": [],
                     "before": {"type": "directory", "sha256": None}}]}]}
        node = ("const p=JSON.parse(require('fs').readFileSync(0,'utf8'));const c=(v)=>Array.isArray(v)?`[${v.map(c).join(',')}]`"
                ":v&&typeof v==='object'?`{${Object.keys(v).sort().map(k=>`${JSON.stringify(k)}:${c(v[k])}`).join(',')}}`:JSON.stringify(v);"
                "console.log(require('crypto').createHash('sha256').update(c(p)).digest('hex'))")
        plan["scopes"][0]["items"][0]["before"]["sha256"] = self.run_ok(
            ["node", "-e", "const {fingerprint}=require(process.argv[1]);console.log(fingerprint(process.argv[2]))",
             ROOT / "bin/skill-ownership.js", victim]).stdout.strip()
        plan["digest"] = subprocess.run(["node", "-e", node], input=json.dumps(plan), capture_output=True, text=True).stdout.strip()
        path = self.root / "forged.json"
        path.write_text(json.dumps(plan), encoding="utf-8")
        result = self.apply(plan, path)
        self.assertEqual(result["scopes"][0]["error"]["code"], "stale-plan")
        self.assertTrue((victim / "notes.txt").exists())

    def test_support_stays_with_a_kept_copy_and_optional_old_names_stay(self):
        # Prediction (review MEDIUM): beside an edited devlyn-ideate, _shared and the marker are not listed; an optional
        # skill under its pre-4.0 colon name is kept as optional-skill, while a core one is removed.
        self.install(self.root, "--global")
        root = self.home / ".agents/skills"
        edited = root / "devlyn-ideate/SKILL.md"
        edited.write_text(edited.read_text(encoding="utf-8") + "\nMine.\n", encoding="utf-8")
        for name in ("devlyn:pencil-pull", "devlyn:ideate"):
            (root / name).mkdir()
            (root / name / "SKILL.md").write_text("old\n", encoding="utf-8")
        self.historical_skill(root / "devlyn:ideate")
        plan, _ = self.plan("--machine")
        listed = {(Path(item["path"]).name, item["action"], (item["reasons"] or [{}])[0].get("code"))
                  for item in plan["scopes"][0]["items"] if Path(item["path"]).parent == root}
        self.assertIn(("devlyn-ideate", "skip", "modified-copy"), listed)
        self.assertIn(("devlyn:pencil-pull", "skip", "optional-skill"), listed)
        self.assertIn(("devlyn:ideate", "remove", None), listed)
        self.assertNotIn("_shared", {name for name, _, _ in listed})
        self.assertNotIn(".devlyn-install.json", {name for name, _, _ in listed})

    def test_a_narrowed_plan_keeps_support_beside_the_copy_it_left_out(self):
        # Prediction (review round 2): dropping devlyn-ideate from a genuine plan keeps it, and with it the _shared and
        # marker beside it; devlyn-engines, which the plan kept, goes.
        self.install(self.root, "--global")
        plan, _ = self.plan("--machine")
        root = self.home / ".agents/skills"
        plan["scopes"][0]["items"] = [item for item in plan["scopes"][0]["items"] if item["path"] != str(root / "devlyn-ideate")]
        node = ("const p=JSON.parse(require('fs').readFileSync(0,'utf8'));delete p.digest;const c=(v)=>Array.isArray(v)?`[${v.map(c).join(',')}]`"
                ":v&&typeof v==='object'?`{${Object.keys(v).sort().map(k=>`${JSON.stringify(k)}:${c(v[k])}`).join(',')}}`:JSON.stringify(v);"
                "console.log(require('crypto').createHash('sha256').update(c(p)).digest('hex'))")
        plan["digest"] = subprocess.run(["node", "-e", node], input=json.dumps(plan), capture_output=True, text=True).stdout.strip()
        path = self.root / "narrowed.json"
        path.write_text(json.dumps(plan), encoding="utf-8")
        self.apply(plan, path)
        self.assertEqual(sorted(entry.name for entry in root.iterdir()), [".devlyn-install.json", "_shared", "devlyn-ideate"])

    def test_support_stays_beside_a_copy_refused_at_apply(self):
        # Prediction (review round 2 LOW): devlyn-engines replaced by another shipped version after review is refused at
        # apply and stays, so the _shared and marker beside it stay too; devlyn-ideate, unchanged, goes.
        self.install(self.root, "--global")
        plan, path = self.plan("--machine")
        root = self.home / ".agents/skills"
        shutil.rmtree(root / "devlyn-engines")
        self.historical_skill(root / "devlyn-engines", name="devlyn:engines")
        self.apply(plan, path)
        self.assertEqual(sorted(entry.name for entry in root.iterdir()), [".devlyn-install.json", "_shared", "devlyn-engines"])

    def test_the_home_folder_is_not_cleaned_as_a_project(self):
        # Prediction (review LOW): --project $HOME is skipped whole; the machine scope cleans those roots under its locks.
        self.install(self.root, "--global")
        self.run_ok(["git", "init", "-q"], cwd=self.home)
        plan, _ = self.plan("--project", self.home)
        self.assertEqual([(item["action"], item["reasons"][0]["code"]) for item in plan["scopes"][0]["items"]],
                         [("skip", "home-folder")])

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_tracked_linked_roots_deliver_each_real_copy_once(self):
        # Prediction: two tracked skill-root links into the project list each real copy once for delivery;
        # one apply merges their removal, preserving the links, their target and the owner's skill.
        repo = self.repo("linked-delivery")
        self.install(repo, "--claude")
        (repo / ".agents/skills").rename(repo / "skills")
        shutil.rmtree(repo / ".claude/skills")
        for agent in (".agents", ".claude"):
            (repo / agent / "skills").symlink_to("../skills", target_is_directory=True)
        own = repo / "skills/owner/SKILL.md"
        own.parent.mkdir()
        own.write_text("Owner's skill.\n")
        self.run_ok(["git", "add", "-A"], cwd=repo)
        self.run_ok(["git", "commit", "-qm", "linked install"], cwd=repo)
        self.fake_github(repo)
        plan, path = self.plan("--project", repo)
        self.assertEqual(sorted((i["relative"], i["action"], i["route"], i["reasons"]) for i in plan["scopes"][0]["items"]),
                         [(f"skills/{name}", "remove", "delivery", [])
                          for name in (".devlyn-install.json", "_shared", "devlyn-engines", "devlyn-ideate")])
        result = self.apply(plan, path)
        self.assertEqual((result["state"], result["scopes"][0]["delivery"]["state"]), ("succeeded", "merged"))
        self.assertEqual(sorted(p.name for p in (repo / "skills").iterdir()), ["owner"])
        self.assertEqual(own.read_text(), "Owner's skill.\n")
        for agent in (".agents", ".claude"):
            self.assertEqual(os.readlink(repo / agent / "skills"), "../skills")
        self.assertEqual(self.run_ok(["git", "status", "--porcelain"], cwd=repo).stdout, "")

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_tracked_linked_roots_preserve_links_after_delivery(self):
        # Prediction: one apply merges removal of the last tracked copies and preserves the
        # skill-root link's value, even when Git prunes its empty target directory.
        repo = self.repo("linked-empty-delivery")
        self.install(repo)
        (repo / ".claude").mkdir()
        (repo / ".claude/skills").symlink_to("../.agents/skills", target_is_directory=True)
        self.run_ok(["git", "add", "-A"], cwd=repo)
        self.run_ok(["git", "commit", "-qm", "linked install"], cwd=repo)
        self.fake_github(repo)
        plan, path = self.plan("--project", repo)
        result = self.apply(plan, path)
        self.assertEqual((result["state"], result["scopes"][0]["delivery"]["state"]), ("succeeded", "merged"))
        self.assertEqual(os.readlink(repo / ".claude/skills"), "../.agents/skills")
        for item in plan["scopes"][0]["items"]:
            self.assertFalse(Path(item["path"]).exists(), item["path"])

    @unittest.skipIf(os.name == "nt", "skill-root symlinks and fake GitHub require POSIX")
    def test_base_link_review_preserves_intermediate_directory_hops(self):
        # Prediction: a tracked spare directory makes ../spare/../skills traversable at the base,
        # without materializing spare's unrelated contents. A caller-only spare must not do so.
        for tracked in (True, False):
            with self.subTest(tracked=tracked):
                repo = self.repo("link-hops-" + str(tracked))
                self.install(repo)
                (repo / ".agents/skills").rename(repo / "skills")
                (repo / ".agents/skills").symlink_to("../spare/../skills", target_is_directory=True)
                spare = repo / "spare/owner.txt"
                spare.parent.mkdir()
                spare.write_text("Owner contents stay outside the snapshot.\n")
                self.run_ok(["git", "add", ".agents", "skills", "AGENTS.md", *(["spare"] if tracked else [])], cwd=repo)
                self.run_ok(["git", "commit", "-qm", "linked install"], cwd=repo)
                self.fake_github(repo)
                trace = self.root / f"link-hops-{tracked}.jsonl"
                preload = self.root / "link-hops.cjs"
                preload.write_text("const fs = require('fs'); const readdir = fs.readdirSync;\n"
                    "fs.readdirSync = (file, ...args) => { if (String(file).includes('/dc-') && String(file).endsWith('/skills'))\n"
                    f"fs.appendFileSync({json.dumps(str(trace))}, JSON.stringify({{spare:fs.existsSync(require('path').join(file, '../spare')), contents:fs.existsSync(require('path').join(file, '../spare/owner.txt'))}}) + '\\n');\n"
                    "return readdir(file, ...args); };\n")
                self.env["NODE_OPTIONS"] = "--require " + json.dumps(str(preload), ensure_ascii=False)
                plan, _ = self.plan("--project", repo)
                self.env.pop("NODE_OPTIONS")
                items = plan["scopes"][0]["items"]
                if tracked:
                    self.assertEqual(len(items), 4, items)
                    self.assertTrue(all(i["relative"].startswith("skills/") and i["route"] == "delivery"
                                        and i["action"] == "remove" for i in items), items)
                    observations = [json.loads(line) for line in trace.read_text().splitlines()]
                    self.assertTrue(observations)
                    self.assertTrue(all(o == {"spare": True, "contents": False} for o in observations), observations)
                else:
                    self.assertFalse(any(i["action"] == "remove" for i in items), items)
                    self.assertTrue(any(i["reasons"][0]["code"] == "outside-link" for i in items), items)

    @unittest.skipIf(os.name == "nt", "skill-root symlinks and fake GitHub require POSIX")
    def test_base_link_review_omits_empty_tree_directory_hops(self):
        # Prediction: an explicit empty spare tree creates no directory in a full checkout.
        # Base review must match that checkout, so repeated plan/apply never offers unreachable
        # skills/devlyn-ideate or enters a delivery-failed loop through ../spare/../skills.
        repo = self.repo("link-empty-tree")
        (repo / ".agents").mkdir()
        (repo / ".agents/skills").symlink_to("../spare/../skills", target_is_directory=True)
        shutil.copytree(ROOT / "config/skills/devlyn-ideate", repo / "skills/devlyn-ideate")
        self.run_ok(["git", "add", ".agents", "skills"], cwd=repo)
        indexed_tree = self.run_ok(["git", "write-tree"], cwd=repo).stdout.strip()
        entries = self.run_ok(["git", "ls-tree", indexed_tree], cwd=repo).stdout
        empty = self.run_ok(["git", "mktree"], cwd=repo, input="").stdout.strip()
        tree = self.run_ok(["git", "mktree"], cwd=repo,
                           input=entries + f"040000 tree {empty}\tspare\n").stdout.strip()
        commit = self.run_ok(["git", "commit-tree", tree, "-p", "HEAD", "-m", "linked install with empty tree"],
                             cwd=repo).stdout.strip()
        self.run_ok(["git", "reset", "--hard", commit], cwd=repo)
        self.assertEqual(self.run_ok(["git", "ls-tree", "HEAD", "spare"], cwd=repo).stdout,
                         f"040000 tree {empty}\tspare\n")
        self.assertFalse((repo / "spare").exists())
        self.assertEqual(self.run_ok(["git", "ls-files", "--", "spare/"], cwd=repo).stdout, "")
        # Without a remote, review scans the full checkout directly.
        full, _ = self.plan("--project", repo)
        self.assertEqual(self.actions(full["scopes"][0]), [("core-skill", "skip", "skills", "delivery", "outside-link")])
        self.fake_github(repo)
        for _ in range(2):
            plan, path = self.plan("--project", repo)
            self.assertEqual(plan["scopes"][0]["reviewBase"], commit)
            self.assertEqual(plan["scopes"][0]["items"], full["scopes"][0]["items"])
            result = self.apply(plan, path)
            self.assertEqual(result["state"], "succeeded")
            scope = result["scopes"][0]
            self.assertEqual((scope["state"], scope["delivery"], scope["error"]), ("skipped", None, None))
        self.assertTrue((repo / "skills/devlyn-ideate/SKILL.md").is_file())

    @unittest.skipIf(os.name == "nt", "fake GitHub uses POSIX wrappers")
    def test_base_review_materializes_case_variant_scanner_paths(self):
        # Prediction: case-variant roots (including a root link) and instructions review the base
        # on a case-insensitive filesystem, never falling back to persistent tracked-copy skips.
        repo = self.repo("case-variant-snapshot")
        self.install(repo)
        if not (repo / ".AGENTS/skills").is_dir():
            self.skipTest("case-insensitive filesystem required")
        (repo / ".agents").rename(repo / "agents-temp")
        (repo / "agents-temp").rename(repo / ".AGENTS")
        (repo / ".CLAUDE").mkdir()
        (repo / "linked-skills/devlyn-engines").mkdir(parents=True)
        shutil.copytree(ROOT / "config/skills/devlyn-engines", repo / "linked-skills/devlyn-engines", dirs_exist_ok=True)
        (repo / ".CLAUDE/SKILLS").symlink_to("../linked-skills", target_is_directory=True)
        template = subprocess.check_output(["git", "show", "v3.0.1:CLAUDE.md"], cwd=ROOT).decode()
        body = "Project-specific instructions outside this managed block take precedence over these defaults.\n\n" + template.rstrip("\n") + "\n"
        (repo / "claude.md").write_text("<!-- devlyn:instructions:begin sha256=" + hashlib.sha256(body.encode()).hexdigest()
                                       + " -->\n" + body + "<!-- devlyn:instructions:end -->\n")
        self.run_ok(["git", "add", "-A"], cwd=repo)
        self.run_ok(["git", "commit", "-qm", "case variant install"], cwd=repo)
        self.fake_github(repo)
        plan, _ = self.plan("--project", repo)
        items = plan["scopes"][0]["items"]
        self.assertEqual(len(items), 6, items)
        self.assertTrue(all(i["route"] == "delivery" and i["action"] in ("remove", "edit") and not i["reasons"] for i in items), items)
        self.assertTrue(any(i["relative"] == "linked-skills/devlyn-engines" for i in items), items)
        self.assertTrue(any(i["kind"] == "instructions" for i in items), items)

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_tracked_copies_are_delivered_by_the_project_policy(self):
        # Prediction: committed copies are removed on a fresh branch from the remote base, committed once and merged by
        # the default auto policy; the remote main loses the copies and keeps AGENTS.md's block and owner text, and the
        # checkout on main takes the merge, so its copies are gone too.
        repo = self.repo("delivered")
        (repo / "AGENTS.md").write_text("# Team rules\n", encoding="utf-8")
        self.install(repo)
        self.run_ok(["git", "add", "-A"], cwd=repo)
        self.run_ok(["git", "commit", "-qm", "install"], cwd=repo)
        bare = self.fake_github(repo)
        agents = (repo / "AGENTS.md").read_bytes()
        plan, path = self.plan("--project", repo)
        self.assertTrue(all(item["route"] == "delivery" and item["action"] == "remove" for item in plan["scopes"][0]["items"]))
        result = self.apply(plan, path)
        [scope] = result["scopes"]
        self.assertEqual((result["state"], scope["state"], scope["delivery"]["state"]), ("succeeded", "done", "merged"), scope)
        listed = self.run_ok(["git", "--git-dir", bare, "ls-tree", "-r", "--name-only", "main"]).stdout.split()
        self.assertFalse([name for name in listed if name.startswith((".agents/", ".claude/skills/"))])
        self.assertEqual(self.run_ok(["git", "--git-dir", bare, "show", "main:AGENTS.md"]).stdout.encode(), agents)
        self.assertEqual(self.run_ok(["git", "rev-parse", "HEAD"], cwd=repo).stdout,
                         self.run_ok(["git", "--git-dir", bare, "rev-parse", "main"]).stdout)
        self.assertFalse((repo / ".agents/skills/devlyn-ideate").exists())
        self.assertEqual(self.run_ok(["git", "status", "--porcelain"], cwd=repo).stdout, "")

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_tracked_copies_under_an_ignored_folder_are_delivered(self):
        # Prediction: with -A, tracked copies under ignored .claude/ fail delivery-failed. With -u,
        # cleanup merges their removals (including the chosen modified legacy command) and settings
        # edit; remote main loses the copies and the checkout takes the merge with a clean status.
        # An ignored untracked command is removed locally, and an unrelated ignored file stays.
        repo = self.repo("ignored-delivery")
        self.install(repo, "--claude")
        commands = repo / ".claude/commands"
        commands.mkdir()
        chosen = commands / "devlyn.design-system.md"
        chosen.write_text("Owner's edited design-system command.\n", encoding="utf-8")
        settings = repo / ".claude/settings.json"
        retired = {"type": "command", "command": 'python3 "$CLAUDE_PROJECT_DIR/.claude/skills/_shared/resolve-stop-hook.py"'}
        settings.write_text(json.dumps({"custom": "owner", "hooks": {"Stop": [{"hooks": [retired]}]}}) + "\n")
        self.run_ok(["git", "add", "-A"], cwd=repo)
        self.run_ok(["git", "commit", "-qm", "legacy install"], cwd=repo)
        ignore = repo / ".gitignore"
        ignore.write_text(ignore.read_text(encoding="utf-8") + "\n.claude/\n", encoding="utf-8")
        self.run_ok(["git", "add", ".gitignore"], cwd=repo)
        self.run_ok(["git", "commit", "-qm", "ignore claude folder after tracking copies"], cwd=repo)
        bare = self.fake_github(repo)
        local = commands / "devlyn.review.md"
        local.write_text("Owner's local legacy command.\n", encoding="utf-8")
        kept = repo / ".claude/owner.txt"
        kept.write_text("Keep my file.\n", encoding="utf-8")
        self.run_ok(["git", "check-ignore", "--no-index", "--quiet", str(chosen)], cwd=repo)
        plan, path = self.plan("--project", repo)
        items = plan["scopes"][0]["items"]
        self.assertIn(("legacy-command", "skip", chosen.name, "delivery", "modified-copy"), self.actions(plan["scopes"][0]))
        self.assertIn(("legacy-command", "skip", local.name, "local", "modified-copy"), self.actions(plan["scopes"][0]))
        self.assertIn(("settings-entry", "edit", "settings.json", "delivery", None), self.actions(plan["scopes"][0]))
        include = [item["id"] for item in items if item["path"] in (str(chosen), str(local))]
        result = self.apply(plan, path, include=include)
        [scope] = result["scopes"]
        self.assertEqual((result["state"], scope["state"], scope["error"]), ("succeeded", "done", None), scope)
        self.assertEqual(scope["delivery"]["state"], "merged")
        listed = self.run_ok(["git", "--git-dir", bare, "ls-tree", "-r", "--name-only", "main"]).stdout.splitlines()
        self.assertFalse([name for name in listed if name.startswith((".agents/skills/", ".claude/skills/", ".claude/commands/"))])
        cleaned = {"custom": "owner"}
        self.assertEqual(json.loads(self.run_ok(["git", "--git-dir", bare, "show", "main:.claude/settings.json"]).stdout), cleaned)
        self.assertEqual(json.loads(settings.read_text()), cleaned)
        self.assertEqual(self.run_ok(["git", "rev-parse", "HEAD"], cwd=repo).stdout,
                         self.run_ok(["git", "--git-dir", bare, "rev-parse", "main"]).stdout)
        self.assertFalse(chosen.exists())
        self.assertFalse(local.exists())
        self.assertEqual(kept.read_text(encoding="utf-8"), "Keep my file.\n")
        self.assertNotIn(".claude/owner.txt", listed)
        self.assertEqual(self.run_ok(["git", "status", "--porcelain"], cwd=repo).stdout, "")
        again, _ = self.plan("--project", repo)
        self.assertEqual(again["scopes"][0]["items"], [])

    @unittest.skipIf(os.name == "nt", "fake GitHub uses POSIX wrappers")
    def test_allocation_auth_failure_is_reported(self):
        repo = self.repo("allocation-auth")
        self.install(repo)
        self.run_ok(["git", "add", "-A"], cwd=repo)
        self.run_ok(["git", "commit", "-qm", "installed skills"], cwd=repo)
        self.fake_github(repo)
        plan, path = self.plan("--project", repo)
        (self.root / "bin/gh").write_text(
            f"#!{sys.executable}\nimport sys\nprint('Run gh auth login', file=sys.stderr)\nsys.exit(1)\n")
        result = self.apply(plan, path)
        scope = result["scopes"][0]
        self.assertEqual((scope["state"], scope["error"]["code"]), ("failed", "auth-failed"))
        self.assertIn("gh auth login", scope["error"]["params"]["detail"])
        self.assertEqual(self.run_ok(["git", "branch", "--list", "devlyn/cleanup-*"], cwd=repo).stdout, "")

    def removed_upstream(self, repo, bare, plan, also=None):
        """What an earlier cleanup merged: the plan's tracked copies removed on the remote main only. `also`
        changes the upstream clone further before that commit."""
        upstream = self.root / f"{repo.name}-upstream"
        self.run_ok(["git", "clone", "-q", bare, upstream])
        relatives = [item["relative"] for item in plan["scopes"][0]["items"]
                     if item["route"] == "delivery" and item["action"] == "remove"]
        self.assertTrue(relatives)
        self.run_ok(["git", "rm", "-rq", "--", *relatives], cwd=upstream)
        if also:
            also(upstream)
        self.run_ok(["git", "commit", "-qm", "remove legacy copies"], cwd=upstream)
        self.run_ok(["git", "push", "-q", "origin", "main"], cwd=upstream)

    def installed_and_pushed(self, name):
        repo = self.repo(name)
        self.install(repo)
        self.run_ok(["git", "add", "-A"], cwd=repo)
        self.run_ok(["git", "commit", "-qm", "install"], cwd=repo)
        return repo, self.fake_github(repo)

    def rewritten_upstream(self, repo, bare):
        upstream = self.root / f"{repo.name}-upstream"
        self.run_ok(["git", "clone", "-q", bare, upstream])
        skill = upstream / ".agents/skills/devlyn-ideate"
        shutil.rmtree(skill)
        self.historical_skill(skill)
        self.run_ok(["git", "add", "-A"], cwd=upstream)
        self.run_ok(["git", "commit", "-qm", "another shipped copy"], cwd=upstream)
        self.run_ok(["git", "push", "-q", "origin", "main"], cwd=upstream)

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_plan_updates_a_behind_checkout_before_reviewing_delivery(self):
        # Prediction: planning takes an already rewritten base and reviews its shipped copy; one apply merges
        # the cleanup, removes the copy from the checkout, and leaves no cleanup branch or worktree.
        repo, bare = self.installed_and_pushed("plan-behind")
        self.rewritten_upstream(repo, bare)
        base = self.run_ok(["git", "--git-dir", bare, "rev-parse", "main"]).stdout
        expected = self.run_ok(
            ["node", "-e", "const {fingerprint}=require(process.argv[1]);console.log(fingerprint(process.argv[2]))",
             ROOT / "bin/skill-ownership.js", self.root / "plan-behind-upstream/.agents/skills/devlyn-ideate"]).stdout.strip()
        plan, path = self.plan("--project", repo)
        self.assertEqual(self.run_ok(["git", "rev-parse", "HEAD"], cwd=repo).stdout, base)
        item = next(i for i in plan["scopes"][0]["items"] if i["relative"] == ".agents/skills/devlyn-ideate")
        self.assertEqual((item["action"], item["route"], item["before"]),
                         ("remove", "delivery", {"type": "directory", "sha256": expected}))
        [scope] = self.apply(plan, path)["scopes"]
        self.assertEqual((scope["state"], scope["error"], scope["delivery"]["state"]), ("done", None, "merged"), scope)
        self.assertFalse((repo / ".agents/skills/devlyn-ideate").exists())
        self.assertEqual(self.run_ok(["git", "branch", "--list", "devlyn/cleanup-*"], cwd=repo).stdout.strip(), "")
        self.assertFalse(list((self.root / "plan-behind.devlyn.noindex").glob("devlyn-cleanup-*")))

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_plan_refreshes_scopes_sharing_a_behind_checkout(self):
        # Prediction: when project inputs share a behind checkout, all scopes review the base copy's
        # preimage with one fetch/snapshot, even though only the first scope's update moves HEAD.
        # checkout-index receives only scanner inputs; planning allocates no delivery receipt.
        repo, bare = self.installed_and_pushed("plan-shared")
        self.rewritten_upstream(repo, bare)
        base = self.run_ok(["git", "--git-dir", bare, "rev-parse", "main"]).stdout
        expected = self.run_ok(
            ["node", "-e", "const {fingerprint}=require(process.argv[1]);console.log(fingerprint(process.argv[2]))",
             ROOT / "bin/skill-ownership.js", self.root / "plan-shared-upstream/.agents/skills/devlyn-ideate"]).stdout.strip()
        trace = self.root / "snapshot-trace.jsonl"
        preload = self.root / "trace-snapshot.cjs"
        preload.write_text("const cp = require('child_process'); const spawn = cp.spawnSync;\n"
            "cp.spawnSync = (cmd, args, opts) => {\n"
            f"if (cmd === 'git') require('fs').appendFileSync({json.dumps(str(trace))}, JSON.stringify({{args, input:opts?.input}}) + '\\n');\n"
            "return spawn(cmd, args, opts); };\n")
        self.env["NODE_OPTIONS"] = "--require " + json.dumps(str(preload), ensure_ascii=False)
        alias = self.root / "plan-shared-alias"
        alias.symlink_to(repo, target_is_directory=True)
        plan, _ = self.plan("--project", repo, "--project", repo / ".agents", "--project", alias / ".agents/skills")
        self.env.pop("NODE_OPTIONS")
        commands = [json.loads(line) for line in trace.read_text().splitlines()]
        self.assertEqual(sum("fetch" in c["args"] for c in commands), 1)
        self.assertEqual(sum("read-tree" in c["args"] for c in commands), 1)
        enumerations = [c["args"] for c in commands if "ls-files" in c["args"]
                        and Path(c["args"][1]).parent == self.snapshots]
        self.assertEqual(len(enumerations), 2)
        self.assertTrue(all("--" in args and args.index("--") < len(args) - 1 for args in enumerations))
        self.assertTrue(all(p.startswith(":(icase,literal)") for args in enumerations for p in args[args.index("--") + 1:]))
        self.assertTrue(any("--stage" in args and args[-2:] == [":(icase,literal).agents/skills", ":(icase,literal).claude/skills"]
                            for args in enumerations))
        self.assertFalse(any("ls-tree" in c["args"] for c in commands))
        [checkout] = [c for c in commands if "checkout-index" in c["args"]]
        names = checkout["input"].split("\0")
        self.assertNotIn("README.md", names)
        self.assertFalse((repo / ".git/devlyn-completion").exists())
        self.assertEqual(self.run_ok(["git", "rev-parse", "HEAD"], cwd=repo).stdout, base)
        self.assertEqual(len(plan["scopes"]), 3)
        for scope in plan["scopes"]:
            with self.subTest(scope=scope["id"]):
                item = next(i for i in scope["items"] if i["relative"] == ".agents/skills/devlyn-ideate")
                self.assertEqual((item["action"], item["route"], item["before"]),
                                 ("remove", "delivery", {"type": "directory", "sha256": expected}))

    def test_plan_linked_worktrees_with_distinct_origins_review_their_own_bases(self):
        for relative in (False, True):
            with self.subTest(relative=relative):
                self.check_linked_worktree_origins(relative)

    def check_linked_worktree_origins(self, relative):
        # Prediction: absolute origins or identical relative URLs resolving to different repositories
        # with the same repository/base identity still fetch separately. Each review uses its own
        # preimage; only the main checkout advances, to its
        # own origin's commit. Neither fetched views nor their refs/registrations/directories leak.
        mode = "relative" if relative else "absolute"
        repo = self.repo(f"distinct-origins-{mode}")
        self.install(repo)
        self.run_ok(["git", "add", "-A"], cwd=repo)
        self.run_ok(["git", "commit", "-qm", "install"], cwd=repo)
        initial = self.run_ok(["git", "rev-parse", "HEAD"], cwd=repo).stdout.strip()
        self.run_ok(["git", "config", "extensions.worktreeConfig", "true"], cwd=repo)
        self.run_ok(["git", "checkout", "-qb", "anchor"], cwd=repo)
        worktrees, origins, bases, preimages = [], [], [], []
        for index, branch in enumerate(("review", "main")):
            tree = self.root / f"{mode}-{index}/tree"
            self.run_ok(["git", "worktree", "add", "-q", *(["-b", branch] if index == 0 else []),
                         tree, *(["HEAD"] if index == 0 else [branch])], cwd=repo)
            self.repos.append(tree)
            worktrees.append(tree)
            # Local transports exercise real Git fetches; both URLs identify test/project on main.
            origin = tree.parent / "remote/github.com/test/project.git"
            origin.parent.mkdir(parents=True)
            self.run_ok(["git", "init", "-q", "--bare", "--initial-branch=main", origin])
            self.run_ok(["git", "push", "-q", origin, "main"], cwd=repo)
            url = "../remote/github.com/test/project.git" if relative else origin.as_uri()
            origins.append(url)
            self.run_ok(["git", "config", "--worktree", "remote.origin.url", url], cwd=tree)
            upstream = self.root / f"upstream-{mode}-{index}"
            self.run_ok(["git", "clone", "-q", origin, upstream])
            skill = upstream / ".agents/skills/devlyn-ideate"
            if index == 0:
                shutil.rmtree(skill)
                self.historical_skill(skill)
            (upstream / "README.md").write_text(f"origin {index}\n")
            self.run_ok(["git", "add", "-A"], cwd=upstream)
            self.run_ok(["git", "commit", "-qm", "origin-specific base"], cwd=upstream)
            self.run_ok(["git", "push", "-q", "origin", "main"], cwd=upstream)
            bases.append(self.run_ok(["git", "rev-parse", "HEAD"], cwd=upstream).stdout.strip())
            preimages.append(self.run_ok(
                ["node", "-e", "const {fingerprint}=require(process.argv[1]);console.log(fingerprint(process.argv[2]))",
                 ROOT / "bin/skill-ownership.js", skill]).stdout.strip())
        self.assertNotEqual(bases[0], bases[1])
        self.assertNotEqual(preimages[0], preimages[1])
        self.assertEqual(origins[0] == origins[1], relative)
        trace = self.root / f"distinct-origin-{mode}-trace.jsonl"
        preload = self.root / "trace-origins.cjs"
        preload.write_text("const cp = require('child_process'); const spawn = cp.spawnSync;\n"
            "cp.spawnSync = (cmd, args, opts) => {\n"
            f"if (cmd === 'git') require('fs').appendFileSync({json.dumps(str(trace))}, JSON.stringify(args) + '\\n');\n"
            "return spawn(cmd, args, opts); };\n")
        self.env["NODE_OPTIONS"] = "--require " + json.dumps(str(preload), ensure_ascii=False)
        plan, _ = self.plan(*[arg for tree in worktrees for arg in ("--project", tree)])
        self.env.pop("NODE_OPTIONS")
        self.assertEqual(len(plan["scopes"]), 2)
        for index, scope in enumerate(plan["scopes"]):
            with self.subTest(origin=origins[index]):
                self.assertEqual(scope["remote"], {"repository": "test/project", "base": "main"})
                self.assertEqual(scope.get("reviewBase"), bases[index])
                item = next(i for i in scope["items"] if i["relative"] == ".agents/skills/devlyn-ideate")
                self.assertEqual((item["action"], item["route"], item["before"]),
                                 ("remove", "delivery", {"type": "directory", "sha256": preimages[index]}))
                self.assertEqual(item["path"], str(worktrees[index] / item["relative"]))
                self.assertEqual(self.run_ok(["git", "remote", "get-url", "origin"], cwd=worktrees[index]).stdout.strip(), origins[index])
        self.assertEqual(self.run_ok(["git", "rev-parse", "HEAD"], cwd=worktrees[0]).stdout.strip(), initial)
        self.assertEqual((worktrees[0] / "README.md").read_text(), "# project\n")
        self.assertEqual(self.run_ok(["git", "rev-parse", "HEAD"], cwd=worktrees[1]).stdout.strip(), bases[1])
        self.assertEqual((worktrees[1] / "README.md").read_text(), "origin 1\n")
        commands = [json.loads(line) for line in trace.read_text().splitlines()]
        self.assertEqual([args[1] for args in commands if "fetch" in args], [str(tree) for tree in worktrees])
        self.assertEqual([args[-1] for args in commands if "read-tree" in args], bases)
        self.assertEqual([(args[1], args[-1]) for args in commands if "merge" in args], [(str(worktrees[1]), bases[1])])
        self.assertEqual([args[1] for args in commands if "worktree" in args and "remove" in args],
                         [str(tree) for tree in worktrees])

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_plan_on_another_branch_reviews_the_base_copy(self):
        # Prediction: a rewritten base does not move another branch during planning; the review uses the
        # preimage at the base; delivery merges, then reports update-checkout without moving HEAD.
        repo, bare = self.installed_and_pushed("plan-feature")
        self.rewritten_upstream(repo, bare)
        self.run_ok(["git", "checkout", "-qb", "work"], cwd=repo)
        before = self.run_ok(["git", "rev-parse", "HEAD"], cwd=repo).stdout
        expected = self.run_ok(
            ["node", "-e", "const {fingerprint}=require(process.argv[1]);console.log(fingerprint(process.argv[2]))",
             ROOT / "bin/skill-ownership.js", self.root / "plan-feature-upstream/.agents/skills/devlyn-ideate"]).stdout.strip()
        plan, path = self.plan("--project", repo)
        self.assertEqual(self.run_ok(["git", "rev-parse", "HEAD"], cwd=repo).stdout, before)
        item = next(i for i in plan["scopes"][0]["items"] if i["relative"] == ".agents/skills/devlyn-ideate")
        self.assertEqual((item["action"], item["route"], item["before"]),
                         ("remove", "delivery", {"type": "directory", "sha256": expected}))
        [scope] = self.apply(plan, path)["scopes"]
        self.assertEqual((scope["state"], scope["error"]["code"], scope["delivery"]["state"]), ("failed", "update-checkout", "merged"), scope)
        self.assertEqual(self.run_ok(["git", "rev-parse", "HEAD"], cwd=repo).stdout, before)

    @unittest.skipIf(os.name == "nt", "fake GitHub uses POSIX wrappers")
    def test_base_skill_review_uses_the_system_default_temp_directory(self):
        # Prediction: with all fixture temp overrides removed, macOS's /tmp -> /private/tmp alias
        # still yields actionable base skill items rooted in the caller, and leaves no snapshot.
        repo, _ = self.installed_and_pushed("default-temp")
        for name in ("TMPDIR", "TMP", "TEMP"):
            self.env.pop(name, None)
        trace = self.root / "default-temp.jsonl"
        preload = self.root / "default-temp.cjs"
        preload.write_text("const fs = require('fs'); const mkdtemp = fs.mkdtempSync;\n"
            "fs.mkdtempSync = (...args) => { const result = mkdtemp(...args);\n"
            f"fs.appendFileSync({json.dumps(str(trace))}, JSON.stringify({{path:result, temp:require('os').tmpdir()}}) + '\\n');\n"
            "return result; };\n")
        self.env["NODE_OPTIONS"] = "--require " + json.dumps(str(preload), ensure_ascii=False)
        plan, _ = self.plan("--project", repo)
        [snapshot] = [json.loads(line) for line in trace.read_text().splitlines()]
        self.assertEqual(Path(snapshot["path"]).parent, Path(snapshot["temp"]))
        self.assertFalse(Path(snapshot["path"]).exists())
        items = plan["scopes"][0]["items"]
        self.assertEqual({Path(i["path"]).name for i in items},
                         {"devlyn-ideate", "devlyn-engines", "_shared", ".devlyn-install.json"})
        for item in items:
            self.assertEqual((item["route"], item["action"], item["reasons"]), ("delivery", "remove", []))
            self.assertEqual(item["path"], str(repo / item["relative"]))
            self.assertEqual(item["base"], str(repo))

    @unittest.skipIf(os.name == "nt", "fake GitHub uses POSIX wrappers")
    def test_non_directory_skill_root_does_not_hide_the_other_root(self):
        # Prediction: core.symlinks=false checks out the tracked Claude root link as a file;
        # the Agents root still gets a complete delivery review without an ENOTDIR scope failure.
        repo, _ = self.installed_and_pushed("symlinks-disabled")
        root = repo / ".claude/skills"
        root.parent.mkdir(exist_ok=True)
        root.symlink_to("../.agents/skills", target_is_directory=True)
        self.run_ok(["git", "add", ".claude/skills"], cwd=repo)
        self.run_ok(["git", "commit", "-qm", "root link"], cwd=repo)
        self.run_ok(["git", "push", "-q", "origin", "main"], cwd=repo)
        self.run_ok(["git", "config", "core.symlinks", "false"], cwd=repo)
        root.unlink()
        self.run_ok(["git", "checkout", "--", ".claude/skills"], cwd=repo)
        self.assertTrue(root.is_file() and not root.is_symlink())
        plan, _ = self.plan("--project", repo)
        items = plan["scopes"][0]["items"]
        self.assertEqual(len(items), 4)
        self.assertTrue(all(i["relative"].startswith(".agents/skills/") and i["route"] == "delivery"
                            and i["action"] == "remove" for i in items), items)

    @unittest.skipIf(os.name == "nt", "fake GitHub uses POSIX wrappers")
    def test_index_held_candidates_open_base_review_after_unstaged_deletion(self):
        # Prediction: every scanner candidate family opens the fetch gate from the index alone;
        # deleting all caller copies unstaged still reviews their base bytes as delivery items.
        history = self.ai_os_package()
        legacy_bytes = subprocess.check_output(["git", "show", "v3.0.1:config/commit-conventions.md"], cwd=ROOT)
        cases = [(".agents/skills", None), (".AGENTS/skills", None), (".CLAUDE/skills", None),
                 *[(directory + "/devlyn.fixture.md", self.ai_command) for directory in history["commandDirectories"]],
                 (".claude/commit-conventions.md", legacy_bytes), (".claude/hooks/hook-to-file.mjs", self.ai_script)]
        for index, (relative, contents) in enumerate(cases):
            with self.subTest(relative=relative):
                repo = self.repo(f"deleted-candidates-{index}")
                target = repo / relative
                if contents is None:
                    shutil.copytree(ROOT / "config/skills", target)
                else:
                    target.parent.mkdir(parents=True)
                    target.write_bytes(contents)
                self.run_ok(["git", "add", "-A"], cwd=repo)
                self.run_ok(["git", "commit", "-qm", "legacy copies"], cwd=repo)
                bare = self.fake_github(repo)
                baseline, _ = self.plan("--project", repo)
                if target.is_dir():
                    shutil.rmtree(target)
                else:
                    target.unlink()
                before = self.checkout_state(repo)
                plan, _ = self.plan("--project", repo)
                scope = plan["scopes"][0]
                self.assertEqual(scope.get("reviewBase"), self.run_ok(["git", "--git-dir", bare, "rev-parse", "main"]).stdout.strip())
                self.assertEqual(scope["items"], baseline["scopes"][0]["items"])
                if contents is not None or (repo / relative.split('/')[0].lower()).is_dir():
                    self.assertTrue(scope["items"])
                    self.assertTrue(all(i["route"] == "delivery" and i["action"] == "remove" for i in scope["items"]), scope["items"])
                self.assertEqual(self.checkout_state(repo), before)

    @unittest.skipIf(os.name == "nt", "fake GitHub uses POSIX wrappers")
    def test_no_tracked_legacy_items_never_fetch_or_snapshot(self):
        # Prediction: an unreachable remote costs no fetch, owned ref or snapshot for either an
        # empty caller or a caller holding only local legacy copies, even with tracked owner
        # instructions/settings. Those ubiquitous paths alone must not open the fetch gate.
        repo = self.repo("no-tracked-legacy")
        (repo / ".claude").mkdir()
        for name in ("CLAUDE.md", "AGENTS.md", ".claude/settings.json", ".claude/settings.local.json"):
            (repo / name).write_text("{}\n" if name.endswith(".json") else "Owner instructions.\n")
        self.run_ok(["git", "add", "-A"], cwd=repo)
        self.run_ok(["git", "commit", "-qm", "owner instructions and settings"], cwd=repo)
        bare = self.fake_github(repo)
        shutil.rmtree(bare)
        trace = self.root / "unexpected-fetch.jsonl"
        preload = self.root / "no-fetch.cjs"
        preload.write_text("const cp = require('child_process'); const spawn = cp.spawnSync;\n"
            "cp.spawnSync = (cmd, args, opts) => {\n"
            "if (cmd === 'git' && args.some(a => ['fetch', 'update-ref', 'read-tree'].includes(a))) {\n"
            f"require('fs').appendFileSync({json.dumps(str(trace))}, JSON.stringify(args) + '\\n');\n"
            "throw new Error('unexpected base access'); } return spawn(cmd, args, opts); };\n")
        self.env["NODE_OPTIONS"] = "--require " + json.dumps(str(preload), ensure_ascii=False)
        for installed in (False, True):
            with self.subTest(installed=installed):
                if installed:
                    self.install(repo)
                plan, _ = self.plan("--project", repo)
                self.assertNotIn("reviewBase", plan["scopes"][0])
                items = plan["scopes"][0]["items"]
                self.assertEqual(len(items), 4 if installed else 0)
                self.assertTrue(all(i["route"] == "local" and i["action"] == "remove" for i in items))
                self.assertFalse(trace.exists(), trace.read_text() if trace.exists() else "")

    @unittest.skipIf(os.name == "nt", "fake GitHub uses POSIX wrappers")
    def test_concurrent_plans_release_independent_snapshots_and_refs(self):
        # Prediction: two plans overlap at checkout-index in separate snapshots, review the same
        # base successfully, and leave no owned refs, worktree registrations or snapshot directories.
        repo, _ = self.installed_and_pushed("concurrent-plans")
        trees = self.run_ok(["git", "worktree", "list", "--porcelain"], cwd=repo).stdout
        barrier = self.root / "barrier"
        barrier.mkdir()
        preload = self.root / "concurrent.cjs"
        preload.write_text("const cp = require('child_process'); const spawn = cp.spawnSync; const fs = require('fs');\n"
            "cp.spawnSync = (cmd, args, opts) => { if (cmd === 'git' && args.includes('checkout-index')) {\n"
            f"const dir = {json.dumps(str(barrier))}; fs.writeFileSync(require('path').join(dir, String(process.pid)), 'ready');\n"
            "const deadline = Date.now() + 15000; while (fs.readdirSync(dir).length < 2) {\n"
            "if (Date.now() > deadline) throw new Error('concurrent snapshot barrier timed out');\n"
            "Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 10); }\n"
            "} return spawn(cmd, args, opts); };\n")
        self.env["NODE_OPTIONS"] = "--require " + json.dumps(str(preload), ensure_ascii=False)
        processes = [subprocess.Popen(["node", str(CLI), "cleanup", "--plan", "--project", str(repo), "--json"],
                     cwd=self.root, env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8") for _ in range(2)]
        try:
            plans = []
            for process in processes:
                stdout, stderr = process.communicate(timeout=90)
                self.assertEqual(process.returncode, 0, stdout + stderr)
                envelope = json.loads(stdout.strip().splitlines()[-1])
                self.assertTrue(envelope["ok"], envelope)
                plan = envelope["data"]
                self.assertEqual(len(plan["scopes"][0]["items"]), 4)
                self.assertTrue(all(i["route"] == "delivery" and i["action"] == "remove" for i in plan["scopes"][0]["items"]), plan)
                plans.append(plan)
            self.assertEqual(plans[0], plans[1])
        finally:
            for process in processes:
                if process.poll() is None:
                    process.kill()
                process.communicate()
        self.assertEqual(len(list(barrier.iterdir())), 2)
        self.assertEqual(list(self.snapshots.glob("dc-*")), [])
        self.assertEqual(self.run_ok(["git", "for-each-ref", "refs/devlyn/cleanup/"], cwd=repo).stdout, "")
        self.assertEqual(self.run_ok(["git", "worktree", "list", "--porcelain"], cwd=repo).stdout, trees)

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_plan_with_an_unreachable_remote_reviews_only_local_items(self):
        # Prediction: a failed fetch skips tracked items as repository-unreadable, still reviews local
        # copies, preserves caller state, and leaves no owned ref, snapshot or worktree registration.
        repo, bare = self.installed_and_pushed("plan-offline")
        self.rewritten_upstream(repo, bare)
        shutil.rmtree(bare)
        before = self.run_ok(["git", "rev-parse", "HEAD"], cwd=repo).stdout
        local = repo / ".claude/skills/devlyn-engines"
        shutil.copytree(ROOT / "config/skills/devlyn-engines", local)
        state = self.checkout_state(repo)
        plan, _ = self.plan("--project", repo)
        self.assertEqual(self.checkout_state(repo), state)
        self.assertEqual(self.run_ok(["git", "rev-parse", "HEAD"], cwd=repo).stdout, before)
        tracked = [i for i in plan["scopes"][0]["items"] if i["route"] == "delivery"]
        self.assertTrue(tracked)
        self.assertTrue(all(i["action"] == "skip" and i["reasons"][0]["code"] == "repository-unreadable"
                            and i["reasons"][0]["params"]["detail"] for i in tracked))
        [item] = [i for i in plan["scopes"][0]["items"] if i["route"] == "local"]
        self.assertEqual((item["path"], item["action"]), (str(local), "remove"))
        self.assertEqual(self.run_ok(["git", "for-each-ref", "refs/devlyn/cleanup/"], cwd=repo).stdout, "")

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_the_checkout_update_is_a_fast_forward_whatever_the_branch_merge_options(self):
        # Prediction (review MEDIUM): a branch configured to squash or merge with `-s ours` still lands exactly on the
        # base commit, with nothing left staged.
        for number, options in enumerate(["--squash", "-s ours"]):
            with self.subTest(options=options):
                repo, bare = self.installed_and_pushed(f"options{number}")
                self.run_ok(["git", "config", "branch.main.mergeOptions", options], cwd=repo)
                plan, path = self.plan("--project", repo)
                self.removed_upstream(repo, bare, plan)
                [scope] = self.apply(plan, path)["scopes"]
                self.assertEqual((scope["state"], scope["error"]), ("done", None), scope)
                self.assertEqual(self.run_ok(["git", "rev-parse", "HEAD"], cwd=repo).stdout,
                                 self.run_ok(["git", "--git-dir", bare, "rev-parse", "main"]).stdout)
                self.assertEqual(self.run_ok(["git", "status", "--porcelain"], cwd=repo).stdout, "")

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_the_checkout_update_never_overwrites_an_ignored_file(self):
        # Prediction (review HIGH): when the base now tracks a path the checkout ignores, the fast-forward is refused
        # and the local file keeps its bytes; the scope asks for the update instead of reporting done.
        repo, bare = self.installed_and_pushed("ignored")
        (repo / ".git/info/exclude").write_text("notes/\n", encoding="utf-8")
        (repo / "notes").mkdir()
        (repo / "notes/kept.txt").write_text("mine\n", encoding="utf-8")
        plan, path = self.plan("--project", repo)

        def track(upstream):
            (upstream / "notes").mkdir()
            (upstream / "notes/kept.txt").write_text("theirs\n", encoding="utf-8")
            self.run_ok(["git", "add", "notes/kept.txt"], cwd=upstream)

        self.removed_upstream(repo, bare, plan, also=track)
        before = self.run_ok(["git", "rev-parse", "HEAD"], cwd=repo).stdout
        [scope] = self.apply(plan, path)["scopes"]
        self.assertEqual((scope["state"], scope["error"]["code"]), ("failed", "update-checkout"), scope)
        self.assertEqual((repo / "notes/kept.txt").read_text(encoding="utf-8"), "mine\n")
        self.assertEqual(self.run_ok(["git", "rev-parse", "HEAD"], cwd=repo).stdout, before)
        self.assertEqual(self.run_ok(["git", "for-each-ref", "refs/devlyn/cleanup/"], cwd=repo).stdout, "")

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_a_copy_the_base_kept_under_another_spelling_is_not_taken_as_removed(self):
        # Prediction (review MEDIUM): a reviewed copy the base still holds, renamed only in case, is not one the base
        # removed; the scope stays stale-plan and a checkout with local commits is not moved.
        repo, bare = self.installed_and_pushed("spelling")
        self.run_ok(["git", "commit", "--allow-empty", "-qm", "local work"], cwd=repo)
        plan, path = self.plan("--project", repo)

        def rename(upstream):
            self.run_ok(["git", "checkout", "-q", "HEAD", "--", ".agents/skills/devlyn-ideate"], cwd=upstream)
            self.run_ok(["git", "mv", ".agents/skills/devlyn-ideate", ".agents/skills/moved"], cwd=upstream)
            self.run_ok(["git", "mv", ".agents/skills/moved", ".agents/skills/DEVLYN-IDEATE"], cwd=upstream)

        self.removed_upstream(repo, bare, plan, also=rename)
        before = self.run_ok(["git", "rev-parse", "HEAD"], cwd=repo).stdout
        [scope] = self.apply(plan, path)["scopes"]
        self.assertEqual((scope["state"], scope["error"]["code"]), ("failed", "stale-plan"), scope)
        self.assertIn(".agents/skills/devlyn-ideate", scope["error"]["params"]["detail"])
        self.assertEqual(self.run_ok(["git", "rev-parse", "HEAD"], cwd=repo).stdout, before)

        again, _ = self.plan("--project", repo)
        self.assertTrue(any(i["relative"] == ".agents/skills/DEVLYN-IDEATE" and i["action"] == "remove"
                            for i in again["scopes"][0]["items"]))

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_a_file_the_base_renamed_only_in_case_is_not_settled(self):
        # Prediction: the literal-name scanner misses an uppercase legacy file, but the base tree
        # still contains its case-insensitive counterpart, so apply refuses stale-plan without a PR.
        repo = self.repo("file-spelling")
        relative = ".claude/commit-conventions.md"
        legacy = repo / relative
        legacy.parent.mkdir()
        legacy.write_bytes(subprocess.check_output(["git", "show", "v3.0.1:config/commit-conventions.md"], cwd=ROOT))
        self.run_ok(["git", "add", "-A"], cwd=repo)
        self.run_ok(["git", "commit", "-qm", "legacy file"], cwd=repo)
        bare = self.fake_github(repo)
        plan, path = self.plan("--project", repo)
        self.assertEqual([i["relative"] for i in plan["scopes"][0]["items"]], [relative])

        def rename(upstream):
            self.run_ok(["git", "checkout", "-q", "HEAD", "--", relative], cwd=upstream)
            self.run_ok(["git", "mv", relative, ".claude/moved.md"], cwd=upstream)
            self.run_ok(["git", "mv", ".claude/moved.md", ".claude/COMMIT-CONVENTIONS.md"], cwd=upstream)

        self.removed_upstream(repo, bare, plan, also=rename)
        before = self.checkout_state(repo)
        result = self.apply(plan, path)["scopes"][0]
        self.assertEqual(result["error"]["code"], "stale-plan", result)
        self.assertIn(relative, result["error"]["params"]["detail"])
        self.assertEqual(self.checkout_state(repo), before)
        self.assertFalse(json.loads((self.root / "gh.json").read_text()).get("prs"))

        # Prediction: on a case-sensitive filesystem the scan finds no item at the old spelling;
        # that absence also refuses settlement because ls-tree still holds the case-only rename.
        preload = self.root / "case-sensitive.cjs"
        preload.write_text("const fs = require('fs'); const lstat = fs.lstatSync; const path = require('path');\n"
            "fs.lstatSync = (file, opts) => { if (String(file).endsWith('/.claude/commit-conventions.md')\n"
            "&& opts?.throwIfNoEntry === false && !fs.readdirSync(path.dirname(file)).includes(path.basename(file))) return undefined;\n"
            "return lstat(file, opts); };\n")
        self.env["NODE_OPTIONS"] = "--require " + json.dumps(str(preload), ensure_ascii=False)
        result = self.apply(plan, path)["scopes"][0]
        self.assertEqual(result["error"]["code"], "stale-plan", result)
        self.assertIn(relative, result["error"]["params"]["detail"])
        self.assertEqual(self.checkout_state(repo), before)
        self.assertFalse(json.loads((self.root / "gh.json").read_text()).get("prs"))

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_copies_the_remote_base_already_removed_bring_the_checkout_up_to_date(self):
        # Prediction: a checkout behind a remote main that already dropped the copies (an earlier cleanup's merged PR)
        # takes that main by fast-forward and the scope is done, with no new branch, worktree or PR.
        repo = self.repo("behind")
        self.install(repo)
        self.run_ok(["git", "add", "-A"], cwd=repo)
        self.run_ok(["git", "commit", "-qm", "install"], cwd=repo)
        bare = self.fake_github(repo)
        plan, path = self.plan("--project", repo)
        self.removed_upstream(repo, bare, plan)
        [scope] = self.apply(plan, path)["scopes"]
        self.assertEqual((scope["state"], scope["error"], scope["delivery"]), ("done", None, None), scope)
        self.assertEqual(self.run_ok(["git", "rev-parse", "HEAD"], cwd=repo).stdout,
                         self.run_ok(["git", "--git-dir", bare, "rev-parse", "main"]).stdout)
        self.assertFalse((repo / ".agents/skills/devlyn-ideate").exists())
        self.assertFalse(json.loads((self.root / "gh.json").read_text(encoding="utf-8")).get("prs"))
        self.assertEqual(self.run_ok(["git", "branch", "--list", "devlyn/cleanup-*"], cwd=repo).stdout.strip(), "")
        self.assertFalse(list((self.root / "behind.devlyn.noindex").glob("devlyn-cleanup-*")))

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_items_the_remote_base_already_settled_include_settings_edits(self):
        # Prediction: upstream removals plus the retired settings edit settle the whole review; apply is done,
        # fast-forwards to main, and leaves no PR, cleanup branch or worktree.
        repo, bare = self.installed_and_pushed("settled")
        settings = repo / ".claude/settings.json"
        settings.parent.mkdir(exist_ok=True)
        retired = {"type": "command", "command": 'python3 "$CLAUDE_PROJECT_DIR/.claude/skills/_shared/resolve-stop-hook.py"'}
        data = {"custom": "owner", "hooks": {"Stop": [{"hooks": [retired]}]}}
        settings.write_text(json.dumps(data) + "\n", encoding="utf-8")
        self.run_ok(["git", "add", ".claude/settings.json"], cwd=repo)
        self.run_ok(["git", "commit", "-qm", "retired settings"], cwd=repo)
        self.run_ok(["git", "push", "-q", "origin", "main"], cwd=repo)
        plan, path = self.plan("--project", repo)
        self.assertIn(("settings-entry", "edit", "settings.json", "delivery", None), self.actions(plan["scopes"][0]))
        cleaned = {"custom": "owner"}

        def edit(upstream):
            (upstream / ".claude/settings.json").write_text(json.dumps(cleaned, indent=2) + "\n", encoding="utf-8")
            self.run_ok(["git", "add", ".claude/settings.json"], cwd=upstream)

        self.removed_upstream(repo, bare, plan, also=edit)
        [scope] = self.apply(plan, path)["scopes"]
        self.assertEqual((scope["state"], scope["error"], scope["delivery"]), ("done", None, None), scope)
        self.assertEqual(self.run_ok(["git", "rev-parse", "HEAD"], cwd=repo).stdout,
                         self.run_ok(["git", "--git-dir", bare, "rev-parse", "main"]).stdout)
        self.assertEqual(json.loads(settings.read_text(encoding="utf-8")), cleaned)
        self.assertFalse(json.loads((self.root / "gh.json").read_text(encoding="utf-8")).get("prs"))
        self.assertEqual(self.run_ok(["git", "branch", "--list", "devlyn/cleanup-*"], cwd=repo).stdout.strip(), "")
        self.assertFalse(list((self.root / "settled.devlyn.noindex").glob("devlyn-cleanup-*")))

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_stale_delivery_leaves_checkout_until_the_next_review(self):
        # Prediction: changed upstream bytes fail stale-plan without deletion, PR or checkout update;
        # a fresh plan takes and reviews the base, then delivers successfully.
        repo, bare = self.installed_and_pushed("rewritten")
        (repo / "unrelated").mkdir()
        (repo / "unrelated/note").write_text("owner\n", encoding="utf-8")
        plan, path = self.plan("--project", repo)
        before = self.run_ok(["git", "rev-parse", "HEAD"], cwd=repo).stdout
        self.rewritten_upstream(repo, bare)
        base = self.run_ok(["git", "--git-dir", bare, "rev-parse", "main"]).stdout
        [scope] = self.apply(plan, path)["scopes"]
        self.assertEqual((scope["state"], scope["error"]["code"], scope["delivery"]), ("failed", "stale-plan", None), scope)
        self.assertIn(".agents/skills/devlyn-ideate", scope["error"]["params"]["detail"])
        self.assertFalse(json.loads((self.root / "gh.json").read_text(encoding="utf-8")).get("prs"))
        self.assertEqual(self.run_ok(["git", "branch", "--list", "devlyn/cleanup-*"], cwd=repo).stdout.strip(), "")
        self.assertFalse(list((self.root / "rewritten.devlyn.noindex").glob("devlyn-cleanup-*")))
        self.assertEqual(self.run_ok(["git", "rev-parse", "HEAD"], cwd=repo).stdout, before)
        self.assertEqual(self.run_ok(["git", "diff", "HEAD", "--"], cwd=repo).stdout, "")
        self.assertTrue(all(Path(item["path"]).exists() for item in plan["scopes"][0]["items"]))
        self.assertEqual((repo / "unrelated/note").read_text(encoding="utf-8"), "owner\n")
        plan, path = self.plan("--project", repo)
        self.assertEqual(self.run_ok(["git", "rev-parse", "HEAD"], cwd=repo).stdout, base)
        [scope] = self.apply(plan, path)["scopes"]
        self.assertEqual((scope["state"], scope["error"], scope["delivery"]["state"]), ("done", None, "merged"), scope)

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_stale_delivery_on_another_branch_requires_base_review(self):
        # Prediction: changed base bytes require a new base review even on another branch; report stale-plan,
        # keep HEAD and the copies unchanged, and release the allocation without opening a PR.
        repo, bare = self.installed_and_pushed("rewritten-feature")
        self.run_ok(["git", "checkout", "-qb", "work"], cwd=repo)
        before = self.run_ok(["git", "rev-parse", "HEAD"], cwd=repo).stdout
        plan, path = self.plan("--project", repo)
        self.rewritten_upstream(repo, bare)
        [scope] = self.apply(plan, path)["scopes"]
        self.assertEqual((scope["state"], scope["error"]["code"], scope["delivery"]), ("failed", "stale-plan", None), scope)
        self.assertEqual(self.run_ok(["git", "rev-parse", "HEAD"], cwd=repo).stdout, before)
        self.assertEqual(self.run_ok(["git", "diff", "HEAD", "--"], cwd=repo).stdout, "")
        self.assertTrue(all(Path(item["path"]).exists() for item in plan["scopes"][0]["items"]))
        self.assertFalse(json.loads((self.root / "gh.json").read_text(encoding="utf-8")).get("prs"))
        self.assertEqual(self.run_ok(["git", "branch", "--list", "devlyn/cleanup-*"], cwd=repo).stdout.strip(), "")
        self.assertFalse(list((self.root / "rewritten-feature.devlyn.noindex").glob("devlyn-cleanup-*")))

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_a_checkout_on_another_branch_is_left_and_asked_to_update(self):
        # Prediction: with another branch checked out, the copies the remote main dropped stay on disk and the scope
        # says the checkout needs updating; the branch is not moved and nothing is left allocated.
        repo = self.repo("feature")
        self.install(repo)
        self.run_ok(["git", "add", "-A"], cwd=repo)
        self.run_ok(["git", "commit", "-qm", "install"], cwd=repo)
        bare = self.fake_github(repo)
        self.run_ok(["git", "checkout", "-qb", "work"], cwd=repo)
        plan, path = self.plan("--project", repo)
        self.removed_upstream(repo, bare, plan)
        before = self.run_ok(["git", "rev-parse", "HEAD"], cwd=repo).stdout
        [scope] = self.apply(plan, path)["scopes"]
        self.assertEqual((scope["state"], scope["error"]["code"]), ("failed", "update-checkout"), scope)
        self.assertEqual(self.run_ok(["git", "rev-parse", "HEAD"], cwd=repo).stdout, before)
        self.assertTrue((repo / ".agents/skills/devlyn-ideate").exists())
        self.assertEqual(self.run_ok(["git", "branch", "--list", "devlyn/cleanup-*"], cwd=repo).stdout.strip(), "")
        self.assertFalse(list((self.root / "feature.devlyn.noindex").glob("devlyn-cleanup-*")))


    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_copies_the_remote_base_lacks_are_informational_leftovers(self):
        # Prediction: branch-only copies are tracked-copy skips; apply has no delivery actions and
        # allocates nothing. A renewed plan cannot offer the same impossible removal.
        repo = self.repo("unpushed")
        self.fake_github(repo)
        self.install(repo)
        self.run_ok(["git", "add", "-A"], cwd=repo)
        self.run_ok(["git", "commit", "-qm", "install, not pushed"], cwd=repo)
        plan, path = self.plan("--project", repo)
        [scope] = self.apply(plan, path)["scopes"]
        self.assertEqual((scope["state"], scope["error"]), ("skipped", None))
        self.assertTrue(all(i["action"] == "skip" and i["reasons"][0]["code"] == "tracked-copy"
                            for i in plan["scopes"][0]["items"]))
        self.assertEqual(self.run_ok(["git", "branch", "--list", "devlyn/cleanup-*"], cwd=repo).stdout.strip(), "")
        self.assertFalse(list((self.root / "unpushed.devlyn.noindex").glob("devlyn-cleanup-*")))

    @unittest.skipIf(os.name == "nt", "fake GitHub uses POSIX wrappers")
    def test_feature_branch_dirty_install_reviews_and_delivers_base(self):
        # Prediction: branch commits and dirty deletions/rewritten support never supply delivery
        # proofs. Plan preserves HEAD/index/files/FETCH_HEAD, one PR removes the old base copies,
        # reconciliation reports update-checkout, and a renewed review lists only skipped leftovers.
        repo, bare = self.installed_and_pushed("field-case")
        baseline, _ = self.plan("--project", repo)
        self.run_ok(["git", "checkout", "-qb", "feature/dashboard"], cwd=repo)
        (repo / "README.md").write_text("Feature work.\n")
        self.run_ok(["git", "commit", "-qam", "feature"], cwd=repo)
        root = repo / ".agents/skills"
        for name in ("devlyn-ideate", "devlyn-engines", "_shared"):
            shutil.rmtree(root / name)
        self.historical_skill(root / "_shared", name="_shared")
        (repo / ".git/FETCH_HEAD").write_text("Owner's fetch evidence\n")
        state = self.checkout_state(repo)
        plan, file = self.plan("--project", repo)
        self.assertEqual(self.checkout_state(repo), state)
        self.assertEqual([(i["relative"], i["action"], i["before"]) for i in plan["scopes"][0]["items"]],
                         [(i["relative"], i["action"], i["before"]) for i in baseline["scopes"][0]["items"]])
        self.assertEqual(plan["scopes"][0]["reviewBase"], self.run_ok(["git", "--git-dir", bare, "rev-parse", "main"]).stdout.strip())
        result = self.apply(plan, file)["scopes"][0]
        self.assertEqual((result["error"]["code"], result["delivery"]["state"]), ("update-checkout", "merged"))
        self.assertEqual(len(json.loads((self.root / "gh.json").read_text())["prs"]), 1)
        again, _ = self.plan("--project", repo)
        self.assertTrue(again["scopes"][0]["items"])
        self.assertTrue(all(i["action"] == "skip" and i["reasons"][0]["code"] == "update-checkout"
                            for i in again["scopes"][0]["items"]))
        self.assertEqual(self.checkout_state(repo)["head"], state["head"])
        self.assertEqual(self.checkout_state(repo)["files"], state["files"])

    @unittest.skipIf(os.name == "nt", "fake GitHub uses POSIX wrappers")
    def test_delivery_proofs_use_git_checkout_line_endings(self):
        # Prediction: installer-written LF marker, legacy file, settings and instructions are
        # reviewed as Git's CRLF checkout bytes under both autocrlf and attributes. Delivery opens a PR
        # without stale-plan; its in-process selfcheck reads its own committed bytes and records it.
        for mode in ("autocrlf", "attributes"):
            with self.subTest(mode=mode):
                repo = self.repo("eol-" + mode)
                self.run_ok(["git", "config", "core.autocrlf", "true" if mode == "autocrlf" else "false"], cwd=repo)
                self.install(repo)
                if mode == "attributes":
                    (repo / ".gitattributes").write_bytes(b"* text eol=crlf\n")
                legacy = repo / ".claude/commit-conventions.md"
                legacy.parent.mkdir(exist_ok=True)
                legacy.write_bytes(subprocess.check_output(["git", "show", "v3.0.1:config/commit-conventions.md"], cwd=ROOT))
                template = subprocess.check_output(["git", "show", "v3.0.1:CLAUDE.md"], cwd=ROOT).decode()
                body = "Project-specific instructions outside this managed block take precedence over these defaults.\n\n" + template.rstrip("\n") + "\n"
                instructions = repo / "CLAUDE.md"
                instructions.write_bytes(("<!-- devlyn:instructions:begin sha256=" + hashlib.sha256(body.encode()).hexdigest()
                                          + " -->\n" + body + "<!-- devlyn:instructions:end -->\n").encode())
                settings = repo / ".claude/settings.json"
                settings.write_text(json.dumps({"owner": True, "hooks": {"Stop": [{"hooks": [{"type": "command", "command":
                    'python3 "$CLAUDE_PROJECT_DIR/.claude/skills/_shared/resolve-stop-hook.py"'}]}]}}) + "\n")
                marker = repo / ".agents/skills/.devlyn-install.json"
                self.run_ok(["git", "add", "-A"], cwd=repo)
                self.run_ok(["git", "commit", "-qm", "LF install"], cwd=repo)
                self.fake_github(repo)
                self.run_ok(["git", "config", "devlyn.completionMode", "pr"], cwd=repo)
                for file in (marker, legacy, instructions, settings):
                    self.assertNotIn(b"\r\n", file.read_bytes())
                plan, file = self.plan("--project", repo)
                for target in (marker, legacy, instructions, settings):
                    matches = [i for i in plan["scopes"][0]["items"] if i["path"] == str(target)]
                    self.assertEqual(len(matches), 1, (str(target), plan["scopes"][0]["items"]))
                    [item] = matches
                    self.assertIn(item["action"], ("remove", "edit"))
                    self.assertEqual(item["before"]["sha256"], hashlib.sha256(target.read_bytes().replace(b"\n", b"\r\n")).hexdigest())
                result = self.apply(plan, file)["scopes"][0]
                self.assertEqual((result["state"], result["delivery"]["state"]), ("done", "pr-open"), result)
                trees = self.run_ok(["git", "worktree", "list", "--porcelain"], cwd=repo).stdout.splitlines()
                delivery = next(Path(line.removeprefix("worktree ")) for line in trees
                                if line.startswith("worktree ") and Path(line.removeprefix("worktree ")).name.startswith("devlyn-cleanup-"))
                acceptance = json.loads((delivery / ".devlyn/acceptance.json").read_text())
                self.assertEqual(acceptance["checks"][0]["command"],
                                 f"in-process cleanupProjectScan({json.dumps(str(delivery), ensure_ascii=False)}, current): verify readable scan and no actionable applied items")
                check = json.loads((delivery / ".devlyn/cleanup-check.json").read_text())
                self.assertTrue(check["ok"])
                self.assertFalse([i for i in check["data"]["scopes"][0]["items"] if i["action"] != "skip"])
                # Release this intentionally open fixture's worktree; no registration survives a test.
                self.run_ok(["git", "worktree", "remove", "--force", delivery], cwd=repo)

    @unittest.skipIf(os.name == "nt", "fake GitHub uses POSIX wrappers")
    def test_unreviewed_base_sibling_keeps_reviewed_support(self):
        # Prediction: a removable sibling added after review keeps reviewed _shared, refusing the
        # entire delivery as stale-plan; the next review contains both and safely delivers both.
        repo = self.repo("new-sibling")
        shared = repo / ".agents/skills/_shared"
        shutil.copytree(ROOT / "config/skills/_shared", shared)
        self.run_ok(["git", "add", "-A"], cwd=repo)
        self.run_ok(["git", "commit", "-qm", "support"], cwd=repo)
        bare = self.fake_github(repo)
        plan, file = self.plan("--project", repo)
        self.assertEqual([i["relative"] for i in plan["scopes"][0]["items"]], [".agents/skills/_shared"])
        upstream = self.root / "sibling-upstream"
        self.run_ok(["git", "clone", "-q", bare, upstream])
        shutil.copytree(ROOT / "config/skills/devlyn-ideate", upstream / ".agents/skills/devlyn-ideate")
        self.run_ok(["git", "add", "-A"], cwd=upstream)
        self.run_ok(["git", "commit", "-qm", "add sibling"], cwd=upstream)
        self.run_ok(["git", "push", "-q", "origin", "main"], cwd=upstream)
        result = self.apply(plan, file)["scopes"][0]
        self.assertEqual(result["error"]["code"], "stale-plan")
        self.run_ok(["git", "--git-dir", bare, "cat-file", "-e", "main:.agents/skills/_shared"])
        self.assertFalse(json.loads((self.root / "gh.json").read_text()).get("prs"))
        plan, file = self.plan("--project", repo)
        self.assertEqual({Path(i["path"]).name for i in plan["scopes"][0]["items"]}, {"_shared", "devlyn-ideate"})
        self.assertEqual(self.apply(plan, file)["scopes"][0]["delivery"]["state"], "merged")

    @unittest.skipIf(os.name == "nt", "fake GitHub uses POSIX wrappers")
    def test_surviving_caller_copies_always_keep_delivery_support(self):
        # Prediction: a new, unselected, changed, failed-removal or branch-only caller copy retains
        # both tracked support entries. None of these applies can publish their removal.
        for case in ("new", "unselected", "changed", "failed-removal", "branch-only"):
            with self.subTest(case=case):
                repo = self.repo("survivor-" + case)
                self.install(repo)
                root = repo / ".agents/skills"
                copy = root / "devlyn-ideate"
                shutil.rmtree(root / "devlyn-engines")
                if case in ("new", "branch-only"):
                    shutil.rmtree(copy)
                self.run_ok(["git", "add", ".agents/skills/_shared", ".agents/skills/.devlyn-install.json", "AGENTS.md"], cwd=repo)
                self.run_ok(["git", "commit", "-qm", "tracked support"], cwd=repo)
                bare = self.fake_github(repo)
                plan, file = self.plan("--project", repo)
                if case in ("new", "branch-only"):
                    shutil.copytree(ROOT / "config/skills/devlyn-ideate", copy)
                if case == "branch-only":
                    self.run_ok(["git", "add", ".agents/skills/devlyn-ideate"], cwd=repo)
                    self.run_ok(["git", "commit", "-qm", "branch-only copy"], cwd=repo)
                if case == "unselected":
                    plan["scopes"][0]["items"] = [i for i in plan["scopes"][0]["items"] if i["path"] != str(copy)]
                    del plan["digest"]
                    plan["digest"] = hashlib.sha256(json.dumps(plan, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
                    file.write_text(json.dumps(plan))
                if case == "changed":
                    (copy / "SKILL.md").write_text("Owner's replacement.\n")
                if case == "failed-removal":
                    preload = self.root / "failed-local-remove.cjs"
                    preload.write_text("const fs = require('fs'); const rm = fs.rmSync;\n"
                        f"fs.rmSync = (file, opts) => {{ if (file === {json.dumps(str(copy))}) throw new Error('fixture removal refused');\n"
                        "return rm(file, opts); };\n")
                    self.env["NODE_OPTIONS"] = "--require " + json.dumps(str(preload), ensure_ascii=False)
                result = self.apply(plan, file)["scopes"][0]
                self.env.pop("NODE_OPTIONS", None)
                self.assertEqual(result["error"]["code"], "apply-failed" if case == "failed-removal" else "stale-plan")
                self.assertIsNone(result["delivery"])
                self.assertTrue(copy.is_dir())
                for name in ("_shared", ".devlyn-install.json"):
                    self.assertTrue((root / name).exists())
                    self.run_ok(["git", "--git-dir", bare, "cat-file", "-e", f"main:.agents/skills/{name}"])
                self.assertFalse(json.loads((self.root / "gh.json").read_text()).get("prs"))

    @unittest.skipIf(os.name == "nt", "fake GitHub uses POSIX wrappers")
    def test_unselected_local_copy_at_a_delivered_path_keeps_support(self):
        # Prediction: delivering the base's copy does not count as removing an unselected local
        # copy at the very same relative path. The caller copy and upstream support survive.
        repo, bare = self.installed_and_pushed("surviving-route-collision")
        self.run_ok(["git", "checkout", "-qb", "work"], cwd=repo)
        relative = ".agents/skills/devlyn-ideate"
        self.run_ok(["git", "rm", "-r", "--cached", relative], cwd=repo)
        self.run_ok(["git", "commit", "-qm", "untrack copy"], cwd=repo)
        plan, file = self.plan("--project", repo)
        plan["scopes"][0]["items"] = [i for i in plan["scopes"][0]["items"] if i["route"] != "local"]
        del plan["digest"]
        plan["digest"] = hashlib.sha256(json.dumps(plan, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
        file.write_text(json.dumps(plan))
        result = self.apply(plan, file)["scopes"][0]
        self.assertEqual(result["delivery"]["state"], "merged")
        self.assertTrue((repo / relative).is_dir())
        for name in ("_shared", ".devlyn-install.json"):
            self.run_ok(["git", "--git-dir", bare, "cat-file", "-e", f"main:.agents/skills/{name}"])
        self.assertNotIn(relative, self.run_ok(["git", "--git-dir", bare, "ls-tree", "-r", "--name-only", "main"]).stdout)

    @unittest.skipIf(os.name == "nt", "fake GitHub uses POSIX wrappers")
    def test_caller_edited_untracked_copy_keeps_base_support(self):
        # Prediction: edited untracked copies are caller context even though absent on the base;
        # both base support entries stay as dependent-copy while other base copies can be delivered.
        repo, _ = self.installed_and_pushed("kept-local")
        kept = repo / ".agents/skills/workflow-routing"
        kept.mkdir()
        (kept / "SKILL.md").write_text("Owner copy.\n")
        plan, file = self.plan("--project", repo)
        support = [i for i in plan["scopes"][0]["items"] if Path(i["path"]).name in ("_shared", ".devlyn-install.json")]
        self.assertEqual(len(support), 2)
        self.assertTrue(all(i["route"] == "delivery" and i["reasons"][0]["code"] == "dependent-copy" for i in support))
        self.assertEqual(self.apply(plan, file)["scopes"][0]["delivery"]["state"], "merged")
        self.assertTrue((kept.parent / "_shared").exists())
        self.assertEqual((kept / "SKILL.md").read_text(), "Owner copy.\n")

    @unittest.skipIf(os.name == "nt", "fake GitHub uses POSIX wrappers")
    def test_same_path_local_and_base_have_distinct_routes(self):
        # Prediction: a branch that untracked a base copy reviews both provenances at the same path.
        # Local cleanup removes caller bytes, delivery removes base bytes, and neither shadows the other.
        repo, bare = self.installed_and_pushed("two-routes")
        self.run_ok(["git", "checkout", "-qb", "work"], cwd=repo)
        relative = ".agents/skills/devlyn-ideate"
        self.run_ok(["git", "rm", "-r", "--cached", relative], cwd=repo)
        self.run_ok(["git", "commit", "-qm", "untrack copy"], cwd=repo)
        plan, file = self.plan("--project", repo)
        copies = [i for i in plan["scopes"][0]["items"] if i["relative"] == relative]
        self.assertEqual({i["route"] for i in copies}, {"local", "delivery"})
        self.assertEqual(len({i["id"] for i in copies}), 2)
        self.assertTrue(all(i["action"] == "remove" for i in copies))
        result = self.apply(plan, file)["scopes"][0]
        self.assertEqual((result["error"]["code"], result["delivery"]["state"]), ("update-checkout", "merged"))
        self.assertFalse((repo / relative).exists())
        self.assertNotIn(relative, self.run_ok(["git", "--git-dir", bare, "ls-tree", "-r", "--name-only", "main"]).stdout)

    @unittest.skipIf(os.name == "nt", "fake GitHub uses POSIX wrappers")
    def test_caller_queue_and_install_occupancy_guard_base_items(self):
        # Prediction: queue/process/install-lock guards use caller paths even while proof reads the
        # snapshot. Modified copies expose each blocker in the plan, so include is never offered.
        repo, _ = self.installed_and_pushed("caller-busy")
        edited = repo / ".agents/skills/devlyn-ideate/SKILL.md"
        edited.write_text(edited.read_text() + "\nOwner edit.\n")
        self.run_ok(["git", "commit", "-qam", "modified copy"], cwd=repo)
        self.run_ok(["git", "push", "-q", "origin", "main"], cwd=repo)
        preload = self.root / "queue-busy.cjs"
        preload.write_text("const cp = require('child_process'); const spawn = cp.spawnSync;\n"
            "cp.spawnSync = (cmd, args, opts) => {\n"
            "if (args.includes('inspect') && args.some(a => a.endsWith('/queue.py'))) {\n"
            f"if (args[args.indexOf('--repo') + 1] !== {json.dumps(str(repo))}) throw new Error('queue checked outside caller');\n"
            "return {status:0, stdout:JSON.stringify({counts:{active:1}}), stderr:''}; }\n"
            "return spawn(cmd, args, opts); };\n")
        for blocker in ("legacy-queue", "in-use", "occupied-lock"):
            with self.subTest(blocker=blocker):
                if blocker == "legacy-queue": self.env["NODE_OPTIONS"] = "--require " + json.dumps(str(preload), ensure_ascii=False)
                if blocker == "in-use": self.env["FIXTURE_PROCESSES"] = f"python {repo}/.agents/skills/devlyn-ideate/run.py"
                lock = repo / ".agents/skills/.devlyn-install.lock"
                if blocker == "occupied-lock": lock.write_text("occupied")
                plan, file = self.plan("--project", repo)
                copies = [i for i in plan["scopes"][0]["items"] if i["route"] == "delivery"]
                self.assertTrue(copies)
                self.assertTrue(all(i["action"] == "skip" and i["reasons"][0]["code"] == blocker for i in copies))
                self.assertEqual(self.apply(plan, file, code=2, include=[copies[0]["id"]])["code"], "invalid-arguments")
                self.env.pop("NODE_OPTIONS", None)
                self.env.pop("FIXTURE_PROCESSES", None)
                if lock.exists(): lock.unlink()

    @unittest.skipIf(os.name == "nt", "fake GitHub uses POSIX wrappers")
    def test_snapshot_failure_releases_resources_without_fallback(self):
        # Prediction: even checkout-index failure after registration releases the owned snapshot/ref;
        # tracked items become repository-unreadable while local review and caller bytes survive.
        repo, _ = self.installed_and_pushed("snapshot-failure")
        local = repo / ".claude/skills/devlyn-engines"
        shutil.copytree(ROOT / "config/skills/devlyn-engines", local)
        state = self.checkout_state(repo)
        preload = self.root / "snapshot-failure.cjs"
        preload.write_text("const cp = require('child_process'); const spawn = cp.spawnSync;\n"
            "cp.spawnSync = (cmd, args, opts) => args.includes('checkout-index') || (args.includes('worktree') && args.includes('remove'))\n"
            "? {status:1, stdout:'', stderr:'fixture snapshot failure'} : spawn(cmd, args, opts);\n")
        self.env["NODE_OPTIONS"] = "--require " + json.dumps(str(preload), ensure_ascii=False)
        plan, _ = self.plan("--project", repo)
        self.env.pop("NODE_OPTIONS")
        self.assertEqual(self.checkout_state(repo), state)
        self.assertTrue(all(i["action"] == "skip" and i["reasons"][0]["code"] == "repository-unreadable"
                            for i in plan["scopes"][0]["items"] if i["route"] == "delivery"))
        self.assertEqual(next(i for i in plan["scopes"][0]["items"] if i["route"] == "local")["action"], "remove")

    @unittest.skipIf(os.name == "nt", "fake GitHub uses POSIX wrappers")
    def test_caller_guards_appearing_after_review_report_the_guard(self):
        # Prediction: unchanged base bytes refused by a late caller lock, process or queue report
        # that guard, even when the base advanced; no PR or failed delivery resources remain.
        for blocker in ("occupied-lock", "in-use", "legacy-queue"):
            with self.subTest(blocker=blocker):
                repo, bare = self.installed_and_pushed("late-" + blocker)
                plan, file = self.plan("--project", repo)
                if blocker == "occupied-lock":
                    (repo / ".agents/skills/.devlyn-install.lock").write_text("occupied")
                    upstream = self.root / "late-lock-upstream"
                    self.run_ok(["git", "clone", "-q", bare, upstream])
                    self.run_ok(["git", "commit", "--allow-empty", "-qm", "advance base"], cwd=upstream)
                    self.run_ok(["git", "push", "-q", "origin", "main"], cwd=upstream)
                if blocker == "in-use":
                    self.env["FIXTURE_PROCESSES"] = f"python {repo}/.agents/skills/devlyn-ideate/run.py"
                if blocker == "legacy-queue":
                    preload = self.root / "late-queue.cjs"
                    preload.write_text("const cp = require('child_process'); const spawn = cp.spawnSync;\n"
                        "cp.spawnSync = (cmd, args, opts) => args.includes('inspect') && args.some(a => a.endsWith('/queue.py'))\n"
                        "? {status:0, stdout:JSON.stringify({counts:{active:1}}), stderr:''} : spawn(cmd, args, opts);\n")
                    self.env["NODE_OPTIONS"] = "--require " + json.dumps(str(preload), ensure_ascii=False)
                result = self.apply(plan, file)["scopes"][0]
                self.env.pop("NODE_OPTIONS", None)
                self.env.pop("FIXTURE_PROCESSES", None)
                self.assertEqual(result["error"]["code"], blocker, result)
                self.assertIsNone(result["delivery"])
                self.assertFalse(json.loads((self.root / "gh.json").read_text()).get("prs"))
                self.assertEqual(self.run_ok(["git", "branch", "--list", "devlyn/cleanup-*"], cwd=repo).stdout, "")
                self.assertEqual(self.run_ok(["git", "worktree", "list", "--porcelain"], cwd=repo).stdout.count("worktree "), 1)

    @unittest.skipIf(os.name == "nt", "fake GitHub uses POSIX wrappers")
    def test_included_directory_late_guards_use_the_reviewed_proof_mode(self):
        # Prediction: unchanged included modified-directory bytes report the late lock/process
        # guard, with either an advanced or unchanged base, rather than a proof mismatch.
        for blocker in ("occupied-lock", "in-use"):
            with self.subTest(blocker=blocker):
                repo, bare = self.installed_and_pushed("included-late-" + blocker)
                edited = repo / ".agents/skills/devlyn-ideate/SKILL.md"
                edited.write_text(edited.read_text() + "\nOwner edit.\n")
                self.run_ok(["git", "commit", "-qam", "modified directory"], cwd=repo)
                self.run_ok(["git", "push", "-q", "origin", "main"], cwd=repo)
                plan, file = self.plan("--project", repo)
                chosen = next(i for i in plan["scopes"][0]["items"] if i["relative"] == ".agents/skills/devlyn-ideate")
                self.assertEqual(chosen["reasons"][0]["code"], "modified-copy")
                if blocker == "occupied-lock":
                    (repo / ".agents/skills/.devlyn-install.lock").write_text("occupied")
                    upstream = self.root / "included-late-upstream"
                    self.run_ok(["git", "clone", "-q", bare, upstream])
                    self.run_ok(["git", "commit", "--allow-empty", "-qm", "advance base"], cwd=upstream)
                    self.run_ok(["git", "push", "-q", "origin", "main"], cwd=upstream)
                else:
                    self.env["FIXTURE_PROCESSES"] = f"python {repo}/.agents/skills/devlyn-ideate/run.py"
                before = edited.read_bytes()
                result = self.apply(plan, file, include=[chosen["id"]])["scopes"][0]
                self.env.pop("FIXTURE_PROCESSES", None)
                self.assertEqual(result["error"]["code"], blocker, result)
                self.assertEqual(edited.read_bytes(), before)
                self.assertIsNone(result["delivery"])
                self.assertFalse(json.loads((self.root / "gh.json").read_text()).get("prs"))
                self.assertEqual(self.run_ok(["git", "branch", "--list", "devlyn/cleanup-*"], cwd=repo).stdout, "")
                self.assertEqual(self.run_ok(["git", "worktree", "list", "--porcelain"], cwd=repo).stdout.count("worktree "), 1)

    @unittest.skipIf(os.name == "nt", "fake GitHub uses POSIX wrappers")
    def test_post_commit_scan_failure_never_writes_acceptance(self):
        # Prediction: a filesystem scan failure after the delivery commit returns delivery-failed
        # with the actual error, writes no success evidence/acceptance, and never calls publication.
        repo, _ = self.installed_and_pushed("selfcheck-failure")
        plan, file = self.plan("--project", repo)
        trace = self.root / "selfcheck-trace.jsonl"
        preload = self.root / "selfcheck-failure.cjs"
        preload.write_text("const cp = require('child_process'); const spawn = cp.spawnSync; const fs = require('fs');\n"
            "const lstat = fs.lstatSync; const write = fs.writeFileSync; let committed = false;\n"
            "cp.spawnSync = (cmd, args, opts) => { const result = spawn(cmd, args, opts);\n"
            "if (cmd === 'git' && args.includes('commit') && args[1].includes('devlyn-cleanup-') && result.status === 0) committed = true;\n"
            "return result; };\n"
            "fs.lstatSync = (file, opts) => { if (committed && String(file).endsWith('/.agents/skills')) {\n"
            f"fs.appendFileSync({json.dumps(str(trace))}, JSON.stringify('scan failed') + '\\n');\n"
            "throw new Error('fixture post-commit scan failure'); } return lstat(file, opts); };\n"
            "fs.writeFileSync = (file, ...args) => { if (['/cleanup-check.json', '/acceptance.json'].some(name => String(file).endsWith(name)))\n"
            f"fs.appendFileSync({json.dumps(str(trace))}, JSON.stringify(String(file)) + '\\n');\n"
            "return write(file, ...args); };\n")
        self.env["NODE_OPTIONS"] = "--require " + json.dumps(str(preload), ensure_ascii=False)
        result = self.apply(plan, file)["scopes"][0]
        self.env.pop("NODE_OPTIONS")
        self.assertEqual(result["error"]["code"], "delivery-failed", result)
        self.assertIn("cleanupProjectScan: fixture post-commit scan failure", result["error"]["params"]["detail"])
        self.assertEqual([json.loads(line) for line in trace.read_text().splitlines()], ["scan failed"])
        self.assertFalse(json.loads((self.root / "gh.json").read_text()).get("prs"))
        self.assertEqual(self.run_ok(["git", "branch", "--list", "devlyn/cleanup-*"], cwd=repo).stdout, "")
        self.assertEqual(self.run_ok(["git", "worktree", "list", "--porcelain"], cwd=repo).stdout.count("worktree "), 1)

    @unittest.skipIf(os.name == "nt", "fake GitHub uses POSIX wrappers")
    def test_same_commit_different_checkout_bytes_reports_delivery_failure(self):
        # Prediction: changing checkout conversion after review at the identical commit cannot be
        # cured by an upstream refresh; strict proof reports delivery-failed with the changed path.
        repo, _ = self.installed_and_pushed("same-commit-eol")
        plan, file = self.plan("--project", repo)
        self.run_ok(["git", "config", "core.autocrlf", "true"], cwd=repo)
        result = self.apply(plan, file)["scopes"][0]
        self.assertEqual(result["error"]["code"], "delivery-failed")
        self.assertIn(".agents/skills/.devlyn-install.json", result["error"]["params"]["detail"])
        self.assertFalse(json.loads((self.root / "gh.json").read_text()).get("prs"))

    @unittest.skipIf(os.name == "nt", "fake GitHub uses POSIX wrappers")
    def test_caller_local_settings_keep_base_hook(self):
        # Prediction: caller-only local hook references retain the base script, both during review
        # and if added after review. Identical base bytes report dependent-copy when blocked at apply.
        self.ai_os_package()
        repo = self.repo("base-local-hook")
        script, settings, data = self.ai_os_install(repo)
        self.run_ok(["git", "add", "-A"], cwd=repo)
        self.run_ok(["git", "commit", "-qm", "hook pair"], cwd=repo)
        bare = self.fake_github(repo)
        original, file = self.plan("--project", repo)
        (repo / ".claude/settings.local.json").write_text(json.dumps(data))
        plan, _ = self.plan("--project", repo)
        [item] = [i for i in plan["scopes"][0]["items"] if i["kind"] == "legacy-hook"]
        self.assertEqual((item["route"], item["action"], item["reasons"][0]["code"]), ("delivery", "skip", "dependent-copy"))
        result = self.apply(original, file)["scopes"][0]
        self.assertEqual(result["error"]["code"], "dependent-copy", result)
        self.assertTrue(script.is_file())
        self.assertEqual(json.loads(settings.read_text()), data)
        self.run_ok(["git", "--git-dir", bare, "cat-file", "-e", "main:" + str(script.relative_to(repo))])
        self.assertFalse(json.loads((self.root / "gh.json").read_text()).get("prs"))

    def test_edited_install_marker_is_kept(self):
        # Prediction: the marker is also a removal category; owner-added fields are not installer bytes.
        self.install(self.root, "--global")
        marker = self.home / ".agents/skills/.devlyn-install.json"
        data = json.loads(marker.read_bytes())
        data["owner-note"] = "keep this"
        data["skills"]["constructor"] = "owner fingerprint"
        marker.write_text(json.dumps(data, indent=2) + "\n")
        plan, path = self.plan("--machine")
        item = next(i for i in plan["scopes"][0]["items"] if i["path"] == str(marker))
        self.assertEqual(item["action"], "skip")
        self.assertEqual(item["reasons"][0]["code"], "modified-copy")
        self.apply(plan, path)
        self.assertEqual(json.loads(marker.read_bytes()), data)

    def test_legacy_names_require_shipped_content(self):
        # Prediction: edits/additions under renamed or retired names and edited commands are skipped;
        # tagged originals (including npm's colon alias, CRLF and install stamps) are removable.
        root = self.home / ".agents/skills"
        for name, source in [("devlyn:ideate", "devlyn:ideate"), ("devlyn:queue", "devlyn:queue")]:
            with self.subTest(name=name):
                dest = root / name
                self.historical_skill(dest, name=source)
                plan, _ = self.plan("--machine")
                self.assertEqual(next(i for i in plan["scopes"][0]["items"] if i["path"] == str(dest))["action"], "remove")
                (dest / "owner.txt").write_text("mine")
                plan, _ = self.plan("--machine")
                item = next(i for i in plan["scopes"][0]["items"] if i["path"] == str(dest))
                self.assertEqual(item["action"], "skip")
                self.assertEqual(item["reasons"][0]["code"], "modified-copy")
        alias = root / "DEVLYN\uf03aENGINES"
        self.historical_skill(alias, name="devlyn:engines")
        for file in alias.rglob("*"):
            if file.is_file():
                file.write_bytes(file.read_bytes().replace(b"${CLAUDE_SKILL_DIR:-__DEVLYN_SKILL_DIR__}", b"${CLAUDE_SKILL_DIR:-" + str(alias).encode() + b"}").replace(b"\n", b"\r\n"))
        command = self.home / ".claude/commands/devlyn.review.md"
        command.parent.mkdir(parents=True)
        command.write_bytes(subprocess.check_output(["git", "show", "v0.5.0:config/commands/devlyn.review.md"], cwd=ROOT).replace(b"\n", b"\r\n"))
        plan, _ = self.plan("--machine")
        for target in [alias, command]:
            self.assertEqual(next(i for i in plan["scopes"][0]["items"] if i["path"] == str(target))["action"], "remove")
        command.write_bytes(command.read_bytes() + b"owner note\n")
        plan, path = self.plan("--machine")
        item = next(i for i in plan["scopes"][0]["items"] if i["path"] == str(command))
        self.assertEqual(item["action"], "skip")
        self.assertEqual(item["reasons"][0]["code"], "modified-copy")
        self.apply(plan, path)
        self.assertTrue(command.exists())
        self.assertTrue((root / "devlyn:ideate/owner.txt").exists())

    def test_old_writers_and_opted_in_addons_are_recognized(self):
        # Prediction (review MEDIUM): a byte-exact 4.2.0 marker (no skills field), and a command shipped from
        # .claude/commands before config/ existed, are proven copies; an opted-in current optional add-on under a
        # retired standard's name is not listed, so it does not hold _shared and the marker back.
        self.install(self.root, "--global")
        root = self.home / ".agents/skills"
        addon = root / "code-health-standards"
        addon.mkdir()
        (addon / "SKILL.md").write_bytes((ROOT / "optional-skills/code-health-standards/SKILL.md").read_bytes())
        marker = root / ".devlyn-install.json"
        marker.write_text(json.dumps({"schemaVersion": 1, "package": "devlyn-cli", "version": "4.2.0"}, indent=2) + "\n")
        command = self.home / ".claude/commands/devlyn.handoff.md"
        command.parent.mkdir(parents=True)
        command.write_bytes(subprocess.check_output(["git", "show", "7a90bdb4:.claude/commands/devlyn.handoff.md"], cwd=ROOT))
        plan, path = self.plan("--machine")
        listed = {Path(item["path"]): item["action"] for item in plan["scopes"][0]["items"]}
        self.assertNotIn(addon, listed)
        self.assertEqual((listed[root / "_shared"], listed[marker], listed[command]), ("remove", "remove", "remove"))
        self.apply(plan, path)
        self.assertEqual(sorted(entry.name for entry in root.iterdir()), ["code-health-standards"])
        self.assertFalse(command.exists())

    def test_unreadable_index_never_authorizes_local_cleanup(self):
        # Prediction: a corrupt index makes ownership unknown, including files not otherwise tracked.
        repo = self.repo("corrupt")
        self.install(repo)
        self.run_ok(["git", "add", "-A"], cwd=repo)
        (repo / ".git/index").write_bytes(b"corrupt index")
        plan, path = self.plan("--project", repo)
        self.assertTrue(plan["scopes"][0]["items"])
        self.assertTrue(all(i["action"] == "skip" and i["reasons"][0]["code"] == "repository-unreadable"
                            for i in plan["scopes"][0]["items"]))
        self.apply(plan, path)
        self.assertTrue((repo / ".agents/skills/devlyn-ideate/SKILL.md").exists())

    def test_machine_git_ownership_preserves_tracked_copies_and_support(self):
        # Prediction: home/dotfiles-tracked skills stay with untracked helpers; there is no PR route.
        self.install(self.root, "--global")
        self.run_ok(["git", "init", "-q"], cwd=self.home)
        self.run_ok(["git", "add", ".agents/skills/devlyn-ideate"], cwd=self.home)
        plan, path = self.plan("--machine")
        item = next(i for i in plan["scopes"][0]["items"] if i["path"] == str(self.home / ".agents/skills/devlyn-ideate"))
        self.assertEqual(item["action"], "skip")
        self.assertEqual(item["reasons"][0]["code"], "tracked-copy")
        self.apply(plan, path)
        for name in ["devlyn-ideate", "_shared", ".devlyn-install.json"]:
            self.assertTrue((self.home / ".agents/skills" / name).exists(), name)

    @unittest.skipIf(os.name == "nt", "fake GitHub uses POSIX wrappers")
    def test_delivery_identity_changes_refuse_before_allocation(self):
        # Prediction: changing origin or its default base invalidates review before even local deletion.
        repo = self.repo("identity")
        self.install(repo)
        self.run_ok(["git", "add", "-A"], cwd=repo)
        self.run_ok(["git", "commit", "-qm", "install"], cwd=repo)
        self.fake_github(repo)
        self.run_ok(["git", "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main"], cwd=repo)
        plan, path = self.plan("--project", repo)
        for change, restore in [
            (["remote", "set-url", "origin", "https://github.com/other/project.git"], ["remote", "set-url", "origin", "https://github.com/test/project.git"]),
            (["symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/other"], ["symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main"]),
        ]:
            with self.subTest(change=change):
                self.run_ok(["git", *change], cwd=repo)
                result = self.apply(plan, path)
                self.assertEqual(result["scopes"][0]["error"]["code"], "stale-plan")
                self.assertFalse((repo / ".git/devlyn-completion").exists())
                self.run_ok(["git", *restore], cwd=repo)

    @unittest.skipIf(os.name == "nt", "fake GitHub uses POSIX wrappers")
    def test_delivery_reviews_base_despite_different_caller_preimage(self):
        # Prediction: local commits do not supply delivery bytes; cleanup merges removal of the base
        # copy and reports update-checkout because the caller cannot fast-forward.
        repo = self.repo("different")
        self.install(repo)
        self.run_ok(["git", "add", "-A"], cwd=repo)
        self.run_ok(["git", "commit", "-qm", "install"], cwd=repo)
        bare = self.fake_github(repo)
        skill = repo / ".agents/skills/devlyn-ideate"
        shutil.rmtree(skill)
        self.historical_skill(skill)
        self.run_ok(["git", "add", "-A"], cwd=repo)
        self.run_ok(["git", "commit", "-qm", "another shipped copy, not pushed"], cwd=repo)
        before = self.run_ok(["git", "--git-dir", bare, "rev-parse", "main"]).stdout
        plan, path = self.plan("--project", repo)
        result = self.apply(plan, path)["scopes"][0]
        self.assertEqual(result["state"], "failed")
        self.assertEqual(result["error"]["code"], "update-checkout")
        self.assertEqual(result["delivery"]["state"], "merged")
        self.assertNotEqual(self.run_ok(["git", "--git-dir", bare, "rev-parse", "main"]).stdout, before)
        self.assertEqual(self.run_ok(["git", "branch", "--list", "devlyn/cleanup-*"], cwd=repo).stdout.strip(), "")
        self.assertFalse(list((self.root / "different.devlyn.noindex").glob("devlyn-cleanup-*")))

    @unittest.skipIf(os.name == "nt", "fake GitHub uses POSIX wrappers")
    def test_local_support_stays_beside_branch_only_copies(self):
        # Prediction: branch-only tracked copies are informational skips and keep local support.
        repo = self.repo("failed-mixed")
        self.fake_github(repo)
        self.install(repo)
        self.run_ok(["git", "add", ".agents/skills/devlyn-ideate", ".agents/skills/devlyn-engines"], cwd=repo)
        self.run_ok(["git", "commit", "-qm", "skills not pushed"], cwd=repo)
        plan, path = self.plan("--project", repo)
        result = self.apply(plan, path)
        self.assertEqual((result["scopes"][0]["state"], result["scopes"][0]["error"]), ("skipped", None))
        for name in ["devlyn-ideate", "_shared", ".devlyn-install.json"]:
            self.assertTrue((repo / ".agents/skills" / name).exists(), name)

    @unittest.skipIf(os.name == "nt", "fake GitHub uses POSIX wrappers")
    def test_local_support_stays_while_tracked_copies_await_delivery(self):
        # Prediction: PR mode leaves tracked copies on disk; untracked support must survive this apply.
        repo = self.repo("mixed")
        self.install(repo)
        self.run_ok(["git", "add", ".agents/skills/devlyn-ideate", ".agents/skills/devlyn-engines"], cwd=repo)
        self.run_ok(["git", "commit", "-qm", "skills only"], cwd=repo)
        self.fake_github(repo)
        self.run_ok(["git", "config", "devlyn.completionMode", "pr"], cwd=repo)
        plan, path = self.plan("--project", repo)
        result = self.apply(plan, path)
        self.assertEqual(result["scopes"][0]["delivery"]["state"], "pr-open")
        for name in ["devlyn-ideate", "_shared", ".devlyn-install.json"]:
            self.assertTrue((repo / ".agents/skills" / name).exists(), name)

if __name__ == "__main__":
    unittest.main(verbosity=2)
