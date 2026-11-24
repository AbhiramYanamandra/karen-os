#!/usr/bin/env python3
"""Run the routine engineering-pipeline steps, one command each.

  pipeline.py claim <issue> [--agent NAME] [--machine NAME] [--type T] [--slug S]
  pipeline.py pr <issue> [--refs] [--title TITLE] [--body-file FILE]
  pipeline.py ready <pr> [--timeout SECONDS] [--interval SECONDS]
  pipeline.py cleanup
  pipeline.py sync [--repo OWNER/NAME] [--dry-run]

Run from the project's checkout; `gh` and `git` act on that repository.
Engineering standard: docs/organisation/engineering.md.

The script never merges, approves, closes or deletes, never pushes or force-pushes
the default branch, never changes repository settings, and never edits labels from
the board: `Runner` refuses those commands before they run. Board updates (GitHub
Projects, configured in context/board.json) are one way, label to card. When the
board is unreachable, claim, pr and ready warn and carry on.

Standard library plus the `gh` and `git` CLIs. Timestamps are UTC, ISO 8601.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOARD_CONFIG = ROOT / "context" / "board.json"
FALLBACK_TEMPLATE = ROOT / "docs" / "templates" / "github" / "pull_request_template.md"
BRANCH_TYPES = ("feat", "fix", "hotfix", "refactor", "docs", "test", "chore", "ci", "release")
TYPES_RE = "|".join(BRANCH_TYPES)
CLAIM_RE = re.compile(r"Claimed by .*?Started (\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ)", re.S)
STOP_WORDS = {"a", "an", "the", "and", "or", "of", "to", "for", "in", "on", "with", "by"}
BOARD_ERRORS = (KeyError, TypeError, ValueError, IndexError)


class PipelineError(Exception):
    """A step that cannot go ahead. Nothing after it runs."""


class RunError(PipelineError):
    def __init__(self, args, code, stderr):
        super().__init__("`%s` failed (exit %s): %s" % (" ".join(args), code, stderr.strip()[:300]))


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def warn(message: str) -> None:
    print("warning: " + message, file=sys.stderr)


def refusal(args, protected) -> str | None:
    """Why a command is outside the standing authority, or None if it is allowed."""
    a = list(args)
    if a[:1] == ["gh"] and len(a) > 1:
        verb = a[1:3]
        if a[1] in ("api", "ruleset", "secret", "variable", "release", "label"):
            return "gh %s is not used by the pipeline" % a[1]
        if verb in (["pr", "merge"], ["pr", "close"], ["issue", "close"], ["issue", "delete"],
                    ["issue", "transfer"], ["repo", "edit"], ["repo", "delete"], ["repo", "rename"]):
            return "%s is owner-only" % " ".join(a[:3])
        if verb == ["pr", "review"] and "--approve" in a:
            return "approving is owner-only"
        if verb == ["issue", "edit"] and any(x.startswith("--") and x not in ("--add-label", "--remove-label") for x in a[3:]):
            return "only label changes are allowed on issues"
    if a[:2] == ["git", "push"]:
        if any(x.startswith(("--force", "--mirror", "--delete", "--all", "--tags", "+")) or x in ("-f", "-d") for x in a[2:]):
            return "force, delete and bulk pushes are not allowed"
        for ref in a[2:]:
            if ref.split(":")[-1].replace("refs/heads/", "") in protected:
                return "pushing the default branch is owner-only"
    if a[:2] == ["git", "tag"] and len(a) > 2:
        return "tags are owner-only"
    return None


class Runner:
    """Runs gh and git, refusing anything outside the standing authority."""

    def __init__(self):
        self.protected = {"main", "master"}

    def execute(self, args):
        proc = subprocess.run(list(args), capture_output=True, text=True)
        return proc.returncode, proc.stdout, proc.stderr

    def try_run(self, *args):
        reason = refusal(args, self.protected)
        if reason:
            raise PipelineError("refused (%s): %s" % (reason, " ".join(args)))
        return self.execute(args)

    def run(self, *args) -> str:
        code, out, err = self.try_run(*args)
        if code:
            raise RunError(args, code, err)
        return out

    def json(self, *args):
        out = self.run(*args)
        return json.loads(out) if out.strip() else None


def repo_info(r):
    data = r.json("gh", "repo", "view", "--json", "nameWithOwner,defaultBranchRef")
    default = data["defaultBranchRef"]["name"]
    r.protected.add(default)
    return data["nameWithOwner"], default


def label_names(item) -> set[str]:
    return {l["name"] if isinstance(l, dict) else l for l in item.get("labels") or []}


def slugify(title: str, max_words: int = 5, max_len: int = 40) -> str:
    words = re.findall(r"[a-z0-9]+", title.lower())
    words = [w for w in words if w not in STOP_WORDS] or words
    slug = ""
    for word in words[:max_words]:
        candidate = slug + "-" + word if slug else word
        if len(candidate) > max_len:
            break
        slug = candidate
    return slug or "work"


def issue_from_branch(branch: str):
    m = re.match(r"^(?:%s)/([0-9]+)-" % TYPES_RE, branch or "")
    return int(m.group(1)) if m else None


def with_issue_link(body: str, issue: int, refs: bool) -> str:
    link = "%s #%d" % ("Refs" if refs else "Closes", issue)
    if re.search(r"(?i)\b(?:closes|fixes|resolves|refs)\s+#%d\b" % issue, body):
        return body
    body, n = re.subn(r"(?m)^(?:Closes|Refs) #[ \t]*$", link, body, count=1)
    if n:
        return body
    body, n = re.subn(r"(?m)^(## Why[^\n]*\n)", lambda m: m.group(1) + "\n" + link + "\n", body, count=1)
    return body if n else body.rstrip() + "\n\n## Why\n\n" + link + "\n"


def add_timing(body: str, line: str) -> str:
    """Add a line to the PR's Timing section, creating the section at the end if needed."""
    m = re.search(r"(?m)^## Timing[^\n]*\n", body)
    if not m:
        return body.rstrip() + "\n\n## Timing\n\n" + line + "\n"
    nxt = re.search(r"(?m)^## ", body[m.end():])
    end = m.end() + nxt.start() if nxt else len(body)
    section = body[m.end():end].rstrip()
    rest = "\n" + body[end:] if nxt else ""
    return body[:m.end()] + (section + "\n" if section else "\n") + line + "\n" + rest


