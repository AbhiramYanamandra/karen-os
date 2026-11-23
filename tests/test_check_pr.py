"""Tests for scripts/check_pr.py. Secret-like fixtures are assembled at run time
so this file never contains a literal match for the patterns it tests."""
import importlib.util
import io
import pathlib
import tempfile
import unittest
from contextlib import redirect_stdout

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("check_pr", ROOT / "scripts" / "check_pr.py")
check_pr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_pr)

HOME = "/" + "Users" + "/someone/project"
GH_TOKEN = "gh" + "p_" + "A" * 36
PRIVATE_KEY = "-----BEGIN " + "PRIVATE KEY-----"
NOTION = "nt" + "n_" + "b" * 44


def diff_adding(*lines, path="docs/example.md"):
    body = "\n".join("+" + line for line in lines)
    return f"diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n@@ -0,0 +1 @@\n{body}\n"


class BranchTests(unittest.TestCase):
    def test_valid_branches(self):
        for name in ("feat/21-pipeline-script", "ci/22-pr-metadata-check", "fix/7-x", "docs/17-daily-review-proposal"):
            self.assertEqual(check_pr.check_branch(name), [], name)

    def test_invalid_branches(self):
        for name in ("main", "feature/21-x", "feat/pipeline", "feat/21_pipeline", "Feat/21-x", "feat/21-", "dependabot/npm/x", ""):
            self.assertTrue(check_pr.check_branch(name), name)


class BodyTests(unittest.TestCase):
    def test_links(self):
        for body in ("Closes #22", "closes #5.", "Refs #17", "Fixes AbhiramYanamandra/karen-os#31", "Why\n\nResolves #3"):
            self.assertEqual(check_pr.check_body(body), [], body)

    def test_missing_link(self):
        for body in ("", "Closes #", "See issue 22", "Closes 22", "#22 only"):
            self.assertTrue(check_pr.check_body(body), body)


class DiffTests(unittest.TestCase):
    def test_clean_diff(self):
        self.assertEqual(check_pr.check_diff(diff_adding("Run ~/.config/karen-os/ setup", "/home is fine", "Users/x")), [])

    def test_forbidden_content(self):
        for line, label in ((HOME, "home-directory path"), ("/home/ana/x", "home-directory path"),
                            ("token = " + GH_TOKEN, "GitHub token"), (PRIVATE_KEY, "private key"),
                            ("NOTION=" + NOTION, "Notion token")):
            problems = check_pr.check_diff(diff_adding(line, path="scripts/x.py"))
            self.assertEqual(len(problems), 1, line)
            self.assertIn(label, problems[0])
            self.assertIn("scripts/x.py", problems[0])

    def test_removed_lines_and_context_ignored(self):
        diff = f"+++ b/a.md\n-{HOME}\n {HOME}\n"
        self.assertEqual(check_pr.check_diff(diff), [])

    def test_allow_marker(self):
        self.assertEqual(check_pr.check_diff(diff_adding(HOME + "  # pr-check: allow")), [])

    def test_checker_source_does_not_flag_itself(self):
        source = (ROOT / "scripts" / "check_pr.py").read_text().splitlines()
        self.assertEqual(check_pr.check_diff(diff_adding(*source, path="scripts/check_pr.py")), [])


class CommandLineTests(unittest.TestCase):
    def run_cli(self, branch, body, diff):
        with tempfile.TemporaryDirectory() as tmp:
            body_file = pathlib.Path(tmp, "body.md")
            diff_file = pathlib.Path(tmp, "change.diff")
            body_file.write_text(body)
            diff_file.write_text(diff)
            out = io.StringIO()
            with redirect_stdout(out):
                code = check_pr.main(["--branch", branch, "--body-file", str(body_file), "--diff-file", str(diff_file)])
            return code, out.getvalue()

    def test_passing_pr(self):
        code, out = self.run_cli("ci/22-pr-metadata-check", "## Why\n\nCloses #22", diff_adding("hello"))
        self.assertEqual(code, 0)
        self.assertIn("ok", out)

    def test_failing_pr_reports_every_problem(self):
        code, out = self.run_cli("my-branch", "no link", diff_adding(HOME))
        self.assertEqual(code, 1)
        self.assertEqual(out.count("error:"), 3)


if __name__ == "__main__":
    unittest.main()
