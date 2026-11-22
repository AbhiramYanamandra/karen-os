"""Extract local startup-reader tool results and the raw final receipt from CLI JSONL."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex


def argv(command):
    try:
        parts = shlex.split(command)
        if len(parts) == 3 and parts[1] == '-lc':
            parts = shlex.split(parts[2])
        return parts
    except ValueError:
        return []


def collect(runtime, text):
    events = [json.loads(line) for line in text.splitlines() if line.strip()]
    outputs = []
    final = ''
    uses = {}
    for event in events:
        if runtime == 'codex' and event.get('type') == 'item.completed':
            item = event.get('item', {})
            if item.get('type') == 'command_execution':
                outputs.append(dict(argv=argv(item.get('command', '')), stdout=item.get('aggregated_output', ''), exit_code=item.get('exit_code')))
            elif item.get('type') == 'agent_message':
                final = item.get('text', '')
        if runtime == 'claude':
            if event.get('type') == 'assistant':
                for block in event.get('message', {}).get('content', []):
                    if block.get('type') == 'tool_use':
                        uses[block['id']] = block
            if event.get('type') == 'user':
                for block in event.get('message', {}).get('content', []):
                    if block.get('type') != 'tool_result':
                        continue
                    use = uses.get(block['tool_use_id'], {})
                    if use.get('name') == 'Bash':
                        content = block.get('content', '')
                        if isinstance(content, list):
                            content = '\n'.join(b.get('text', '') for b in content)
                        outputs.append(dict(argv=argv(use.get('input', {}).get('command', '')), stdout=content, exit_code=1 if block.get('is_error') else 0))
            if event.get('type') == 'result':
                structured = event.get('structured_output')
                final = json.dumps(structured, ensure_ascii=False) if structured is not None else event.get('result', '')
    # Keep actual tool text only for the startup reader; other logs stay temporary.
    selected = [o for o in outputs if 'scripts/startup.py' in o['argv']]
    return dict(runtime=runtime, raw_trace_sha256=hashlib.sha256(text.encode()).hexdigest(), outputs=selected), final


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runtime', choices=['codex', 'claude'], required=True)
    p.add_argument('--trace', required=True)
    p.add_argument('--prefix', required=True)
    args = p.parse_args()
    evidence, receipt = collect(args.runtime, Path(args.trace).read_text())
    prefix = Path(args.prefix)
    Path(str(prefix) + '.tools.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
    Path(str(prefix) + '.receipt.txt').write_text(receipt)
    print(json.dumps({'tool_results_retained': len(evidence['outputs']), 'receipt_present': bool(receipt)}))


if __name__ == '__main__':
    main()
