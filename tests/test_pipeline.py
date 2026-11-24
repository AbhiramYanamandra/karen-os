"""Tests for scripts/pipeline.py with a fake runner and recorded gh output. No network."""
import importlib.util
import io
import json
import pathlib
import unittest
from contextlib import redirect_stderr, redirect_stdout

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("pipeline", ROOT / "scripts" / "pipeline.py")
pipeline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pipeline)

REPO = "octo/demo"
BOARD = {"owner": "octo", "project_number": 1, "status_field": "Status", "repositories": [REPO, "octo/other"]}
OPTIONS = {"Backlog": "opt-backlog", "Ready": "opt-ready", "In Progress": "opt-progress", "Review": "opt-review", "Done": "opt-done"}
FIELDS = {"fields": [{"id": "field-status", "name": "Status", "type": "ProjectV2SingleSelectField",
                      "options": [{"id": v, "name": k} for k, v in OPTIONS.items()]}]}


def url(kind, n, repo=REPO):
    return "https://github.com/%s/%s/%d" % (repo, kind, n)


def item(item_id, kind, n, status, repo=REPO):
    return {"id": item_id, "status": status,
            "content": {"number": n, "repository": repo, "type": "Issue" if kind == "issues" else "PullRequest", "url": url(kind, n, repo)}}


def issue(n=21, labels=("P1", "type:feat", "status:ready"), state="OPEN", title="Pipeline script: claim, PR, ready and cleanup", comments=()):
    return {"number": n, "title": title, "state": state, "url": url("issues", n),
            "labels": [{"name": l} for l in labels], "comments": [{"body": b} for b in comments]}


class FakeRunner(pipeline.Runner):
    """Answers commands by prefix. A response is stdout, (code, stdout, stderr), JSON data, or a Seq used in turn."""

    def __init__(self, rules):
        super().__init__()
        self.rules = [(tuple(prefix), response) for prefix, response in rules]
        self.calls = []

    def execute(self, args):
        self.calls.append(tuple(args))
        for prefix, response in self.rules:
            if tuple(args[:len(prefix)]) == prefix:
                if isinstance(response, Seq):
                    response = response.next()
                if isinstance(response, tuple):
                    return response
                if isinstance(response, (dict, list)):
                    return 0, json.dumps(response), ""
                return 0, response, ""
        raise AssertionError("unexpected command: %s" % " ".join(args))

    def called(self, *prefix):
        return [c for c in self.calls if c[:len(prefix)] == prefix]


class Seq:
    """Responses returned in turn; the last one repeats."""

    def __init__(self, *responses):
        self.responses = list(responses)

    def next(self):
        return self.responses.pop(0) if len(self.responses) > 1 else self.responses[0]


def base_rules(items=()):
    return [
        (["gh", "repo", "view"], {"nameWithOwner": REPO, "defaultBranchRef": {"name": "main"}}),
        (["gh", "project", "view"], {"id": "project-1"}),
        (["gh", "project", "field-list"], FIELDS),
        (["gh", "project", "item-list"], {"items": list(items), "totalCount": len(items)}),
        (["gh", "project", "item-add"], {"id": "new-item"}),
        (["gh", "project", "item-edit"], ""),
    ]


UNREACHABLE = [(["gh", "project"], (1, "", "error: your token has not been granted the required scopes"))]


def run(rules, *argv, board=BOARD, sleep=None):
    runner = FakeRunner(rules)
    out, err = io.StringIO(), io.StringIO()
    ticks = iter(range(0, 100000, 10))
    with redirect_stdout(out), redirect_stderr(err):
        code = pipeline.main(list(argv), runner=runner, board_config=board,
                             sleep=sleep or (lambda s: None), clock=lambda: next(ticks))
    return code, runner, out.getvalue(), err.getvalue()


def status_edits(runner):
    """(item id, option id) for every board Status change."""
    return [(c[c.index("--id") + 1], c[-1]) for c in runner.called("gh", "project", "item-edit")]


