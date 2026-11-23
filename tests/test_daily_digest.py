"""Tests for scripts/daily_digest.py with recorded gh output. No network, no credentials."""
import importlib.util
import io
import json
import pathlib
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("daily_digest", ROOT / "scripts" / "daily_digest.py")
digest = importlib.util.module_from_spec(spec)
spec.loader.exec_module(digest)

NOW = datetime(2026, 3, 14, 7, 0, tzinfo=timezone.utc)
DEMO = "octo/demo"


def u(kind, n, repo=DEMO):
    return "https://github.com/%s/%s/%d" % (repo, kind, n)


def labels(*names):
    return [{"name": n} for n in names]


CHECK_OK = {"__typename": "CheckRun", "name": "tests", "status": "COMPLETED", "conclusion": "SUCCESS"}
CHECK_FAIL = {"__typename": "CheckRun", "name": "tests", "status": "COMPLETED", "conclusion": "FAILURE"}
CHECK_RUNNING = {"__typename": "CheckRun", "name": "tests", "status": "IN_PROGRESS", "conclusion": ""}

DEMO_DATA = {
    ("pr", "open"): [
        {"number": 40, "title": "Add retry to the uploader", "url": u("pull", 40), "isDraft": False, "createdAt": "2026-03-13T10:00:00Z",
         "reviewDecision": "", "statusCheckRollup": [CHECK_OK]},
        {"number": 41, "title": "Fix the parser", "url": u("pull", 41), "isDraft": False, "createdAt": "2026-03-13T11:00:00Z",
         "reviewDecision": "CHANGES_REQUESTED", "statusCheckRollup": [CHECK_OK, CHECK_FAIL]},
        {"number": 42, "title": "Draft work", "url": u("pull", 42), "isDraft": True, "createdAt": "2026-03-13T12:00:00Z",
         "reviewDecision": "", "statusCheckRollup": []},
    ],
    ("issue", "open"): [
        {"number": 1, "title": "Old P2 task", "url": u("issues", 1), "labels": labels("P2", "status:ready"), "createdAt": "2026-01-01T00:00:00Z"},
        {"number": 2, "title": "Urgent fix", "url": u("issues", 2), "labels": labels("P0", "status:ready"), "createdAt": "2026-03-01T00:00:00Z"},
        {"number": 3, "title": "Decide the format", "url": u("issues", 3), "labels": labels("P1", "status:needs-owner"), "createdAt": "2026-03-02T00:00:00Z"},
        {"number": 4, "title": "Waiting on vendor", "url": u("issues", 4), "labels": labels("P1", "status:blocked"), "createdAt": "2026-03-03T00:00:00Z"},
        {"number": 5, "title": "Being built", "url": u("issues", 5), "labels": labels("P1", "status:in-progress"), "createdAt": "2026-03-04T00:00:00Z"},
        {"number": 6, "title": "Newer P2 task", "url": u("issues", 6), "labels": labels("P2", "status:ready"), "createdAt": "2026-02-01T00:00:00Z"},
        {"number": 7, "title": "No priority", "url": u("issues", 7), "labels": labels("status:ready"), "createdAt": "2025-12-01T00:00:00Z"},
    ],
    ("repo",): {"defaultBranchRef": {"name": "main"}},
    ("run",): [
        {"workflowName": "checks", "conclusion": "failure", "status": "completed", "url": "https://github.com/octo/demo/actions/runs/9", "createdAt": "2026-03-14T06:00:00Z", "event": "push"},
        {"workflowName": "checks", "conclusion": "success", "status": "completed", "url": "https://github.com/octo/demo/actions/runs/8", "createdAt": "2026-03-13T06:00:00Z", "event": "push"},
        {"workflowName": "pages", "conclusion": "failure", "status": "completed", "url": "https://github.com/octo/demo/actions/runs/7", "createdAt": "2026-03-12T06:00:00Z", "event": "push"},
        {"workflowName": "pages", "conclusion": "success", "status": "completed", "url": "https://github.com/octo/demo/actions/runs/10", "createdAt": "2026-03-14T06:30:00Z", "event": "push"},
    ],
    ("pr", "merged"): [{"number": 39, "title": "Add the CLI", "url": u("pull", 39), "mergedAt": "2026-03-13T20:00:00Z"}],
    ("issue", "closed"): [{"number": 8, "title": "Ship the CLI", "url": u("issues", 8), "closedAt": "2026-03-13T20:00:01Z", "stateReason": "COMPLETED"}],
}


