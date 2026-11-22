"""Read bounded startup context or assess a receipt against captured tool evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

from check_context import check, local_path

PROTOCOL = 'karen-startup-read/v1'
POLICY_ANSWERS = dict(ui='approval', security='approval', push='approval', paid='approval',
                      missing_context='hold', handoff='revalidate')
FIELDS = {'project', 'task', 'manifest_revision', 'status', 'architecture_sha256',
          'sources', 'policy_checks', 'capabilities', 'gaps', 'summary'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def core(root, task=None):
    root = Path(root).resolve()
    manifest_path = local_path(root, 'context/manifest.json')
    manifest = json.loads(manifest_path.read_text())
    paths = [('manifest', 'context/manifest.json')]
    paths += [(s['id'], s['path']) for s in manifest['sources'] if s['startup_read'] == 'complete' and (task is not None or not s.get('validation_only', False))]
    if task is not None:
        paths.append(('task', task))
    return manifest, paths


def read(root, task=None):
    root = Path(root).resolve()
    manifest, paths = core(root, task)
    snapshot = check(root, task=task)
    pins = {s['id']: s['sha256'] for s in manifest['sources']}
    task_pin = manifest.get('task_revisions', {}).get(task)
    records = []
    for source_id, relative in paths:
        path = local_path(root, relative)
        record = dict(id=source_id, path=relative, located=path.is_file())
        if path.is_file():
            data = path.read_bytes()
            pin = task_pin if source_id == 'task' else pins.get(source_id)
            verified = sha(data) == pin if pin else source_id == 'manifest'
            record.update(content=data.decode('utf-8'), sha256=sha(data),
                          revision_verified=verified, revision_basis='snapshot digest' if source_id == 'manifest' else ('reference pin' if pin else 'no reference pin'),
                          first_line=1, last_line=len(data.decode('utf-8').splitlines()))
        records.append(record)
    return dict(protocol=PROTOCOL, project='karen-os', manifest_revision=manifest['revision'],
                context_errors=snapshot['errors'], sources=records)


PROJECT_RECORD = '.karen/project.json'
KAREN_ONLY_SOURCES = {'project', 'claude_entry'}


def project_record(project_root):
    """Validate an external project's record; return (record, errors)."""
    path = local_path(project_root, PROJECT_RECORD)
    if not path.is_file():
        return None, ['missing project record: ' + PROJECT_RECORD]
    try:
        record = json.loads(path.read_text())
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        return None, ['malformed project record: ' + str(error)]
    errors = []
    if not isinstance(record, dict) or record.get('schema_version') != 1:
        return None, ['unsupported project record schema']
    for key in ('project_id', 'karen_manifest_revision', 'project_instructions'):
        if not isinstance(record.get(key), str) or not record[key]:
            errors.append('project record field must be a nonempty string: ' + key)
    if record.get('integration_level') not in (1, 2, 3):
        errors.append('project record integration_level must be 1, 2 or 3')
    for key in ('task_location', 'karen_os_path'):
        if key in record and (not isinstance(record[key], str) or not record[key]):
            errors.append('project record field must be a nonempty string: ' + key)
    if 'karen_os_repository' in record and not repository_name(record['karen_os_repository']):
        errors.append('project record karen_os_repository must look like owner/name')
    if 'pipeline' in record:
        errors += pipeline_errors(record['pipeline'])
    return record, errors


def repository_name(value):
    """True for a GitHub owner/name pair; no network lookup."""
    if not isinstance(value, str) or value.count('/') != 1:
        return False
    allowed = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.')
    owner, name = value.split('/')
    return bool(owner) and bool(name) and set(owner + name) <= allowed and name not in ('.', '..')


