#!/usr/bin/env python3
"""Check the machine-checkable parts of a pull request (engineering standard).

Fails when:
- the head branch is not `<type>/<issue>-<short-description>`;
- the PR body links no issue with `Closes #<n>` or `Refs #<n>`;
- the diff adds a home-directory path or a common secret pattern;
- a skill quarantine record is removed or changed, or a skill leaves quarantine without
  an owner `lifted` (docs/organisation/skill-onboarding.md; attested: CI can't prove who lifted);
- the `karen-profile` block is missing or fails the workflow-profile checks
  (docs/proposals/pr-enforcement.md, revision 1). Each check is labelled there as
  verified (CI really checks it) or attested (CI only sees that the claim exists).

In CI it reads the GitHub event file and diffs against the base branch.
Locally: `check_pr.py --branch NAME --body-file FILE --diff-file FILE [--repo OWNER/NAME]`.
A diff line containing `pr-check: allow` is skipped, for deliberate examples.
Standard library only.
"""
from __future__ import annotations

import argparse
import codecs
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import profiles  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]

BRANCH_TYPES = ("feat", "fix", "hotfix", "refactor", "docs", "test", "chore", "ci", "release")
BRANCH_RE = re.compile(r"^(?:%s)/[0-9]+-[a-z0-9]+(?:-[a-z0-9]+)*$" % "|".join(BRANCH_TYPES))
LINK_RE = re.compile(r"\b(?:Closes|Fixes|Resolves|Refs)\s+(?:[\w.-]+/[\w.-]+)?#[0-9]+\b", re.IGNORECASE)
ALLOW_MARK = "pr-check: allow"

PROFILE_RE = re.compile(r"```karen-profile[ \t]*\n(.*?)\n```", re.S)
PROFILE_KEYS = {"type", "risk", "flags", "design_approval", "skills", "review", "tests", "owner_interventions", "exceptions"}
# Which profiles each branch type may declare: UI and security work arrive on feat or fix branches.
BRANCH_PROFILES = {"feat": {"feature", "ui", "security"}, "fix": {"bug", "security"}, "hotfix": {"bug", "security"},
                   "docs": {"docs"}, "test": {"testing"}, "chore": {"chore"}, "refactor": {"chore"},
                   "ci": {"chore"}, "release": {"chore"}}
# shortcut: any added line in these files counts as a new dependency, so version bumps need the flag too; parse them when that gets noisy.
DEPENDENCY_FILES = ("requirements.txt", "pyproject.toml", "package.json", "Pipfile", "go.mod", "Cargo.toml", "Gemfile")
DESIGN_PR_RE = re.compile(r"https://github\.com/([\w.-]+/[\w.-]+)/pull/([0-9]+)")

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


def git_path(token: str, prefixed: bool = True) -> str:
    """A path as git prints it: `b/x`, or C-quoted `"b/caf\\303\\251"` for unusual names. Returns `x`."""
    token = token.strip()
    if token.startswith('"') and token.endswith('"'):
        token = codecs.escape_decode(token[1:-1].encode("utf-8"))[0].decode("utf-8", "replace")
    return token[2:] if prefixed and token[:2] in ("a/", "b/") else token


def added_lines(diff: str):
    """Yield (file, line) for each added line of a unified diff."""
    current = None
    for line in diff.split("\n"):  # not splitlines(): git keeps U+2028 and friends raw in paths
        if line.startswith("+++ "):
            current = git_path(line[4:])
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


CANDIDATES = "docs/organisation/skill-candidates.json"


def check_quarantine(base: dict | None, head: dict | None) -> list[str]:
    """Compare skill-candidates.json before and after: a quarantine record never disappears or
    changes, except by gaining an owner `lifted`, and an entry leaves quarantine only once lifted."""
    if not base or not head:
        return []
    after = {e.get("id"): e for e in head.get("candidates", [])}
    problems = []
    for old in base.get("candidates", []):
        record = old.get("quarantine")
        if not isinstance(record, dict):
            continue
        new = after.get(old.get("id"))
        name = old.get("id")
        if not isinstance(new, dict) or not isinstance(new.get("quarantine"), dict):
            problems.append("%s: quarantine record for %s was removed; records stay after an owner lift" % (CANDIDATES, name))
            continue
        changed = new["quarantine"]
        # An unlifted record may gain `lifted` and nothing else; a lifted record never changes.
        unchanged = changed == record if record.get("lifted") else {k: v for k, v in changed.items() if k != "lifted"} == record
        if not unchanged:
            problems.append("%s: quarantine record for %s was changed; it may only gain an owner `lifted`" % (CANDIDATES, name))
        lifted = changed.get("lifted")
        if old.get("state") == "quarantined" and new.get("state") != "quarantined" and not (
                isinstance(lifted, dict) and lifted.get("by") == "owner"):
            problems.append("%s: %s left quarantine without `lifted` by the owner" % (CANDIDATES, name))
    return problems


