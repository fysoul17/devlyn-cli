#!/usr/bin/env python3
"""Legacy cleanup fixtures: real installs made by this package's installer in temporary homes and
repositories, then `devlyn cleanup --plan` and `--apply`. No model calls; GitHub is task-complete's
own fake gh over a local bare repository."""
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
        path.write_text(json.dumps(plan), encoding="utf-8")
        return plan, path

    def apply(self, plan, path, code=0):
        return self.cli("cleanup", "--apply", "--plan-file", path, "--digest", plan["digest"], code=code)

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

    def test_the_home_folder_is_not_cleaned_as_a_project(self):
        # Prediction (review LOW): --project $HOME is skipped whole; the machine scope cleans those roots under its locks.
        self.install(self.root, "--global")
        self.run_ok(["git", "init", "-q"], cwd=self.home)
        plan, _ = self.plan("--project", self.home)
        self.assertEqual([(item["action"], item["reasons"][0]["code"]) for item in plan["scopes"][0]["items"]],
                         [("skip", "home-folder")])

    @unittest.skipIf(os.name == "nt", "fake gh and transport wrappers are POSIX shell scripts")
    def test_tracked_copies_are_delivered_by_the_project_policy(self):
        # Prediction: committed copies are removed on a fresh branch from the remote base, committed once and merged by
        # the default auto policy; the remote main loses the copies and keeps AGENTS.md's block and owner text.
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

if __name__ == "__main__":
    unittest.main(verbosity=2)
