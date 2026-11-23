"""Tests for scripts/linkedin_post.py with simulated publisher responses. Nothing is posted."""
import importlib.util
import io
import json
import pathlib
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("linkedin_post", ROOT / "scripts" / "linkedin_post.py")
lp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lp)

NOW = datetime(2026, 3, 14, 9, 0, tzinfo=timezone.utc)
ACCOUNT = "example-person"
TEXT = "Shipped a read-only engineering digest this week.\n\nIt turns GitHub state into a short morning brief.\n"


class StaticKey:
    def __init__(self, key=b"test-key-not-secret"):
        self.key = key

    def get(self):
        return self.key


class FakePublisher:
    def __init__(self, outcomes=("ok",), existing=None):
        self.outcomes, self.existing, self.published = list(outcomes), existing, []

    def publish(self, account, text):
        outcome = self.outcomes.pop(0) if len(self.outcomes) > 1 else self.outcomes[0]
        if outcome == "uncertain":
            raise lp.Uncertain("connection reset after sending")
        if outcome == "failed":
            raise lp.PublishFailed("401 token expired")
        self.published.append((account, text))
        return {"id": "urn:li:share:%d" % len(self.published), "url": "https://www.linkedin.com/feed/update/%d" % len(self.published)}

    def find(self, account, text):
        return self.existing


class Flow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store_path = pathlib.Path(self.tmp.name, "state", "store.json")
        self.key = StaticKey()

    def tearDown(self):
        self.tmp.cleanup()

    def store(self):
        return lp.Store(self.store_path)

    def drafted(self, text=TEXT):
        return lp.create_draft(self.store(), text, "https://github.com/octo/demo/pull/40", ACCOUNT, NOW)["id"]

    def approved(self, hours=24, now=NOW):
        draft_id = self.drafted()
        code = lp.code_for(lp.text_hash(TEXT))
        lp.approve(self.store(), self.key, draft_id, hours, now, is_tty=lambda: True, ask=lambda prompt: code, say=lambda *a: None)
        return draft_id

    def post(self, draft_id, publisher, now=NOW, account=ACCOUNT, key=None, dry_run=False):
        return lp.post(self.store(), key or self.key, publisher, draft_id, account, now, dry_run)