def candidates_at(ref: str) -> dict | None:
    """skill-candidates.json at a git ref, or None when it doesn't exist there."""
    shown = subprocess.run(["git", "show", "%s:%s" % (ref, CANDIDATES)], capture_output=True, text=True)
    return json.loads(shown.stdout) if shown.returncode == 0 else None


GIT_HEADER = re.compile(r'^diff --git ("(?:[^"\\]|\\.)*"|a/.*?) ("(?:[^"\\]|\\.)*"|b/.*)$')


PATH_LINES = ("rename from ", "rename to ", "copy from ", "copy to ")


def changed_files(diff: str) -> set[str]:
    """Source and destination of every changed file, so a rename out of a guarded folder still counts.

    The `diff --git` header is ambiguous when a path contains " b/", so the one-path lines
    (rename/copy from/to, ---/+++) are read too; the header only adds paths for mode-only changes."""
    files = set()
    for line in diff.split("\n"):  # not splitlines(): git keeps U+2028 and friends raw in paths
        found = GIT_HEADER.match(line)
        if found:
            files.update(git_path(token) for token in found.groups())
        elif line.startswith(PATH_LINES):
            files.add(git_path(line.split(" ", 2)[2], prefixed=False))
        elif line.startswith(("--- ", "+++ ")) and line[4:].strip() != "/dev/null":
            files.add(git_path(line[4:]))
    return files


def pinned_paths() -> set[str]:
    manifest = json.loads((ROOT / "context" / "manifest.json").read_text(encoding="utf-8"))
    return {s["path"] for s in manifest["sources"]} | set(manifest.get("task_revisions", {}))


def diff_flags(diff: str, pinned: set[str]) -> set[str]:
    """Flags the diff itself proves are needed (check 4)."""
    files = changed_files(diff)
    added = {path for path, _ in added_lines(diff)}
    needed = set()
    if any(f.startswith(".github/workflows/") for f in files):
        needed.add("ci_change")
    if files & pinned:
        needed.add("pinned_policy")
    if any(Path(f or "").name in DEPENDENCY_FILES for f in added):
        needed.add("new_dependency")
    return needed


def gh_pr_merged(repo: str, number: int) -> bool:
    out = subprocess.run(["gh", "api", "repos/%s/pulls/%d" % (repo, number), "--jq", ".merged"],
                         check=True, capture_output=True, text=True).stdout
    return out.strip() == "true"


def _filled(value) -> bool:
    return bool(str(value or "").strip())


