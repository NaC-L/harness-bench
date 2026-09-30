import tomllib
import unittest
from pathlib import Path
from bench.runner import load_harnesses

ROOT = Path(__file__).resolve().parents[1]


class DescriptorConfigTests(unittest.TestCase):
    def test_harnesses_differ_only_in_overlay_filename(self):
        path = ROOT / 'benchmark-omp-descriptors.toml'
        config = tomllib.loads(path.read_text(encoding='utf-8'))
        self.assertEqual(set(config), {'harnesses'})
        self.assertEqual(list(config['harnesses']), ['omp-baseline', 'omp-inline'])
        baseline = config['harnesses']['omp-baseline']
        inline = config['harnesses']['omp-inline']
        self.assertEqual(set(baseline), {'kind', 'command', 'version_command', 'state_template', 'env_commands'})
        index = baseline['command'].index('--config') + 1
        self.assertEqual(baseline['command'].count('--config'), 1)
        self.assertEqual(inline['command'][index],
                         '{benchmark_dir}/experiments/omp-descriptors/inline.yml')
        self.assertEqual(baseline['command'][index],
                         '{benchmark_dir}/experiments/omp-descriptors/baseline.yml')
        normalized = {**inline, 'command': list(inline['command'])}
        normalized['command'][index] = baseline['command'][index]
        self.assertEqual(baseline, normalized)
        self.assertEqual(list(load_harnesses(path)), ['omp-baseline', 'omp-inline'])

    def test_existing_omp_flags_preserved_without_old_overlay(self):
        reference = tomllib.loads((ROOT / 'benchmark-pi-omp-sol.toml').read_text(encoding='utf-8'))
        expected = reference['harnesses']['omp-sol']
        actual = tomllib.loads((ROOT / 'benchmark-omp-descriptors.toml').read_text(encoding='utf-8'))
        for name, overlay in (('omp-baseline', 'baseline.yml'), ('omp-inline', 'inline.yml')):
            with self.subTest(harness=name):
                command = list(expected['command'])
                command[command.index('--config') + 1] = (
                    '{benchmark_dir}/experiments/omp-descriptors/' + overlay)
                isolation = {'state_template': 'experiments/omp-isolated/agent',
                             'env_commands': {'OPENAI_CODEX_OAUTH_TOKEN': ['omp', 'token', 'openai-codex']}}
                self.assertEqual(actual['harnesses'][name], {**expected, 'command': command, **isolation})
                self.assertNotIn('{benchmark_dir}/.tools/sol-comparison.yml', command)
                self.assertEqual(command[command.index('--model') + 1], 'openai-codex/gpt-6.1-sol')
                self.assertEqual(command[command.index('--thinking') + 1], 'high')
                self.assertEqual(command[command.index('--tools') + 1], 'read,bash,edit,write')
                for flag in ('--no-title', '--no-prewalk', '--no-extensions', '--no-skills', '--no-rules'):
                    self.assertIn(flag, command)

    def test_overlays_only_set_quoted_descriptor_mode(self):
        for filename, mode in (('baseline.yml', 'off'), ('inline.yml', 'on')):
            with self.subTest(overlay=filename):
                text = (ROOT / 'experiments' / 'omp-descriptors' / filename).read_text(encoding='utf-8')
                self.assertEqual(text, f'inlineToolDescriptors: "{mode}"\n')

    def test_isolated_state_template_holds_only_benchmark_settings(self):
        template = ROOT / 'experiments' / 'omp-isolated' / 'agent'
        self.assertEqual(sorted(p.name for p in template.rglob('*')), ['config.yml'])
        text = (template / 'config.yml').read_text(encoding='utf-8')
        self.assertIn('backend: "off"', text)


if __name__ == '__main__':
    unittest.main()
