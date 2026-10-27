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

    def run_ok(self, argv, cwd=None, code=0):
        result = subprocess.run([str(part) for part in argv], cwd=cwd or self.root, env=self.env, capture_output=True,
                                text=True, encoding="utf-8")
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return result

    def cli(self, *args, cwd=None, code=0):
        result = self.run_ok(["node", CLI, *args, "--json"], cwd=cwd, code=code)
        envelope = json.loads(result.stdout.strip().splitlines()[-1])
        return envelope["data"] if envelope["ok"] else envelope["error"]

    def repo(self, name):
        repo = self.root / name
        repo.mkdir()
        self.run_ok(["git", "init", "-q", "--initial-branch=main"], cwd=repo)
        (repo / "README.md").write_text("# project\n", encoding="utf-8")
        self.run_ok(["git", "add", "README.md"], cwd=repo)
        self.run_ok(["git", "commit", "-qm", "init"], cwd=repo)
        return repo

    def install(self, cwd, *flags):
        self.run_ok(["node", CLI, "-y", *flags], cwd=cwd)

    def plan(self, *args):
        plan = self.cli("cleanup", "--plan", *args)
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
        # cannot prove unchanged bytes, so --include refuses it as stale-plan and keeps all contents.
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
        result = self.apply(plan, path, include=[item["id"]])
        self.assertEqual(result["scopes"][0]["error"]["code"], "stale-plan")
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
                result = self.apply(plan, path, include=[chosen["id"]])
                self.assertEqual(result["scopes"][0]["error"]["code"], "stale-plan")
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
        # delivery is refused before deletion or PR, then main takes those upstream bytes.
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
        self.assertEqual(edited.read_text(), "Another owner's edit.\n")
        self.assertTrue((edited.parent.parent / "devlyn-engines").is_dir())
        self.assertEqual(self.run_ok(["git", "branch", "--list", "devlyn/cleanup-*"], cwd=repo).stdout, "")

    def test_include_keeps_dependent_local_support_and_refuses_no_remote(self):
        # Prediction: local support retained for a tracked copy remains dependent-copy when that
        # modified copy is included; without a remote the chosen copy fails proof before any removal.
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
        result = self.apply(plan, path, include=[chosen["id"]])
        self.assertEqual(result["scopes"][0]["error"]["code"], "stale-plan")
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
        cleaned = {"custom": "owner", "hooks": {"Stop": []}}
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
    def test_plan_refreshes_both_scopes_sharing_a_behind_checkout(self):
        # Prediction: when two project inputs share a behind checkout, both scopes review the base copy's
        # preimage even though only the first scope's update moves HEAD.
        repo, bare = self.installed_and_pushed("plan-shared")
        self.rewritten_upstream(repo, bare)
        base = self.run_ok(["git", "--git-dir", bare, "rev-parse", "main"]).stdout
        expected = self.run_ok(
            ["node", "-e", "const {fingerprint}=require(process.argv[1]);console.log(fingerprint(process.argv[2]))",
             ROOT / "bin/skill-ownership.js", self.root / "plan-shared-upstream/.agents/skills/devlyn-ideate"]).stdout.strip()
        plan, _ = self.plan("--project", repo, "--project", repo / ".agents")
        self.assertEqual(self.run_ok(["git", "rev-parse", "HEAD"], cwd=repo).stdout, base)
        self.assertEqual(len(plan["scopes"]), 2)
        for scope in plan["scopes"]:
            with self.subTest(scope=scope["id"]):
                item = next(i for i in scope["items"] if i["relative"] == ".agents/skills/devlyn-ideate")
                self.assertEqual((item["action"], item["route"], item["before"]),
                                 ("remove", "delivery", {"type": "directory", "sha256": expected}))

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_plan_on_another_branch_reviews_the_local_copy(self):
        # Prediction: a rewritten base does not move another branch during planning; the review keeps the local
        # preimage and apply still reports update-checkout without moving HEAD.
        repo, bare = self.installed_and_pushed("plan-feature")
        self.rewritten_upstream(repo, bare)
        self.run_ok(["git", "checkout", "-qb", "work"], cwd=repo)
        before = self.run_ok(["git", "rev-parse", "HEAD"], cwd=repo).stdout
        expected = self.run_ok(
            ["node", "-e", "const {fingerprint}=require(process.argv[1]);console.log(fingerprint(process.argv[2]))",
             ROOT / "bin/skill-ownership.js", repo / ".agents/skills/devlyn-ideate"]).stdout.strip()
        plan, path = self.plan("--project", repo)
        self.assertEqual(self.run_ok(["git", "rev-parse", "HEAD"], cwd=repo).stdout, before)
        item = next(i for i in plan["scopes"][0]["items"] if i["relative"] == ".agents/skills/devlyn-ideate")
        self.assertEqual((item["action"], item["route"], item["before"]),
                         ("remove", "delivery", {"type": "directory", "sha256": expected}))
        [scope] = self.apply(plan, path)["scopes"]
        self.assertEqual((scope["state"], scope["error"]["code"]), ("failed", "update-checkout"), scope)
        self.assertEqual(self.run_ok(["git", "rev-parse", "HEAD"], cwd=repo).stdout, before)

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_plan_with_an_unreachable_remote_keeps_the_local_review(self):
        # Prediction: a failed fetch still returns the local review with HEAD unchanged and no owned ref left.
        repo, bare = self.installed_and_pushed("plan-offline")
        self.rewritten_upstream(repo, bare)
        shutil.rmtree(bare)
        before = self.run_ok(["git", "rev-parse", "HEAD"], cwd=repo).stdout
        expected = self.run_ok(
            ["node", "-e", "const {fingerprint}=require(process.argv[1]);console.log(fingerprint(process.argv[2]))",
             ROOT / "bin/skill-ownership.js", repo / ".agents/skills/devlyn-ideate"]).stdout.strip()
        plan, _ = self.plan("--project", repo)
        self.assertEqual(self.run_ok(["git", "rev-parse", "HEAD"], cwd=repo).stdout, before)
        item = next(i for i in plan["scopes"][0]["items"] if i["relative"] == ".agents/skills/devlyn-ideate")
        self.assertEqual((item["action"], item["route"], item["before"]),
                         ("remove", "delivery", {"type": "directory", "sha256": expected}))
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
        cleaned = {"custom": "owner", "hooks": {"Stop": []}}

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
    def test_stale_delivery_updates_a_behind_checkout_for_the_next_review(self):
        # Prediction: changed upstream bytes still fail stale-plan without deletion or a PR, but main takes
        # the base; a fresh plan then reviews those bytes and delivers successfully.
        repo, bare = self.installed_and_pushed("rewritten")
        (repo / "unrelated").mkdir()
        (repo / "unrelated/note").write_text("owner\n", encoding="utf-8")
        plan, path = self.plan("--project", repo)
        self.rewritten_upstream(repo, bare)
        base = self.run_ok(["git", "--git-dir", bare, "rev-parse", "main"]).stdout
        [scope] = self.apply(plan, path)["scopes"]
        self.assertEqual((scope["state"], scope["error"]["code"], scope["delivery"]), ("failed", "stale-plan", None), scope)
        self.assertIn(".agents/skills/devlyn-ideate", scope["error"]["params"]["detail"])
        self.assertFalse(json.loads((self.root / "gh.json").read_text(encoding="utf-8")).get("prs"))
        self.assertEqual(self.run_ok(["git", "branch", "--list", "devlyn/cleanup-*"], cwd=repo).stdout.strip(), "")
        self.assertFalse(list((self.root / "rewritten.devlyn.noindex").glob("devlyn-cleanup-*")))
        self.assertEqual(self.run_ok(["git", "rev-parse", "HEAD"], cwd=repo).stdout, base)
        self.assertEqual(self.run_ok(["git", "diff", "HEAD", "--"], cwd=repo).stdout, "")
        self.assertTrue(all(Path(item["path"]).exists() for item in plan["scopes"][0]["items"]))
        self.assertEqual((repo / "unrelated/note").read_text(encoding="utf-8"), "owner\n")
        plan, path = self.plan("--project", repo)
        [scope] = self.apply(plan, path)["scopes"]
        self.assertEqual((scope["state"], scope["error"], scope["delivery"]["state"]), ("done", None, "merged"), scope)

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_stale_delivery_on_another_branch_requires_checkout_update(self):
        # Prediction: a behind checkout on another branch cannot take the changed base; report update-checkout,
        # keep HEAD and the copies unchanged, and release the allocation without opening a PR.
        repo, bare = self.installed_and_pushed("rewritten-feature")
        self.run_ok(["git", "checkout", "-qb", "work"], cwd=repo)
        before = self.run_ok(["git", "rev-parse", "HEAD"], cwd=repo).stdout
        plan, path = self.plan("--project", repo)
        self.rewritten_upstream(repo, bare)
        [scope] = self.apply(plan, path)["scopes"]
        self.assertEqual((scope["state"], scope["error"]["code"], scope["delivery"]), ("failed", "update-checkout", None), scope)
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
    def test_copies_the_remote_base_lacks_fail_and_release_the_allocation(self):
        # Prediction (review MEDIUM): copies committed locally but not pushed are not on the remote base; apply fails the
        # scope as stale-plan instead of reporting done, and leaves no cleanup worktree or branch behind.
        repo = self.repo("unpushed")
        self.fake_github(repo)
        self.install(repo)
        self.run_ok(["git", "add", "-A"], cwd=repo)
        self.run_ok(["git", "commit", "-qm", "install, not pushed"], cwd=repo)
        plan, path = self.plan("--project", repo)
        [scope] = self.apply(plan, path)["scopes"]
        self.assertEqual((scope["state"], scope["error"]["code"]), ("failed", "stale-plan"))
        self.assertEqual(self.run_ok(["git", "branch", "--list", "devlyn/cleanup-*"], cwd=repo).stdout.strip(), "")
        self.assertFalse(list((self.root / "unpushed.devlyn.noindex").glob("devlyn-cleanup-*")))

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
    def test_delivery_rejects_different_shipped_preimage(self):
        # Prediction: two proven shipped versions still differ in reviewed bytes; no PR is authorized.
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
        self.assertEqual(result["error"]["code"], "stale-plan")
        self.assertIn(".agents/skills/devlyn-ideate", result["error"]["params"]["detail"])
        self.assertEqual(self.run_ok(["git", "--git-dir", bare, "rev-parse", "main"]).stdout, before)
        self.assertEqual(self.run_ok(["git", "branch", "--list", "devlyn/cleanup-*"], cwd=repo).stdout.strip(), "")
        self.assertFalse(list((self.root / "different.devlyn.noindex").glob("devlyn-cleanup-*")))

    @unittest.skipIf(os.name == "nt", "fake GitHub uses POSIX wrappers")
    def test_local_support_stays_when_delivery_fails(self):
        # Prediction: an unpushed tracked copy fails delivery, but still needs local helpers afterward.
        repo = self.repo("failed-mixed")
        self.fake_github(repo)
        self.install(repo)
        self.run_ok(["git", "add", ".agents/skills/devlyn-ideate", ".agents/skills/devlyn-engines"], cwd=repo)
        self.run_ok(["git", "commit", "-qm", "skills not pushed"], cwd=repo)
        plan, path = self.plan("--project", repo)
        result = self.apply(plan, path)
        self.assertEqual(result["scopes"][0]["error"]["code"], "stale-plan")
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
