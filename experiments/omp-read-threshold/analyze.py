"""Read-only mechanism counts for OMP benchmark sessions; emits JSON per run."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re


def analyze(row):
    metrics = row.get('metrics') or {}
    counts = Counter(dict.fromkeys(('bare_reads', 'ranged_reads', 'followup_reads', 'folded_reads', 'read_output_characters', 'edit_errors', 'unseen_line_errors', 'edit_output_characters', 'shell_file_dump_candidates', 'bash_calls', 'bash_null_fields', 'bash_optional_fields', 'write_content_characters'), 0))
    reads = Counter()
    pending = {}
    files = list(dict.fromkeys(metrics.get('session_files') or []))
    initial_input_tokens = None
    initial_assistant_seen = False
    write_paths = []
    for filename in files:
        with Path(filename).open(encoding='utf-8') as stream:
            for line in stream:
                record = json.loads(line)
                message = record.get('message') or {}
                if not initial_assistant_seen and message.get('role') == 'assistant':
                    initial_assistant_seen = True
                    usage = message.get('usage')
                    if not isinstance(usage, dict):
                        usage = {}
                    initial = [usage.get(key) for key in ('input', 'cacheRead', 'cacheWrite')]
                    if all(isinstance(n, (int, float)) for n in initial):
                        initial_input_tokens = sum(initial)
                for block in message.get('content') or []:
                    if not isinstance(block, dict) or block.get('type') != 'toolCall':
                        continue
                    name = block.get('name')
                    args = block.get('arguments') or {}
                    pending[block.get('id')] = name
                    if name == 'read':
                        path = args.get('path', '')
                        base = re.sub(r':(?:raw|\d.*|-[\d]+).*$', '', path)
                        ranged = base != path
                        counts['ranged_reads' if ranged else 'bare_reads'] += 1
                        counts['followup_reads'] += reads[base] > 0
                        reads[base] += 1
                    elif name == 'bash':
                        command = args.get('command', '')
                        counts['bash_calls'] += 1
                        counts['bash_null_fields'] += sum(value is None for value in args.values())
                        counts['bash_optional_fields'] += sum(key not in ('i', 'command') for key in args)
                        counts['shell_file_dump_candidates'] += bool(re.search(r'\b(?:cat|type|Get-Content)\s|\breadFile(?:Sync)?\s*\(|\bread_text\s*\(', command))
                    elif name == 'write':
                        write_paths.append(args.get('path'))
                        content = args.get('content')
                        if isinstance(content, str):
                            counts['write_content_characters'] += len(content)
                if message.get('role') != 'toolResult':
                    continue
                name = message.get('toolName') or pending.get(message.get('toolCallId'))
                text = '\n'.join(b.get('text', '') for b in message.get('content') or [] if isinstance(b, dict) and b.get('type') == 'text')
                if name == 'read':
                    counts['read_output_characters'] += len(text)
                    counts['folded_reads'] += bool(re.search(r'(?:ln|lines) elided|elision recovery|elided.*re-read', text))
                if name == 'edit':
                    counts['edit_errors'] += bool(message.get('isError'))
                    counts['unseen_line_errors'] += 'never displayed' in text
                    counts['edit_output_characters'] += len(text)
    token_keys = ('input_tokens', 'output_tokens', 'cache_read_tokens', 'cache_write_tokens')
    tokens = {key: metrics.get(key) for key in token_keys}
    uncached = [tokens[key] for key in ('input_tokens', 'output_tokens', 'cache_write_tokens')]
    return {'run_id': row['run_id'], 'harness': row['harness'], 'task': row['task'], 'trial': row['trial'], 'passed': row['passed'], 'requests': metrics.get('requests'), 'session_files': len(files), 'tokens': tokens, 'uncached_tokens': sum(uncached) if all(isinstance(n, (int, float)) for n in uncached) else None, 'initial_input_tokens': initial_input_tokens, 'write_paths': write_paths, 'verified_after_final_edit': metrics.get('verified_after_final_edit'), 'reproduced_before_first_edit': metrics.get('reproduced_before_first_edit'), 'mechanisms': dict(counts) if files else None}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('results', type=Path)
    args = parser.parse_args()
    with (args.results / 'runs.jsonl').open(encoding='utf-8') as stream:
        for line in stream:
            print(json.dumps(analyze(json.loads(line)), sort_keys=True))
