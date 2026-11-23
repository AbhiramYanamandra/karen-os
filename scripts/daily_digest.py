#!/usr/bin/env python3
"""Print a read-only engineering digest across the configured repositories.

  daily_digest.py [--repo OWNER/NAME ...] [--since ISO] [--top N] [--json]
                  [--output FILE] [--state FILE | --no-state]

Sections: PRs waiting for the owner (with CI state), issues that need the owner,
blocked issues, top status:ready issues, claimed work, failing CI on default
branches, and what was merged or closed since the last digest. Every item has a
link; every source that cannot be read is listed as unavailable, never guessed.

Repositories come from --repo, else `repositories` in
~/.config/karen-os/daily-review.json, else context/board.json. The last observed
time per repository is kept in ~/.local/state/karen-os/digest-state.json so the
next run can say what changed. Nothing is written to GitHub: the runner allows
only read commands. No model calls. Standard library plus the `gh` CLI.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOARD_CONFIG = ROOT / "context" / "board.json"
USER_CONFIG = Path.home() / ".config" / "karen-os" / "daily-review.json"
STATE_FILE = Path.home() / ".local" / "state" / "karen-os" / "digest-state.json"
DEFAULT_LOOKBACK = timedelta(hours=24)
READ_VERBS = {("pr", "list"), ("issue", "list"), ("run", "list"), ("repo", "view")}
SECTIONS = (
    ("waiting", "Waiting for you"),
    ("needs_owner", "Needs you"),
    ("blocked", "Blocked"),
    ("failing_ci", "Failing CI on default branches"),
    ("ready", "Ready to start"),
    ("in_progress", "In progress"),
    ("done", "Done since last digest"),
)
FAILED = {"FAILURE", "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED", "STARTUP_FAILURE", "ERROR"}


class Unavailable(Exception):
    """A source could not be read."""


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc)


class Runner:
    """Runs read-only gh commands and refuses everything else."""

    def execute(self, args):
        proc = subprocess.run(list(args), capture_output=True, text=True)
        return proc.returncode, proc.stdout, proc.stderr

    def json(self, *args):
        if args[:1] != ("gh",) or tuple(args[1:3]) not in READ_VERBS:
            raise PermissionError("the digest only reads GitHub: refused %s" % " ".join(args))
        code, out, err = self.execute(args)
        if code:
            raise Unavailable((err.strip() or "exit %d" % code).splitlines()[0][:160])
        try:
            return json.loads(out or "null")
        except ValueError as error:
            raise Unavailable("unreadable output (%s)" % error)


def labels_of(item) -> set[str]:
    return {l["name"] for l in item.get("labels") or []}


def priority(item) -> str | None:
    return next((p for p in ("P0", "P1", "P2", "P3") if p in labels_of(item)), None)


def ci_state(rollup) -> str:
    if not rollup:
        return "no checks"
    states = [(c.get("conclusion") or c.get("state") or "").upper() for c in rollup]
    if any(s in FAILED for s in states):
        return "CI failing"
    if any(c.get("status", "COMPLETED") != "COMPLETED" or s in ("", "PENDING", "EXPECTED") for c, s in zip(rollup, states)):
        return "CI running"
    return "CI passing"


def entry(repo, item, detail=""):
    return {"repo": repo, "number": item.get("number"), "title": item.get("title", ""), "url": item.get("url", ""),
            "priority": priority(item), "detail": detail}


def read_repo(r, repo: str, since: datetime, top: int):
    """Collect one repository's sections. Returns (sections, unavailable)."""
    sections = {key: [] for key, _ in SECTIONS}
    unavailable = []

    def source(name, *args):
        try:
            return r.json(*args)
        except Unavailable as error:
            unavailable.append({"repo": repo, "source": name, "error": str(error)})
            return None

    prs = source("pull requests", "gh", "pr", "list", "-R", repo, "--state", "open", "--limit", "200",
                 "--json", "number,title,url,isDraft,createdAt,reviewDecision,statusCheckRollup")
    for pr in prs or []:
        if not pr.get("isDraft"):
            detail = ci_state(pr.get("statusCheckRollup"))
            if pr.get("reviewDecision") == "CHANGES_REQUESTED":
                detail += ", changes requested"
            sections["waiting"].append(entry(repo, pr, detail))

    issues = source("issues", "gh", "issue", "list", "-R", repo, "--state", "open", "--limit", "500",
                    "--json", "number,title,url,labels,createdAt")
    ready = []
    for issue in issues or []:
        labels = labels_of(issue)
        if "status:needs-owner" in labels:
            sections["needs_owner"].append(entry(repo, issue))
        if "status:blocked" in labels:
            sections["blocked"].append(entry(repo, issue))
        if "status:in-progress" in labels:
            sections["in_progress"].append(entry(repo, issue))
        if "status:ready" in labels and not labels & {"status:blocked", "status:needs-owner"}:
            ready.append(issue)
    ready.sort(key=lambda i: (priority(i) or "P9", i.get("createdAt", "")))
    sections["ready"] = [entry(repo, i) for i in ready[:top]]
    if len(ready) > top:
        sections["ready"].append({"repo": repo, "number": None, "title": "and %d more ready" % (len(ready) - top),
                                  "url": "https://github.com/%s/issues?q=is%%3Aopen+label%%3Astatus%%3Aready" % repo,
                                  "priority": None, "detail": ""})

    meta = source("default branch", "gh", "repo", "view", repo, "--json", "defaultBranchRef")
    branch = ((meta or {}).get("defaultBranchRef") or {}).get("name")
    if branch:
        runs = source("CI runs", "gh", "run", "list", "-R", repo, "--branch", branch, "--limit", "30",
                      "--json", "workflowName,conclusion,status,url,createdAt,event")
        latest = {}
        for run in sorted(runs or [], key=lambda x: x.get("createdAt", ""), reverse=True):
            if run.get("status") == "completed":
                latest.setdefault(run.get("workflowName"), run)
        for name, run in sorted(latest.items(), key=lambda kv: kv[0] or ""):
            if (run.get("conclusion") or "").upper() in FAILED:
                sections["failing_ci"].append({"repo": repo, "number": None, "title": "%s on %s" % (name, branch),
                                               "url": run.get("url", ""), "priority": None,
                                               "detail": "%s at %s" % (run.get("conclusion"), run.get("createdAt"))})

    stamp = iso(since)
    merged = source("merged PRs", "gh", "pr", "list", "-R", repo, "--state", "merged", "--limit", "100",
                    "--search", "merged:>=" + stamp, "--json", "number,title,url,mergedAt")
    for pr in merged or []:
        sections["done"].append(entry(repo, pr, "merged %s" % pr.get("mergedAt", "")))
    closed = source("closed issues", "gh", "issue", "list", "-R", repo, "--state", "closed", "--limit", "100",
                    "--search", "closed:>=" + stamp, "--json", "number,title,url,closedAt,stateReason")
    for issue in closed or []:
        reason = (issue.get("stateReason") or "closed").lower().replace("_", " ")
        sections["done"].append(entry(repo, issue, "%s %s" % (reason, issue.get("closedAt", ""))))
    return sections, unavailable


