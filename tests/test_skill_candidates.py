import copy
import hashlib
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / 'docs/organisation/skill-candidates.json'
REGISTRY = ROOT / 'docs/organisation/skills.json'

REQUIRED = {
    'id', 'source', 'location', 'version', 'skill_md_sha256', 'tree_sha256', 'upstream_match',
    'licence', 'dependencies', 'tools', 'privileges', 'compatibility', 'duplicates', 'stage',
    'state', 'recommendation', 'rationale', 'owner_decision',
}
SHA256 = re.compile(r'^[0-9a-f]{64}$')
HOME_PATH = re.compile(r'/Users/[A-Za-z0-9._-]+|/home/[a-z_][a-z0-9_-]*/|~/')


def decision_errors(entry, data):
    """Schema check of an entry's owner_decision. Shape only: it cannot prove the owner wrote it."""
    owner_only = set(data['owner_only_states'])
    schema = data['owner_decision_schema']
    decision = entry['owner_decision']
    if entry['state'] not in owner_only:
        return [] if decision is None else ['decision recorded but state is not owner-only']
    if not isinstance(decision, dict):
        return ['owner-only state without an owner_decision']
    kind = decision.get('decision')
    if kind not in schema:
        return ['unknown decision %r' % kind]
    errors = []
    if schema[kind]['sets_state'] != entry['state']:
        errors.append('decision %r does not set state %r' % (kind, entry['state']))
    errors += ['missing %s' % f for f in schema[kind]['required'] if not decision.get(f)]
    if kind == 'approve' and decision.get('approved_sha256') != entry['tree_sha256']:
        errors.append('approved_sha256 does not match tree_sha256')
    if kind == 'revoke' and not SHA256.match(str(decision.get('revoked_sha256', ''))):
        errors.append('revoked_sha256 is not a SHA-256')
    return errors


class SkillCandidates(unittest.TestCase):
    """The candidate inventory stays a proposal until the owner decides an entry."""

    def setUp(self):
        self.text = CANDIDATES.read_text(encoding='utf-8')
        self.data = json.loads(self.text)
        self.entries = self.data['candidates']

    def test_every_entry_has_the_inventory_fields(self):
        for entry in self.entries:
            with self.subTest(entry=entry.get('id')):
                self.assertEqual(REQUIRED - entry.keys(), set())

    def test_ids_are_unique(self):
        ids = [entry['id'] for entry in self.entries]
        self.assertEqual(len(ids), len(set(ids)))

    def test_states_and_recommendations_are_known(self):
        for entry in self.entries:
            with self.subTest(entry=entry['id']):
                self.assertIn(entry['state'], self.data['states'])
                self.assertIn(entry['recommendation'], self.data['recommendations'])

    def test_recorded_decisions_match_the_schema(self):
        for entry in self.entries:
            with self.subTest(entry=entry['id']):
                self.assertEqual(decision_errors(entry, self.data), [])

    def test_only_the_ponytail_install_is_owner_decided(self):
        # #51: the owner approved the Ponytail v5.3.3 install on 2026-11-24. Every other entry stays a proposal.
        self.assertEqual([e['id'] for e in self.entries if e['owner_decision'] is not None], ['ponytail-plugin'])

    def test_inspected_packages_carry_full_hashes(self):
        for entry in self.entries:
            with self.subTest(entry=entry['id']):
                if entry['state'] == 'discovered':
                    continue
                self.assertRegex(entry['skill_md_sha256'], SHA256)
                self.assertRegex(entry['tree_sha256'], SHA256)

    def test_ui_ux_pro_max_variants_stay_unresolved(self):
        variants = [e for e in self.entries if e['id'].startswith('ui-ux-pro-max')]
        self.assertEqual(len(variants), 2)
        self.assertNotEqual(variants[0]['tree_sha256'], variants[1]['tree_sha256'])
        for entry in variants:
            self.assertEqual((entry['state'], entry['recommendation']), ('under-review', 'hold'))

    def test_pinned_files_reproduce_the_tree_hash(self):
        for entry in self.entries:
            files = entry.get('pinned_files')
            if not files:
                continue
            with self.subTest(entry=entry['id']):
                lines = ''.join('%s\0%s\n' % (path, files[path]) for path in sorted(files))
                self.assertEqual(hashlib.sha256(lines.encode('utf-8')).hexdigest(), entry['tree_sha256'])
                self.assertIn(entry['skill_md_sha256'], files.values())

    def test_no_private_paths(self):
        self.assertIsNone(HOME_PATH.search(self.text))

    def test_registry_lists_only_approved_candidates(self):
        approved = {e['id'] for e in self.entries if e['state'] == 'approved'}
        registry = json.loads(REGISTRY.read_text(encoding='utf-8'))
        self.assertEqual({e.get('id') for e in registry['entries']} - approved, set())


class OwnerDecisionSchema(unittest.TestCase):
    """Synthetic decisions: approve binds to a hash, revoke withdraws a cited approval."""

    def setUp(self):
        self.data = json.loads(CANDIDATES.read_text(encoding='utf-8'))
        self.entry = copy.deepcopy(next(e for e in self.data['candidates'] if e['id'] == 'tdd'))
        self.hash = self.entry['tree_sha256']
        self.approve = dict(decision='approve', by='owner', date='2026-12-01',
                            reference='https://example.invalid/approval', approved_sha256=self.hash,
                            scope='bugs-and-tests')
        self.revoke = dict(decision='revoke', by='owner', date='2026-12-05',
                           reference='https://example.invalid/revocation', reason='unsafe output',
                           revokes='https://example.invalid/approval', revoked_sha256=self.hash)

    def errors(self, state, decision):
        self.entry.update(state=state, owner_decision=decision)
        return decision_errors(self.entry, self.data)

    def test_valid_approve_and_revoke_pass(self):
        self.assertEqual(self.errors('approved', self.approve), [])
        self.assertEqual(self.errors('revoked', self.revoke), [])

    def test_approved_state_without_decision_fails(self):
        self.assertIn('owner-only state without an owner_decision', self.errors('approved', None))

    def test_rejected_state_is_owner_only_too(self):
        self.assertTrue(self.errors('rejected', None))

    def test_approval_of_different_content_fails(self):
        self.assertIn('approved_sha256 does not match tree_sha256',
                      self.errors('approved', dict(self.approve, approved_sha256='0' * 64)))

    def test_revoke_must_cite_the_approval_it_withdraws(self):
        bad = {k: v for k, v in self.revoke.items() if k != 'revokes'}
        self.assertIn('missing revokes', self.errors('revoked', bad))

    def test_decision_kind_must_match_state(self):
        self.assertIn("decision 'approve' does not set state 'revoked'", self.errors('revoked', self.approve))

    def test_decision_on_a_non_owner_state_fails(self):
        self.assertTrue(self.errors('under-review', self.approve))


if __name__ == '__main__':
    unittest.main()