def load_project_profile(root: Path | None = None) -> dict | None:
    """The repository's own `.karen/profile.json`, if it has one. Projects can tighten company profiles, never loosen."""
    path = (root or Path.cwd()) / ".karen" / "profile.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def check_profile(branch: str, body: str, diff: str, repo: str | None = None, pr_merged=gh_pr_merged,
                  data=None, registry=None, pinned=None, project=None, runtimes=None) -> list[str]:
    """Checks 1 to 10 of the PR-enforcement proposal against the PR's karen-profile block."""
    match = PROFILE_RE.search(body or "")
    if not match:
        return ["PR body has no ```karen-profile block (docs/organisation/engineering.md, Pull requests)"]
    try:
        block = json.loads(match.group(1))
    except ValueError as exc:
        return ["karen-profile block is not valid JSON: %s" % exc]
    if not isinstance(block, dict):
        return ["karen-profile block must be a JSON object"]
    data = data if data is not None else json.loads(profiles.PROFILES.read_text(encoding="utf-8"))
    if registry is None or runtimes is None:
        entries = json.loads(profiles.REGISTRY.read_text(encoding="utf-8")).get("entries", [])
        if registry is None:
            registry = {e["id"]: e.get("sha256") for e in entries if e.get("approval_status") == "approved"}
        if runtimes is None:
            runtimes = {e["id"]: e.get("compatible_runtimes") or [] for e in entries}
    problems = ["karen-profile has unknown fields: %s" % ", ".join(sorted(block.keys() - PROFILE_KEYS))] if block.keys() - PROFILE_KEYS else []

    kind = branch.split("/", 1)[0]
    declared = data["type_aliases"].get(block.get("type"), block.get("type"))
    if kind in BRANCH_PROFILES and declared not in BRANCH_PROFILES[kind]:
        problems.append("karen-profile type %r does not fit a %s/ branch (allowed: %s)"
                        % (block.get("type"), kind, ", ".join(sorted(BRANCH_PROFILES[kind]))))
    flags = block.get("flags") or []
    if not isinstance(flags, list):
        return problems + ["karen-profile flags must be a list"]
    missing_flags = sorted(diff_flags(diff, pinned if pinned is not None else pinned_paths()) - set(flags))
    problems += ["the diff needs flag %r in karen-profile" % f for f in missing_flags]
    try:
        # Resolve with the flags the diff proves, so a missing flag can't also hide its requirements.
        result = profiles.resolve(data, block.get("type"), block.get("risk"), flags + missing_flags,
                                  project=project, exceptions=block.get("exceptions") or [], registry=set(registry))
    except profiles.InvalidInput as exc:
        return problems + ["karen-profile: %s" % exc]
    problems += ["karen-profile conflict: %s" % c for c in result["conflicts"]]

    skills = block.get("skills") or []
    if not isinstance(skills, list) or not all(isinstance(s, dict) for s in skills):
        return problems + ["karen-profile skills must be a list of objects"]
    # Every listed skill, required or not, names a stage, runtime and evidence, at its registry hash.
    for entry in skills:
        name = entry.get("id") or "(no id)"
        if entry.get("stage") not in result["stages"]:
            problems.append("skill %s has no valid stage" % name)
        if name in registry and entry.get("sha256") != registry[name]:
            problems.append("skill %s sha256 is not the registry version" % name)
        if name in runtimes and _filled(entry.get("runtime")) and entry["runtime"] not in runtimes[name]:
            problems.append("skill %s is not approved for runtime %s" % (name, entry["runtime"]))
        for field in ("runtime", "evidence"):
            if not _filled(entry.get(field)):
                problems.append("skill %s has no %s" % (name, "load evidence" if field == "evidence" else field))
    listed = {(s.get("id"), s.get("stage")) for s in skills}
    for stage, info in result["stages"].items():
        for skill, level in info["skills"].items():
            if level != "required" or skill in info["waived"]:
                continue
            if skill not in registry:
                problems.append("required skill %s (%s) is not in the registry, so that stage holds" % (skill, stage))
            elif (skill, stage) not in listed:
                problems.append("required skill %s (%s) is not listed for that stage in karen-profile skills" % (skill, stage))

    if result["stages"]["design"]["gates"]:
        found = DESIGN_PR_RE.fullmatch(str(block.get("design_approval") or "").strip())
        if not found:
            problems.append("design gate: design_approval must link the merged design PR")
        elif repo and found.group(1).lower() != repo.lower():
            problems.append("design gate: design_approval must be a PR in %s" % repo)
        else:
            try:
                merged = pr_merged(found.group(1), int(found.group(2)))
            except (OSError, subprocess.CalledProcessError) as exc:
                problems.append("design gate: could not confirm the design PR is merged (%s)" % exc)
            else:
                if not merged:
                    problems.append("design gate: the design PR is not merged")

    if result["risk"] != "low":
        review = block.get("review") if isinstance(block.get("review"), dict) else {}
        if not all(_filled(review.get(k)) for k in ("by", "session", "findings")) \
                or str(review.get("by")).strip().lower() in ("self", "self-review"):
            problems.append("%s risk needs a review by a different session or provider: fill review.by, "
                            "review.session and review.findings" % result["risk"])
    tests = block.get("tests")
    if not isinstance(tests, list) or not any(_filled(t) for t in tests):
        problems.append("karen-profile tests is empty: list the commands run and their results")
    interventions = block.get("owner_interventions")
    if not isinstance(interventions, int) or isinstance(interventions, bool) or interventions < 0:
        problems.append("karen-profile owner_interventions must be a whole number")
    return problems


def check(branch: str, body: str, diff: str, base_ref: str | None = None, **profile_options) -> list[str]:
    problems = check_branch(branch) + check_body(body) + check_diff(diff)
    if base_ref and CANDIDATES in changed_files(diff):
        head = Path(CANDIDATES)
        problems += check_quarantine(candidates_at(base_ref), json.loads(head.read_text(encoding="utf-8")) if head.is_file() else None)
    return problems + check_profile(branch, body, diff, **profile_options)


def from_github_event(event_path: str) -> tuple[str, str, str, str, str]:
    with open(event_path, encoding="utf-8") as handle:
        event = json.load(handle)
    pr = event["pull_request"]
    base = pr["base"]["sha"]
    diff = subprocess.run(["git", "-c", "core.quotePath=false", "diff", "--no-color", base + "...HEAD"],
                          check=True, capture_output=True, text=True).stdout
    return pr["head"]["ref"], pr.get("body") or "", diff, event["repository"]["full_name"], base


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--branch")
    parser.add_argument("--body-file")
    parser.add_argument("--diff-file")
    parser.add_argument("--repo", help="OWNER/NAME, so a design approval must be a PR in this repository")
    parser.add_argument("--base", help="base git ref, to compare skill quarantine records (CI uses the PR base)")
    args = parser.parse_args(argv)
    if args.branch is not None:
        def read(path):
            if not path:
                return ""
            with open(path, encoding="utf-8") as handle:
                return handle.read()
        body, diff, branch, repo, base = read(args.body_file), read(args.diff_file), args.branch, args.repo, args.base
        project = load_project_profile()
    else:
        event_path = os.environ.get("GITHUB_EVENT_PATH")
        if not event_path:
            parser.error("pass --branch, or run in GitHub Actions on a pull_request event")
        branch, body, diff, repo, base = from_github_event(event_path)
        project = load_project_profile()
    problems = check(branch, body, diff, base_ref=base, repo=repo, project=project)
    for problem in problems:
        print("::error::" + problem if os.environ.get("GITHUB_ACTIONS") else "error: " + problem)
    if not problems:
        print("PR metadata ok: branch, issue link, no home paths or secrets added, karen-profile checks pass")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
