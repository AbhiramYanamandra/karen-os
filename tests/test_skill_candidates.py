import copy
import importlib.util
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
COMMIT = re.compile(r'^[0-9a-f]{40}$')
HOME_PATH = re.compile(r'/Users/[A-Za-z0-9._-]+|/home/[a-z_][a-z0-9_-]*/|~/')


def quarantine_errors(entry, data):
    """Any agent may quarantine (it lowers trust); only the owner may lift it."""
    record = entry.get('quarantine')
    if record is None:
        return ['quarantined state without a quarantine record'] if entry['state'] == 'quarantined' else []
    if not isinstance(record, dict):
        return ['quarantine must be an object']
    schema = data['quarantine_schema']
    errors = ['quarantine missing %s' % f for f in schema['required']
              if f not in record or (f != 'observed_sha256' and not record[f])]
    observed = record.get('observed_sha256')
    if observed is not None and not SHA256.match(str(observed)):
        errors.append('quarantine observed_sha256 is not a SHA-256')
    lifted = record.get('lifted')
    if entry['state'] == 'quarantined':
        if lifted:
            errors.append('quarantine is lifted but state is still quarantined')
    elif not isinstance(lifted, dict) or lifted.get('by') != 'owner' or not all(lifted.get(f) for f in schema['lift_required']):
        errors.append('only the owner lifts a quarantine: quarantine.lifted needs by owner, date and reference')
    return errors


def approval_errors(entry, decision, data):
    """Provenance and separate grants on an approve decision."""
    errors = []
    commit = decision.get('source_commit', '')
    if commit is None:
        legacy = str(decision.get('date')) <= data['source_commit_required_after']
        if not decision.get('source_commit_note') or not (legacy or entry['tree_sha256'] is None):
            errors.append('source_commit may be null only with a note, for a remote connector or an approval '
                          'dated on or before %s' % data['source_commit_required_after'])
    elif not COMMIT.match(str(commit)):
        errors.append('source_commit must be a full 40-character commit SHA')
    grants = decision.get('grants')
    if (not isinstance(grants, dict) or set(grants) != set(data['grant_fields'])
            or not all(isinstance(v, list) and all(isinstance(x, str) for x in v) for v in grants.values())):
        errors.append('grants must hold exactly %s, each a list of strings' % ', '.join(data['grant_fields']))
    return errors


