#!/usr/bin/env python3
"""Check the machine-checkable parts of a pull request (engineering standard).

Fails when:
- the head branch is not `<type>/<issue>-<short-description>`;
- the PR body links no issue with `Closes #<n>` or `Refs #<n>`;
- the diff adds a home-directory path or a common secret pattern.

In CI it reads the GitHub event file and diffs against the base branch.
Locally: `check_pr.py --branch NAME --body-file FILE --diff-file FILE`.
A diff line containing `pr-check: allow` is skipped, for deliberate examples.
Standard library only.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

BRANCH_TYPES = ("feat", "fix", "hotfix", "refactor", "docs", "test", "chore", "ci", "release")
BRANCH_RE = re.compile(r"^(?:%s)/[0-9]+-[a-z0-9]+(?:-[a-z0-9]+)*$" % "|".join(BRANCH_TYPES))
LINK_RE = re.compile(r"\b(?:Closes|Fixes|Resolves|Refs)\s+(?:[\w.-]+/[\w.-]+)?#[0-9]+\b", re.IGNORECASE)
ALLOW_MARK = "pr-check: allow"

# (label, pattern) for content that must never be added to a public repository.
FORBIDDEN = (
    ("home-directory path", re.compile(r"/Users/[A-Za-z0-9._-]+|/home/[a-z_][a-z0-9_-]*/")),
    ("GitHub token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36}\b|\bgithub_pat_[A-Za-z0-9_]{22,}")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----")),
    ("Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("API secret key", re.compile(r"\bsk-(?:ant-|proj-)?[A-Za-z0-9_-]{20,}")),
    ("Notion token", re.compile(r"\b(?:secret_[A-Za-z0-9]{43}|ntn_[A-Za-z0-9]{40,})\b")),
)


def check_branch(branch: str) -> list[str]:
    if BRANCH_RE.match(branch or ""):
        return []
    return ["branch %r is not <type>/<issue>-<short-description> with type one of %s"
            % (branch, ", ".join(BRANCH_TYPES))]


def check_body(body: str) -> list[str]:
    if LINK_RE.search(body or ""):
        return []
    return ["PR body links no issue: add `Closes #<issue>` (or `Refs #<issue>` for design gates)"]


def added_lines(diff: str):
    """Yield (file, line) for each added line of a unified diff."""
    current = None
    for line in diff.splitlines():
        if line.startswith("+++ "):
            path = line[4:].strip()
            current = path[2:] if path.startswith("b/") else path
        elif line.startswith("+") and not line.startswith("+++"):
            yield current, line[1:]


def check_diff(diff: str) -> list[str]:
    problems = []
    for path, line in added_lines(diff):
        if ALLOW_MARK in line:
            continue
        for label, pattern in FORBIDDEN:
            if pattern.search(line):
                problems.append("%s added in %s: %s" % (label, path, line.strip()[:80]))
    return problems


def check(branch: str, body: str, diff: str) -> list[str]:
    return check_branch(branch) + check_body(body) + check_diff(diff)


def from_github_event(event_path: str) -> tuple[str, str, str]:
    with open(event_path, encoding="utf-8") as handle:
        event = json.load(handle)
    pr = event["pull_request"]
    base = pr["base"]["sha"]
    diff = subprocess.run(["git", "diff", "--no-color", base + "...HEAD"],
                          check=True, capture_output=True, text=True).stdout
    return pr["head"]["ref"], pr.get("body") or "", diff


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--branch")
    parser.add_argument("--body-file")
    parser.add_argument("--diff-file")
    args = parser.parse_args(argv)
    if args.branch is not None:
        def read(path):
            if not path:
                return ""
            with open(path, encoding="utf-8") as handle:
                return handle.read()
        body, diff, branch = read(args.body_file), read(args.diff_file), args.branch
    else:
        event_path = os.environ.get("GITHUB_EVENT_PATH")
        if not event_path:
            parser.error("pass --branch, or run in GitHub Actions on a pull_request event")
        branch, body, diff = from_github_event(event_path)
    problems = check(branch, body, diff)
    for problem in problems:
        print("::error::" + problem if os.environ.get("GITHUB_ACTIONS") else "error: " + problem)
    if not problems:
        print("PR metadata ok: branch, issue link, no home paths or secrets added")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
