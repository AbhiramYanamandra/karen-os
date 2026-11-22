"""Check a local context snapshot without fetching, rewriting, or approving it."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import sys

REQUIRED_IDS = {
    'owner_vision', 'architecture', 'acceptance', 'policy', 'contract',
    'sops', 'project', 'skills', 'templates', 'codex_entry', 'claude_entry',
    'receipt_format', 'context_amendment',
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def local_path(root, value):
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise ValueError('path must be a nonempty repository-relative string')
    path = (root / value).resolve()
    if not path.is_relative_to(root):
        raise ValueError('path escapes repository root')
    return path


def check(root, manifest_path='context/manifest.json', task=None):
    root = Path(root).resolve()
    result = {'ok': False, 'errors': [], 'warnings': [], 'sources': []}
    try:
        manifest = json.loads(local_path(root, manifest_path).read_text())
        if manifest['schema_version'] != 1 or manifest['project_id'] != 'karen-os':
            raise ValueError('unsupported schema or project')
        if not manifest['revision'] or not manifest['reviewed_on']:
            raise ValueError('missing manifest revision or review date')
        sources = manifest['sources']
        if not isinstance(sources, list):
            raise ValueError('sources must be a list')
        ids = [s['id'] for s in sources]
        if len(ids) != len(set(ids)):
            raise ValueError('duplicate source IDs')
        if not REQUIRED_IDS.issubset(ids):
            raise ValueError('missing mandatory source IDs: ' + ', '.join(sorted(REQUIRED_IDS - set(ids))))
        result['manifest_revision'] = manifest['revision']
        result['manifest_sha256'] = digest(local_path(root, manifest_path))
        policy_rules = []
        for source in sources:
            source_id = source['id']
            if not isinstance(source['required'], bool):
                raise ValueError('required must be boolean')
            if source_id in REQUIRED_IDS and not source['required']:
                raise ValueError(source_id + ' cannot be optional')
            if source['startup_read'] not in ('complete', 'on-demand'):
                raise ValueError('invalid startup reading requirement')
            if source_id in {'policy', 'project', 'codex_entry', 'claude_entry', 'receipt_format'} and source['startup_read'] != 'complete':
                raise ValueError('mandatory core cannot be made selective')
            if not source['load_when']:
                raise ValueError('missing reading trigger for ' + source_id)
            path = local_path(root, source['path'])
            if not path.is_file():
                bucket = 'errors' if source['required'] else 'warnings'
                result[bucket].append('missing source: ' + source_id)
                continue
            actual = digest(path)
            if actual != source['sha256']:
                result['errors'].append('stale or changed source: ' + source_id)
            if source.get('kind') == 'policy' or source_id == 'policy':
                match = re.search(r'```json\n(.*?)\n```', path.read_text(), re.S)
                if not match:
                    raise ValueError('policy lacks explicit rule set: ' + source_id)
                policy_rules.append((source_id, json.loads(match.group(1))))
            result['sources'].append({'id': source_id, 'path': source['path'], 'sha256': actual})
        for index, (left_id, left) in enumerate(policy_rules):
            for right_id, right in policy_rules[index + 1:]:
                if any(left[key] != right[key] for key in left.keys() & right.keys()):
                    result['errors'].append('conflicting policy sources: ' + left_id + ' / ' + right_id)
        by_id = {s['id']: s for s in sources}
        architecture_hash = by_id['architecture']['sha256']
        acceptance_path = local_path(root, by_id['acceptance']['path'])
        if acceptance_path.is_file() and architecture_hash not in acceptance_path.read_text():
            result['errors'].append('acceptance does not bind the architecture digest')
        claude = local_path(root, by_id['claude_entry']['path'])
        if claude.is_file() and claude.read_text().strip() != '@AGENTS.md':
            result['errors'].append('Claude entry must import the shared entry only')
        skills_path = local_path(root, by_id['skills']['path'])
        if skills_path.is_file():
            registry = json.loads(skills_path.read_text())
            for entry in registry['entries']:
                if not set(registry['entry_requirements']).issubset(entry):
                    result['errors'].append('incomplete skill metadata')
        if task is not None:
            task_path = local_path(root, task)
            if not task_path.is_file():
                result['errors'].append('missing task context: ' + task)
            else:
                result['task'] = {'path': task, 'sha256': digest(task_path)}
        result['architecture_disposition'] = manifest['architecture_disposition']
    except (OSError, ValueError, KeyError, TypeError) as error:
        result['errors'].append('invalid context: ' + str(error))
    result['ok'] = not result['errors']
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument('--manifest', default='context/manifest.json')
    parser.add_argument('--task', help='optional repository-relative current task file')
    args = parser.parse_args()
    result = check(args.root, args.manifest, args.task)
    print(json.dumps(result, indent=2))
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