class FakeRunner(digest.Runner):
    def __init__(self, data_by_repo, failures=()):
        self.data, self.failures, self.calls = data_by_repo, set(failures), []

    def execute(self, args):
        self.calls.append(tuple(args))
        repo = args[args.index("-R") + 1] if "-R" in args else args[3]
        kind = args[1]
        state = args[args.index("--state") + 1] if "--state" in args else None
        key = (kind, state) if state else (kind,)
        if (repo, kind) in self.failures or repo not in self.data:
            return 1, "", "HTTP 404: Not Found (https://api.github.com/repos/%s)\nmore" % repo
        return 0, json.dumps(self.data[repo].get(key, [])), ""


def run_cli(runner, *argv):
    out = io.StringIO()
    with redirect_stdout(out):
        code = digest.main(list(argv), runner=runner, now=NOW)
    return code, out.getvalue()


class DigestTests(unittest.TestCase):
    def build(self, failures=(), repos=(DEMO,)):
        runner = FakeRunner({DEMO: DEMO_DATA, "octo/empty": {}}, failures)
        return digest.build_digest(runner, list(repos), {}, NOW, top=2), runner

    def numbers(self, d, section):
        return [i["number"] for i in d["sections"][section]]

    def test_sections(self):
        d, _ = self.build()
        self.assertEqual(self.numbers(d, "waiting"), [40, 41])
        self.assertEqual([i["detail"] for i in d["sections"]["waiting"]], ["CI passing", "CI failing, changes requested"])
        self.assertEqual(self.numbers(d, "needs_owner"), [3])
        self.assertEqual(self.numbers(d, "blocked"), [4])
        self.assertEqual(self.numbers(d, "in_progress"), [5])
        self.assertEqual(self.numbers(d, "ready"), [2, 1, None])
        self.assertIn("and 2 more ready", d["sections"]["ready"][-1]["title"])
        self.assertEqual(self.numbers(d, "done"), [39, 8])
        self.assertEqual(d["unavailable"], [])

    def test_failing_ci_uses_latest_run_per_workflow(self):
        d, _ = self.build()
        failing = d["sections"]["failing_ci"]
        self.assertEqual([f["title"] for f in failing], ["checks on main"])
        self.assertTrue(failing[0]["url"].endswith("/runs/9"))

    def test_since_defaults_to_24_hours_and_is_used_in_searches(self):
        d, runner = self.build()
        self.assertEqual(d["since"][DEMO], "2026-03-13T07:00:00Z")
        searches = [c[c.index("--search") + 1] for c in runner.calls if "--search" in c]
        self.assertEqual(searches, ["merged:>=2026-03-13T07:00:00Z", "closed:>=2026-03-13T07:00:00Z"])

    def test_unavailable_sources_are_reported_not_guessed(self):
        d, _ = self.build(failures={(DEMO, "pr")})
        self.assertEqual(self.numbers(d, "waiting"), [])
        self.assertEqual(self.numbers(d, "done"), [8])
        sources = [(x["repo"], x["source"]) for x in d["unavailable"]]
        self.assertEqual(sources, [(DEMO, "pull requests"), (DEMO, "merged PRs")])
        self.assertEqual(d["unavailable"][0]["error"], "HTTP 404: Not Found (https://api.github.com/repos/octo/demo)")

    def test_unreadable_repository(self):
        runner = FakeRunner({DEMO: DEMO_DATA})
        d = digest.build_digest(runner, [DEMO, "octo/missing"], {}, NOW)
        self.assertTrue(all(x["repo"] == "octo/missing" for x in d["unavailable"]))
        self.assertEqual(len(d["unavailable"]), 5)
        self.assertEqual(self.numbers(d, "waiting"), [40, 41])

    def test_only_read_commands(self):
        _, runner = self.build()
        for call in runner.calls:
            self.assertIn(tuple(call[1:3]), digest.READ_VERBS, call)
        with self.assertRaises(PermissionError):
            runner.json("gh", "issue", "edit", "1", "--add-label", "x")
        with self.assertRaises(PermissionError):
            runner.json("gh", "api", "repos/octo/demo")

    def test_ci_state(self):
        self.assertEqual(digest.ci_state([]), "no checks")
        self.assertEqual(digest.ci_state([CHECK_OK, CHECK_RUNNING]), "CI running")
        self.assertEqual(digest.ci_state([{"__typename": "StatusContext", "state": "PENDING"}]), "CI running")
        self.assertEqual(digest.ci_state([{"__typename": "StatusContext", "state": "ERROR"}]), "CI failing")