class ApprovalTests(Flow):
    def test_approved_text_posts_once_and_records_link(self):
        draft_id, pub = self.approved(), FakePublisher()
        result = self.post(draft_id, pub, now=NOW + timedelta(hours=1))
        self.assertEqual(pub.published, [(ACCOUNT, TEXT)])
        draft = self.store().draft(draft_id)
        self.assertEqual(draft["state"], "posted")
        self.assertEqual(draft["post"]["url"], result["url"])
        with self.assertRaisesRegex(lp.Refused, "already posted"):
            self.post(draft_id, pub)
        self.assertEqual(len(pub.published), 1)

    def test_unapproved_draft_never_posts(self):
        draft_id, pub = self.drafted(), FakePublisher()
        with self.assertRaisesRegex(lp.Refused, "no owner approval"):
            self.post(draft_id, pub)
        self.assertEqual(pub.published, [])

    def test_approve_needs_interactive_terminal(self):
        draft_id = self.drafted()
        with self.assertRaisesRegex(lp.Refused, "interactive terminal"):
            lp.approve(self.store(), self.key, draft_id, 24, NOW, is_tty=lambda: False, ask=lambda p: "x", say=lambda *a: None)
        self.assertEqual(self.store().data["approvals"], {})

    def test_wrong_code_does_not_approve(self):
        draft_id = self.drafted()
        with self.assertRaisesRegex(lp.Refused, "not approved"):
            lp.approve(self.store(), self.key, draft_id, 24, NOW, is_tty=lambda: True, ask=lambda p: "yes", say=lambda *a: None)
        self.assertEqual(self.store().data["approvals"], {})

    def test_approval_shows_full_text_and_account(self):
        draft_id, shown = self.drafted(), []
        code = lp.code_for(lp.text_hash(TEXT))
        lp.approve(self.store(), self.key, draft_id, 24, NOW, is_tty=lambda: True, ask=lambda p: code, say=shown.append)
        self.assertIn(TEXT.rstrip(), "\n".join(shown))
        self.assertIn(ACCOUNT, "\n".join(shown))

    def test_edited_text_blocks_posting(self):
        draft_id = self.approved()
        store = self.store()
        store.data["drafts"][draft_id]["text"] = TEXT + "One more line.\n"
        store.save()
        pub = FakePublisher()
        with self.assertRaisesRegex(lp.Refused, "text changed"):
            self.post(draft_id, pub)
        self.assertEqual(pub.published, [])

    def test_expired_approval(self):
        draft_id = self.approved(hours=2)
        with self.assertRaisesRegex(lp.Refused, "expired"):
            self.post(draft_id, FakePublisher(), now=NOW + timedelta(hours=2))

    def test_revoked_approval_cannot_be_restored(self):
        draft_id = self.approved()
        saved = dict(self.store().data["approvals"][draft_id])
        self.assertTrue(lp.revoke(self.store(), draft_id))
        with self.assertRaisesRegex(lp.Refused, "no owner approval"):
            self.post(draft_id, FakePublisher())
        store = self.store()
        store.data["approvals"][draft_id] = saved  # a copy put back by hand
        store.save()
        with self.assertRaisesRegex(lp.Refused, "revoked or already used"):
            self.post(draft_id, FakePublisher())

    def test_other_account(self):
        draft_id = self.approved()
        with self.assertRaisesRegex(lp.Refused, "account"):
            self.post(draft_id, FakePublisher(), account="someone-else")

    def test_forged_or_altered_approval(self):
        draft_id = self.drafted()
        store = self.store()
        forged = {"draft_id": draft_id, "sha256": lp.text_hash(TEXT), "account": ACCOUNT, "action": lp.ACTION,
                  "approved_at": lp.iso(NOW), "expires_at": lp.iso(NOW + timedelta(days=1)), "nonce": "n1"}
        forged["mac"] = lp.mac(b"guessed-key", forged)
        store.data["approvals"][draft_id] = forged
        store.save()
        with self.assertRaisesRegex(lp.Refused, "signature"):
            self.post(draft_id, FakePublisher())

        draft_id = self.approved()
        store = self.store()
        store.data["approvals"][draft_id]["expires_at"] = lp.iso(NOW + timedelta(days=365))
        store.save()
        with self.assertRaisesRegex(lp.Refused, "signature"):
            self.post(draft_id, FakePublisher())

    def test_dry_run_checks_but_does_not_publish(self):
        draft_id, pub = self.approved(), FakePublisher()
        self.assertTrue(self.post(draft_id, pub, dry_run=True)["dry_run"])
        self.assertEqual(pub.published, [])
        self.assertEqual(self.store().draft(draft_id)["state"], "approved")

    def test_no_publisher_configured(self):
        draft_id = self.approved()
        with self.assertRaisesRegex(lp.Refused, "no publisher configured"):
            self.post(draft_id, None)


class RetryTests(Flow):
    def test_uncertain_blocks_retry_until_reconciled_found(self):
        draft_id = self.approved()
        with self.assertRaises(lp.Uncertain):
            self.post(draft_id, FakePublisher(["uncertain"]))
        pub = FakePublisher()
        with self.assertRaisesRegex(lp.Refused, "reconcile"):
            self.post(draft_id, pub)
        self.assertEqual(pub.published, [])
        found = FakePublisher(existing={"id": "urn:li:share:7", "url": "https://www.linkedin.com/feed/update/7"})
        self.assertIn("posted", lp.reconcile(self.store(), found, draft_id, NOW))
        self.assertEqual(self.store().draft(draft_id)["post"]["id"], "urn:li:share:7")
        with self.assertRaisesRegex(lp.Refused, "already posted"):
            self.post(draft_id, pub)

    def test_uncertain_then_not_found_allows_one_retry(self):
        draft_id = self.approved()
        with self.assertRaises(lp.Uncertain):
            self.post(draft_id, FakePublisher(["uncertain"]))
        self.assertIn("not posted", lp.reconcile(self.store(), FakePublisher(existing=None), draft_id, NOW))
        pub = FakePublisher()
        self.post(draft_id, pub)
        self.assertEqual(len(pub.published), 1)

    def test_definite_failure_keeps_approval_for_retry(self):
        draft_id = self.approved()
        with self.assertRaises(lp.PublishFailed):
            self.post(draft_id, FakePublisher(["failed"]))
        self.assertEqual(self.store().data["attempts"][draft_id]["result"], "failed")
        pub = FakePublisher()
        self.post(draft_id, pub)
        self.assertEqual(len(pub.published), 1)

    def test_attempt_recorded_before_publishing(self):
        draft_id, seen = self.approved(), []

        class Crashing(FakePublisher):
            def publish(inner, account, text):
                seen.append(lp.Store(self.store_path).data["attempts"][draft_id]["result"])
                raise KeyboardInterrupt

        with self.assertRaises(KeyboardInterrupt):
            self.post(draft_id, Crashing())
        self.assertEqual(seen, ["uncertain"])
        with self.assertRaisesRegex(lp.Refused, "reconcile"):
            self.post(draft_id, FakePublisher())