def claim_time(comments) -> str | None:
    for comment in reversed(comments or []):
        m = CLAIM_RE.search(comment.get("body", ""))
        if m:
            return m.group(1)
    return None


# ---------------------------------------------------------------- board

def status_for_issue(labels) -> str:
    for label, status in (("status:in-review", "Review"), ("status:in-progress", "In Progress"), ("status:ready", "Ready")):
        if label in labels:
            return status
    return "Backlog"


def status_for_pr(pr) -> str:
    return "In Progress" if pr.get("isDraft") else "Review"


class Board:
    """One-way sync to the Engineering HQ Project. Only reads and writes Project items."""

    def __init__(self, r, config):
        self.r, self.cfg, self.loaded = r, config or {}, False

    def connected(self, repo: str) -> bool:
        return repo.lower() in {x.lower() for x in self.cfg.get("repositories", [])}

    def _project(self):
        return str(self.cfg["project_number"]), self.cfg["owner"]

    def load(self):
        if not self.cfg.get("owner"):
            raise PipelineError("no board configured in context/board.json")
        num, owner = self._project()
        self.project_id = self.r.json("gh", "project", "view", num, "--owner", owner, "--format", "json")["id"]
        fields = self.r.json("gh", "project", "field-list", num, "--owner", owner, "--format", "json")["fields"]
        status = [f for f in fields if f["name"] == self.cfg.get("status_field", "Status")]
        if not status:
            raise PipelineError("the board has no Status field")
        self.field_id = status[0]["id"]
        self.options = {o["name"]: o["id"] for o in status[0]["options"]}
        items = self.r.json("gh", "project", "item-list", num, "--owner", owner, "--limit", "2000", "--format", "json")["items"]
        self.items = {it["content"]["url"]: it for it in items if (it.get("content") or {}).get("url")}
        self.loaded = True

    def ensure(self, url: str, status: str, dry_run: bool = False):
        """Add the item if missing and set its Status. Returns what changed, or None."""
        item, action = self.items.get(url), None
        if item is None:
            if dry_run:
                return "would add as " + status
            num, owner = self._project()
            added = self.r.json("gh", "project", "item-add", num, "--owner", owner, "--url", url, "--format", "json")
            item = self.items[url] = {"id": added["id"], "status": None}
            action = "added"
        if item.get("status") != status:
            if dry_run:
                return "would move %s -> %s" % (item.get("status"), status)
            self.r.run("gh", "project", "item-edit", "--project-id", self.project_id, "--id", item["id"],
                       "--field-id", self.field_id, "--single-select-option-id", self.options[status])
            action = (action + ", " if action else "") + "%s -> %s" % (item.get("status"), status)
            item["status"] = status
        return action

    def update(self, repo: str, url: str, status: str) -> None:
        """For claim, pr and ready: never raises, so the board cannot block a step."""
        if not self.connected(repo):
            return
        try:
            if not self.loaded:
                self.load()
            change = self.ensure(url, status)
            if change:
                print("board: %s %s" % (url, change))
        except (PipelineError,) + BOARD_ERRORS as error:
            warn("board not updated (%s); run `pipeline.py sync` later" % error)