class OutputTests(unittest.TestCase):
    def test_markdown(self):
        runner = FakeRunner({DEMO: DEMO_DATA})
        with tempfile.TemporaryDirectory() as tmp:
            code, out = run_cli(runner, "--repo", DEMO, "--state", str(pathlib.Path(tmp, "state.json")))
        self.assertEqual(code, 0)
        self.assertIn("Observed 2026-03-14T07:00:00Z · since 2026-03-13T07:00:00Z · 1 repositories (octo/demo)", out)
        self.assertIn("## Waiting for you (2)\n\n- [octo/demo#40](%s) Add retry to the uploader · CI passing" % u("pull", 40), out)
        self.assertIn("- [octo/demo#2](%s) Urgent fix · P0" % u("issues", 2), out)
        self.assertIn("## Failing CI on default branches (1)", out)
        self.assertIn("merged 2026-03-13T20:00:00Z", out)
        self.assertNotIn("## Unavailable", out)

    def test_markdown_lists_unavailable_first_and_exits_2(self):
        runner = FakeRunner({DEMO: DEMO_DATA}, failures={(DEMO, "issue")})
        code, out = run_cli(runner, "--repo", DEMO, "--no-state")
        self.assertEqual(code, 2)
        self.assertLess(out.index("## Unavailable"), out.index("## Waiting for you"))
        self.assertIn("- octo/demo issues: HTTP 404", out)

    def test_json(self):
        code, out = run_cli(FakeRunner({DEMO: DEMO_DATA}), "--repo", DEMO, "--json", "--no-state")
        data = json.loads(out)
        self.assertEqual(data["observed_at"], "2026-03-14T07:00:00Z")
        self.assertEqual([i["number"] for i in data["sections"]["needs_owner"]], [3])

    def test_empty_sections_say_none(self):
        code, out = run_cli(FakeRunner({"octo/empty": {("repo",): {"defaultBranchRef": {"name": "main"}}}}), "--repo", "octo/empty", "--no-state")
        self.assertEqual(code, 0)
        self.assertIn("## Waiting for you (0)\n\nNone.", out)


class StateTests(unittest.TestCase):
    def test_state_advances_only_fully_read_repositories(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = pathlib.Path(tmp, "nested", "state.json")
            runner = FakeRunner({DEMO: DEMO_DATA, "octo/other": DEMO_DATA}, failures={("octo/other", "run")})
            run_cli(runner, "--repo", DEMO, "--repo", "octo/other", "--state", str(state))
            saved = json.loads(state.read_text())["last_observed"]
            self.assertEqual(saved, {DEMO: "2026-03-14T07:00:00Z"})

            runner = FakeRunner({DEMO: DEMO_DATA, "octo/other": DEMO_DATA})
            code, out = run_cli(runner, "--repo", DEMO, "--repo", "octo/other", "--state", str(state), "--json")
            self.assertEqual(json.loads(out)["since"], {DEMO: "2026-03-14T07:00:00Z", "octo/other": "2026-03-13T07:00:00Z"})

    def test_since_flag_overrides_state(self):
        code, out = run_cli(FakeRunner({DEMO: DEMO_DATA}), "--repo", DEMO, "--since", "2026-03-10T00:00:00Z", "--json", "--no-state")
        self.assertEqual(json.loads(out)["since"][DEMO], "2026-03-10T00:00:00Z")

    def test_repositories_fall_back_to_board_config(self):
        args = digest.build_parser().parse_args(["--config", "/nonexistent/daily-review.json"])
        with tempfile.TemporaryDirectory() as tmp:
            board = pathlib.Path(tmp, "board.json")
            board.write_text(json.dumps({"repositories": [DEMO, "octo/other"]}))
            original, digest.BOARD_CONFIG = digest.BOARD_CONFIG, board
            try:
                self.assertEqual(digest.load_repos(args), [DEMO, "octo/other"])
                board.unlink()
                with self.assertRaises(SystemExit):
                    digest.load_repos(args)
            finally:
                digest.BOARD_CONFIG = original


if __name__ == "__main__":
    unittest.main()
