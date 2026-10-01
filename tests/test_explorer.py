import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from bench.explorer import collect, compile_explorer, render


class ExplorerTests(unittest.TestCase):
    def test_external_artifact_paths_are_not_embedded(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'bundle'
            root.mkdir()
            outside = Path(temp) / 'private'
            outside.mkdir()
            (outside / 'patch.diff').write_text('private contents', encoding='utf-8')
            rows = [{'run_id': 'one', 'artifact_dir': str(outside)},
                    {'run_id': 'two', 'artifact_dir': '../private'}]
            (root / 'runs.jsonl').write_text('\n'.join(map(json.dumps, rows)), encoding='utf-8')
            self.assertEqual([run['files'] for run in collect(root)['runs']], [{}, {}])

    def test_external_chart_symlink_is_not_embedded(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'bundle'
            (root / 'charts').mkdir(parents=True)
            (root / 'runs.jsonl').write_text('', encoding='utf-8')
            outside = Path(temp) / 'private.svg'
            outside.write_text('<svg xmlns="http://www.w3.org/2000/svg">'
                               '<title>private chart</title></svg>', encoding='utf-8')
            try:
                (root / 'charts' / 'summary.svg').symlink_to(outside)
            except OSError as exc:
                self.skipTest(f'symlinks unavailable: {exc}')
            self.assertEqual(collect(root)['charts'], [])

    def test_payload_preserves_hostile_text_without_closing_script(self):
        data = {'runs': [], 'report': '</script><script>alert(1)</script>& __BENCH_STYLE__', 'title': 'ü'}
        html = render(data)
        payload = html.split('<script type="application/json" id="bench-data">', 1)[1].split('</script>', 1)[0]
        self.assertNotIn('<', payload)
        self.assertEqual(json.loads(payload), data)

    def test_svg_checkout_line_endings_do_not_change_export_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'bundle'
            (root / 'charts').mkdir(parents=True)
            (root / 'runs.jsonl').write_text('', encoding='utf-8')
            svg = (b'<svg xmlns="http://www.w3.org/2000/svg">\n'
                   b'<title>Recorded metric</title>\n'
                   b'<desc>Value: 10 seconds.</desc>\n</svg>\n')
            outputs = []
            for name, ending in (('lf', b'\n'), ('crlf', b'\r\n')):
                (root / 'charts' / 'summary.svg').write_bytes(svg.replace(b'\n', ending))
                out = Path(temp) / f'{name}.html'
                compile_explorer(root, out)
                outputs.append(out.read_bytes())
            self.assertEqual(hashlib.sha256(outputs[0]).hexdigest(),
                             hashlib.sha256(outputs[1]).hexdigest())
            self.assertEqual([content.count(b'\r\n') for content in outputs], [0, 0])

    def test_missing_transcripts_and_unknown_measurements_remain_unknown(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            row = {'run_id': 'a', 'artifact_dir': 'runs/a', 'metrics': {'input_tokens': None}}
            artifact = root / 'runs' / 'a'
            artifact.mkdir(parents=True)
            (artifact / 'check.txt').write_text('tests failed\n', encoding='utf-8')
            (root / 'runs.jsonl').write_text(json.dumps(row) + '\n', encoding='utf-8')
            data = collect(root)
            self.assertEqual(data['runs'][0]['row'], row)
            self.assertEqual(data['runs'][0]['files'], {'check.txt': 'tests failed\n'})
            self.assertIsNone(data['report'])

    def test_existing_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / 'view.html'
            out.write_text('user work', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'already exists'):
                compile_explorer(Path(temp), out)
            self.assertEqual(out.read_text(encoding='utf-8'), 'user work')

    def test_automatic_export_respects_transcript_opt_in(self):
        from bench.export import export
        from tests.test_charts import rows

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'source'
            source.mkdir()
            artifact = source / 'artifact'
            (artifact / 'sessions').mkdir(parents=True)
            transcript = json.dumps({'type': 'message', 'message': {
                'role': 'user', 'content': 'private transcript marker'}})
            (artifact / 'sessions' / 'session.jsonl').write_text(transcript, encoding='utf-8')
            records = rows()
            for row in records:
                row['artifact_dir'] = str(artifact)
            for include in (False, True):
                with self.subTest(include_transcripts=include):
                    out = root / str(include)
                    export(records, source, out, 'base', 'cand', include_transcripts=include)
                    html = (out / 'EXPLORER.html').read_text(encoding='utf-8')
                    payload = html.split('<script type="application/json" id="bench-data">', 1)[1].split('</script>', 1)[0]
                    data = json.loads(payload)
                    self.assertEqual('private transcript marker' in html, include)
                    self.assertEqual({run['row']['run_id'] for run in data['runs']},
                                     {row['run_id'] for row in records})
                    if include:
                        for run in data['runs']:
                            self.assertIn(transcript, run['files'].values())