# ---------------------------------------------------------------- commands

def cmd_claim(r, board, a, **_):
    repo, default = repo_info(r)
    issue = r.json("gh", "issue", "view", str(a.issue), "--json", "number,title,state,labels,url")
    labels, n = label_names(issue), str(issue["number"])
    claimed = labels & {"status:in-progress", "status:in-review"}
    if issue["state"] != "OPEN":
        raise PipelineError("#%s is not open" % n)
    if claimed:
        raise PipelineError("#%s is already claimed (%s)" % (n, ", ".join(sorted(claimed))))
    if labels & {"status:blocked", "status:needs-owner"} or "status:ready" not in labels:
        raise PipelineError("#%s is not status:ready; only the owner marks issues ready" % n)
    btype = a.type or next((l.split(":", 1)[1] for l in sorted(labels) if l.startswith("type:")), None)
    if btype not in BRANCH_TYPES:
        raise PipelineError("#%s has no type:* label matching a branch type; pass --type" % n)
    slug = a.slug or slugify(issue["title"])
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        raise PipelineError("slug %r must be lowercase kebab-case" % slug)
    branch = "%s/%s-%s" % (btype, n, slug)
    if r.run("git", "status", "--porcelain").strip():
        raise PipelineError("the working tree has uncommitted changes; commit or stash them first")
    r.run("git", "fetch", "origin", default)
    r.run("git", "switch", "-c", branch, "origin/" + default)
    started = now()
    r.run("gh", "issue", "edit", n, "--remove-label", "status:ready", "--add-label", "status:in-progress")
    r.run("gh", "issue", "comment", n, "--body",
          "Claimed by %s (%s). Branch `%s`. Started %s." % (a.agent, a.machine, branch, started))
    board.update(repo, issue["url"], "In Progress")
    print("claimed #%s on %s at %s" % (n, branch, started))


def template_body(r) -> str:
    try:
        candidate = Path(r.run("git", "rev-parse", "--show-toplevel").strip()) / ".github" / "pull_request_template.md"
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8")
    except PipelineError:
        pass
    return FALLBACK_TEMPLATE.read_text(encoding="utf-8") if FALLBACK_TEMPLATE.is_file() else ""


