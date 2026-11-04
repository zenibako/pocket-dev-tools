"""Test-build version numbering shared by the Pocket ports."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import pocket_version

SCRIPT = Path(__file__).resolve().parent / "pocket_version.py"


class PocketVersionTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.repo = Path(temp.name)
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "Test")
        self.git("config", "commit.gpgsign", "false")
        self.git("config", "tag.gpgsign", "false")
        self.core_json = self.repo / "core.json"
        self.commit("0.1.0")
        self.git("tag", "v0.1.0")

    def git(self, *args):
        subprocess.run(["git", "-C", str(self.repo), *args], check=True, capture_output=True)

    def commit(self, version):
        self.core_json.write_text(json.dumps({"core": {"metadata": {"version": version}}}))
        self.git("add", "core.json")
        self.git("commit", "-q", "--allow-empty", "-m", version)

    def version(self, **kwargs):
        return pocket_version.test_version(self.repo, **kwargs)

    def test_bumps_the_patch_and_counts_commits_since_the_tag(self):
        self.assertEqual(self.version(), "0.1.1-rc.0")
        self.commit("0.1.0")
        self.commit("0.1.0")
        self.assertEqual(self.version(core_json=self.core_json), "0.1.1-rc.2")

    def test_uses_the_newest_tag_merged_into_head(self):
        self.commit("0.1.0")
        self.git("tag", "v0.2.0")
        self.git("tag", "v0.10.0", "HEAD~1")
        self.git("tag", "not-a-release")
        self.commit("0.2.0")
        self.assertEqual(self.version(), "0.10.1-rc.2")

    def test_ignores_tags_not_merged_into_head(self):
        self.git("checkout", "-q", "-b", "side")
        self.commit("0.1.0")
        self.git("tag", "v0.9.0")
        self.git("checkout", "-q", "-")
        self.assertEqual(self.version(), "0.1.1-rc.0")

    def test_prefers_a_committed_release_prep_bump(self):
        self.commit("0.3.0")
        self.assertEqual(self.version(core_json=self.core_json), "0.3.0-rc.1")
        # Without --core-json the bump is not consulted.
        self.assertEqual(self.version(), "0.1.1-rc.1")

    def test_ignores_a_committed_version_that_is_not_newer(self):
        self.commit("0.0.1")
        self.assertEqual(self.version(core_json=self.core_json), "0.1.1-rc.1")

    def test_next_version_overrides_and_must_be_newer(self):
        self.commit("0.3.0")
        self.assertEqual(self.version(core_json=self.core_json, next_version="v1.0.0"), "1.0.0-rc.1")
        with self.assertRaisesRegex(pocket_version.VersionError, "newer than v0.1.0"):
            self.version(next_version="0.1.0")
        with self.assertRaisesRegex(pocket_version.VersionError, "MAJOR.MINOR.PATCH"):
            self.version(next_version="1.0")

    def test_rejects_versions_longer_than_core_json_allows(self):
        with self.assertRaisesRegex(pocket_version.VersionError, "31"):
            self.version(next_version="0.1." + "9" * 30)

    def test_explains_a_missing_tag(self):
        self.git("tag", "-d", "v0.1.0")
        with self.assertRaisesRegex(pocket_version.VersionError, "--unshallow --tags"):
            self.version()

    def test_cli_prints_the_version_and_fails_cleanly(self):
        run = lambda *args, **env: subprocess.run(
            [sys.executable, str(SCRIPT), "--repo", str(self.repo), *args],
            env=dict(os.environ, **env), capture_output=True, text=True)
        good = run("--core-json", str(self.core_json))
        self.assertEqual((good.returncode, good.stdout), (0, "0.1.1-rc.0\n"))
        self.assertEqual(run(NEXT_VERSION="2.0.0").stdout, "2.0.0-rc.0\n")
        bad = run(NEXT_VERSION="0.0.9")
        self.assertEqual((bad.returncode, bad.stdout), (1, ""))
        self.assertIn("newer than v0.1.0", bad.stderr)
        empty = tempfile.TemporaryDirectory()
        self.addCleanup(empty.cleanup)
        outside = subprocess.run([sys.executable, str(SCRIPT), "--repo", empty.name],
                                 capture_output=True, text=True)
        self.assertEqual(outside.returncode, 1)
        self.assertIn("pocket_version:", outside.stderr)


if __name__ == "__main__":
    unittest.main()
