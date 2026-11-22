import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'scripts'))
from prepare_startup_fixtures import prepare

SPEC = importlib.util.spec_from_file_location('check_context', REPO / 'scripts/check_context.py')
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


class ContextFailures(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manifest = json.loads((REPO / 'context/manifest.json').read_text())
        for source in self.manifest['sources']:
            target = self.root / source['path']
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO / source['path'], target)
        (self.root / 'context').mkdir(exist_ok=True)
        self.save()

    def save(self):
        (self.root / 'context/manifest.json').write_text(json.dumps(self.manifest))

    def source(self, source_id):
        return next(s for s in self.manifest['sources'] if s['id'] == source_id)

    def test_fixture_generation_preserves_canonical_policy(self):
        task = self.root / 'docs/tasks/startup-validation.md'
        task.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / 'docs/tasks/startup-validation.md', task)
        policy = self.root / self.source('policy')['path']
        original = policy.read_bytes()
        destination = self.root / 'isolated-fixtures'
        prepare(self.root, destination)
        self.assertEqual(policy.read_bytes(), original)
        self.assertTrue(checker.check(destination / 'clean')['ok'])
        self.assertFalse(checker.check(destination / 'missing')['ok'])
        conflict = checker.check(destination / 'conflict')
        self.assertFalse(conflict['ok'])
        self.assertTrue(any('conflicting policy' in e for e in conflict['errors']))

    def test_fixture_copy_rejects_repository_escape(self):
        self.manifest['sources'].append(dict(path='../blocked-input.txt'))
        self.save()
        with self.assertRaises(ValueError):
            prepare(self.root, self.root / 'isolated-fixtures')

    def test_current_snapshot(self):
        self.assertTrue(checker.check(self.root)['ok'])

    def test_missing_policy_blocks(self):
        (self.root / self.source('policy')['path']).unlink()
        result = checker.check(self.root)
        self.assertFalse(result['ok'])
        self.assertIn('missing source: policy', result['errors'])

    def test_policy_drift_blocks(self):
        (self.root / self.source('policy')['path']).write_text('different policy')
        result = checker.check(self.root)
        self.assertFalse(result['ok'])
        self.assertIn('stale or changed source: policy', result['errors'])

    def test_repinning_architecture_does_not_reapprove(self):
        source = self.source('architecture')
        path = self.root / source['path']
        path.write_text(path.read_text() + '\nChanged design\n')
        source['sha256'] = checker.digest(path)
        self.save()
        result = checker.check(self.root)
        self.assertFalse(result['ok'])
        self.assertIn('acceptance does not bind the architecture digest', result['errors'])

    def test_missing_project_not_assumed(self):
        result = checker.check(self.root, task='docs/tasks/nonexistent.md')
        self.assertFalse(result['ok'])
        self.assertIn('missing task context: docs/tasks/nonexistent.md', result['errors'])

    def test_path_escape_rejected(self):
        self.source('policy')['path'] = '../outside-policy.md'
        self.save()
        self.assertFalse(checker.check(self.root)['ok'])

    def test_missing_source_cannot_be_hidden(self):
        self.manifest['sources'] = [s for s in self.manifest['sources'] if s['id'] != 'policy']
        self.save()
        self.assertFalse(checker.check(self.root)['ok'])

    def test_mandatory_policy_cannot_be_optional(self):
        self.source('policy')['required'] = False
        self.save()
        self.assertFalse(checker.check(self.root)['ok'])

    def test_malformed_manifest_blocks(self):
        (self.root / 'context/manifest.json').write_text('{')
        self.assertFalse(checker.check(self.root)['ok'])

    def test_conflicting_claude_copy_detected_even_if_repinned(self):
        source = self.source('claude_entry')
        path = self.root / source['path']
        path.write_text('Independent conflicting policy\n')
        source['sha256'] = checker.digest(path)
        self.save()
        self.assertFalse(checker.check(self.root)['ok'])


if __name__ == '__main__':
    unittest.main()
