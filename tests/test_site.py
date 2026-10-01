import json
import tempfile
import unittest
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

from bench.site import build


class IndexEvidence(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.links = []
        self.dates = []
        self.first_article_link = False
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == 'article':
            self.first_article_link = True
        elif tag == 'a' and self.first_article_link:
            self.links.append(values['href'])
            self.first_article_link = False
        elif tag == 'time':
            self.dates.append(values['datetime'])


class SiteTests(unittest.TestCase):
    def bundle(self, root, label, starts):
        directory = root / label
        directory.mkdir(parents=True)
        rows = [{'run_id': str(i), 'harness': 'arm', 'task': 'task', 'trial': i,
                 'started': value, 'metrics': {}} for i, value in enumerate(starts)]
        (directory / 'runs.jsonl').write_text('\n'.join(map(json.dumps, rows)), encoding='utf-8')

    def test_index_orders_all_reports_by_experiment_start_not_name_or_latest_run(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'published'
            stamp = lambda value: datetime.fromisoformat(value + '+00:00').timestamp()
            self.bundle(root, 'zulu', [stamp('2026-01-01T00:00:00'), stamp('2026-12-31T00:00:00')])
            self.bundle(root, 'alpha', [stamp('2026-05-02T06:30:00')])
            self.bundle(root, 'beta', [stamp('2026-05-02T12:30:00')])
            (root / 'legacy-2026-03-10').mkdir()
            (root / 'undated').mkdir()
            out = Path(temp) / 'site'
            build(root, out)
            page = IndexEvidence((out / 'index.html').read_text(encoding='utf-8'))
            self.assertEqual([link.removesuffix('/EXPLORER.html').split('/')[-1] for link in page.links],
                             ['beta', 'alpha', 'legacy-2026-03-10', 'zulu', 'undated'])
            self.assertEqual(page.dates, ['2026-05-02T12:30:00+00:00',
                                         '2026-05-02T06:30:00+00:00', '2026-03-10',
                                         '2026-01-01T00:00:00+00:00'])

    def test_invalid_timestamps_use_ancestor_month_without_inventing_day_or_time(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'published'
            self.bundle(root, 'experiment-2026-09/condition', [True, 1e100, -1e100, None])
            self.bundle(root, 'unknown', [None])
            out = Path(temp) / 'site'
            build(root, out)
            page = IndexEvidence((out / 'index.html').read_text(encoding='utf-8'))
            self.assertEqual(page.dates, ['2026-09'])
            self.assertTrue(page.links[0].endswith('experiment-2026-09/condition/EXPLORER.html'))
            self.assertTrue(page.links[1].endswith('unknown/EXPLORER.html'))