def decision_errors(entry, data):
    """Schema check of an entry's owner_decision. Shape only: it cannot prove the owner wrote it."""
    owner_only = set(data['owner_only_states'])
    schema = data['owner_decision_schema']
    decision = entry['owner_decision']
    errors = quarantine_errors(entry, data)
    if entry['state'] not in owner_only:
        # A quarantined entry keeps its earlier decision for the record.
        if decision is None or entry['state'] == 'quarantined':
            return errors
        return errors + ['decision recorded but state is not owner-only']
    if not isinstance(decision, dict):
        return errors + ['owner-only state without an owner_decision']
    kind = decision.get('decision')
    if kind not in schema:
        return errors + ['unknown decision %r' % kind]
    if schema[kind]['sets_state'] != entry['state']:
        errors.append('decision %r does not set state %r' % (kind, entry['state']))
    required = schema[kind]['required']
    if kind == 'approve' and entry['tree_sha256'] is None:
        # A remote connector has no local content to pin; its approval binds to scope only.
        required = [f for f in required if f != 'approved_sha256']
    errors += ['missing %s' % f for f in required if not decision.get(f)]
    if kind == 'approve' and decision.get('approved_sha256') != entry['tree_sha256']:
        errors.append('approved_sha256 does not match tree_sha256')
    if kind == 'revoke' and not SHA256.match(str(decision.get('revoked_sha256', ''))):
        errors.append('revoked_sha256 is not a SHA-256')
    if kind == 'approve':
        errors += approval_errors(entry, decision, data)
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

    def test_only_the_owner_decided_entries_carry_decisions(self):
        # #51: owner decisions of 2026-11-24. Every other entry stays a proposal.
        decided = {e['id']: e['state'] for e in self.entries if e['owner_decision'] is not None}
        self.assertEqual(decided, {
            'unslop': 'approved', 'tdd': 'approved', 'diagnosing-bugs': 'approved',
            'principle-prove-it-works': 'approved', 'thermo-nuclear-code-quality-review': 'approved',
            'code-review': 'approved', 'ecc:security-review': 'approved',
            'ui-ux-pro-max@shared-agents-skills': 'approved', 'ui-ux-pro-max@claude-user-skills': 'rejected',
            'ponytail-plugin': 'approved', 'figma': 'approved',
        })

    def test_inspected_packages_carry_full_hashes(self):
        for entry in self.entries:
            with self.subTest(entry=entry['id']):
                if entry['state'] == 'discovered' or entry['location'] == 'remote-connector':
                    continue
                self.assertRegex(entry['skill_md_sha256'], SHA256)
                self.assertRegex(entry['tree_sha256'], SHA256)

    def test_ui_ux_pro_max_resolves_to_one_approved_copy(self):
        variants = {e['id']: e for e in self.entries if e['id'].startswith('ui-ux-pro-max')}
        self.assertEqual(variants['ui-ux-pro-max@shared-agents-skills']['state'], 'approved')
        self.assertEqual(variants['ui-ux-pro-max@claude-user-skills']['state'], 'rejected')
        self.assertEqual([e for e in variants.values() if e['state'] == 'approved'],
                         [variants['ui-ux-pro-max@shared-agents-skills']])

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

    def test_registry_entries_match_their_owner_decisions(self):
        registry = json.loads(REGISTRY.read_text(encoding='utf-8'))
        decided = {e['id']: e for e in self.entries if e['state'] == 'approved'}
        for entry in registry['entries']:
            with self.subTest(entry=entry['id']):
                self.assertEqual(set(registry['entry_requirements']) - entry.keys(), set())
                self.assertEqual(entry['approval_status'], 'approved')
                decision = decided[entry['id']]['owner_decision']
                self.assertEqual(entry['sha256'], decision.get('approved_sha256'))
                self.assertEqual(entry['approval_reference'], decision['reference'])

    def test_registry_lists_only_approved_candidates(self):
        # Quarantined and revoked entries are not approved, so they must leave the registry.
        approved = {e['id'] for e in self.entries if e['state'] == 'approved'}
        registry = json.loads(REGISTRY.read_text(encoding='utf-8'))
        self.assertEqual({e.get('id') for e in registry['entries']} - approved, set())

    def test_registry_entries_have_an_activate_grant(self):
        decided = {e['id']: e['owner_decision'] for e in self.entries if e['state'] == 'approved'}
        for entry in json.loads(REGISTRY.read_text(encoding='utf-8'))['entries']:
            with self.subTest(entry=entry['id']):
                self.assertTrue(decided[entry['id']]['grants']['activate'])

    def test_one_approved_entry_per_skill_name(self):
        # A lookalike or second copy under the same name cannot be approved alongside the first.
        names = [e['id'].split('@')[0] for e in self.entries if e['state'] == 'approved']
        self.assertEqual(len(names), len(set(names)))


