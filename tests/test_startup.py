import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import startup
import test_context
from collect_startup_evidence import collect


class ReceiptCoverage(unittest.TestCase):
    save = test_context.ContextFailures.save
    source = test_context.ContextFailures.source

    def setUp(self):
        test_context.ContextFailures.setUp(self)
        target = self.root / 'docs/tasks/startup-validation.md'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('A bounded read-only task.\n')
        self.task = 'docs/tasks/startup-validation.md'
        self.manifest['task_revisions'] = {self.task: startup.sha(target.read_bytes())}
        self.save()
        payload = startup.read(self.root, self.task)
        self.evidence = {'outputs': [{'argv': ['python3', '-B', 'scripts/startup.py', 'read', '--task', self.task], 'stdout': json.dumps(payload), 'exit_code': 0}]}
        self.receipt = dict(project='karen-os', task='startup-validation', manifest_revision=self.manifest['revision'], status='PASS',
            architecture_sha256=self.source('architecture')['sha256'],
            sources=[dict(id=r['id'], located=True, read='complete', revision_verified=True) for r in payload['sources']],
            policy_checks=startup.POLICY_ANSWERS.copy(), capabilities=dict(read='verified', hash='verified', write='unverified', network='unverified'), gaps=[], summary='Complete bounded startup.')

    def assess(self, receipt=None, evidence=None):
        return startup.assess(self.root, self.task, json.dumps(receipt or self.receipt), evidence if evidence is not None else self.evidence)

    def test_exploration_needs_no_task_or_receipt_template(self):
        payload = startup.read(self.root)
        ids = {r['id'] for r in payload['sources']}
        self.assertNotIn('task', ids)
        self.assertNotIn('receipt_format', ids)
        self.assertTrue({'manifest', 'policy', 'project', 'codex_entry', 'claude_entry'}.issubset(ids))
        self.assertFalse((self.root / 'docs/tasks/exploration.md').exists())

    def test_explicit_task_still_required_for_validation(self):
        import subprocess
        p = subprocess.run([sys.executable, '-B', str(Path(startup.__file__)), 'assess', '--explore'], capture_output=True, text=True)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('explicit task', p.stderr)

    def test_required_on_demand_source_is_not_in_startup_payload(self):
        detail = self.root / 'context/on-demand-detail.md'
        detail.write_text('Detail retrieved only when its trigger applies.\n')
        self.manifest['sources'].append(dict(
            id='fixture_detail', path='context/on-demand-detail.md', required=True,
            startup_read='on-demand', load_when='Fixture detail is needed',
            sha256=startup.sha(detail.read_bytes())))
        self.save()
        for task in (None, self.task):
            with self.subTest(task=task):
                payload = startup.read(self.root, task)
                self.assertEqual(payload['context_errors'], [])
                self.assertNotIn('fixture_detail', {r['id'] for r in payload['sources']})
                self.assertNotIn(detail.read_text(), json.dumps(payload))

    def test_complete_tool_delivered_context_passes(self):
        self.assertEqual(self.assess()['status'], 'PASS')

    def test_self_report_without_tool_evidence_never_passes(self):
        self.assertEqual(self.assess(evidence={'outputs': []})['status'], 'PARTIAL')

    def test_partial_actual_read_cannot_pass(self):
        payload = json.loads(self.evidence['outputs'][0]['stdout'])
        row = next(r for r in payload['sources'] if r['id'] == 'policy')
        row['content'] = row['content'][:100]
        self.evidence['outputs'][0]['stdout'] = json.dumps(payload)
        self.assertEqual(self.assess()['status'], 'PARTIAL')

    def test_false_revision_claim_rejected(self):
        self.receipt['sources'][0]['revision_verified'] = False
        self.assertEqual(self.assess()['status'], 'PARTIAL')

    def test_long_receipt_rejected_even_if_minified(self):
        self.receipt['summary'] = 'word ' * 251
        self.assertEqual(self.assess()['status'], 'PARTIAL')

    def test_missing_required_field_rejected(self):
        del self.receipt['capabilities']
        self.assertEqual(self.assess()['status'], 'PARTIAL')

    def test_incorrect_comprehension_rejected(self):
        self.receipt['policy_checks']['push'] = 'allowed'
        self.assertEqual(self.assess()['status'], 'PARTIAL')

    def test_unobserved_write_capability_rejected(self):
        self.receipt['capabilities']['write'] = 'verified'
        self.assertEqual(self.assess()['status'], 'PARTIAL')

    def test_duplicate_source_rows_rejected(self):
        self.receipt['sources'][0] = self.receipt['sources'][1].copy()
        self.assertEqual(self.assess()['status'], 'PARTIAL')

    def test_arbitrary_echo_is_not_read_evidence(self):
        self.evidence['outputs'][0]['argv'] = ['echo', 'fake']
        self.assertEqual(self.assess()['status'], 'PARTIAL')

    def test_failed_reader_is_not_evidence(self):
        self.evidence['outputs'][0]['exit_code'] = 1
        self.assertEqual(self.assess()['status'], 'PARTIAL')

    def test_missing_policy_blocks_false_pass(self):
        (self.root / self.source('policy')['path']).unlink()
        self.assertEqual(self.assess()['status'], 'BLOCKED')

    def test_conflict_blocks_even_with_individually_valid_hashes(self):
        original = self.root / self.source('policy')['path']
        conflict = self.root / 'context/conflicting-policy.md'
        conflict.write_text(original.read_text().replace('"publication_requires_approval":true', '"publication_requires_approval":false'))
        import hashlib
        self.manifest['sources'].append(dict(id='fixture_policy', path='context/conflicting-policy.md', kind='policy', required=True, startup_read='complete', load_when='Fixture policy claim', sha256=hashlib.sha256(conflict.read_bytes()).hexdigest()))
        self.save()
        self.assertEqual(self.assess()['status'], 'BLOCKED')

    def test_reported_partial_stays_partial(self):
        self.receipt['status'] = 'PARTIAL'
        self.assertEqual(self.assess()['status'], 'PARTIAL')

    def test_unknown_coverage_field_is_rejected(self):
        self.receipt['sources'][0]['revision_basis'] = 'snapshot digest'
        self.assertEqual(self.assess()['status'], 'PARTIAL')

    def test_unpinned_task_is_truthful_partial(self):
        self.manifest.pop('task_revisions')
        self.save()
        payload = startup.read(self.root, self.task)
        self.evidence['outputs'][0]['stdout'] = json.dumps(payload)
        self.receipt['sources'] = [dict(id=r['id'], located=r['located'], read='complete', revision_verified=r['revision_verified']) for r in payload['sources']]
        self.receipt['status'] = 'PARTIAL'
        self.receipt['gaps'] = ['Task revision has no reference pin.']
        result = self.assess()
        self.assertEqual(result['status'], 'PARTIAL')
        self.assertTrue(result['receipt_valid'])

    def test_native_structured_receipt_extracted_without_repair(self):
        payload = {'status': 'PARTIAL', 'summary': 'Observed result'}
        trace = json.dumps(dict(type='result', result='presentation text', structured_output=payload))
        evidence, receipt = collect('claude', trace)
        self.assertEqual(json.loads(receipt), payload)
        self.assertEqual(evidence['outputs'], [])

    def test_actual_tool_stdout_is_retained_verbatim(self):
        command = 'python3 -B scripts/startup.py read --task docs/tasks/startup-validation.md'
        stdout = '{"protocol":"karen-startup-read/v1","sources":[]}'
        events = [dict(type='assistant', message=dict(content=[dict(type='tool_use', id='read-1', name='Bash', input={'command': command})])), dict(type='user', message=dict(content=[dict(type='tool_result', tool_use_id='read-1', content=stdout)]))]
        evidence, receipt = collect('claude', '\n'.join(json.dumps(e) for e in events))
        self.assertEqual(evidence['outputs'][0]['stdout'], stdout)
        self.assertEqual(receipt, '')

    def test_json_fences_are_not_a_valid_receipt(self):
        result = startup.assess(self.root, self.task, '```json\n' + json.dumps(self.receipt) + '\n```', self.evidence)
        self.assertEqual(result['status'], 'PARTIAL')