def pipeline_errors(pipeline):
    """Validate the optional GitHub pipeline declaration in a project record."""
    if not isinstance(pipeline, dict):
        return ['project record pipeline must be an object']
    errors = []
    if pipeline.get('tracker') != 'github':
        errors.append('project record pipeline.tracker must be github')
    if not repository_name(pipeline.get('repository')):
        errors.append('project record pipeline.repository must look like owner/name')
    branch = pipeline.get('default_branch')
    if not isinstance(branch, str) or not branch or any(c.isspace() for c in branch) or branch.startswith('-'):
        errors.append('project record pipeline.default_branch must be a branch name')
    return errors


def read_project(root, project):
    """Shared core from this checkout plus one external project's declared context.

    Reads only the project's record, the instruction file it names and the
    file names in its declared task folder. Writes nothing.
    """
    root = Path(root).resolve()
    project_root = Path(project).expanduser().resolve()
    manifest, _ = core(root)
    shared = read(root)
    records = [r for r in shared['sources'] if r['id'] not in KAREN_ONLY_SOURCES]
    result = dict(protocol=PROTOCOL, mode='project', project=None, project_root=str(project_root),
                  manifest_revision=manifest['revision'], context_errors=shared['context_errors'],
                  project_status='invalid', project_errors=[], project_warnings=[], tasks=[], pipeline=None, karen_os_repository=None, sources=records)
    if not project_root.is_dir():
        result['project_errors'].append('project directory not found')
        return result
    try:
        record, errors = project_record(project_root)
        result['project_errors'] += errors
        if record is None or errors:
            return result
        result['project'] = record['project_id']
        result['pipeline'] = record.get('pipeline')
        result['karen_os_repository'] = record.get('karen_os_repository')
        for source_id, relative in (('project_record', PROJECT_RECORD), ('project_instructions', record['project_instructions'])):
            path = local_path(project_root, relative)
            row = dict(id=source_id, path=relative, located=path.is_file())
            if path.is_file():
                data = path.read_bytes()
                text = data.decode('utf-8')
                row.update(content=text, sha256=sha(data), revision_verified=False, revision_basis='project file',
                           first_line=1, last_line=len(text.splitlines()))
            else:
                result['project_errors'].append('missing project instructions: ' + relative)
            records.append(row)
        if 'task_location' in record:
            folder = local_path(project_root, record['task_location'])
            if folder.is_dir():
                result['tasks'] = sorted(p.name for p in folder.iterdir() if p.is_file() and p.suffix == '.md')
            else:
                result['project_warnings'].append('task location not found: ' + record['task_location'])
    except (ValueError, UnicodeDecodeError) as error:
        result['project_errors'].append('invalid project context: ' + str(error))
        return result
    if result['project_errors']:
        return result
    if record['karen_manifest_revision'] != manifest['revision']:
        result['project_warnings'].append('stale: project pins KAREN OS revision ' + record['karen_manifest_revision']
                                          + ' but the current revision is ' + manifest['revision'])
        result['project_status'] = 'stale'
    else:
        result['project_status'] = 'ok'
    return result


def word_count(text):
    return len(re.findall(r'[\w]+(?:-[\w]+)*', text))


