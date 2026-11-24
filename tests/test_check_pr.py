"""Tests for scripts/check_pr.py. Secret-like fixtures are assembled at run time
so this file never contains a literal match for the patterns it tests."""
import importlib.util
import io
import json
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


REGISTRY = {e["id"]: e["sha256"] for e in json.loads((ROOT / "docs/organisation/skills.json").read_text())["entries"]}


def skill(skill_id, stage):
    return {"id": skill_id, "stage": stage, "sha256": REGISTRY[skill_id], "runtime": "claude-code",
            "evidence": "transcript: Base directory for this skill: <path>"}


def profile(**fields):
    """A valid low-risk chore block; keyword arguments override fields."""
    block = {"type": "chore", "risk": "low", "flags": [], "design_approval": "",
             "skills": [skill("ponytail-plugin", "implement"), skill("principle-prove-it-works", "verify")],
             "review": {"by": "", "session": "", "findings": ""}, "tests": ["unittest: 10 OK"],
             "owner_interventions": 0, "exceptions": []}
    block.update(fields)
    return "## Why\n\nCloses #22\n\n## Profile\n\n```karen-profile\n" + json.dumps(block, indent=2) + "\n```\n"


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
        for line, label in ((HOME, "home-directory path"), ("/" + "home/ana/x", "home-directory path"),
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
        code, out = self.run_cli("ci/22-pr-metadata-check", profile(), diff_adding("hello"))
        self.assertEqual(code, 0)
        self.assertIn("ok", out)

    def test_failing_pr_reports_every_problem(self):
        code, out = self.run_cli("my-branch", "no link", diff_adding(HOME))
        self.assertEqual(code, 1)
        self.assertEqual(out.count("error:"), 4)


REVIEW = {"by": "Codex gpt-6.1-sol", "session": "01a2-example", "findings": "none"}
FEATURE = dict(type="feat", risk="medium", flags=["design_required"],
               design_approval="https://github.com/o/r/pull/58", review=REVIEW,
               skills=[skill("ponytail-plugin", "implement"), skill("principle-prove-it-works", "verify"),
                       skill("code-review", "review")])


class ProfileTests(unittest.TestCase):
    """Checks 1 to 10 of docs/proposals/pr-enforcement.md, including the #46 simulations."""

    PINNED = {"docs/organisation/engineering.md"}

    def check(self, body, branch="feat/46-x", diff=None, merged=True, repo="o/r"):
        return check_pr.check_profile(branch, body, diff if diff is not None else diff_adding("x", path="scripts/a.py"),
                                      repo=repo, pr_merged=lambda _repo, _n: merged, pinned=self.PINNED)

    def assertOneProblem(self, problems, text):
        self.assertEqual(len(problems), 1, problems)
        self.assertIn(text, problems[0])

    def test_valid_feature_passes(self):
        self.assertEqual(self.check(profile(**FEATURE)), [])

    def test_missing_or_broken_block(self):
        self.assertOneProblem(self.check("Closes #46"), "no ```karen-profile block")
        self.assertOneProblem(self.check("```karen-profile\n{nope\n```"), "not valid JSON")
        self.assertOneProblem(self.check(profile(**dict(FEATURE, extra=1))), "unknown fields: extra")

    def test_type_must_fit_branch(self):
        self.assertOneProblem(self.check(profile(type="docs", skills=[skill("principle-prove-it-works", "verify")])),
                              "does not fit a feat/ branch")

    def test_skipped_required_skill_fails(self):
        skills = [s for s in FEATURE["skills"] if s["id"] != "ponytail-plugin"]
        self.assertOneProblem(self.check(profile(**dict(FEATURE, skills=skills))), "ponytail-plugin (implement) is not listed")

    def test_bogus_attestation_fails(self):
        wrong_hash = [dict(s, sha256="0" * 64) if s["id"] == "code-review" else s for s in FEATURE["skills"]]
        self.assertOneProblem(self.check(profile(**dict(FEATURE, skills=wrong_hash))), "code-review sha256 is not the registry version")
        no_evidence = [dict(s, evidence="") if s["id"] == "code-review" else s for s in FEATURE["skills"]]
        self.assertOneProblem(self.check(profile(**dict(FEATURE, skills=no_evidence))), "code-review has no load evidence")

    def test_owner_exception_waives_a_required_skill(self):
        skills = [s for s in FEATURE["skills"] if s["id"] != "ponytail-plugin"]
        exc = [{"skill": "ponytail-plugin", "stage": "implement", "scope": "this PR", "reference": "https://github.com/o/r/issues/46#c1"}]
        self.assertEqual(self.check(profile(**dict(FEATURE, skills=skills, exceptions=exc))), [])

    def test_missing_or_unmerged_design_approval_fails(self):
        self.assertOneProblem(self.check(profile(**dict(FEATURE, design_approval=""))), "must link the merged design PR")
        self.assertOneProblem(self.check(profile(**FEATURE), merged=False), "design PR is not merged")
        self.assertOneProblem(self.check(profile(**FEATURE), repo="o/other"), "must be a PR in o/other")

    def test_unconfirmable_merge_fails_closed(self):
        def broken(_repo, _n):
            raise OSError("gh not found")
        problems = check_pr.check_profile("feat/46-x", profile(**FEATURE), diff_adding("x"), repo="o/r",
                                          pr_merged=broken, pinned=self.PINNED)
        self.assertOneProblem(problems, "could not confirm")

    def test_self_review_at_medium_risk_fails(self):
        self.assertOneProblem(self.check(profile(**dict(FEATURE, review=dict(REVIEW, by="self")))), "medium risk needs a review")
        self.assertOneProblem(self.check(profile(**dict(FEATURE, review={}))), "medium risk needs a review")

    def test_unflagged_workflow_change_fails_and_raises_risk(self):
        diff = diff_adding("permissions: write-all", path=".github/workflows/checks.yml")
        problems = self.check(profile(), branch="chore/9-x", diff=diff)
        self.assertEqual(len(problems), 3, problems)
        self.assertIn("needs flag 'ci_change'", problems[0])
        self.assertTrue(any("code-review (review) is not listed" in p for p in problems))
        self.assertTrue(any("medium risk needs a review" in p for p in problems))

    def test_pinned_policy_and_new_dependency_need_flags(self):
        pinned = self.check(profile(), branch="chore/9-x", diff=diff_adding("x", path="docs/organisation/engineering.md"))
        self.assertIn("needs flag 'pinned_policy'", pinned[0])
        dep = self.check(profile(), branch="chore/9-x", diff=diff_adding("requests==2.0", path="requirements.txt"))
        self.assertIn("needs flag 'new_dependency'", dep[0])

    def test_tests_and_owner_interventions_are_recorded(self):
        self.assertOneProblem(self.check(profile(**dict(FEATURE, tests=[]))), "tests is empty")
        self.assertOneProblem(self.check(profile(**dict(FEATURE, owner_interventions=True))), "owner_interventions")

    # Regression tests for the Codex review of #46 (session 01a20c17).
    def test_quoted_unicode_workflow_path_still_needs_ci_change(self):
        path = '".github/workflows/caf\\303\\251.yml"'
        diff = ('diff --git "a/.github/workflows/caf\\303\\251.yml" "b/.github/workflows/caf\\303\\251.yml"\n'
                '--- /dev/null\n+++ ' + path[:1] + 'b/' + path[1:] + '\n@@ -0,0 +1 @@\n+on: push\n')
        self.assertEqual(check_pr.changed_files(diff), {".github/workflows/caf\u00e9.yml"})
        problems = self.check(profile(), branch="chore/9-x", diff=diff)
        self.assertIn("needs flag 'ci_change'", problems[0])

    def test_project_profile_is_enforced(self):
        stricter = {"profiles": {"feature": {"stages": {"verify": {"skills": {"tdd": "required"}}}}}}
        problems = check_pr.check_profile("feat/46-x", profile(**FEATURE), diff_adding("x", path="a.py"), repo="o/r",
                                          pr_merged=lambda *_: True, pinned=self.PINNED, project=stricter)
        self.assertOneProblem(problems, "tdd (verify) is not listed")
        looser = {"profiles": {"feature": {"stages": {"implement": {"skills": {"ponytail-plugin": "optional"}}}}}}
        problems = check_pr.check_profile("feat/46-x", profile(**FEATURE), diff_adding("x", path="a.py"), repo="o/r",
                                          pr_merged=lambda *_: True, pinned=self.PINNED, project=looser)
        self.assertOneProblem(problems, "conflict")

    def test_skill_stage_runtime_and_optional_evidence_are_checked(self):
        wrong_stage = [dict(s, stage="verify") if s["id"] == "code-review" else s for s in FEATURE["skills"]]
        self.assertOneProblem(self.check(profile(**dict(FEATURE, skills=wrong_stage))), "code-review (review) is not listed for that stage")
        no_runtime = [dict(s, runtime="") if s["id"] == "code-review" else s for s in FEATURE["skills"]]
        self.assertOneProblem(self.check(profile(**dict(FEATURE, skills=no_runtime))), "code-review has no runtime")
        optional = FEATURE["skills"] + [dict(skill("tdd", "implement"), evidence="")]
        self.assertOneProblem(self.check(profile(**dict(FEATURE, skills=optional))), "tdd has no load evidence")
        incompatible = [dict(s, runtime="cursor") if s["id"] == "code-review" else s for s in FEATURE["skills"]]
        self.assertOneProblem(self.check(profile(**dict(FEATURE, skills=incompatible))), "code-review is not approved for runtime cursor")

    def test_rename_out_of_a_guarded_folder_still_needs_its_flag(self):
        # Regression for the Codex re-review of #46 (session 01a20c1a).
        rename = ("diff --git a/.github/workflows/checks.yml b/old/checks.yml\nsimilarity index 100%\n"
                  "rename from .github/workflows/checks.yml\nrename to old/checks.yml\n")
        self.assertEqual(check_pr.changed_files(rename), {".github/workflows/checks.yml", "old/checks.yml"})
        self.assertIn("needs flag 'ci_change'", self.check(profile(), branch="chore/9-x", diff=rename)[0])
        moved = "diff --git a/docs/organisation/engineering.md b/docs/old.md\nrename from x\nrename to y\n"
        self.assertIn("needs flag 'pinned_policy'", self.check(profile(), branch="chore/9-x", diff=moved)[0])

    def test_ambiguous_header_cannot_hide_a_rename_into_a_guarded_folder(self):
        # Regression for the final Codex check of #46 (session 01a20c1e).
        for verb in ("rename", "copy"):
            diff = ("diff --git a/old b/name.yml b/.github/workflows/new.yml\nsimilarity index 100%%\n"
                    "%s from old b/name.yml\n%s to .github/workflows/new.yml\n" % (verb, verb))
            with self.subTest(verb=verb):
                self.assertIn(".github/workflows/new.yml", check_pr.changed_files(diff))
                self.assertIn("needs flag 'ci_change'", self.check(profile(), branch="chore/9-x", diff=diff)[0])
        pinned = ("diff --git a/x b/y b/docs/organisation/engineering.md\n--- a/x b/y\n"
                  "+++ b/docs/organisation/engineering.md\n@@ -1 +1 @@\n-a\n+b\n")
        self.assertIn("needs flag 'pinned_policy'", self.check(profile(), branch="chore/9-x", diff=pinned)[0])

    def test_unicode_line_separator_in_a_path_cannot_hide_it(self):
        # Regression for the Codex confirmation pass of #46 (session 01a20c21).
        name = ".github/workflows/a\u2028b.yml"
        for extra in ("old mode 100644\nnew mode 100755\n", "Binary files a/%s and b/%s differ\n" % (name, name)):
            diff = "diff --git a/%s b/%s\n%s" % (name, name, extra)
            with self.subTest(extra=extra[:10]):
                self.assertIn(name, check_pr.changed_files(diff))
                self.assertIn("needs flag 'ci_change'", self.check(profile(), branch="chore/9-x", diff=diff)[0])

    def test_workflow_rechecks_edited_descriptions(self):
        workflow = (ROOT / ".github/workflows/checks.yml").read_text()
        self.assertRegex(workflow, r"pull_request:\n\s+types: \[[^\]]*\bedited\b")

    def test_unknown_risk_is_reported(self):
        self.assertOneProblem(self.check(profile(**dict(FEATURE, risk="extreme"))), "unknown risk")


if __name__ == "__main__":
    unittest.main()