class RefusalTests(unittest.TestCase):
    def test_refused_commands(self):
        protected = {"main", "trunk"}
        for args in (["gh", "pr", "merge", "3"], ["gh", "pr", "review", "3", "--approve"], ["gh", "issue", "close", "3"],
                     ["gh", "issue", "delete", "3"], ["gh", "repo", "edit", "--visibility", "private"], ["gh", "api", "repos/x"],
                     ["gh", "label", "edit", "x"], ["gh", "ruleset", "list"], ["gh", "issue", "edit", "3", "--title", "x"],
                     ["git", "push", "origin", "main"], ["git", "push", "origin", "HEAD:trunk"], ["git", "push", "--force", "origin", "feat/1-x"],
                     ["git", "push", "origin", "+feat/1-x"], ["git", "push", "origin", "--delete", "feat/1-x"], ["git", "tag", "v1"]):
            self.assertTrue(pipeline.refusal(args, protected), args)

    def test_allowed_commands(self):
        for args in (["git", "push", "-u", "origin", "feat/1-x"], ["gh", "issue", "edit", "1", "--add-label", "status:in-review"],
                     ["gh", "pr", "ready", "2"], ["gh", "project", "item-edit", "--id", "x"], ["git", "tag"]):
            self.assertIsNone(pipeline.refusal(args, {"main"}), args)

    def test_runner_refuses_before_executing(self):
        runner = FakeRunner([])
        with self.assertRaises(pipeline.PipelineError):
            runner.run("gh", "pr", "merge", "1")
        self.assertEqual(runner.calls, [])


class HelperTests(unittest.TestCase):
    def test_slugify(self):
        self.assertEqual(pipeline.slugify("Pipeline script: claim, PR, ready and cleanup in one command each"), "pipeline-script-claim-pr-ready")
        self.assertEqual(pipeline.slugify("!!!"), "work")

    def test_issue_link(self):
        self.assertIn("Closes #21", pipeline.with_issue_link("## Why\n\nCloses #\n", 21, False))
        self.assertIn("Refs #21", pipeline.with_issue_link("## Why\n\nCloses #\n", 21, True))
        self.assertEqual(pipeline.with_issue_link("Closes #21", 21, False), "Closes #21")
        self.assertIn("## Why\n\nCloses #4\n", pipeline.with_issue_link("## Summary\n\nx\n", 4, False))

    def test_timing_section(self):
        body = pipeline.add_timing("## Summary\n\nx\n", "- Started: T1")
        self.assertTrue(body.endswith("## Timing\n\n- Started: T1\n"))
        body = pipeline.add_timing(body + "\n## Notes\n\ny\n", "- Finished (CI passed): T2")
        self.assertIn("- Started: T1\n- Finished (CI passed): T2\n\n## Notes", body)

    def test_claim_time_reads_latest_claim(self):
        comments = [{"body": "Claimed by A (x). Branch `feat/1-a`. Started 2026-01-01T00:00:00Z."}, {"body": "unrelated"}]
        self.assertEqual(pipeline.claim_time(comments), "2026-01-01T00:00:00Z")
        self.assertIsNone(pipeline.claim_time([]))