def assess(root, task, receipt_text, evidence):
    """Evidence contains tool-result outputs, never an agent's reading claims."""
    root = Path(root).resolve()
    expected = read(root, task)
    manifest, paths = core(root, task)
    snapshot = check(root, task=task)
    issues = []
    observed = {}
    accepted_outputs = 0
    expected_command = ['python3', '-B', 'scripts/startup.py', 'read', '--task', task]
    for output in evidence.get('outputs', []):
        if output.get('exit_code') != 0 or output.get('argv') != expected_command:
            continue
        try:
            payload = json.loads(output['stdout'])
        except (ValueError, KeyError, TypeError):
            continue
        if payload.get('protocol') != PROTOCOL:
            continue
        accepted_outputs += 1
        for record in payload.get('sources', []):
            observed[record.get('id')] = record
    expected_by_id = {s['id']: s for s in expected['sources']}
    coverage = []
    for source_id, path in paths:
        wanted = expected_by_id[source_id]
        got = observed.get(source_id, {})
        located = wanted['located'] and got.get('located') is True and got.get('path') == path
        content = got.get('content')
        complete = located and content == wanted.get('content') and got.get('first_line') == 1 and got.get('last_line') == wanted.get('last_line')
        verified = located and got.get('sha256') == wanted.get('sha256') and wanted.get('revision_verified') is True and got.get('revision_verified') is True
        row = dict(id=source_id, located=bool(located), read='complete' if complete else ('partial' if content else 'none'), revision_verified=bool(verified))
        coverage.append(row)
    verified_caps = dict(read='verified' if any(r['read'] == 'complete' for r in coverage) else 'unverified',
                         hash='verified' if any(r['revision_verified'] for r in coverage) else 'unverified',
                         write='unverified', network='unverified')
    try:
        receipt = json.loads(receipt_text)
        if not isinstance(receipt, dict) or set(receipt) != FIELDS:
            raise ValueError('required fields or unexpected fields')
        if not isinstance(receipt['summary'], str) or not isinstance(receipt['gaps'], list) or not all(isinstance(g, str) for g in receipt['gaps']):
            raise ValueError('invalid summary or gaps')
        if word_count(receipt_text) > manifest['startup_receipt_word_limit']:
            issues.append('receipt exceeds word limit')
        if receipt['project'] != 'karen-os' or receipt['task'] != Path(task).stem or receipt['manifest_revision'] != manifest['revision']:
            issues.append('project, task, or manifest revision differs')
        architecture = next(s for s in manifest['sources'] if s['id'] == 'architecture')
        if receipt['architecture_sha256'] != architecture['sha256']:
            issues.append('architecture revision differs')
        rows = receipt['sources']
        if not isinstance(rows, list) or len(rows) != len(coverage):
            raise ValueError('missing or duplicate coverage rows')
        reported = {}
        for row in rows:
            if set(row) != {'id', 'located', 'read', 'revision_verified'} or type(row['located']) is not bool or type(row['revision_verified']) is not bool or row['read'] not in ('complete', 'partial', 'none'):
                raise ValueError('invalid coverage row')
            if row['id'] in reported:
                raise ValueError('duplicate source row')
            reported[row['id']] = row
        if reported != {r['id']: r for r in coverage}:
            issues.append('reported coverage differs from tool evidence')
        if not isinstance(receipt['policy_checks'], dict) or set(receipt['policy_checks']) != set(POLICY_ANSWERS):
            raise ValueError('missing policy scenarios')
        if snapshot['errors']:
            if receipt['policy_checks']['missing_context'] != 'hold' or not receipt['gaps']:
                issues.append('missing or conflicting context was not held and disclosed')
        elif receipt['policy_checks'] != POLICY_ANSWERS:
            issues.append('policy comprehension scenario failed')
        if receipt['capabilities'] != verified_caps:
            issues.append('unsupported capability claim')
        if receipt['status'] not in ('PASS', 'PARTIAL', 'BLOCKED'):
            raise ValueError('invalid status')
    except (ValueError, TypeError, KeyError) as error:
        receipt = {}
        issues.append('invalid receipt format: ' + str(error))
    incomplete = not accepted_outputs or any(r['read'] != 'complete' or not r['revision_verified'] for r in coverage)
    status = 'BLOCKED' if snapshot['errors'] else ('PARTIAL' if issues or incomplete else 'PASS')
    if receipt.get('status') != status:
        issues.append('reported status differs from evidence assessment')
        if status == 'PASS':
            status = 'PARTIAL'
    return dict(status=status, receipt_valid=not issues, issues=issues,
                context_errors=snapshot['errors'], coverage=coverage,
                policy_comprehension_tested=bool(accepted_outputs and not snapshot['errors'] and receipt.get('policy_checks') == POLICY_ANSWERS),
                tool_capabilities_verified=[k for k, v in verified_caps.items() if v == 'verified'],
                words=word_count(receipt_text), word_limit=manifest['startup_receipt_word_limit'])


