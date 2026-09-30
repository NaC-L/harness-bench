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
    return ET.fromstring(svg).findall('.//svg:rect[@class="run-marker"]', NS)


class ChartsTests(unittest.TestCase):
    def setUp(self):
        self.rows = rows()
        self.result = report.compare(self.rows, 'base', 'cand')

    def test_three_valid_accessible_self_contained_instrument_panels(self):
        charts = render_charts(self.result, self.rows)
        self.assertEqual(set(charts), {'summary.svg', 'tokens-per-task.svg', 'wall-time-per-task.svg'})
        palette = {'#000', '#ededed', '#a1a1a1', '#757575', '#44cfff', '#4ade80', '#f4644a',
                   'rgba(255,255,255,.06)', 'rgba(255,255,255,.14)'}
        for name, svg in charts.items():
            with self.subTest(name=name):
                root = ET.fromstring(svg)
                self.assertEqual(root.get('version'), '1.1')
                self.assertEqual(root.get('width'), '760')
                self.assertEqual(root.get('role'), 'img')
                self.assertEqual(root.get('aria-labelledby'), 'chart-title chart-desc')
                self.assertTrue(root.find('svg:title', NS).text)
                self.assertTrue(root.find('svg:desc', NS).text)
                self.assertEqual(root.find('svg:rect', NS).get('fill'), '#000')
                self.assertEqual(root.findall('svg:rect', NS)[1].get('stroke'), 'rgba(255,255,255,.06)')
                used = {node.get(attr) for node in root.iter() for attr in ('fill', 'stroke')
                        if node.get(attr) and node.get(attr) != 'none' and not node.get(attr).startswith('url(')}
                self.assertLessEqual(used, palette)
                for tag in ('script', 'image', 'foreignObject', 'circle', 'linearGradient', 'radialGradient'):
                    self.assertFalse(root.findall(f'.//svg:{tag}', NS))
                self.assertNotIn('href=', svg)
                self.assertIn("'Berkeley Mono'", root.find('svg:g', NS).get('font-family'))
                self.assertIn('font-variant-numeric:tabular-nums', svg)
                text = [node.text for node in root.findall('.//svg:text', NS)]
                self.assertIn('BASE (BASELINE)', text)
                self.assertIn('CAND (CANDIDATE)', text)
                self.assertTrue(any(value.startswith('← ') for value in text))
                captions = root.findall('.//svg:text[@class="caption"]', NS)
                self.assertTrue(captions)
                self.assertTrue(all(node.get('font-size') == '10' and node.get('letter-spacing') == '.06em'
                                    and node.get('fill') == '#757575' for node in captions))
                self.assertIn('·', ' '.join(node.text for node in captions))

    def test_descriptions_state_findings_and_list_exact_underlying_numbers(self):
        charts = render_charts(self.result, self.rows)
        for name, key in (('tokens-per-task.svg', 'tokens'), ('wall-time-per-task.svg', 'seconds')):
            desc = ET.fromstring(charts[name]).find('svg:desc', NS).text
            self.assertIn('CAND USES FEWER TOKENS' if key == 'tokens' else 'CAND RUNS FASTER', desc.upper())
            for row in self.rows:
                value = (sum(row['metrics'][field] for field in
                             ('input_tokens', 'cache_read_tokens', 'cache_write_tokens', 'output_tokens'))
                         if key == 'tokens' else row['wall_time_sec'])
                self.assertIn(f'{value} {key} ({"passed" if row["passed"] else "failed"})', desc)
                self.assertIn(f'{row["task"]}, {row["harness"]}:', desc)
            self.assertIn('median=', desc)
            self.assertIn('delta=', desc)
        desc = ET.fromstring(charts['summary.svg']).find('svg:desc', NS).text
        self.assertIn('VERDICT: BETTER', desc)
        for arm in ('base', 'cand'):
            for key in ('tokens_per_correct', 'uncached_tokens_per_correct', 'cost_per_correct',
                        'median_wall_time_sec', 'p90_wall_time_sec'):
                self.assertIn(str(self.result['scorecards'][arm][key]), desc)
        self.assertIn('4/6 correct runs', desc)

    def test_every_known_run_has_a_square_and_failures_are_hollow(self):
        charts = render_charts(self.result, self.rows)
        for name in ('tokens-per-task.svg', 'wall-time-per-task.svg'):
            squares = markers(charts[name])
            self.assertEqual(len(squares), len(self.rows))
            failed = [square for square in squares if square.get('data-passed') == 'false']
            self.assertEqual(len(failed), 4)
            self.assertTrue(all(square.get('fill') == '#000' and square.get('stroke-width') == '1'
                                for square in failed))
            self.assertTrue(all(square.get('fill') in ('#757575', '#44cfff')
                                for square in squares if square not in failed))
            self.assertTrue(all(square.get('opacity') == '0.35' and square.get('width') == '4'
                                and square.get('height') == '4' for square in squares))
            self.assertTrue(all(square.get('shape-rendering') == 'crispEdges' for square in squares))
            root = ET.fromstring(charts[name])
            medians = root.findall('.//svg:rect[@class="median-marker"]', NS)
            self.assertEqual(len(medians), 4)
            self.assertEqual(len(root.findall('.//svg:line[@class="median-link"]', NS)), 2)
            halos = root.findall('.//svg:rect[@class="hero-halo"]', NS)
            self.assertEqual(len(halos), 2)
            self.assertTrue(all(halo.get('width') == '12' and halo.get('fill') == '#44cfff'
                                and halo.get('fill-opacity') == '.2' for halo in halos))
            self.assertIn('HOLLOW = FAILED RUN', charts[name])
            self.assertIn('MEDIAN OF 3 RUNS PER ARM', charts[name])

    def test_dumbbell_rows_columns_and_medians_include_failed_attempts(self):
        root = ET.fromstring(render_charts(self.result, self.rows)['tokens-per-task.svg'])
        task_rows = root.findall('.//svg:g[@class="task-row"]', NS)
        self.assertEqual([row.get('data-task') for row in task_rows], ['alpha', 'long-task-name'])
        for row in task_rows:
            self.assertEqual([float(mark.get('data-value')) for mark in
                              row.findall('svg:rect[@class="median-marker"]', NS)], [2800, 2400])
            texts = row.findall('svg:text', NS)
            self.assertEqual([text.text for text in texts], [row.get('data-task'), '2.8k', '2.4k', '−14.3%'])
            self.assertEqual([text.get('x') for text in texts[1:]], ['580.00', '658.00', '736.00'])
        self.rows[2]['metrics']['input_tokens'] = 1
        root = ET.fromstring(render_charts(report.compare(self.rows, 'base', 'cand'), self.rows)['tokens-per-task.svg'])
        self.assertEqual(root.find('.//svg:rect[@class="median-marker"]', NS).get('data-value'), '1800')

    def test_unknown_tokens_and_times_are_omitted_and_counted(self):
        self.rows[0]['metrics'] = None
        self.rows[1]['metrics']['input_tokens'] = None
        self.rows[2]['metrics']['output_tokens'] = None
        self.rows[3]['wall_time_sec'] = None
        result = report.compare(self.rows, 'base', 'cand')
        charts = render_charts(result, self.rows)
        self.assertEqual(len(markers(charts['tokens-per-task.svg'])), 9)
        self.assertIn('3 RUNS OMITTED: UNKNOWN TOKENS', charts['tokens-per-task.svg'])
        self.assertIn('1 TASKS WITHOUT PAIRED MEDIANS', charts['tokens-per-task.svg'])
        self.assertEqual(len(markers(charts['wall-time-per-task.svg'])), 11)
        self.assertIn('1 RUNS OMITTED: UNKNOWN SECONDS', charts['wall-time-per-task.svg'])
        self.assertIn('MEDIAN OF KNOWN RUNS (0–3 PER ARM/TASK)', charts['tokens-per-task.svg'])
        summary = ET.fromstring(charts['summary.svg'])
        unknown = summary.findall('.//svg:g[@class="metric-row"][@data-change="unknown"]', NS)
        self.assertEqual(len(unknown), 3)
        self.assertTrue(all(not row.findall('svg:rect[@class="summary-marker"]', NS) for row in unknown))
        self.assertTrue(all('UNKNOWN' in [node.text for node in row.findall('svg:text', NS)] for row in unknown))
        self.assertEqual(len(summary.findall('.//svg:rect[@class="summary-marker"]', NS)), 2)

    def test_summary_relative_values_margin_dither_and_verdict(self):
        svg = render_charts(self.result, self.rows)['summary.svg']
        self.assertIn('VERDICT: BETTER — CAND BEATS BASE', svg)
        self.assertIn('← LOWER IS BETTER', svg)
        self.assertIn('DITHER = ±10% MARGIN', svg)
        self.assertIn('−20.0%', svg)
        self.assertIn('−14.3%', svg)
        self.assertIn('Tokens / correct · uncached', svg)
        root = ET.fromstring(svg)
        self.assertEqual(len(root.findall('.//svg:rect[@class="summary-marker"]', NS)), 5)
        arrows = root.findall('.//svg:line[@class="delta-arrow"]', NS)
        self.assertEqual(len(arrows), 5)
        self.assertTrue(all(line.get('stroke-dasharray') == '2,2' for line in arrows))
        pattern = root.find('.//svg:pattern', NS)
        self.assertEqual((pattern.get('width'), pattern.get('height')), ('2', '2'))
        self.assertEqual(pattern.get('patternUnits'), 'userSpaceOnUse')
        pixels = pattern.findall('svg:rect', NS)
        self.assertEqual(len(pixels), 2)
        self.assertEqual((pixels[1].get('x'), pixels[1].get('y')), ('1', '1'))
        self.assertTrue(all(pixel.get('fill') == '#757575' and pixel.get('fill-opacity') == '.25'
                            for pixel in pixels))
        band = root.find('.//svg:rect[@class="margin-band"]', NS)
        self.assertEqual(band.get('fill'), 'url(#margin-dither)')
        self.assertEqual(band.get('data-margin'), '0.1')

    def test_delta_sign_and_semantic_colors_respect_margin(self):
        result = copy.deepcopy(self.result)
        baseline, candidate = result['scorecards']['base'], result['scorecards']['cand']
        for key, factor in (('tokens_per_correct', .8), ('uncached_tokens_per_correct', 1.2),
                            ('cost_per_correct', .95), ('median_wall_time_sec', .9),
                            ('p90_wall_time_sec', 1.1)):
            baseline[key], candidate[key] = 100, 100 * factor
        root = ET.fromstring(render_charts(result, self.rows)['summary.svg'])
        rows_by_key = {row.get('data-metric'): row for row in root.findall('.//svg:g[@class="metric-row"]', NS)}
        for key, text, color in (('tokens_per_correct', '−20.0%', '#4ade80'),
                                 ('uncached_tokens_per_correct', '+20.0%', '#f4644a'),
                                 ('cost_per_correct', '−5.0%', '#a1a1a1'),
                                 ('median_wall_time_sec', '−10.0%', '#a1a1a1'),
                                 ('p90_wall_time_sec', '+10.0%', '#a1a1a1')):
            row = rows_by_key[key]
            self.assertEqual(row.find('svg:rect[@class="summary-marker"]', NS).get('fill'), color)
            labels = [node for node in row.findall('svg:text', NS) if node.text == text]
            self.assertEqual(len(labels), 2)
            self.assertTrue(all(node.get('fill') == color for node in labels))

    def test_all_verdicts_use_plain_words(self):
        for verdict, words in (('better', 'BEATS'), ('worse', 'LOSES TO'), ('tradeoff', 'TRADES OFF WITH'),
                               ('equivalent', 'MATCHES'), ('inconclusive', 'VS')):
            result = dict(self.result, verdict=verdict)
            title = ET.fromstring(render_charts(result, self.rows)['summary.svg']).find('svg:title', NS).text
            self.assertEqual(title, f'VERDICT: {verdict.upper()} — CAND {words} BASE')

    def test_zero_baseline_and_all_unknown_do_not_divide_by_zero(self):
        for row in self.rows:
            row['wall_time_sec'] = 0
            row['metrics'] = None
        charts = render_charts(report.compare(self.rows, 'base', 'cand'), self.rows)
        summary = ET.fromstring(charts['summary.svg'])
        self.assertEqual(len(summary.findall('.//svg:g[@class="metric-row"][@data-change="unknown"]', NS)), 5)
        self.assertFalse(summary.findall('.//svg:rect[@class="summary-marker"]', NS))
        self.assertEqual(len(markers(charts['tokens-per-task.svg'])), 0)
        self.assertEqual(len(markers(charts['wall-time-per-task.svg'])), len(self.rows))
        self.assertIn('12 RUNS OMITTED: UNKNOWN TOKENS', charts['tokens-per-task.svg'])
        self.assertIn('NO COMPARABLE TOKENS MEDIANS', charts['tokens-per-task.svg'])
        self.assertIn('NO KNOWN RELATIVE EFFICIENCY METRICS', charts['summary.svg'])

    def test_missing_cache_counts_are_zero_and_unrelated_arms_ignored(self):
        for row in self.rows:
            del row['metrics']['cache_read_tokens']
            del row['metrics']['cache_write_tokens']
        self.rows.append(dict(self.rows[0], harness='other', task='not-shown'))
        charts = render_charts(report.compare(self.rows, 'base', 'cand'), self.rows)
        self.assertEqual(len(markers(charts['tokens-per-task.svg'])), 12)
        self.assertNotIn('not-shown', charts['tokens-per-task.svg'])
        self.assertIn('base: runs [1200 tokens', charts['tokens-per-task.svg'])

    def test_ticks_evenly_divide_actual_domain_with_compact_units(self):
        for row in self.rows:
            row['metrics']['input_tokens'] = 10000
            row['wall_time_sec'] = 1
        charts = render_charts(report.compare(self.rows, 'base', 'cand'), self.rows)
        for name, expected, labels in (
                ('tokens-per-task.svg', [0, 2700, 5400, 8100, 10800], ['0', '2.7k', '5.4k', '8.1k', '10.8k']),
                ('wall-time-per-task.svg', [0, .25, .5, .75, 1], ['0s', '0.25s', '0.5s', '0.75s', '1s'])):
            ticks = ET.fromstring(charts[name]).findall('.//svg:text[@class="scale-tick"]', NS)
            self.assertEqual([float(tick.get('data-value')) for tick in ticks], expected)
            self.assertEqual([tick.text for tick in ticks], labels)
            self.assertTrue(all(tick.get('font-size') == '11' and tick.get('fill') == '#757575' for tick in ticks))
        summary_ticks = ET.fromstring(charts['summary.svg']).findall('.//svg:text[@class="scale-tick"]', NS)
        values = [float(tick.get('data-value')) for tick in summary_ticks]
        self.assertEqual(values[2], 0)
        self.assertEqual(values[0], -values[-1])
        self.assertAlmostEqual(values[1] - values[0], values[4] - values[3])

    def test_grid_and_marks_are_pixel_snapped_without_axis_lines(self):
        for svg in render_charts(self.result, self.rows).values():
            root = ET.fromstring(svg)
            grids = root.findall('.//svg:line[@class="gridline"]', NS)
            self.assertEqual(len(grids), 5)
            for grid in grids:
                self.assertEqual(grid.get('stroke-dasharray'), '2,4')
                self.assertEqual(grid.get('stroke'), 'rgba(255,255,255,.06)')
                self.assertEqual(grid.get('stroke-width'), '1')
            for line in root.findall('.//svg:line', NS):
                self.assertEqual(line.get('shape-rendering'), 'crispEdges')
                for key in ('x1', 'y1', 'x2', 'y2'):
                    self.assertEqual(float(line.get(key)) % 1, .5)
            for square in root.findall('.//svg:rect[@class="run-marker"]', NS):
                self.assertEqual(float(square.get('x')) % 1, 0)
                self.assertEqual(float(square.get('y')) % 1, 0)
            self.assertFalse(root.findall('.//svg:line[@class="axis"]', NS))

    def test_long_task_labels_truncate_only_when_needed(self):
        long_name = 'W' * 70 + '-task'
        for row in self.rows:
            if row['task'] == 'long-task-name':
                row['task'] = long_name
        root = ET.fromstring(render_charts(report.compare(self.rows, 'base', 'cand'), self.rows)['tokens-per-task.svg'])
        task_rows = root.findall('.//svg:g[@class="task-row"]', NS)
        for row in task_rows:
            label = row.find('svg:text', NS).text
            if row.get('data-task') == 'alpha':
                self.assertEqual(label, 'alpha')
            else:
                self.assertTrue(label.endswith('…'))
                self.assertLess(len(label), len(long_name))
                self.assertEqual(row.find('svg:title', NS).text, long_name)
                self.assertIn(long_name, root.find('svg:desc', NS).text)

    def test_caption_finding_tracks_worse_and_tied_data(self):
        for factor, expected in ((1.4, ('USES MORE TOKENS', 'RUNS SLOWER')),
                                 (1, ('MATCHES BASE', 'MATCHES BASE'))):
            records = rows()
            for row in records:
                row['metrics']['input_tokens'] = 2000 * (factor if row['harness'] == 'cand' else 1)
                row['wall_time_sec'] = 20 * (factor if row['harness'] == 'cand' else 1)
            charts = render_charts(report.compare(records, 'base', 'cand'), records)
            for name, finding in zip(('tokens-per-task.svg', 'wall-time-per-task.svg'), expected):
                self.assertIn(f'CAND {finding}', charts[name])

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