class ClaimTests(unittest.TestCase):
    def rules(self, issue_data, porcelain="", items=()):
        return [(["gh", "issue", "view"], issue_data), (["git", "status"], porcelain), (["git", "fetch"], ""),
                (["git", "switch"], ""), (["gh", "issue", "edit"], ""), (["gh", "issue", "comment"], "")] + base_rules(items)

    def test_claim_ready_issue(self):
        code, r, out, err = run(self.rules(issue()), "claim", "21", "--agent", "Codex", "--machine", "cloud session")
        self.assertEqual(code, 0, err)
        branch = "feat/21-pipeline-script-claim-pr-ready"
        switch = ("git", "switch", "-c", branch, "origin/main")
        self.assertIn(switch, r.calls)
        self.assertIn(("gh", "issue", "edit", "21", "--remove-label", "status:ready", "--add-label", "status:in-progress"), r.calls)
        comment = r.called("gh", "issue", "comment")[0][-1]
        self.assertRegex(comment, r"^Claimed by Codex \(cloud session\)\. Branch `%s`\. Started \d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ\.$" % branch)
        self.assertLess(r.calls.index(switch), r.calls.index(r.called("gh", "issue", "edit")[0]))
        self.assertEqual(status_edits(r), [("new-item", "opt-progress")])

    def test_claim_refusals_change_nothing(self):
        cases = {"already claimed": issue(labels=("type:feat", "status:in-progress")),
                 "in review": issue(labels=("type:feat", "status:in-review")),
                 "not ready": issue(labels=("type:feat", "status:needs-owner")),
                 "no status": issue(labels=("type:feat",)),
                 "closed": issue(state="CLOSED"),
                 "no type": issue(labels=("status:ready",))}
        for name, data in cases.items():
            code, r, out, err = run(self.rules(data), "claim", "21")
            self.assertEqual(code, 1, name)
            self.assertIn("error:", err, name)
            self.assertFalse(r.called("gh", "issue", "edit") or r.called("git", "switch") or r.called("gh", "project"), name)

    def test_claim_refuses_dirty_tree(self):
        code, r, out, err = run(self.rules(issue(), porcelain=" M README.md\n"), "claim", "21")
        self.assertEqual(code, 1)
        self.assertIn("uncommitted", err)
        self.assertFalse(r.called("gh", "issue", "edit"))

    def test_claim_continues_when_board_unreachable(self):
        code, r, out, err = run(UNREACHABLE + self.rules(issue()), "claim", "21")
        self.assertEqual(code, 0)
        self.assertIn("board not updated", err)
        self.assertTrue(r.called("gh", "issue", "comment"))

    def test_unconnected_repo_skips_board(self):
        code, r, out, err = run(self.rules(issue()), "claim", "21", board={"owner": "octo", "project_number": 1, "repositories": []})
        self.assertEqual(code, 0)
        self.assertFalse(r.called("gh", "project"))


class PullRequestTests(unittest.TestCase):
    CLAIM = "Claimed by Codex (x). Branch `feat/21-pipeline`. Started 2026-11-23T05:00:00Z."

    def rules(self, branch="feat/21-pipeline"):
        return [(["git", "branch", "--show-current"], branch + "\n"), (["gh", "issue", "view"], issue(comments=[self.CLAIM])),
                (["git", "rev-parse"], str(ROOT) + "\n"), (["git", "push"], ""),
                (["gh", "pr", "create"], "Creating draft pull request\n" + url("pull", 40) + "\n")] + base_rules()

    def test_opens_draft_with_link_and_start_time(self):
        code, r, out, err = run(self.rules(), "pr", "21")
        self.assertEqual(code, 0, err)
        self.assertIn(("git", "push", "-u", "origin", "feat/21-pipeline"), r.calls)
        create = r.called("gh", "pr", "create")[0]
        self.assertIn("--draft", create)
        body = create[create.index("--body") + 1]
        self.assertIn("Closes #21", body)
        self.assertIn("- Started: 2026-11-23T05:00:00Z", body)
        self.assertEqual(create[create.index("--base") + 1], "main")
        self.assertEqual(status_edits(r), [("new-item", "opt-progress")])
        self.assertIn(url("pull", 40), out)

    def test_refs_for_design_gates(self):
        code, r, out, err = run(self.rules(), "pr", "21", "--refs")
        create = r.called("gh", "pr", "create")[0]
        self.assertIn("Refs #21", create[create.index("--body") + 1])

    def test_refuses_wrong_branch(self):
        for branch in ("main", "feat/22-other", "my-branch"):
            code, r, out, err = run(self.rules(branch), "pr", "21")
            self.assertEqual(code, 1, branch)
            self.assertFalse(r.called("git", "push"), branch)