class CommandLineTests(Flow):
    def cli(self, *argv, publisher=None, is_tty=None, ask=None, config=None):
        cfg = pathlib.Path(self.tmp.name, "linkedin.json")
        cfg.write_text(json.dumps(config if config is not None else {"account": ACCOUNT}))
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = lp.main(["--store", str(self.store_path), "--config", str(cfg)] + list(argv), key_source=self.key,
                           publisher=publisher, now=NOW, is_tty=is_tty or (lambda: False), ask=ask)
        return code, out.getvalue(), err.getvalue()

    def test_end_to_end(self):
        text_file = pathlib.Path(self.tmp.name, "post.txt")
        text_file.write_text(TEXT)
        code, out, err = self.cli("draft", "--text-file", str(text_file), "--source", "https://github.com/octo/demo/pull/40")
        self.assertEqual(code, 0, err)
        draft_id = out.split()[1]
        code, out, err = self.cli("approve", draft_id)
        self.assertEqual(code, 1)
        self.assertIn("interactive terminal", err)
        code_word = lp.code_for(lp.text_hash(TEXT))
        code, out, err = self.cli("approve", draft_id, is_tty=lambda: True, ask=lambda p: code_word)
        self.assertEqual(code, 0, err)
        pub = FakePublisher()
        code, out, err = self.cli("post", draft_id, "--dry-run", publisher=pub)
        self.assertIn("nothing was posted", out)
        code, out, err = self.cli("post", draft_id, publisher=pub)
        self.assertEqual(code, 0, err)
        self.assertIn("posted: https://www.linkedin.com/feed/update/1", out)
        self.assertEqual(len(pub.published), 1)

    def test_uncertain_exit_code_and_manual_reconcile(self):
        draft_id = self.approved()
        code, out, err = self.cli("post", draft_id, publisher=FakePublisher(["uncertain"]))
        self.assertEqual(code, 3)
        self.assertIn("reconcile", err)
        code, out, err = self.cli("reconcile", draft_id, "--posted", "https://www.linkedin.com/feed/update/9")
        self.assertEqual(code, 0, err)
        self.assertEqual(self.store().draft(draft_id)["post"]["url"], "https://www.linkedin.com/feed/update/9")

    def test_store_file_is_private(self):
        self.drafted()
        self.assertEqual(self.store_path.stat().st_mode & 0o777, 0o600)


class CommandPublisherTests(unittest.TestCase):
    def publisher(self, script):
        return lp.CommandPublisher(["python3", "-c", script], None, timeout=5)

    def test_contract(self):
        ok = self.publisher("import json,sys; d=json.load(sys.stdin); print(json.dumps({'id':'x','url':'https://example.invalid/'+d['account']}))")
        self.assertEqual(ok.publish("a", "t")["url"], "https://example.invalid/a")
        with self.assertRaises(lp.PublishFailed):
            self.publisher("import sys; sys.stderr.write('bad request'); sys.exit(1)").publish("a", "t")
        with self.assertRaises(lp.Uncertain):
            self.publisher("import sys; sys.exit(75)").publish("a", "t")
        with self.assertRaises(lp.Uncertain):
            self.publisher("print('not json')").publish("a", "t")
        with self.assertRaises(lp.Refused):
            self.publisher("print('{}')").find("a", "t")


if __name__ == "__main__":
    unittest.main()