def build_digest(r, repos, since_by_repo, observed: datetime, top: int = 5):
    digest = {"observed_at": iso(observed), "repositories": list(repos), "since": {},
              "sections": {key: [] for key, _ in SECTIONS}, "unavailable": []}
    for repo in repos:
        since = since_by_repo.get(repo) or observed - DEFAULT_LOOKBACK
        digest["since"][repo] = iso(since)
        sections, unavailable = read_repo(r, repo, since, top)
        for key in sections:
            digest["sections"][key].extend(sections[key])
        digest["unavailable"].extend(unavailable)
    for key in ("needs_owner", "blocked", "in_progress"):
        digest["sections"][key].sort(key=lambda i: i["priority"] or "P9")
    return digest


def render_markdown(d) -> str:
    since = sorted(set(d["since"].values()))
    lines = ["# Engineering digest", "",
             "Observed %s · since %s · %d repositories (%s)" % (
                 d["observed_at"], since[0] if len(since) == 1 else "per repository", len(d["repositories"]),
                 ", ".join(d["repositories"])), ""]
    if d["unavailable"]:
        lines += ["## Unavailable", "", "These sources could not be read; their sections may be incomplete.", ""]
        lines += ["- %s %s: %s" % (u["repo"], u["source"], u["error"]) for u in d["unavailable"]]
        lines.append("")
    for key, title in SECTIONS:
        items = d["sections"][key]
        lines += ["## %s (%d)" % (title, len([i for i in items if i["number"] is not None or key == "failing_ci"])), ""]
        if not items:
            lines += ["None.", ""]
            continue
        for i in items:
            ref = "%s#%d" % (i["repo"], i["number"]) if i["number"] is not None else i["repo"]
            extra = " · ".join(x for x in (i["priority"], i["detail"]) if x)
            lines.append("- [%s](%s) %s%s" % (ref, i["url"], i["title"], " · " + extra if extra else ""))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def load_repos(args) -> list[str]:
    if args.repo:
        return args.repo
    for path in (args.config, BOARD_CONFIG):
        try:
            with open(path, encoding="utf-8") as handle:
                repos = json.load(handle).get("repositories")
            if repos:
                return list(repos)
        except (OSError, ValueError, AttributeError):
            continue
    raise SystemExit("error: no repositories; pass --repo or list them in %s" % args.config)


def load_state(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return {repo: parse_iso(ts) for repo, ts in json.load(handle).get("last_observed", {}).items()}
    except (OSError, ValueError, AttributeError):
        return {}


def save_state(path, digest, previous):
    """Advance only repositories that were read completely, so nothing is skipped."""
    failed = {u["repo"] for u in digest["unavailable"]}
    state = {repo: iso(ts) for repo, ts in previous.items()}
    for repo in digest["repositories"]:
        if repo not in failed:
            state[repo] = digest["observed_at"]
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"last_observed": state}, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def build_parser():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--repo", action="append", help="owner/name; repeat for several")
    p.add_argument("--config", default=str(USER_CONFIG))
    p.add_argument("--since", help="ISO time; overrides the saved state for every repository")
    p.add_argument("--top", type=int, default=5, help="ready issues per repository")
    p.add_argument("--json", action="store_true", help="print JSON instead of Markdown")
    p.add_argument("--output", help="write to this file instead of stdout")
    p.add_argument("--state", default=str(STATE_FILE))
    p.add_argument("--no-state", action="store_true", help="neither read nor update the saved state")
    return p


def main(argv=None, runner=None, now=None) -> int:
    args = build_parser().parse_args(argv)
    repos = load_repos(args)
    observed = now or datetime.now(timezone.utc)
    previous = {} if args.no_state else load_state(args.state)
    since = {repo: parse_iso(args.since) for repo in repos} if args.since else previous
    digest = build_digest(runner or Runner(), repos, since, observed, args.top)
    text = json.dumps(digest, indent=2) + "\n" if args.json else render_markdown(digest)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    if not args.no_state:
        save_state(args.state, digest, previous)
    return 2 if digest["unavailable"] else 0


if __name__ == "__main__":
    sys.exit(main())
