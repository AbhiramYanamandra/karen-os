"""Copy reviewed local sources into three isolated, read-only-probe fixtures."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

from check_context import local_path


def prepare(repo, destination):
    repo = Path(repo).resolve()
    destination = Path(destination).resolve()
    if destination.exists():
        raise ValueError('use a new empty destination; fixtures are never overwritten')
    destination.mkdir(parents=True)
    manifest = json.loads((repo / 'context/manifest.json').read_text())
    files = {s['path'] for s in manifest['sources']}
    files.update(['context/manifest.json', 'docs/tasks/startup-validation.md',
                  'scripts/startup.py', 'scripts/check_context.py'])
    index = {}
    for case in ('clean', 'missing', 'conflict'):
        root = destination / case
        for relative in sorted(files):
            source = local_path(repo, relative)
            target = local_path(root.resolve(), relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        if case == 'missing':
            (root / 'docs/organisation/policy.md').unlink()
        if case == 'conflict':
            policy = (root / 'docs/organisation/policy.md').read_text()
            conflict = root / 'context/conflicting-policy.md'
            conflict.write_text('# Isolated conflicting policy claim\n\n' + policy.replace('"publication_requires_approval":true', '"publication_requires_approval":false'))
            m = json.loads((root / 'context/manifest.json').read_text())
            m['sources'].append(dict(id='fixture_policy', path='context/conflicting-policy.md', kind='policy', required=True, startup_read='complete', load_when='Startup fixture policy claim', sha256=hashlib.sha256(conflict.read_bytes()).hexdigest()))
            (root / 'context/manifest.json').write_text(json.dumps(m, indent=2) + '\n')
        # Each fixture is a frozen snapshot of actual inputs, not a mutable runtime workspace.
        index[case] = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*')) if p.is_file()}
    return index


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('destination')
    p.add_argument('--repo', default=str(Path(__file__).resolve().parents[1]))
    args = p.parse_args()
    index = prepare(args.repo, args.destination)
    print(json.dumps({'destination': args.destination, 'snapshots': index}, indent=2))


if __name__ == '__main__':
    main()
