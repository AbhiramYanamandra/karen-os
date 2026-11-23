#!/usr/bin/env python3
"""Draft, approve and post LinkedIn updates, posting only exact owner-approved text.

  linkedin_post.py draft --text-file FILE --source URL [--account NAME]
  linkedin_post.py list | show <draft>
  linkedin_post.py approve <draft> [--hours 24]        owner only, interactive
  linkedin_post.py revoke <draft>
  linkedin_post.py post <draft> [--dry-run]
  linkedin_post.py reconcile <draft>

An approval is bound to the SHA-256 of the exact text, the account, the action,
an expiry and a one-time nonce, and is signed with a key kept in the macOS
Keychain. `approve` needs an interactive terminal and the owner typing the
code shown beside the full text, so an agent running commands cannot approve
its own draft. `post` checks everything again immediately before publishing.
Editing the text, a different account, expiry, revocation or an earlier post
all block it. An uncertain publisher response blocks retries until `reconcile`
finds out what happened.

Drafts and receipts live in ~/.local/state/karen-os/linkedin/, never in the
repository. Publishing goes through a command the owner configures in
~/.config/karen-os/linkedin.json after verifying the provider (see
docs/daily-review/linkedin.md); without one, nothing can be posted.
Standard library only.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import secrets
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

STATE_DIR = Path.home() / ".local" / "state" / "karen-os" / "linkedin"
CONFIG = Path.home() / ".config" / "karen-os" / "linkedin.json"
KEYCHAIN = {"service": "karen-os-approval", "account": "karen-os"}
ACTION = "linkedin.post"
MAX_HOURS = 24 * 7
TEMPFAIL = 75  # EX_TEMPFAIL: the publisher could not tell whether it posted


class Refused(Exception):
    """A check failed; nothing was published."""


class PublishFailed(Exception):
    """The publisher reports that it did not post."""


class Uncertain(Exception):
    """The publisher may or may not have posted."""


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def normalise(text: str) -> str:
    return text.replace("\r\n", "\n").strip() + "\n"


def text_hash(text: str) -> str:
    return hashlib.sha256(normalise(text).encode("utf-8")).hexdigest()


def code_for(digest: str) -> str:
    return digest[:8]


class Store:
    """One JSON file, written atomically."""

    def __init__(self, path: Path):
        self.path = Path(path)
        try:
            with open(self.path, encoding="utf-8") as handle:
                self.data = json.load(handle)
        except FileNotFoundError:
            self.data = {}
        for key in ("drafts", "approvals", "attempts", "used_nonces"):
            self.data.setdefault(key, [] if key == "used_nonces" else {})

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(self.data, handle, indent=2)
            handle.write("\n")
        os.replace(tmp, self.path)

    def draft(self, draft_id: str):
        try:
            return self.data["drafts"][draft_id]
        except KeyError:
            raise Refused("no draft %r" % draft_id)


class KeychainKey:
    """The approval-signing key, read from the macOS Keychain on each use."""

    def get(self) -> bytes:
        proc = subprocess.run(["security", "find-generic-password", "-s", KEYCHAIN["service"], "-a", KEYCHAIN["account"], "-w"],
                              capture_output=True, text=True)
        if proc.returncode or not proc.stdout.strip():
            raise Refused("approval key not available from the Keychain (see docs/daily-review/linkedin.md, setup step 1)")
        return proc.stdout.strip().encode("utf-8")


def mac(key: bytes, approval: dict) -> str:
    fields = {k: approval[k] for k in ("draft_id", "sha256", "account", "action", "approved_at", "expires_at", "nonce")}
    return hmac.new(key, json.dumps(fields, sort_keys=True).encode("utf-8"), hashlib.sha256).hexdigest()


def create_draft(store: Store, text: str, source: str, account: str, now: datetime) -> dict:
    if not text.strip():
        raise Refused("the draft is empty")
    if len(normalise(text)) > 3000:
        raise Refused("LinkedIn posts are limited to 3,000 characters")
    draft_id = "d-" + now.strftime("%Y%m%d%H%M%S") + "-" + secrets.token_hex(2)
    draft = {"id": draft_id, "text": normalise(text), "source": source, "account": account,
             "created_at": iso(now), "state": "draft", "post": None}
    store.data["drafts"][draft_id] = draft
    store.save()
    return draft


def approve(store: Store, key_source, draft_id: str, hours: float, now: datetime,
            is_tty=lambda: sys.stdin.isatty() and sys.stdout.isatty(), ask=input, say=print) -> dict:
    """Owner-only: interactive terminal, full text shown, code typed back."""
    if not is_tty():
        raise Refused("approve must be run by the owner in an interactive terminal")
    if not 0 < hours <= MAX_HOURS:
        raise Refused("approval lasts between a minute and %d hours" % MAX_HOURS)
    draft = store.draft(draft_id)
    if draft["state"] == "posted":
        raise Refused("draft %s was already posted" % draft_id)
    digest = text_hash(draft["text"])
    say("Account: %s\nSource: %s\n\n%s\n%s\n%s" % (draft["account"], draft["source"], "-" * 60, draft["text"].rstrip(), "-" * 60))
    say("This approves posting exactly the text above, once, to %s, within %g hours." % (draft["account"], hours))
    typed = ask("Type %s to approve, anything else to cancel: " % code_for(digest)).strip()
    if typed != code_for(digest):
        raise Refused("not approved")
    approval = {"draft_id": draft_id, "sha256": digest, "account": draft["account"], "action": ACTION,
                "approved_at": iso(now), "expires_at": iso(now + timedelta(hours=hours)), "nonce": secrets.token_hex(16)}
    approval["mac"] = mac(key_source.get(), approval)
    store.data["approvals"][draft_id] = approval
    draft["state"] = "approved"
    store.save()
    return approval


def revoke(store: Store, draft_id: str) -> bool:
    draft = store.draft(draft_id)
    approval = store.data["approvals"].pop(draft_id, None)
    if approval:
        store.data["used_nonces"].append(approval["nonce"])
    if draft["state"] == "approved":
        draft["state"] = "draft"
    store.save()
    return approval is not None


def check(store: Store, key_source, draft_id: str, account: str, now: datetime) -> tuple[dict, dict]:
    """Every condition for publishing, checked immediately before it."""
    draft = store.draft(draft_id)
    if draft["state"] == "posted" or draft.get("post"):
        raise Refused("draft %s was already posted: %s" % (draft_id, (draft.get("post") or {}).get("url")))
    attempt = store.data["attempts"].get(draft_id)
    if attempt and attempt["result"] == "uncertain":
        raise Refused("an earlier attempt may have posted; run `reconcile %s` first" % draft_id)
    approval = store.data["approvals"].get(draft_id)
    if not approval:
        raise Refused("draft %s has no owner approval" % draft_id)
    if not hmac.compare_digest(approval.get("mac", ""), mac(key_source.get(), approval)):
        raise Refused("the approval signature is invalid")
    if approval["action"] != ACTION:
        raise Refused("the approval is for %r, not %r" % (approval["action"], ACTION))
    if approval["sha256"] != text_hash(draft["text"]):
        raise Refused("the text changed after approval; approve the new text")
    if approval["account"] != account or draft["account"] != account:
        raise Refused("the approval is for account %r, not %r" % (approval["account"], account))
    if approval["nonce"] in store.data["used_nonces"]:
        raise Refused("this approval was revoked or already used")
    if now >= parse_iso(approval["expires_at"]):
        raise Refused("the approval expired at %s" % approval["expires_at"])
    return draft, approval


def post(store: Store, key_source, publisher, draft_id: str, account: str, now: datetime, dry_run: bool = False) -> dict:
    draft, approval = check(store, key_source, draft_id, account, now)
    if dry_run:
        return {"dry_run": True, "account": account, "sha256": approval["sha256"]}
    if publisher is None:
        raise Refused("no publisher configured in %s; nothing was posted" % CONFIG)
    store.data["attempts"][draft_id] = {"started_at": iso(now), "sha256": approval["sha256"], "nonce": approval["nonce"], "result": "uncertain"}
    store.save()  # recorded before publishing, so a crash mid-call cannot lead to a blind retry
    try:
        result = publisher.publish(account, draft["text"])
    except Uncertain as error:
        store.data["attempts"][draft_id]["error"] = str(error)
        store.save()
        raise
    except PublishFailed as error:
        store.data["attempts"][draft_id].update(result="failed", error=str(error))
        store.save()
        raise
    finish(store, draft, approval, result, now)
    return result


def finish(store: Store, draft: dict, approval: dict, result: dict, now: datetime):
    draft.update(state="posted", post={"id": result.get("id"), "url": result.get("url"), "posted_at": iso(now)})
    store.data["used_nonces"].append(approval["nonce"])
    store.data["attempts"][draft["id"]]["result"] = "posted"
    store.save()


def reconcile(store: Store, publisher, draft_id: str, now: datetime) -> str:
    draft = store.draft(draft_id)
    attempt = store.data["attempts"].get(draft_id)
    if not attempt or attempt["result"] != "uncertain":
        return "nothing to reconcile"
    if publisher is None:
        raise Refused("no publisher configured; cannot check whether the post exists")
    found = publisher.find(draft["account"], draft["text"])
    if found:
        approval = store.data["approvals"].get(draft_id) or {"nonce": attempt["nonce"]}
        finish(store, draft, approval, found, now)
        return "posted: %s" % found.get("url")
    attempt["result"] = "failed"
    attempt["error"] = "not found when reconciled at %s" % iso(now)
    store.save()
    return "not posted; `post` may be run again while the approval is valid"


class CommandPublisher:
    """Runs owner-configured commands. Contract in docs/daily-review/linkedin.md."""

    def __init__(self, publish_command, find_command, timeout=60):
        self.publish_command, self.find_command, self.timeout = publish_command, find_command, timeout

    def _run(self, command, payload):
        try:
            proc = subprocess.run(command, input=json.dumps(payload), capture_output=True, text=True, timeout=self.timeout)
        except subprocess.TimeoutExpired:
            raise Uncertain("the publisher timed out")
        return proc

    def publish(self, account, text):
        proc = self._run(self.publish_command, {"account": account, "text": text})
        if proc.returncode == TEMPFAIL:
            raise Uncertain(proc.stderr.strip()[:200] or "the publisher could not confirm")
        if proc.returncode:
            raise PublishFailed(proc.stderr.strip()[:200] or "exit %d" % proc.returncode)
        try:
            result = json.loads(proc.stdout)
        except ValueError:
            raise Uncertain("the publisher exited 0 without a readable result")
        if not result.get("url") and not result.get("id"):
            raise Uncertain("the publisher returned no post id or link")
        return result

    def find(self, account, text):
        if not self.find_command:
            raise Refused("no find command configured; check LinkedIn by hand, then use `reconcile --posted URL` or `--not-posted`")
        proc = self._run(self.find_command, {"account": account, "text": text})
        if proc.returncode:
            raise Refused("could not check: %s" % (proc.stderr.strip()[:200] or "exit %d" % proc.returncode))
        result = json.loads(proc.stdout or "null")
        return result or None


class ManualAnswer:
    """For `reconcile --posted URL` / `--not-posted`, after the owner checked LinkedIn by hand."""

    def __init__(self, url):
        self.url = url

    def find(self, account, text):
        return {"id": None, "url": self.url} if self.url else None


def load_config(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return {}


def build_parser():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--store", default=str(STATE_DIR / "store.json"))
    p.add_argument("--config", default=str(CONFIG))
    sub = p.add_subparsers(dest="command", required=True)
    d = sub.add_parser("draft")
    d.add_argument("--text-file", required=True)
    d.add_argument("--source", required=True, help="the merged PR or finished project")
    d.add_argument("--account")
    sub.add_parser("list")
    for name in ("show", "approve", "revoke", "post", "reconcile"):
        s = sub.add_parser(name)
        s.add_argument("draft")
        if name == "approve":
            s.add_argument("--hours", type=float, default=24)
        if name == "post":
            s.add_argument("--dry-run", action="store_true")
        if name == "reconcile":
            g = s.add_mutually_exclusive_group()
            g.add_argument("--posted", metavar="URL", help="you found the post on LinkedIn")
            g.add_argument("--not-posted", action="store_true", help="you checked and it is not there")
    return p


def main(argv=None, key_source=None, publisher=None, now=None, is_tty=None, ask=None) -> int:
    args = build_parser().parse_args(argv)
    store, config = Store(args.store), load_config(args.config)
    now = now or datetime.now(timezone.utc)
    key_source = key_source or KeychainKey()
    if publisher is None and config.get("publish_command"):
        publisher = CommandPublisher(config["publish_command"], config.get("find_command"))
    account = config.get("account")
    try:
        if args.command == "draft":
            with open(args.text_file, encoding="utf-8") as handle:
                text = handle.read()
            if not (args.account or account):
                raise Refused("no account: pass --account or set it in %s" % args.config)
            draft = create_draft(store, text, args.source, args.account or account, now)
            print("draft %s saved for %s (code %s); the owner approves with: approve %s" % (
                draft["id"], draft["account"], code_for(text_hash(draft["text"])), draft["id"]))
        elif args.command == "list":
            for draft in store.data["drafts"].values():
                print("%s  %-8s  %s  %s" % (draft["id"], draft["state"], draft["account"], draft["source"]))
        elif args.command == "show":
            draft = store.draft(args.draft)
            print(json.dumps(dict(draft, sha256=text_hash(draft["text"]), approval=store.data["approvals"].get(args.draft)), indent=2))
        elif args.command == "approve":
            options = {k: v for k, v in (("is_tty", is_tty), ("ask", ask)) if v is not None}
            approval = approve(store, key_source, args.draft, args.hours, now, **options)
            print("approved until %s" % approval["expires_at"])
        elif args.command == "revoke":
            print("revoked" if revoke(store, args.draft) else "there was no approval to revoke")
        elif args.command == "post":
            if not account:
                raise Refused("no account set in %s" % args.config)
            result = post(store, key_source, publisher, args.draft, account, now, args.dry_run)
            print("dry run: every check passed; nothing was posted" if args.dry_run else "posted: %s" % result.get("url"))
        elif args.command == "reconcile":
            if args.posted or args.not_posted:
                publisher = ManualAnswer(args.posted)
            print(reconcile(store, publisher, args.draft, now))
        return 0
    except Refused as error:
        print("refused: %s" % error, file=sys.stderr)
        return 1
    except PublishFailed as error:
        print("not posted: %s" % error, file=sys.stderr)
        return 1
    except Uncertain as error:
        print("uncertain: %s. Run `reconcile %s` before anything else." % (error, args.draft), file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
