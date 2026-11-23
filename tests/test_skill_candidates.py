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
    'state', 'recommendation', 'rationale', 'owner_approval',
}
OWNER_ONLY_STATES = {'approved', 'revoked'}
SHA256 = re.compile(r'^[0-9a-f]{64}$')
HOME_PATH = re.compile(r'/Users/[A-Za-z0-9._-]+|/home/[a-z_][a-z0-9_-]*/|~/')


class SkillCandidates(unittest.TestCase):
    """The candidate inventory stays a proposal until the owner approves an entry."""

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

    def test_owner_only_states_need_an_owner_approval_record(self):
        for entry in self.entries:
            with self.subTest(entry=entry['id']):
                if entry['state'] in OWNER_ONLY_STATES:
                    approval = entry['owner_approval']
                    self.assertIsInstance(approval, dict)
                    for field in ('by', 'date', 'reference', 'approved_sha256'):
                        self.assertTrue(approval.get(field), field)
                    self.assertEqual(approval['approved_sha256'], entry['tree_sha256'])

    def test_inspected_packages_carry_full_hashes(self):
        for entry in self.entries:
            with self.subTest(entry=entry['id']):
                if entry['state'] == 'discovered':
                    continue
                self.assertRegex(entry['skill_md_sha256'], SHA256)
                self.assertRegex(entry['tree_sha256'], SHA256)

    def test_no_private_paths(self):
        self.assertIsNone(HOME_PATH.search(self.text))

    def test_registry_lists_only_approved_candidates(self):
        approved = {e['id'] for e in self.entries if e['state'] == 'approved'}
        registry = json.loads(REGISTRY.read_text(encoding='utf-8'))
        self.assertEqual({e.get('id') for e in registry['entries']} - approved, set())


if __name__ == '__main__':
    unittest.main()
