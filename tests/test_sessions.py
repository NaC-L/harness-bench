import json
import os
import shutil
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from bench import sessions

FIXTURES = Path(__file__).parent / "fixtures"
STARTED = datetime.fromisoformat("2026-09-30T00:00:00+00:00").timestamp()
WORKDIR = Path("C:/bench/work")
KEYS = {
    "harness_kind", "session_files", "models", "requests", "tool_calls",
    "tool_calls_per_request", "single_call_requests", "tool_histogram",
    "input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens",
    "cost_usd", "model_time_sec", "compactions", "subagent_sessions",
    "final_message", "errors", "auxiliary_calls", "auxiliary_tokens",
    "auxiliary_cost_usd", "edit_calls", "verified_after_final_edit",
    "reproduced_before_first_edit",
}


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home_patch = patch.object(sessions, "HOME", self.root / "home")
        self.home_patch.start()
        self.addCleanup(self.home_patch.stop)

    def fixture(self, name, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(FIXTURES / name, path)
        return path

    def collect(self, kind, **kwargs):
        options = dict(workdir=WORKDIR, session_dir=None, session_id=None,
                       stdout_path=None, started=STARTED, ended=STARTED + 10, env={})
        options.update(kwargs)
        result = sessions.collect(kind, **options)
        self.assertEqual(set(result), KEYS)
        return result

    def test_omp_usage_side_model_children_and_compaction(self):
        directory = self.root / "explicit"
        self.fixture("omp-main.jsonl", directory / "main.jsonl")
        self.fixture("omp-child.jsonl", directory / "main" / "worker.jsonl")
        result = self.collect("omp", session_dir=directory)
        self.assertEqual(result["requests"], 3)
        self.assertEqual(result["tool_calls"], 4)
        self.assertEqual(result["tool_calls_per_request"], 4 / 3)
        self.assertEqual(result["single_call_requests"], 2)
        self.assertEqual(result["tool_histogram"], {"read": 2, "bash": 1, "write": 1})
        self.assertEqual(result["input_tokens"], 40)
        self.assertEqual(result["output_tokens"], 10)
        self.assertEqual(result["cache_read_tokens"], 14)
        self.assertEqual(result["cache_write_tokens"], 4)
        self.assertAlmostEqual(result["cost_usd"], 0.4)
        self.assertEqual(result["model_time_sec"], 1.75)
        self.assertEqual(result["compactions"], 1)
        self.assertEqual(result["subagent_sessions"], 1)
        self.assertEqual(set(result["models"]), {"primary", "judge", "worker"})
        self.assertEqual(result["final_message"], "main finished")
        self.assertEqual(len(result["session_files"]), 2)
        self.assertTrue(any("malformed" in error for error in result["errors"]))
        self.assertEqual(result["auxiliary_calls"], 1)
        self.assertEqual(result["auxiliary_tokens"], 6)
        self.assertAlmostEqual(result["auxiliary_cost_usd"], 0.03)
        self.assertEqual(result["edit_calls"], 0)
        self.assertIsNone(result["verified_after_final_edit"])
        self.assertIsNone(result["reproduced_before_first_edit"])

    def omp_session(self, calls):
        def assistant(*blocks):
            return {"type": "message", "message": {"role": "assistant", "content": list(blocks)}}

        def call(name, command=None):
            return {"type": "toolCall", "name": name,
                    "arguments": {"command": command} if command else {"path": "src/x.js"}}
        records = [{"type": "session", "cwd": str(WORKDIR)}]
        records += [assistant(call(*c)) for c in calls]
        records.append(assistant({"type": "text", "text": "done"}))
        path = self.root / "verify" / "main.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
        return path.parent

    def test_omp_verification_signals_follow_check_command_around_edits(self):
        full = [("bash", "node --test"), ("edit",), ("bash", "cd x && node --test")]
        cases = [(full, ["node", "--test"], True, True),
                 (full[:2], ["node", "--test"], False, True),
                 (full, None, None, None)]
        for calls, check, verified, reproduced in cases:
            with self.subTest(calls=len(calls), check=check):
                result = self.collect("omp", session_dir=self.omp_session(calls), check_command=check)
                self.assertEqual(result["edit_calls"], 1)
                self.assertEqual(result["verified_after_final_edit"], verified)
                self.assertEqual(result["reproduced_before_first_edit"], reproduced)

    def write_stream(self, records):
        path = self.root / "stdout.jsonl"
        path.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
        return path

    def test_omp_completion_requires_final_agent_end(self):
        def end(reason="stop"):
            return {"type": "message_end", "message": {"role": "assistant", "stopReason": reason}}
        cases = [([end(), {"type": "agent_end"}], ("completed", [])),
                 ([end()], ("incomplete", ["OMP stream is missing final agent_end"])),
                 ([end("error"), {"type": "agent_end"}],
                  ("error", ["OMP final assistant stopped with error"])),
                 ([end(), {"type": "auto_retry_end", "success": False}, {"type": "agent_end"}],
                  ("error", ["OMP automatic retry ended unsuccessfully"]))]
        for records, expected in cases:
            with self.subTest(records=records):
                self.assertEqual(sessions.omp_completion(self.write_stream(records)), expected)

    def test_stream_retries_counts_retry_starts(self):
        path = self.write_stream([{"type": "auto_retry_start"}, {"type": "auto_retry_end", "success": True},
                                  {"type": "auto_retry_start"}])
        self.assertEqual(sessions.stream_retries(path), 2)
        self.assertEqual(sessions.stream_retries(self.root / "missing.jsonl"), 0)

    def test_omp_empty_explicit_directory_falls_back_by_cwd_and_mtime(self):
        directory = sessions.HOME / ".omp" / "agent" / "sessions" / "project"
        path = self.fixture("omp-main.jsonl", directory / "main.jsonl")
        os.utime(path, (STARTED, STARTED))
        child = self.fixture("omp-child.jsonl", directory / "main" / "worker.jsonl")
        rejected = self.fixture("omp-main.jsonl", directory / "wrong-cwd.jsonl")
        rejected.write_text(rejected.read_text().replace("bench", "other"), encoding="utf-8")
        os.utime(rejected, (STARTED, STARTED))
        old = self.fixture("omp-main.jsonl", directory / "old.jsonl")
        os.utime(old, (STARTED - 1000, STARTED - 1000))
        result = self.collect("omp", session_dir=self.root / "empty",
                              workdir=Path("c:/BENCH/work/"))
        self.assertEqual(set(result["session_files"]), {str(path), str(child)})

    def test_omp_explicit_sessions_take_precedence(self):
        self.fixture("omp-main.jsonl", self.root / "explicit" / "main.jsonl")
        fallback = self.fixture("omp-main.jsonl", sessions.HOME / ".omp/agent/sessions/p/extra.jsonl")
        os.utime(fallback, (STARTED, STARTED))
        result = self.collect("omp", session_dir=self.root / "explicit")
        self.assertEqual(len(result["session_files"]), 1)
        self.assertEqual(result["input_tokens"], 33)

    def claude_layout(self):
        project = sessions.HOME / ".claude" / "projects" / "C--bench-work"
        self.fixture("claude-main.jsonl", project / "sid.jsonl")
        self.fixture("claude-child.jsonl", project / "sid" / "subagents" / "child.jsonl")
        stdout = self.fixture("claude-stdout.jsonl", self.root / "stdout.jsonl")
        return project, stdout

    def test_claude_message_and_block_dedupe_and_result(self):
        _, stdout = self.claude_layout()
        result = self.collect("claude", session_id="sid", stdout_path=stdout)
        self.assertEqual(result["requests"], 3)
        self.assertEqual(result["tool_calls"], 3)
        self.assertEqual(result["single_call_requests"], 1)
        self.assertEqual(result["tool_calls_per_request"], 1)
        self.assertEqual(result["tool_histogram"], {"Read": 2, "Bash": 1})
        self.assertEqual(result["input_tokens"], 16)
        self.assertEqual(result["output_tokens"], 8)
        self.assertEqual(result["cache_read_tokens"], 8)
        self.assertEqual(result["cache_write_tokens"], 2)
        self.assertEqual(result["cost_usd"], 0.42)
        self.assertEqual(result["model_time_sec"], 2.5)
        self.assertEqual(result["compactions"], 1)
        self.assertEqual(result["subagent_sessions"], 1)
        self.assertEqual(result["final_message"], "claude finished")
        self.assertEqual(set(result["models"]), {"claude-model", "child-model"})

    def test_claude_slug_fallback(self):
        project, _ = self.claude_layout()
        renamed = project.with_name("unexpected-slug")
        project.rename(renamed)
        result = self.collect("claude", session_id="sid")
        self.assertEqual(result["requests"], 3)
        self.assertTrue(all("unexpected-slug" in path for path in result["session_files"]))
        self.assertIsNone(result["cost_usd"])

    def test_claude_result_only_fallback_and_unknown_api_duration(self):
        stdout = self.fixture("claude-stdout.jsonl", self.root / "stdout.jsonl")
        data = stdout.read_text().replace(',"duration_api_ms":2500', '')
        stdout.write_text(data, encoding="utf-8")
        result = self.collect("claude", session_id="missing", stdout_path=stdout)
        self.assertEqual(result["final_message"], "stdout fallback")
        self.assertEqual(result["requests"], 9)
        self.assertEqual(result["cost_usd"], 0.42)
        self.assertIsNone(result["model_time_sec"])
        self.assertTrue(result["errors"])

    def test_codex_last_totals_cached_input_and_matching_cwd(self):
        directory = sessions.HOME / ".codex" / "sessions" / "2026" / "09" / "30"
        accepted = self.fixture("codex-main.jsonl", directory / "rollout-main.jsonl")
        wrong = self.fixture("codex-main.jsonl", directory / "rollout-wrong.jsonl")
        wrong.write_text(wrong.read_text().replace("BENCH", "OTHER"), encoding="utf-8")
        old = self.fixture("codex-main.jsonl", directory / "rollout-old.jsonl")
        old.write_text(old.read_text().replace("2026-09-30", "2026-09-29"), encoding="utf-8")
        result = self.collect("codex")
        self.assertEqual(result["session_files"], [str(accepted)])
        self.assertEqual(result["input_tokens"], 110)
        self.assertEqual(result["cache_read_tokens"], 70)
        self.assertEqual(result["output_tokens"], 12)
        self.assertIsNone(result["cache_write_tokens"])
        self.assertIsNone(result["cost_usd"])
        self.assertIsNone(result["model_time_sec"])
        self.assertIsNone(result["single_call_requests"])
        self.assertEqual(result["requests"], 2)
        self.assertEqual(result["tool_calls"], 3)
        self.assertEqual(result["tool_histogram"], {"exec_command": 1, "apply_patch": 1, "local_shell": 1})
        self.assertEqual(result["models"], ["codex-model"])
        self.assertEqual(result["final_message"], "codex finished")

    def test_codex_explicit_directory(self):
        self.fixture("codex-main.jsonl", self.root / "explicit" / "rollout-main.jsonl")
        result = self.collect("codex", session_dir=self.root / "explicit")
        self.assertEqual(result["requests"], 2)

    def test_state_directory_overrides(self):
        codex = self.root / "custom-codex"
        codex_file = self.fixture("codex-main.jsonl", codex / "sessions/2026/09/30/rollout-main.jsonl")
        result = self.collect("codex", env={"CODEX_HOME": str(codex)})
        self.assertEqual(result["input_tokens"], 110)
        self.assertEqual(result["errors"], [f"Ignored 1 malformed record(s) in {codex_file}"])

        claude = self.root / "custom-claude"
        claude_file = self.fixture("claude-main.jsonl", claude / "projects/C--bench-work/sid.jsonl")
        result = self.collect("claude", session_id="sid", env={"CLAUDE_CONFIG_DIR": str(claude)})
        self.assertEqual(result["requests"], 2)
        self.assertEqual(result["errors"], [f"Ignored 1 malformed record(s) in {claude_file}"])

        omp = self.root / "custom-omp"
        path = self.fixture("omp-main.jsonl", omp / "sessions/project/main.jsonl")
        os.utime(path, (STARTED, STARTED))
        result = self.collect("omp", env={"PI_CODING_AGENT_DIR": str(omp)})
        self.assertEqual(result["input_tokens"], 33)
        self.assertEqual(result["session_files"], [str(path)])

    def test_none_has_unknown_metrics_and_no_files(self):
        result = self.collect("none")
        for key in KEYS - {"harness_kind", "session_files", "models", "tool_histogram",
                           "subagent_sessions", "errors"}:
            self.assertIsNone(result[key], key)
        self.assertEqual(result["session_files"], [])
        self.assertEqual(result["models"], [])
        self.assertEqual(result["tool_histogram"], {})
        self.assertEqual(result["subagent_sessions"], 0)
        self.assertEqual(result["errors"], [])

    def test_missing_files_never_raise(self):
        for kind in ("omp", "claude", "codex"):
            with self.subTest(kind=kind):
                result = self.collect(kind, session_id="missing")
                self.assertTrue(result["errors"])
                self.assertEqual(result["session_files"], [])
                self.assertIsNone(result["input_tokens"])

    def test_invalid_kind_and_access_failure_never_raise(self):
        self.assertTrue(self.collect("unknown")["errors"])
        with patch.object(sessions, "_omp_files", side_effect=PermissionError("denied")):
            result = self.collect("omp")
        self.assertTrue(any("denied" in error for error in result["errors"]))

    def test_zero_requests_does_not_divide_by_zero(self):
        path = self.root / "explicit" / "main.jsonl"
        path.parent.mkdir()
        path.write_text(json.dumps({"type": "session", "cwd": str(WORKDIR)}) + "\n", encoding="utf-8")
        result = self.collect("omp", session_dir=path.parent)
        self.assertEqual(result["requests"], 0)
        self.assertIsNone(result["tool_calls_per_request"])
        self.assertIsNone(result["input_tokens"])

    def test_final_message_is_truncated(self):
        path = self.root / "explicit" / "main.jsonl"
        path.parent.mkdir()
        path.write_text(json.dumps({"type": "message", "message": {
            "role": "assistant", "content": [{"type": "text", "text": "x" * 4500}]
        }}) + "\n", encoding="utf-8")
        result = self.collect("omp", session_dir=path.parent)
        self.assertEqual(len(result["final_message"]), 4000)


if __name__ == "__main__":
    unittest.main()