class OwnerDecisionSchema(unittest.TestCase):
    """Synthetic decisions: approve binds to a hash, revoke withdraws a cited approval."""

    def setUp(self):
        self.data = json.loads(CANDIDATES.read_text(encoding='utf-8'))
        self.entry = copy.deepcopy(next(e for e in self.data['candidates'] if e['id'] == 'tdd'))
        self.hash = self.entry['tree_sha256']
        self.approve = dict(decision='approve', by='owner', date='2026-12-01',
                            reference='https://example.invalid/approval', approved_sha256=self.hash,
                            scope='bugs-and-tests', source_commit='a' * 40,
                            grants=dict(install=['codex'], activate=['bugs-and-tests'], permissions=[], external_access=[]))
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

    def test_unpinned_approval_only_for_unpinnable_content(self):
        unpinned = {k: v for k, v in self.approve.items() if k != 'approved_sha256'}
        self.assertIn('missing approved_sha256', self.errors('approved', unpinned))
        self.entry['tree_sha256'] = None
        self.assertEqual(self.errors('approved', unpinned), [])

    def test_decision_on_a_non_owner_state_fails(self):
        self.assertTrue(self.errors('under-review', self.approve))

    def test_approval_needs_every_grant_field(self):
        no_grants = {k: v for k, v in self.approve.items() if k != 'grants'}
        self.assertIn('missing grants', self.errors('approved', no_grants))
        partial = dict(self.approve, grants=dict(install=['codex'], activate=['x']))
        self.assertTrue(any(e.startswith('grants must hold') for e in self.errors('approved', partial)))

    def test_approval_needs_a_commit_pinned_source(self):
        for ref in ('main', 'v1.2.0', 'a' * 12):
            with self.subTest(ref=ref):
                self.assertIn('source_commit must be a full 40-character commit SHA',
                              self.errors('approved', dict(self.approve, source_commit=ref)))
        unpinned = dict(self.approve, source_commit=None, source_commit_note='no commit recorded')
        self.assertTrue(self.errors('approved', unpinned))  # dated after the cutoff
        self.assertEqual(self.errors('approved', dict(unpinned, date='2026-11-24')), [])
        self.assertTrue(self.errors('approved', dict(unpinned, date='2026-11-24', source_commit_note='')))


class Quarantine(unittest.TestCase):
    """Any agent may quarantine; only the owner may lift; a quarantined skill counts as missing."""

    def setUp(self):
        self.data = json.loads(CANDIDATES.read_text(encoding='utf-8'))
        self.entry = copy.deepcopy(next(e for e in self.data['candidates'] if e['id'] == 'code-review'))
        self.record = dict(by='Claude Code', date='2026-12-02', reason='hash at load differs from approval',
                           observed_sha256='b' * 64, evidence='scripts/skill_review.py output')

    def errors(self, state, record):
        self.entry.update(state=state, quarantine=record)
        return decision_errors(self.entry, self.data)

    def test_agent_may_quarantine_an_approved_skill(self):
        self.assertEqual(self.errors('quarantined', self.record), [])

    def test_quarantine_needs_its_record(self):
        self.assertIn('quarantined state without a quarantine record', self.errors('quarantined', None))
        self.assertIn('quarantine missing evidence', self.errors('quarantined', dict(self.record, evidence='')))

    def test_only_the_owner_lifts_it(self):
        lift = dict(by='owner', date='2026-12-03', reference='https://example.invalid/lift')
        self.entry['owner_decision'] = None
        self.assertEqual(self.errors('under-review', dict(self.record, lifted=lift)), [])
        agent_lift = dict(self.record, lifted=dict(lift, by='Claude Code'))
        self.assertTrue(any(e.startswith('only the owner lifts') for e in self.errors('under-review', agent_lift)))
        self.assertTrue(any(e.startswith('only the owner lifts') for e in self.errors('under-review', self.record)))

    def test_hash_drift_is_detected(self):
        # A changed package no longer matches its approval, which is the quarantine trigger.
        drifted = dict(self.entry, tree_sha256='c' * 64)
        self.assertIn('approved_sha256 does not match tree_sha256', decision_errors(drifted, self.data))

    def test_quarantined_skill_leaves_the_registry_and_its_stage_holds(self):
        spec = importlib.util.spec_from_file_location('profiles', ROOT / 'scripts/profiles.py')
        profiles = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(profiles)
        registry = json.loads(REGISTRY.read_text(encoding='utf-8'))
        remaining = {'entries': [e for e in registry['entries'] if e['id'] != 'code-review']}
        data = json.loads(profiles.PROFILES.read_text(encoding='utf-8'))
        result = profiles.resolve(data, 'feat', 'medium', registry=profiles.registered(remaining))
        self.assertIn('code-review', result['stages']['review']['holds'])


if __name__ == '__main__':
    unittest.main()
