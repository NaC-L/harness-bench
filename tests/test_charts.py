import copy
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from bench import report
from bench.charts import render_charts
from bench.export import export


NS = {'svg': 'http://www.w3.org/2000/svg'}


def rows():
    return [{'task': task, 'harness': arm, 'passed': trial != 2,
             'agent_exit_code': 0, 'wall_time_sec': (trial + 1) * 10 * scale,
             'prompt_hash': 'prompt', 'task_hash': task,
             'run_id': f'{arm}-{task}-{trial}', 'artifact_dir': 'missing',
             'metrics': {'input_tokens': (trial + 1) * 1000 * scale, 'cache_read_tokens': 500,
                         'cache_write_tokens': 100, 'output_tokens': 200,
                         'cost_usd': 0.01 * scale}}
            for task in ('alpha', 'long-task-name')
            for arm, scale in (('base', 1), ('cand', 0.8)) for trial in range(3)]


def markers(svg):
    return ET.fromstring(svg).findall('.//svg:circle[@class="run-marker"]', NS)


class ChartsTests(unittest.TestCase):
    def setUp(self):
        self.rows = rows()
        self.result = report.compare(self.rows, 'base', 'cand')

    def test_three_valid_accessible_self_contained_svgs(self):
        charts = render_charts(self.result, self.rows)
        self.assertEqual(set(charts), {'summary.svg', 'tokens-per-task.svg', 'wall-time-per-task.svg'})
        for name, svg in charts.items():
            with self.subTest(name=name):
                root = ET.fromstring(svg)
                self.assertEqual(root.get('version'), '1.1')
                self.assertEqual(root.get('role'), 'img')
                self.assertTrue(root.find('svg:title', NS).text)
                self.assertTrue(root.find('svg:desc', NS).text)
                self.assertEqual(root.find('svg:rect', NS).get('fill'), '#FFFFFF')
                self.assertFalse(root.findall('.//svg:script', NS))
                self.assertNotIn('href=', svg)
                self.assertIn('base', svg)
                self.assertIn('cand', svg)
                self.assertIn('#0072B2', svg)
                self.assertIn('#E69F00', svg)

    def test_every_known_run_and_distinct_failed_markers(self):
        charts = render_charts(self.result, self.rows)
        for name in ('tokens-per-task.svg', 'wall-time-per-task.svg'):
            dots = markers(charts[name])
            self.assertEqual(len(dots), len(self.rows))
            failed = [dot for dot in dots if dot.get('data-passed') == 'false']
            self.assertEqual(len(failed), 4)
            self.assertTrue(all(dot.get('fill') == '#FFFFFF' for dot in failed))
            self.assertTrue(all(dot.get('fill') != '#FFFFFF' for dot in dots if dot not in failed))
            root = ET.fromstring(charts[name])
            self.assertEqual(len(root.findall('.//svg:line[@class="median-tick"]', NS)), 4)
            self.assertIn('Failed run (hollow)', charts[name])
            self.assertIn('Median of known runs', charts[name])

    def test_unknown_tokens_and_times_are_omitted_and_counted(self):
        self.rows[0]['metrics'] = None
        self.rows[1]['metrics']['input_tokens'] = None
        self.rows[2]['metrics']['output_tokens'] = None
        self.rows[3]['wall_time_sec'] = None
        result = report.compare(self.rows, 'base', 'cand')
        charts = render_charts(result, self.rows)
        self.assertEqual(len(markers(charts['tokens-per-task.svg'])), 9)
        self.assertIn('3 runs omitted: unknown tokens.', charts['tokens-per-task.svg'])
        self.assertEqual(len(markers(charts['wall-time-per-task.svg'])), 11)
        self.assertIn('1 runs omitted: unknown seconds.', charts['wall-time-per-task.svg'])
        summary = ET.fromstring(charts['summary.svg'])
        self.assertEqual(sum(text.text == 'unknown' for text in summary.findall('.//svg:text', NS)), 3)
        self.assertEqual(len(summary.findall('.//svg:circle[@class="summary-marker"]', NS)), 2)

    def test_summary_relative_values_margin_and_verdict(self):
        svg = render_charts(self.result, self.rows)['summary.svg']
        self.assertIn('verdict: better', svg)
        self.assertIn('lower = better', svg)
        self.assertIn('Shaded band: ±10% margin', svg)
        self.assertIn('-20.0%', svg)
        self.assertIn('-14.3%', svg)  # (7200 / 8400 - 1) * 100, including cache tokens
        self.assertIn('Tokens per correct (uncached)', svg)
        self.assertEqual(len(ET.fromstring(svg).findall('.//svg:circle[@class="summary-marker"]', NS)), 5)

    def test_zero_baseline_and_all_unknown_do_not_divide_by_zero(self):
        for row in self.rows:
            row['wall_time_sec'] = 0
            row['metrics'] = None
        charts = render_charts(report.compare(self.rows, 'base', 'cand'), self.rows)
        summary = ET.fromstring(charts['summary.svg'])
        self.assertEqual(sum(text.text == 'unknown' for text in summary.findall('.//svg:text', NS)), 5)
        self.assertEqual(len(markers(charts['tokens-per-task.svg'])), 0)
        self.assertEqual(len(markers(charts['wall-time-per-task.svg'])), len(self.rows))
        self.assertIn('12 runs omitted: unknown tokens.', charts['tokens-per-task.svg'])

    def test_missing_cache_counts_are_zero_and_unrelated_arms_ignored(self):
        for row in self.rows:
            del row['metrics']['cache_read_tokens']
            del row['metrics']['cache_write_tokens']
        self.rows.append(dict(self.rows[0], harness='other', task='not-shown'))
        charts = render_charts(report.compare(self.rows, 'base', 'cand'), self.rows)
        self.assertEqual(len(markers(charts['tokens-per-task.svg'])), 12)
        self.assertNotIn('not-shown', charts['tokens-per-task.svg'])

    def test_nice_ticks_use_thousands_separators_and_fractional_seconds(self):
        for row in self.rows:
            row['metrics']['input_tokens'] = 10000
            row['wall_time_sec'] = 1
        charts = render_charts(report.compare(self.rows, 'base', 'cand'), self.rows)
        token_text = [text.text for text in ET.fromstring(charts['tokens-per-task.svg']).findall('.//svg:text', NS)]
        time_text = [text.text for text in ET.fromstring(charts['wall-time-per-task.svg']).findall('.//svg:text', NS)]
        self.assertIn('2,500', token_text)
        self.assertNotIn('2,500.0', token_text)
        self.assertIn('0.25 s', time_text)

    def test_deterministic_and_does_not_mutate_inputs(self):
        original_rows, original_result = copy.deepcopy(self.rows), copy.deepcopy(self.result)
        first = render_charts(self.result, self.rows)
        self.assertEqual(first, render_charts(self.result, self.rows))
        self.assertEqual(first, render_charts(self.result, list(reversed(self.rows))))
        self.assertEqual(self.rows, original_rows)
        self.assertEqual(self.result, original_result)

    def test_xml_special_characters_are_escaped(self):
        for row in self.rows:
            row['harness'] = 'base & <arm>' if row['harness'] == 'base' else 'cand "quoted"'
            row['task'] += '<&>'
        result = report.compare(self.rows, 'base & <arm>', 'cand "quoted"')
        for svg in render_charts(result, self.rows).values():
            ET.fromstring(svg)
            self.assertIn('base &amp; &lt;arm&gt;', svg)

    def test_markdown_default_has_no_charts_and_embeddings_follow_dimension_table(self):
        default = report.render_markdown(self.result, self.rows, results_label='results/test')
        self.assertNotIn('## Charts', default)
        self.assertEqual(default, report.render_markdown(self.result, self.rows,
                                                        results_label='results/test', charts=None))
        pairs = [('Summary', 'charts/summary.svg'), ('Tokens per task', 'charts/tokens-per-task.svg')]
        rendered = report.render_markdown(self.result, self.rows, results_label='results/test', charts=pairs)
        self.assertIn('![Summary](charts/summary.svg)', rendered)
        self.assertIn('![Tokens per task](charts/tokens-per-task.svg)', rendered)
        self.assertLess(rendered.index('| safety |'), rendered.index('## Charts'))
        self.assertLess(rendered.index('## Charts'), rendered.index('## Per-task results'))
        added = '\n\n## Charts\n\n' + '\n'.join(f'![{alt}]({path})' for alt, path in pairs)
        self.assertEqual(rendered.replace(added, '', 1), default)

    def test_export_writes_charts_and_embeds_them(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            out = root / 'bundle'
            export(self.rows, root / 'results', out, 'base', 'cand')
            markdown = (out / 'REPORT.md').read_text(encoding='utf-8')
            expected = render_charts(self.result, self.rows)
            self.assertEqual({p.name for p in (out / 'charts').iterdir()}, set(expected))
            for name, svg in expected.items():
                self.assertIn(f'](charts/{name})', markdown)
                self.assertEqual((out / 'charts' / name).read_text(encoding='utf-8'), svg)
                ET.parse(out / 'charts' / name)


if __name__ == '__main__':
    unittest.main()