class ReadyTests(unittest.TestCase):
    PR = {"number": 40, "url": url("pull", 40), "headRefName": "feat/21-pipeline", "isDraft": True, "state": "OPEN",
          "body": "## Why\n\nCloses #21\n\n## Timing\n\n- Started: 2026-11-23T05:00:00Z\n"}
    PASS = [{"name": "tests", "bucket": "pass", "link": "https://ci/1"}, {"name": "PR metadata", "bucket": "pass", "link": "https://ci/2"}]
    PENDING = (8, json.dumps([{"name": "tests", "bucket": "pending", "link": ""}]), "")

    def rules(self, checks, items=()):
        return [(["gh", "pr", "view"], self.PR), (["gh", "pr", "checks"], checks), (["gh", "pr", "edit"], ""),
                (["gh", "pr", "ready"], ""), (["gh", "issue", "edit"], ""), (["gh", "issue", "comment"], "")] + base_rules(items)

    def test_waits_then_marks_ready(self):
        none_yet = (1, "", "no checks reported on the 'feat/21-pipeline' branch")
        sleeps = []
        items = [item("i21", "issues", 21, "In Progress"), item("p40", "pull", 40, "In Progress")]
        code, r, out, err = run(self.rules(Seq(none_yet, self.PENDING, self.PASS), items), "ready", "40", sleep=sleeps.append)
        self.assertEqual(code, 0, err)
        self.assertEqual(len(sleeps), 2)
        body = r.called("gh", "pr", "edit")[0][-1]
        self.assertRegex(body, r"- Started: 2026-11-23T05:00:00Z\n- Finished \(CI passed\): \d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ\n$")
        self.assertIn(("gh", "pr", "ready", "40"), r.calls)
        self.assertIn(("gh", "issue", "edit", "21", "--remove-label", "status:in-progress", "--add-label", "status:in-review"), r.calls)
        self.assertIn("PR #40 is ready for review", r.called("gh", "issue", "comment")[0][-1])
        self.assertEqual(status_edits(r), [("i21", "opt-review"), ("p40", "opt-review")])

    def test_ci_failure_changes_nothing(self):
        failed = (1, json.dumps([{"name": "tests", "bucket": "fail", "link": "https://ci/run/9"}]), "")
        code, r, out, err = run(self.rules(failed), "ready", "40")
        self.assertEqual(code, 1)
        self.assertIn("https://ci/run/9", err)
        self.assertFalse(r.called("gh", "pr", "ready") or r.called("gh", "issue", "edit") or r.called("gh", "pr", "edit"))

    def test_timeout(self):
        code, r, out, err = run(self.rules(self.PENDING), "ready", "40", "--timeout", "30")
        self.assertEqual(code, 1)
        self.assertIn("did not finish", err)
        self.assertFalse(r.called("gh", "issue", "edit"))


class CleanupTests(unittest.TestCase):
    def test_deletes_only_merged_gone_branches(self):
        refs = "main|\nfeat/1-done|[gone]\nfeat/2-squashed|[gone]\nfeat/3-live|[ahead 1]\n"
        rules = [(["gh", "repo", "view"], {"nameWithOwner": REPO, "defaultBranchRef": {"name": "main"}}),
                 (["git", "fetch"], ""), (["git", "branch", "--show-current"], "feat/1-done\n"), (["git", "for-each-ref"], refs),
                 (["git", "merge-base", "--is-ancestor", "feat/1-done"], ""),
                 (["git", "merge-base", "--is-ancestor", "feat/2-squashed"], (1, "", "")),
                 (["git", "status"], ""), (["git", "switch"], ""), (["git", "pull"], ""), (["git", "branch", "-D"], "")]
        code, r, out, err = run(rules, "cleanup")
        self.assertEqual(code, 0, err)
        self.assertEqual(r.called("git", "branch", "-D"), [("git", "branch", "-D", "feat/1-done")])
        self.assertIn(("git", "switch", "main"), r.calls)
        self.assertIn("kept feat/2-squashed", out)


