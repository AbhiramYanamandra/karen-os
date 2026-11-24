#!/usr/bin/env python3
"""Statically review a candidate skill package. Read-only: it runs nothing and makes no network calls.

    python3 -B scripts/skill_review.py <package-folder>

Prints JSON: the catalogue tree hash (docs/organisation/skill-candidates.json `hash_method`), the SKILL.md
hash and one flag per suspicious line or file. Flags are prompts for the human review in
docs/organisation/skill-onboarding.md. A clean result is not approval, and the script never decides:
it exits 0 whenever it could read the folder.
"""
import hashlib
import json
import os
import re
import sys

MAX_TEXT_BYTES = 1_000_000
SCRIPT_EXTENSIONS = {".sh", ".bash", ".zsh", ".py", ".js", ".mjs", ".cjs", ".ts", ".rb", ".pl", ".ps1", ".bat", ".cmd"}
INSTALL_FILES = {"setup.py", "setup.cfg", "pyproject.toml", "Makefile", "install.sh", "postinstall.sh"}
PACKAGE_HOOKS = {"preinstall", "install", "postinstall", "prepare", "prepublish"}
# shortcut: phrase lists catch common patterns only; a careful attacker can evade them. Extend from real findings.
LINE_PATTERNS = [
    ("url", re.compile(r"\bhttps?://[^\s)\"'<>]+", re.I)),
    ("credential_path", re.compile(
        r"\.ssh\b|id_rsa|id_ed25519|\.aws/|\.netrc|\.gnupg|\.npmrc|\.pypirc|\.git-credentials|keychain|"
        r"\.env\b|[A-Z][A-Z0-9_]*(?:TOKEN|SECRET|API_KEY|PASSWORD)\b", re.I)),
    ("settings_or_install", re.compile(
        r"\.claude/settings|settings(?:\.local)?\.json|\.codex/config|hooks\.json|\bskills (?:add|update)\b|"
        r"\b(?:npm|pnpm|yarn|pip3?|brew|gem|cargo) (?:install|add|update)\b|curl[^|\n]*\|\s*(?:ba|z)?sh", re.I)),
    ("override_phrase", re.compile(
        r"ignore (?:all |any )?(?:previous|prior|above|earlier) instructions|disregard (?:the |your )?(?:rules|instructions|system)|"
        r"do not (?:tell|inform|show) the user|without (?:asking|telling) the user|you are now\b|bypass (?:the )?(?:guard|safety|review|approval)",
        re.I)),
]
OVERRIDE = LINE_PATTERNS[-1][1]
CONFIG_PATH = re.compile(r"(?:^|/)(?:\.claude|\.codex|\.cursor|hooks)(?:/|$)|(?:^|/)(?:\.mcp\.json|settings(?:\.local)?\.json|hooks\.json)$")
HIDDEN = re.compile("[\u00ad\u200b-\u200f\u202a-\u202e\u2060-\u2064\ufeff\U000e0000-\U000e007f]")


def tree_hash(root):
    """SHA-256 over 'relative-path NUL file-sha256 LF' in os.walk order, directories and files sorted."""
    records = []
    for folder, dirs, files in os.walk(root):
        dirs.sort()
        linked_dirs = [d for d in dirs if os.path.islink(os.path.join(folder, d))]
        for name in sorted(files + linked_dirs):
            path = os.path.join(folder, name)
            if os.path.islink(path):  # never follow a link out of the package; hash where it points instead
                digest = hashlib.sha256(("symlink:" + os.readlink(path)).encode()).hexdigest()
            elif not os.path.isfile(path):
                digest = hashlib.sha256(b"special-file").hexdigest()
            else:
                with open(path, "rb") as handle:
                    digest = hashlib.sha256(handle.read()).hexdigest()
            records.append("%s\0%s\n" % (os.path.relpath(path, root), digest))
    return hashlib.sha256("".join(records).encode()).hexdigest()


def _package_hooks(text):
    try:
        scripts = json.loads(text).get("scripts") or {}
        if not isinstance(scripts, dict):
            raise ValueError("scripts is not an object")
    except Exception:  # hostile input: any parse failure is a finding, never a crash
        return ["unparseable package.json"]
    return sorted(PACKAGE_HOOKS & set(scripts))


def review(root):
    if not os.path.isdir(root):
        raise ValueError("not a folder: %s" % root)
    flags, files = [], 0
    for folder, dirs, names in os.walk(root):
        dirs.sort()
        for name in sorted(names) + [d for d in dirs if os.path.islink(os.path.join(folder, d))]:
            path = os.path.join(folder, name)
            rel = os.path.relpath(path, root)
            if os.path.islink(path):
                flags.append(dict(kind="symlink", file=rel, detail=os.readlink(path)))
                continue
            if not os.path.isfile(path):
                flags.append(dict(kind="special_file", file=rel, detail="not a regular file, not read"))
                continue
            files += 1
            if CONFIG_PATH.search(rel.replace(os.sep, "/")):
                flags.append(dict(kind="config_file", file=rel, detail="agent or runtime configuration shipped in the package"))
            ext = os.path.splitext(name)[1].lower()
            if ext in SCRIPT_EXTENSIONS or os.access(path, os.X_OK):
                flags.append(dict(kind="executable", file=rel, detail="script or executable file"))
            if name in INSTALL_FILES:
                flags.append(dict(kind="install_hook", file=rel, detail="install or build file"))
            with open(path, "rb") as handle:
                data = handle.read(MAX_TEXT_BYTES + 1)
            if b"\0" in data[:8192]:
                flags.append(dict(kind="binary", file=rel, detail="binary content, not scanned"))
                continue
            if len(data) > MAX_TEXT_BYTES:
                flags.append(dict(kind="oversize", file=rel, detail="only the first %d bytes scanned" % MAX_TEXT_BYTES))
            text = data[:MAX_TEXT_BYTES].decode("utf-8", errors="replace")
            if name == "package.json":
                for hook in _package_hooks(text):
                    flags.append(dict(kind="install_hook", file=rel, detail="package.json script: %s" % hook))
            for number, line in enumerate(text.splitlines(), 1):
                for kind, pattern in LINE_PATTERNS:
                    found = pattern.search(line)
                    if found:
                        flags.append(dict(kind=kind, file=rel, line=number, detail=found.group(0)))
            if HIDDEN.search(text):
                flags.append(dict(kind="hidden_unicode", file=rel, detail="invisible or bidirectional characters"))
            # Phrases split across lines or broken up by invisible characters.
            joined = OVERRIDE.search(re.sub(r"\s+", " ", HIDDEN.sub("", text)))
            if joined and not any(f["kind"] == "override_phrase" and f["file"] == rel for f in flags):
                flags.append(dict(kind="override_phrase", file=rel, detail=joined.group(0)))
    skill_md = os.path.join(root, "SKILL.md")
    skill_sha = None
    if os.path.isfile(skill_md) and not os.path.islink(skill_md):
        with open(skill_md, "rb") as handle:
            skill_sha = hashlib.sha256(handle.read()).hexdigest()
    return dict(tree_sha256=tree_hash(root), skill_md_sha256=skill_sha, files=files,
                flag_kinds=sorted({f["kind"] for f in flags}), flags=flags)


def main(argv):
    if len(argv) != 2:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    try:
        print(json.dumps(review(argv[1]), indent=2))
    except (OSError, ValueError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