def assess_handoff(root, task, receipt_text, evidence):
    """Assess the bounded export fixture, including a host-recorded sender stop."""
    try:
        wrapper = json.loads(receipt_text)
        if set(wrapper) != {'startup', 'handoff'}:
            raise ValueError('handoff receipt requires startup and handoff only')
        manifest, _ = core(root, task)
        declared = {s['id']: s for s in manifest['sources']}
        required_records = {'handoff': 'context/handoff-packet.json', 'owner_stop': 'context/owner-stop.json', 'handoff_profile': 'context/handoff-profile.json', 'handoff_procedure': 'context/handoff-procedure.md'}
        for source_id, path in required_records.items():
            record = declared.get(source_id, {})
            if record.get('required') is not True or record.get('startup_read') != 'complete' or record.get('path') != path:
                raise ValueError('handoff record must be mandatory and completely read: ' + source_id)
        result = assess(root, task, json.dumps(wrapper['startup']), evidence)
        handoff = wrapper['handoff']
        profile = json.loads(local_path(Path(root).resolve(), 'context/handoff-profile.json').read_text())
        stop = json.loads(local_path(Path(root).resolve(), 'context/owner-stop.json').read_text())
        packet = local_path(Path(root).resolve(), 'context/handoff-packet.json')
        expected = dict(handoff_id=profile['handoff_id'], previous_owner_stopped=True,
                        authorised_scope='documentation-export', prohibited_actions=profile['prohibited_actions'],
                        result=profile['expected_result'], claim_released=True)
        if handoff != expected:
            result['issues'].append('handoff scope, continuation, or release differs')
        packet_data = json.loads(packet.read_text())
        if packet_data.get('handoff_id') != profile['handoff_id'] or packet_data.get('authorised_scope') != 'documentation-export' or packet_data.get('prohibited_actions') != profile['prohibited_actions'] or packet_data.get('next_action') != profile['expected_result'] or packet_data.get('claim_released') is not True:
            result['context_errors'].append('handoff packet differs from scoped task')
            result['issues'].append('unsupported handoff scope claim')
        if stop.get('state') != 'exited' or stop.get('exit_code') != 0 or stop.get('packet_sha256') != sha(packet.read_bytes()):
            result['context_errors'].append('previous execution owner stop not established')
            result['issues'].append('unsupported owner-stop claim')
        if word_count(receipt_text) > result['word_limit']:
            result['issues'].append('whole final receipt exceeds word limit')
        result['words'] = word_count(receipt_text)
        result['receipt_valid'] = not result['issues']
        result['status'] = 'BLOCKED' if result['context_errors'] else ('PARTIAL' if result['issues'] or result['status'] != 'PASS' else 'PASS')
        return result
    except (ValueError, TypeError, KeyError, OSError) as error:
        return dict(status='BLOCKED', receipt_valid=False, issues=['invalid handoff receipt or record: ' + str(error)])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['read', 'assess', 'assess-handoff'])
    p.add_argument('--root', default=str(Path(__file__).resolve().parents[1]))
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--task')
    mode.add_argument('--explore', action='store_true')
    mode.add_argument('--project', help='external project directory; returns the shared core plus its declared context')
    p.add_argument('--receipt')
    p.add_argument('--evidence')
    args = p.parse_args()
    if args.action == 'read':
        result = read_project(args.root, args.project) if args.project else read(args.root, args.task)
    else:
        if args.explore or args.project:
            p.error('machine assessment requires an explicit task')
        if not args.receipt or not args.evidence:
            p.error('assess requires --receipt and --evidence')
        judge = assess_handoff if args.action == 'assess-handoff' else assess
        result = judge(args.root, args.task, Path(args.receipt).read_text(), json.loads(Path(args.evidence).read_text()))
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
