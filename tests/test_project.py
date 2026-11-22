import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import startup
import test_context


class ExternalProject(unittest.TestCase):
    """A synthetic project outside the KAREN OS checkout loads the shared core."""
    save = test_context.ContextFailures.save

    def setUp(self):
        test_context.ContextFailures.setUp(self)
        workspace = tempfile.TemporaryDirectory()
        self.addCleanup(workspace.cleanup)
        self.project = Path(workspace.name) / 'synthetic-app'
        (self.project / '.karen').mkdir(parents=True)
        (self.project / 'plans').mkdir()
        (self.project / 'AGENTS.md').write_text('Local rule: always mention the sentinel PLUM.\n')
        (self.project / 'plans/001-first.md').write_text('Private plan body.\n')
        (self.project / 'plans/notes.txt').write_text('Not a plan.\n')
        decoy = Path(workspace.name) / 'sibling-app'
        decoy.mkdir()
        (decoy / 'AGENTS.md').write_text('DECOY sibling instructions.\n')
        self.record = dict(schema_version=1, project_id='synthetic-app', integration_level=2,
                           karen_manifest_revision=self.manifest['revision'],
                           project_instructions='AGENTS.md', task_location='plans',
                           karen_os_path='~/karen-os')
        self.write_record()

    def write_record(self, record=None):
        (self.project / '.karen/project.json').write_text(json.dumps(record or self.record))

    def load(self):
        return startup.read_project(self.root, self.project)

    def test_shared_core_and_project_context_load(self):
        result = self.load()
        self.assertEqual(result['project_status'], 'ok')
        self.assertEqual(result['project'], 'synthetic-app')
        self.assertEqual(result['context_errors'], [])
        ids = {r['id'] for r in result['sources']}
        self.assertTrue({'manifest', 'policy', 'codex_entry', 'project_record', 'project_instructions'}.issubset(ids))
        local = next(r for r in result['sources'] if r['id'] == 'project_instructions')
        self.assertIn('PLUM', local['content'])

    def test_karen_os_own_project_instructions_excluded(self):
        ids = {r['id'] for r in self.load()['sources']}
        self.assertNotIn('project', ids)
        self.assertNotIn('claude_entry', ids)

    def test_only_declared_files_are_read(self):
        result = self.load()
        text = json.dumps(result)
        self.assertNotIn('DECOY', text)
        self.assertNotIn('Private plan body', text)
        self.assertEqual(result['tasks'], ['001-first.md'])

    def test_stale_pin_reported(self):
        self.record['karen_manifest_revision'] = 'older-revision'
        self.write_record()
        result = self.load()
        self.assertEqual(result['project_status'], 'stale')
        self.assertTrue(any('older-revision' in w for w in result['project_warnings']))

    def test_missing_record_reported(self):
        (self.project / '.karen/project.json').unlink()
        result = self.load()
        self.assertEqual(result['project_status'], 'invalid')
        self.assertIn('missing project record: .karen/project.json', result['project_errors'])

    def test_malformed_record_reported(self):
        (self.project / '.karen/project.json').write_text('{not json')
        result = self.load()
        self.assertEqual(result['project_status'], 'invalid')
        self.assertTrue(result['project_errors'][0].startswith('malformed project record'))

    def test_invalid_fields_reported(self):
        self.record['integration_level'] = 9
        del self.record['project_id']
        self.write_record()
        errors = self.load()['project_errors']
        self.assertTrue(any('integration_level' in e for e in errors))
        self.assertTrue(any('project_id' in e for e in errors))

    def test_pipeline_reported(self):
        self.record['pipeline'] = dict(tracker='github', repository='owner/synthetic-app', default_branch='main')
        self.record['karen_os_repository'] = 'owner/karen-os'
        self.write_record()
        result = self.load()
        self.assertEqual(result['project_status'], 'ok')
        self.assertEqual(result['pipeline']['repository'], 'owner/synthetic-app')
        self.assertEqual(result['karen_os_repository'], 'owner/karen-os')

    def test_pipeline_absent_is_none(self):
        result = self.load()
        self.assertEqual(result['project_status'], 'ok')
        self.assertIsNone(result['pipeline'])

    def test_invalid_pipeline_reported(self):
        bad = [
            ('not an object', 'pipeline must be an object'),
            (dict(tracker='gitlab', repository='o/n', default_branch='main'), 'tracker'),
            (dict(tracker='github', repository='https://github.com/o/n', default_branch='main'), 'repository'),
            (dict(tracker='github', repository='o/..', default_branch='main'), 'repository'),
            (dict(tracker='github', repository='o/n', default_branch='my branch'), 'default_branch'),
            (dict(tracker='github', repository='o/n', default_branch='--force'), 'default_branch'),
        ]
        for pipeline, expected in bad:
            with self.subTest(pipeline=pipeline):
                self.record['pipeline'] = pipeline
                self.write_record()
                result = self.load()
                self.assertEqual(result['project_status'], 'invalid')
                self.assertTrue(any(expected in e for e in result['project_errors']), result['project_errors'])

    def test_invalid_karen_os_repository_reported(self):
        self.record['karen_os_repository'] = 'karen-os'
        self.write_record()
        result = self.load()
        self.assertEqual(result['project_status'], 'invalid')
        self.assertTrue(any('karen_os_repository' in e for e in result['project_errors']))

    def test_instructions_path_cannot_escape_project(self):
        self.record['project_instructions'] = '../sibling-app/AGENTS.md'
        self.write_record()
        result = self.load()
        self.assertEqual(result['project_status'], 'invalid')
        self.assertNotIn('DECOY', json.dumps(result))

    def test_symlink_cannot_escape_project(self):
        link = self.project / 'LINKED.md'
        link.symlink_to(self.project.parent / 'sibling-app/AGENTS.md')
        self.record['project_instructions'] = 'LINKED.md'
        self.write_record()
        result = self.load()
        self.assertEqual(result['project_status'], 'invalid')
        self.assertNotIn('DECOY', json.dumps(result))

    def test_missing_instructions_reported(self):
        (self.project / 'AGENTS.md').unlink()
        result = self.load()
        self.assertEqual(result['project_status'], 'invalid')
        self.assertIn('missing project instructions: AGENTS.md', result['project_errors'])

    def test_missing_project_directory_reported(self):
        result = startup.read_project(self.root, self.project.parent / 'does-not-exist')
        self.assertEqual(result['project_status'], 'invalid')

    def test_reader_writes_nothing(self):
        before = sorted(str(p) for p in self.project.rglob('*'))
        self.load()
        self.assertEqual(sorted(str(p) for p in self.project.rglob('*')), before)

    def test_command_line(self):
        script = str(Path(startup.__file__))
        p = subprocess.run([sys.executable, '-B', script, 'read', '--root', str(self.root), '--project', str(self.project)],
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout)['project_status'], 'ok')
        p = subprocess.run([sys.executable, '-B', script, 'assess', '--project', str(self.project)], capture_output=True, text=True)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('explicit task', p.stderr)


if __name__ == '__main__':
    unittest.main()
