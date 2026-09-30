import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bench import sessions
from tests.test_sessions import KEYS, STARTED, WORKDIR


class PiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        home_patch = patch.object(sessions, "HOME", self.root / "home")
        home_patch.start()
        self.addCleanup(home_patch.stop)

    def write_records(self, path, records):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(record, ensure_ascii=False) + "\n"
                                for record in records), encoding="utf-8")
        os.utime(path, (STARTED, STARTED))
        return path

    def header(self, cwd=WORKDIR):
        return {"type": "session", "version": 3, "id": "session-id",
                "cwd": str(cwd), "timestamp": "2026-09-30T00:00:00Z"}

    def usage(self, input=10, output=1, cache_read=5, cache_write=1, cost=0.1):
        return {"input": input, "output": output, "cacheRead": cache_read,
                "cacheWrite": cache_write, "cost": {"total": cost}}

    def assistant(self, text="finished", usage=True, **kwargs):
        message = {"role": "assistant", "provider": "anthropic", "model": "sonnet",
                   "content": [{"type": "text", "text": text}], "stopReason": "stop",
                   "timestamp": int(STARTED * 1000)}
        if usage:
            message["usage"] = usage if isinstance(usage, dict) else self.usage()
        message.update(kwargs)
        return message

    def entry(self, entry_id, message, parent_id=None, **kwargs):
        entry = {"type": "message", "id": entry_id, "parentId": parent_id,
                 "timestamp": "2026-09-30T00:00:01Z", "message": message}
        entry.update(kwargs)
        return entry

    def stdout(self, records=None):
        if records is None:
            records = [self.header(), {"type": "message_end", "message": self.assistant()},
                       {"type": "agent_settled"}]
        return self.write_records(self.root / "stdout.jsonl", records)

    def collect(self, **kwargs):
        options = dict(workdir=WORKDIR, session_dir=None, session_id=None,
                       stdout_path=None, started=STARTED, ended=STARTED + 10, env={})
        options.update(kwargs)
        result = sessions.collect("pi", **options)
        self.assertEqual(set(result), KEYS)
        self.assertEqual(result["harness_kind"], "pi")
        self.assertFalse(any("Session collection failed" in error for error in result["errors"]),
                         result["errors"])
        return result

    def test_persisted_usage_tools_warming_summaries_and_abandoned_branches(self):
        first = self.assistant("abandoned branch", timestamp=int((STARTED + 1000) * 1000),
                               duration=99999)
        first["content"].extend([{"type": "toolCall", "id": "call-read", "name": "read"},
                                 {"type": "toolCall", "id": "call-bash", "name": "bash"}])
        second = self.assistant("persisted active branch",
                                usage=self.usage(20, 2, 6, 2, 0.2))
        second["content"].append({"type": "toolCall", "id": "call-write", "name": "write"})
        warm = {"type": "usage", "id": "warm", "kind": "cache_warm", "provider": "anthropic",
                "model": "anthropic/sonnet", "usage": self.usage(2, 3, 7, 3, 0.03)}
        records = [self.header(), {"type": "model_change", "id": "model", "provider": "anthropic",
                                   "modelId": "sonnet"},
                   self.entry("one", first), self.entry("one", first),
                   self.entry("tool-result", {"role": "toolResult", "toolCallId": "call-read",
                                              "toolName": "read", "content": []}),
                   warm, warm,
                   {"type": "compaction", "id": "compact", "usage": self.usage(3, 4, 8, 4, 0.04)},
                   {"type": "branch_summary", "id": "branch", "parentId": None,
                    "fromId": "one", "usage": self.usage(4, 5, 9, 5, 0.05)},
                   self.entry("two", second, parent_id="branch")]
        path = self.write_records(self.root / "explicit" / "nested" / "main.jsonl", records)
        stream_message = self.assistant("chosen stdout final", usage=self.usage(999, 999, 999, 999, 9))
        stdout = self.stdout([self.header(), {"type": "message_end", "message": stream_message},
                              {"type": "agent_settled"}])
        result = self.collect(session_dir=self.root / "explicit", stdout_path=stdout)
        self.assertEqual(result["session_files"], [str(path)])
        self.assertEqual(result["requests"], 2)
        self.assertEqual(result["tool_calls"], 3)
        self.assertEqual(result["single_call_requests"], 1)
        self.assertEqual(result["tool_calls_per_request"], 1.5)
        self.assertEqual(result["tool_histogram"], {"read": 1, "bash": 1, "write": 1})
        self.assertEqual(result["input_tokens"], 39)
        self.assertEqual(result["output_tokens"], 15)
        self.assertEqual(result["cache_read_tokens"], 35)
        self.assertEqual(result["cache_write_tokens"], 15)
        self.assertAlmostEqual(result["cost_usd"], 0.42)
        self.assertEqual(result["auxiliary_calls"], 3)
        self.assertEqual(result["auxiliary_tokens"], 57)
        self.assertAlmostEqual(result["auxiliary_cost_usd"], 0.12)
        self.assertEqual(result["edit_calls"], 1)
        self.assertIsNone(result["verified_after_final_edit"])
        self.assertEqual(result["compactions"], 1)
        self.assertEqual(result["subagent_sessions"], 0)
        self.assertIsNone(result["model_time_sec"])
        self.assertEqual(result["models"], ["anthropic/sonnet"])
        self.assertEqual(result["final_message"], "chosen stdout final")
        self.assertEqual(result["errors"], [])

    def test_stream_fallback_uses_only_authoritative_message_end(self):
        message = self.assistant(duration=1500)
        message["content"].append({"type": "toolCall", "id": "call", "name": "read"})
        inflated = self.assistant("partial", usage=self.usage(999, 999, 999, 999, 9))
        records = [self.header(), {"type": "agent_start"},
                   {"type": "message_start", "message": inflated},
                   {"type": "message_update", "message": inflated, "usage": inflated["usage"],
                    "assistantMessageEvent": {"type": "text_delta", "delta": "partial"}},
                   {"type": "message_end", "message": message},
                   {"type": "turn_end", "message": message, "toolResults": []},
                   {"type": "tool_execution_start", "toolName": "read", "toolCallId": "call"},
                   {"type": "message_end", "message": {"role": "toolResult", "toolName": "read"}},
                   {"type": "agent_end", "messages": [message], "willRetry": False},
                   {"type": "agent_settled"}]
        stdout = self.stdout(records)
        result = self.collect(stdout_path=stdout)
        self.assertEqual(result["requests"], 1)
        self.assertEqual(result["tool_calls"], 1)
        self.assertEqual(result["single_call_requests"], 1)
        self.assertEqual(result["input_tokens"], 10)
        self.assertEqual(result["output_tokens"], 1)
        self.assertEqual(result["cache_read_tokens"], 5)
        self.assertEqual(result["cache_write_tokens"], 1)
        self.assertEqual(result["cost_usd"], 0.1)
        self.assertEqual(result["compactions"], 0)
        self.assertIsNone(result["model_time_sec"])
        self.assertEqual(result["final_message"], "finished")
        self.assertEqual(sessions.pi_completion(stdout), ("completed", []))

    def test_explicit_directory_excludes_other_cwd_and_takes_precedence(self):
        directory = self.root / "explicit"
        accepted = self.write_records(directory / "nested" / "main.jsonl",
                                      [self.header(Path("c:/BENCH/work/")), self.entry("one", self.assistant())])
        self.write_records(directory / "foreign.jsonl",
                           [self.header(Path("C:/other/work")), self.entry("other", self.assistant())])
        self.write_records(directory / "no-header.jsonl", [self.entry("headerless", self.assistant())])
        self.write_records(sessions.HOME / ".pi/agent/sessions/project/extra.jsonl",
                           [self.header(), self.entry("fallback", self.assistant())])
        result = self.collect(session_dir=directory, stdout_path=self.stdout())
        self.assertEqual(result["session_files"], [str(accepted)])
        self.assertEqual(result["requests"], 1)
        self.assertEqual(result["subagent_sessions"], 0)

    def test_unmatched_cwd_does_not_supply_metrics(self):
        directory = self.root / "explicit"
        self.write_records(directory / "foreign.jsonl",
                           [self.header(Path("C:/other/work")), self.entry("one", self.assistant())])
        result = self.collect(session_dir=directory)
        self.assertEqual(result["session_files"], [])
        self.assertIsNone(result["input_tokens"])
        self.assertIsNone(result["requests"])
        self.assertIsNone(result["final_message"])
        self.assertTrue(any("No matching pi" in error for error in result["errors"]))

    def test_fallback_home_matches_cwd_and_file_time(self):
        directory = sessions.HOME / ".pi/agent/sessions/project"
        accepted = self.write_records(directory / "main.jsonl", [self.header(), self.entry("one", self.assistant())])
        old = self.write_records(directory / "old.jsonl", [self.header(), self.entry("old", self.assistant())])
        os.utime(old, (STARTED - 1000, STARTED - 1000))
        self.write_records(directory / "foreign.jsonl", [self.header(Path("C:/elsewhere"))])
        result = self.collect(session_dir=self.root / "empty", stdout_path=self.stdout())
        self.assertEqual(result["session_files"], [str(accepted)])
        self.assertEqual(result["input_tokens"], 10)

    def test_session_directory_override_precedes_agent_state_directory(self):
        direct = self.root / "direct-sessions"
        custom = self.root / "custom-agent"
        accepted = self.write_records(direct / "project/main.jsonl",
                                      [self.header(), self.entry("direct", self.assistant())])
        self.write_records(custom / "sessions/project/main.jsonl",
                           [self.header(), self.entry("state", self.assistant())])
        result = self.collect(stdout_path=self.stdout(), env={"PI_CODING_AGENT_SESSION_DIR": str(direct),
                                                             "PI_CODING_AGENT_DIR": str(custom)})
        self.assertEqual(result["session_files"], [str(accepted)])
        self.assertEqual(result["requests"], 1)

    def test_custom_agent_home_fallback(self):
        custom = self.root / "custom-agent"
        accepted = self.write_records(custom / "sessions/project/main.jsonl",
                                      [self.header(), self.entry("one", self.assistant())])
        result = self.collect(stdout_path=self.stdout(), env={"PI_CODING_AGENT_DIR": str(custom)})
        self.assertEqual(result["session_files"], [str(accepted)])
        self.assertEqual(result["input_tokens"], 10)

    def test_entry_ids_dedupe_session_copies_not_independent_sessions(self):
        directory = self.root / "explicit"
        records = [self.header(), self.entry("shared-entry", self.assistant())]
        self.write_records(directory / "main.jsonl", records)
        self.write_records(directory / "copy.jsonl", records)
        independent_header = self.header()
        independent_header["id"] = "another-session"
        self.write_records(directory / "independent.jsonl",
                           [independent_header, self.entry("shared-entry", self.assistant())])
        result = self.collect(session_dir=directory, stdout_path=self.stdout())
        self.assertEqual(len(result["session_files"]), 3)
        self.assertEqual(result["requests"], 2)
        self.assertEqual(result["input_tokens"], 20)
        self.assertEqual(result["subagent_sessions"], 0)

    def test_provider_and_model_normalization(self):
        records = [self.header(),
                   {"type": "model_change", "id": "model-one", "provider": "anthropic", "modelId": "sonnet"},
                   {"type": "model_change", "id": "model-two", "provider": "anthropic", "modelId": "anthropic/sonnet"},
                   self.entry("one", self.assistant(model="anthropic/sonnet")),
                   self.entry("two", self.assistant(provider="openai", model="gpt")),
                   {"type": "usage", "id": "unknown-kind", "kind": "future_operation", "provider": "google",
                    "model": "gemini", "usage": self.usage()}]
        path = self.write_records(self.root / "explicit/main.jsonl", records)
        result = self.collect(session_dir=path.parent, stdout_path=self.stdout())
        self.assertEqual(result["models"], ["anthropic/sonnet", "openai/gpt", "google/gemini"])
        self.assertEqual(result["requests"], 2)
        self.assertEqual(result["input_tokens"], 30)

    def test_assistants_without_usage_are_not_requests_and_results_are_not_calls(self):
        no_usage = self.assistant(usage=False)
        no_usage["content"].append({"type": "toolCall", "name": "read", "id": "call"})
        path = self.write_records(self.root / "explicit/main.jsonl", [self.header(), self.entry("one", no_usage),
                                  self.entry("result", {"role": "toolResult", "content": [], "toolName": "read"})])
        result = self.collect(session_dir=path.parent, stdout_path=self.stdout())
        self.assertEqual(result["requests"], 0)
        self.assertEqual(result["tool_calls"], 1)
        self.assertEqual(result["single_call_requests"], 0)
        self.assertIsNone(result["tool_calls_per_request"])
        self.assertIsNone(result["input_tokens"])

    def test_unicode_line_separator_is_not_a_record_boundary(self):
        text = "before\u2028after\u2029end"
        path = self.write_records(self.root / "explicit/main.jsonl",
                                  [self.header(), self.entry("one", self.assistant(text))])
        stdout = self.stdout([self.header(), {"type": "message_end", "message": self.assistant(text)},
                              {"type": "agent_settled"}])
        self.assertIn("\u2028", stdout.read_text(encoding="utf-8"))
        result = self.collect(session_dir=path.parent, stdout_path=stdout)
        self.assertEqual(result["input_tokens"], 10)
        self.assertEqual(result["final_message"], text)
        self.assertEqual(result["errors"], [])
        self.assertEqual(sessions.pi_completion(stdout), ("completed", []))

    def test_malformed_session_and_stream_records_preserve_warnings(self):
        path = self.write_records(self.root / "explicit/main.jsonl",
                                  [self.header(), self.entry("one", self.assistant())])
        with path.open("a", encoding="utf-8") as stream:
            stream.write("not json\n[]\n")
        stdout = self.stdout()
        with stdout.open("a", encoding="utf-8") as stream:
            stream.write("{broken\n")
        result = self.collect(session_dir=path.parent, stdout_path=stdout)
        self.assertEqual(result["input_tokens"], 10)
        self.assertIn(f"Ignored 2 malformed record(s) in {path}", result["errors"])
        self.assertIn(f"Ignored 1 malformed record(s) in {stdout}", result["errors"])
        status, diagnostics = sessions.pi_completion(stdout)
        self.assertEqual(status, "completed")
        self.assertEqual(diagnostics, [f"Ignored 1 malformed record(s) in {stdout}"])

    def test_persisted_messages_do_not_choose_final_text_without_stdout(self):
        path = self.write_records(self.root / "explicit/main.jsonl",
                                  [self.header(), self.entry("one", self.assistant("not final evidence"))])
        result = self.collect(session_dir=path.parent)
        self.assertEqual(result["requests"], 1)
        self.assertIsNone(result["final_message"])
        self.assertIsNone(result["model_time_sec"])

    def test_retry_error_then_recovery_is_completed_and_counts_billed_attempts(self):
        error = self.assistant("sensitive error body", stopReason="error", errorMessage="sensitive error")
        good = self.assistant("recovered")
        stdout = self.stdout([self.header(), {"type": "message_end", "message": error},
                              {"type": "agent_end", "messages": [error], "willRetry": True},
                              {"type": "auto_retry_start", "attempt": 1},
                              {"type": "message_end", "message": good},
                              {"type": "auto_retry_end", "success": True},
                              {"type": "agent_settled"}])
        self.assertEqual(sessions.pi_completion(stdout), ("completed", []))
        result = self.collect(stdout_path=stdout)
        self.assertEqual(result["requests"], 2)
        self.assertEqual(result["input_tokens"], 20)
        self.assertEqual(result["final_message"], "recovered")
        self.assertFalse(any("stopped" in error for error in result["errors"]))

    def test_terminal_retry_failure_is_error_without_transcript_diagnostics(self):
        for with_settled in (False, True):
            with self.subTest(with_settled=with_settled):
                records = [self.header(), {"type": "message_end", "message": self.assistant()},
                           {"type": "auto_retry_end", "success": False, "finalError": "private transcript"}]
                if with_settled:
                    records.append({"type": "agent_settled"})
                status, diagnostics = sessions.pi_completion(self.stdout(records))
                self.assertEqual(status, "error")
                self.assertTrue(diagnostics)
                self.assertNotIn("private transcript", " ".join(diagnostics))

    def test_terminal_retry_failure_can_recover_only_with_later_assistant_and_settled(self):
        records = [self.header(), {"type": "auto_retry_end", "success": False, "finalError": "failure"},
                   {"type": "message_end", "message": self.assistant("recovered")}]
        self.assertEqual(sessions.pi_completion(self.stdout(records))[0], "error")
        records.append({"type": "agent_settled"})
        self.assertEqual(sessions.pi_completion(self.stdout(records)), ("completed", []))

    def test_error_and_aborted_final_assistants_are_errors(self):
        for reason in ("error", "aborted"):
            with self.subTest(reason=reason):
                stdout = self.stdout([self.header(), {"type": "message_end", "message": self.assistant(
                    "private message", stopReason=reason, errorMessage="private error")}, {"type": "agent_settled"}])
                status, diagnostics = sessions.pi_completion(stdout)
                self.assertEqual(status, "error")
                self.assertNotIn("private", " ".join(diagnostics))
                result = self.collect(stdout_path=stdout)
                self.assertIsNone(result["final_message"])
                self.assertTrue(any(f"stopped with {reason}" in error for error in result["errors"]))

    def test_missing_final_settled_is_incomplete_even_with_agent_end(self):
        message = self.assistant()
        stdout = self.stdout([self.header(), {"type": "message_end", "message": message},
                              {"type": "agent_end", "messages": [message], "willRetry": False}])
        self.assertEqual(sessions.pi_completion(stdout)[0], "incomplete")

    def test_settled_before_final_assistant_does_not_complete_the_run(self):
        stdout = self.stdout([self.header(), {"type": "agent_settled"},
                              {"type": "message_end", "message": self.assistant()}])
        self.assertEqual(sessions.pi_completion(stdout)[0], "incomplete")

    def test_new_activity_after_settled_is_incomplete(self):
        stdout = self.stdout([self.header(), {"type": "message_end", "message": self.assistant()},
                              {"type": "agent_settled"}, {"type": "agent_start"}])
        self.assertEqual(sessions.pi_completion(stdout)[0], "incomplete")

    def test_missing_empty_partial_and_header_only_streams_are_incomplete(self):
        missing = self.root / "missing.jsonl"
        status, diagnostics = sessions.pi_completion(missing)
        self.assertEqual(status, "incomplete")
        self.assertTrue(any("Cannot read" in error for error in diagnostics))
        for records in ([], [self.header()], [{"type": "agent_settled"}],
                        [{"type": "message_start", "message": self.assistant()}, {"type": "agent_settled"}],
                        [{"type": "message_end", "message": self.assistant(stopReason="pending")},
                         {"type": "agent_settled"}]):
            with self.subTest(records=records):
                self.assertEqual(sessions.pi_completion(self.stdout(records))[0], "incomplete")

    def test_stream_final_text_is_truncated(self):
        stdout = self.stdout([self.header(), {"type": "message_end", "message": self.assistant("x" * 4500)},
                              {"type": "agent_settled"}])
        self.assertEqual(len(self.collect(stdout_path=stdout)["final_message"]), 4000)


if __name__ == "__main__":
    unittest.main()
