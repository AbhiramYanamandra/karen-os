import json
from pathlib import Path
import unittest
import test_startup
import startup
import test_context


class HandoffValidation(unittest.TestCase):
    save = test_context.ContextFailures.save
    source = test_context.ContextFailures.source

    def setUp(self):
        test_startup.ReceiptCoverage.setUp(self)
        self.profile = dict(handoff_id='unit-handoff', prohibited_actions=['commit', 'push', 'spend', 'deploy', 'other-files'], expected_result='Exploration is read-only.')
        self.packet = dict(handoff_id='unit-handoff', authorised_scope='documentation-export', prohibited_actions=self.profile['prohibited_actions'], next_action=self.profile['expected_result'], claim_released=True)
        for source_id, name, data in [('handoff', 'handoff-packet.json', self.packet), ('handoff_profile', 'handoff-profile.json', self.profile), ('handoff_procedure', 'handoff-procedure.md', 'Use the authorised export only.')]:
            self.add_source(source_id, name, data)
        self.stop = dict(state='exited', exit_code=0, packet_sha256=startup.sha((self.root / 'context/handoff-packet.json').read_bytes()))
        self.add_source('owner_stop', 'owner-stop.json', self.stop)
        self.save()
        payload = startup.read(self.root, self.task)
        self.evidence['outputs'][0]['stdout'] = json.dumps(payload)
        self.receipt['sources'] = [dict(id=r['id'], located=True, read='complete', revision_verified=True) for r in payload['sources']]
        self.wrapper = dict(startup=self.receipt, handoff=dict(handoff_id='unit-handoff', previous_owner_stopped=True, authorised_scope='documentation-export', prohibited_actions=self.profile['prohibited_actions'], result=self.profile['expected_result'], claim_released=True))

    def add_source(self, source_id, name, data):
        path = 'context/' + name
        (self.root / path).write_text(json.dumps(data))
        self.manifest['sources'].append(dict(id=source_id, path=path, required=True, startup_read='complete', load_when='Complete handoff validation', sha256=startup.sha((self.root / path).read_bytes())))

    def assess(self):
        return startup.assess_handoff(self.root, self.task, json.dumps(self.wrapper), self.evidence)

    def test_complete_scoped_export_passes(self):
        self.assertEqual(self.assess()['status'], 'PASS')

    def test_unconfirmed_stop_blocks(self):
        path = self.root / 'context/owner-stop.json'
        self.stop['state'] = 'running'
        path.write_text(json.dumps(self.stop))
        self.source('owner_stop')['sha256'] = startup.sha(path.read_bytes())
        self.save()
        payload = startup.read(self.root, self.task)
        self.evidence['outputs'][0]['stdout'] = json.dumps(payload)
        self.assertEqual(self.assess()['status'], 'BLOCKED')

    def test_handoff_cannot_be_declared_optional_reading(self):
        self.source('handoff')['startup_read'] = 'on-demand'
        self.save()
        payload = startup.read(self.root, self.task)
        self.evidence['outputs'][0]['stdout'] = json.dumps(payload)
        self.wrapper['startup']['sources'] = [dict(id=r['id'], located=True, read='complete', revision_verified=True) for r in payload['sources']]
        self.assertEqual(self.assess()['status'], 'BLOCKED')

    def test_partial_handoff_read_cannot_pass(self):
        payload = json.loads(self.evidence['outputs'][0]['stdout'])
        next(r for r in payload['sources'] if r['id'] == 'handoff')['content'] = 'partial'
        self.evidence['outputs'][0]['stdout'] = json.dumps(payload)
        self.assertEqual(self.assess()['status'], 'PARTIAL')

    def test_out_of_scope_continuation_rejected(self):
        self.wrapper['handoff']['result'] = 'Publish now.'
        self.assertEqual(self.assess()['status'], 'PARTIAL')

    def test_claim_must_be_released(self):
        self.wrapper['handoff']['claim_released'] = False
        self.assertEqual(self.assess()['status'], 'PARTIAL')

    def test_whole_final_receipt_limit_enforced(self):
        self.wrapper['handoff']['result'] = 'word ' * 251
        self.assertEqual(self.assess()['status'], 'PARTIAL')