def profile_block(branch: str) -> str:
    """A karen-profile block pre-filled from the resolver at low risk. The agent fills risk, flags and evidence."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import profiles
    data = json.loads(profiles.PROFILES.read_text(encoding="utf-8"))
    entries = json.loads(profiles.REGISTRY.read_text(encoding="utf-8")).get("entries", [])
    hashes = {e["id"]: e.get("sha256") for e in entries if e.get("approval_status") == "approved"}
    kind = branch.split("/", 1)[0]
    result = profiles.resolve(data, kind, "low", registry=set(hashes))
    skills = [{"id": s, "stage": stage, "sha256": hashes.get(s), "runtime": "", "evidence": ""}
              for stage, info in result["stages"].items() for s, lvl in info["skills"].items() if lvl == "required"]
    block = {"type": kind, "risk": "low", "flags": [], "design_approval": "", "skills": skills,
             "review": {"by": "", "session": "", "findings": ""}, "tests": [], "owner_interventions": 0, "exceptions": []}
    return "```karen-profile\n" + json.dumps(block, indent=2) + "\n```\n"


def with_profile(body: str, branch: str) -> str:
    """Add a pre-filled karen-profile block under `## Profile`, or as a new section, unless one is there."""
    if "```karen-profile" in body:
        return body
    m = re.search(r"(?m)^## Profile[^\n]*\n", body)
    if m:
        return body[:m.end()] + "\n" + profile_block(branch) + body[m.end():]
    return body.rstrip() + "\n\n## Profile\n\n" + profile_block(branch)


def cmd_pr(r, board, a, **_):
    repo, default = repo_info(r)
    branch = r.run("git", "branch", "--show-current").strip()
    if issue_from_branch(branch) != a.issue or branch in r.protected:
        raise PipelineError("the current branch %r is not a branch for #%d" % (branch, a.issue))
    issue = r.json("gh", "issue", "view", str(a.issue), "--json", "number,title,url,comments")
    if a.body_file:
        with open(a.body_file, encoding="utf-8") as handle:
            body = handle.read()
    else:
        body = template_body(r)
    body = with_issue_link(body, a.issue, a.refs)
    body = with_profile(body, branch)
    body = add_timing(body, "- Started: %s" % (claim_time(issue.get("comments")) or "not recorded"))
    r.run("git", "push", "-u", "origin", branch)
    out = r.run("gh", "pr", "create", "--draft", "--base", default, "--head", branch,
                "--title", a.title or issue["title"], "--body", body)
    url = out.strip().splitlines()[-1]
    board.update(repo, url, "In Progress")
    print("draft PR: " + url)


def wait_for_checks(r, pr: str, timeout: float, interval: float, sleep, clock):
    """Poll CI inside the script so the agent does not. Returns the final checks."""
    deadline = clock() + timeout
    while True:
        code, out, err = r.try_run("gh", "pr", "checks", pr, "--json", "name,bucket,link")
        if not out.strip() and code and "no checks reported" not in err:
            raise RunError(("gh", "pr", "checks", pr), code, err)
        checks = json.loads(out) if out.strip() else []
        if any(c["bucket"] in ("fail", "cancel") for c in checks):
            return checks
        if checks and not any(c["bucket"] == "pending" for c in checks):
            return checks
        if clock() >= deadline:
            raise PipelineError("CI did not finish within %d seconds; run `ready` again later" % timeout)
        sleep(interval)


def cmd_ready(r, board, a, sleep=time.sleep, clock=time.monotonic, **_):
    repo, _default = repo_info(r)
    n = str(a.pr)
    pr = r.json("gh", "pr", "view", n, "--json", "number,url,body,headRefName,isDraft,state")
    if pr["state"] != "OPEN":
        raise PipelineError("PR #%s is not open" % n)
    issue = issue_from_branch(pr["headRefName"])
    if issue is None:
        raise PipelineError("PR #%s branch %r names no issue" % (n, pr["headRefName"]))
    checks = wait_for_checks(r, n, a.timeout, a.interval, sleep, clock)
    failed = [c for c in checks if c["bucket"] in ("fail", "cancel")]
    if failed:
        for c in failed:
            print("failed: %s %s" % (c["name"], c.get("link", "")), file=sys.stderr)
        raise PipelineError("CI failed on PR #%s; fix the cause, push, and run `ready` again" % n)
    finished = now()
    r.run("gh", "pr", "edit", n, "--body", add_timing(pr.get("body") or "", "- Finished (CI passed): %s" % finished))
    if pr["isDraft"]:
        r.run("gh", "pr", "ready", n)
    r.run("gh", "issue", "edit", str(issue), "--remove-label", "status:in-progress", "--add-label", "status:in-review")
    r.run("gh", "issue", "comment", str(issue), "--body", "PR #%s is ready for review. CI passed at %s." % (n, finished))
    board.update(repo, "https://github.com/%s/issues/%d" % (repo, issue), "Review")
    board.update(repo, pr["url"], "Review")
    print("PR #%s ready for review; #%d is status:in-review" % (n, issue))


def cmd_cleanup(r, board, a, **_):
    _repo, default = repo_info(r)
    r.run("git", "fetch", "--prune", "origin")
    current = r.run("git", "branch", "--show-current").strip()
    refs = r.run("git", "for-each-ref", "--format=%(refname:short)|%(upstream:track)", "refs/heads")
    gone = [name for name, track in (line.split("|", 1) for line in refs.splitlines() if "|" in line) if track == "[gone]"]
    for branch in gone:
        if branch in r.protected:
            continue
        code, _, _ = r.try_run("git", "merge-base", "--is-ancestor", branch, "origin/" + default)
        if code:
            print("kept %s: not merged into %s (delete it by hand if it was squash-merged)" % (branch, default))
            continue
        if branch == current:
            if r.run("git", "status", "--porcelain").strip():
                print("kept %s: it is checked out with uncommitted changes" % branch)
                continue
            r.run("git", "switch", default)
            r.run("git", "pull", "--ff-only")
            current = default
        r.run("git", "branch", "-D", branch)
        print("deleted merged branch " + branch)
    if not gone:
        print("no merged branches to delete")


def cmd_sync(r, board, a, **_):
    repos = list(board.cfg.get("repositories", []))
    if a.repo:
        if not board.connected(a.repo):
            raise PipelineError("%s is not listed in context/board.json" % a.repo)
        repos = [a.repo]
    try:
        board.load()
    except (PipelineError,) + BOARD_ERRORS as error:
        warn("board unreachable (%s); nothing changed" % error)
        return 1
    changes, status = 0, 0
    for repo in repos:
        try:
            issues = r.json("gh", "issue", "list", "-R", repo, "--state", "open", "--limit", "1000", "--json", "number,url,labels")
            prs = r.json("gh", "pr", "list", "-R", repo, "--state", "open", "--limit", "500", "--json", "number,url,isDraft")
            wanted = [(i["url"], status_for_issue(label_names(i))) for i in issues] + [(p["url"], status_for_pr(p)) for p in prs]
            for url, want in wanted:
                change = board.ensure(url, want, a.dry_run)
                if change:
                    changes += 1
                    print("%s: %s" % (url, change))
        except (PipelineError,) + BOARD_ERRORS as error:
            warn("%s not synced (%s)" % (repo, error))
            status = 1
    if changes:
        print("%d card(s) %s" % (changes, "to change" if a.dry_run else "changed"))
    else:
        print("board in sync, nothing changed")
    return status


def load_board_config(path: Path = BOARD_CONFIG):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError) as error:
        warn("no board config (%s); board sync is off" % error)
        return {}


def build_parser():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="command", required=True)
    c = sub.add_parser("claim", help="claim a status:ready issue and create its branch")
    c.add_argument("issue", type=int)
    c.add_argument("--agent", default=os.environ.get("KAREN_AGENT", "an agent"), help="who is working, e.g. Codex")
    c.add_argument("--machine", default=os.environ.get("KAREN_MACHINE", "local checkout"),
                   help="where, without personal details (not the hostname)")
    c.add_argument("--type", choices=BRANCH_TYPES)
    c.add_argument("--slug")
    c.set_defaults(func=cmd_claim)
    pr = sub.add_parser("pr", help="push the branch and open a draft PR")
    pr.add_argument("issue", type=int)
    pr.add_argument("--refs", action="store_true", help="link with Refs, for design-gate PRs that should not close the issue")
    pr.add_argument("--title")
    pr.add_argument("--body-file")
    pr.set_defaults(func=cmd_pr)
    rd = sub.add_parser("ready", help="wait for CI, then mark the PR ready and the issue in review")
    rd.add_argument("pr", type=int)
    rd.add_argument("--timeout", type=float, default=1800)
    rd.add_argument("--interval", type=float, default=15)
    rd.set_defaults(func=cmd_ready)
    sub.add_parser("cleanup", help="prune and delete local branches merged on GitHub").set_defaults(func=cmd_cleanup)
    sy = sub.add_parser("sync", help="add missing items to the board and set Status from labels")
    sy.add_argument("--repo")
    sy.add_argument("--dry-run", action="store_true")
    sy.set_defaults(func=cmd_sync)
    return p


def main(argv=None, runner=None, board_config=None, sleep=time.sleep, clock=time.monotonic) -> int:
    args = build_parser().parse_args(argv)
    r = runner or Runner()
    board = Board(r, board_config if board_config is not None else load_board_config())
    try:
        return args.func(r, board, args, sleep=sleep, clock=clock) or 0
    except PipelineError as error:
        print("error: %s" % error, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