class SyncTests(unittest.TestCase):
    ISSUES = [{"number": 1, "url": url("issues", 1), "labels": [{"name": "status:ready"}]},
              {"number": 2, "url": url("issues", 2), "labels": [{"name": "status:in-progress"}]},
              {"number": 3, "url": url("issues", 3), "labels": [{"name": "status:needs-owner"}]}]
    PRS = [{"number": 4, "url": url("pull", 4), "isDraft": False}]

    def rules(self, items, other_issues=()):
        return [(["gh", "issue", "list", "-R", REPO], self.ISSUES), (["gh", "pr", "list", "-R", REPO], self.PRS),
                (["gh", "issue", "list", "-R", "octo/other"], list(other_issues)),
                (["gh", "pr", "list", "-R", "octo/other"], [])] + base_rules(items)

    def assert_board_only(self, runner):
        """Sync may read anything but only writes Project items."""
        for call in runner.calls:
            self.assertNotIn(call[1:3], (("issue", "edit"), ("pr", "edit"), ("issue", "close"), ("pr", "ready")), call)
            self.assertNotIn(call[1], ("label", "repo", "api", "ruleset"), call)

    def test_adds_missing_and_fixes_wrong_columns(self):
        items = [item("i1", "issues", 1, "Ready"), item("i2", "issues", 2, "Backlog"), item("p4", "pull", 4, "In Progress")]
        other = [{"number": 9, "url": url("issues", 9, "octo/other"), "labels": []}]
        code, r, out, err = run(self.rules(items, other), "sync")
        self.assertEqual(code, 0, err)
        added = [c[c.index("--url") + 1] for c in r.called("gh", "project", "item-add")]
        self.assertEqual(added, [url("issues", 3), url("issues", 9, "octo/other")])
        self.assertEqual(status_edits(r), [("i2", "opt-progress"), ("new-item", "opt-backlog"), ("p4", "opt-review"), ("new-item", "opt-backlog")])
        self.assertIn("4 card(s) changed", out)
        self.assert_board_only(r)

    def test_no_change_run(self):
        items = [item("i1", "issues", 1, "Ready"), item("i2", "issues", 2, "In Progress"),
                 item("i3", "issues", 3, "Backlog"), item("p4", "pull", 4, "Review")]
        code, r, out, err = run(self.rules(items), "sync", "--repo", REPO)
        self.assertEqual(code, 0, err)
        self.assertFalse(r.called("gh", "project", "item-add") or r.called("gh", "project", "item-edit"))
        self.assertIn("board in sync", out)
        self.assertFalse(r.called("gh", "issue", "list", "-R", "octo/other"))

    def test_dry_run_writes_nothing(self):
        code, r, out, err = run(self.rules([item("i1", "issues", 1, "Backlog")]), "sync", "--dry-run")
        self.assertEqual(code, 0)
        self.assertFalse(r.called("gh", "project", "item-add") or r.called("gh", "project", "item-edit"))
        self.assertIn("would move Backlog -> Ready", out)

    def test_unreachable_board(self):
        code, r, out, err = run(UNREACHABLE + self.rules([]), "sync")
        self.assertEqual(code, 1)
        self.assertIn("board unreachable", err)
        self.assertFalse(r.called("gh", "issue", "list"))
        self.assert_board_only(r)

    def test_unlisted_repo_refused(self):
        code, r, out, err = run(self.rules([]), "sync", "--repo", "someone/else")
        self.assertEqual(code, 1)
        self.assertEqual(r.calls, [])

    def test_real_board_config_is_valid(self):
        config = json.loads((ROOT / "context" / "board.json").read_text())
        self.assertEqual(config["project_number"], 1)
        self.assertIn("AbhiramYanamandra/karen-os", config["repositories"])



class ProfileBlockTests(unittest.TestCase):
    """`pr` pre-fills a karen-profile block from the resolver; the agent completes it."""

    def block(self, body):
        return json.loads(body.split("```karen-profile\n", 1)[1].split("\n```", 1)[0])

    def test_prefill_lists_required_skills_at_registry_hashes(self):
        body = pipeline.with_profile("## Summary\n\nx\n", "feat/46-x")
        block = self.block(body)
        self.assertEqual((block["type"], block["risk"]), ("feat", "low"))
        registry = {e["id"]: e["sha256"] for e in json.loads((ROOT / "docs/organisation/skills.json").read_text())["entries"]}
        self.assertEqual({s["id"]: s["sha256"] for s in block["skills"]},
                         {k: registry[k] for k in ("ponytail-plugin", "principle-prove-it-works")})
        self.assertTrue(all(s["evidence"] == "" for s in block["skills"]))

    def test_prefill_goes_under_the_profile_heading_once(self):
        body = pipeline.with_profile("## Profile\n\n<!-- note -->\n\n## Why\n", "docs/9-x")
        self.assertLess(body.index("```karen-profile"), body.index("## Why"))
        self.assertEqual(pipeline.with_profile(body, "docs/9-x"), body)


if __name__ == "__main__":
    unittest.main()
