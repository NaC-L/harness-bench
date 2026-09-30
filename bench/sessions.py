"""Read-only session adapters. Unknown measurements remain None, never invented.

HOME is injectable for isolated tests. Codex request counts approximate assistant
turns using token_count events with non-null info, not HTTP request counts.
"""
from __future__ import annotations

import json
import math
import os
import posixpath
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from .environment import state_dir

HOME = Path.home()


def _empty(kind: str) -> dict:
    return {
        "harness_kind": kind, "session_files": [], "models": [],
        "requests": None, "tool_calls": None, "tool_calls_per_request": None,
        "single_call_requests": None, "tool_histogram": {},
        "input_tokens": None, "output_tokens": None, "cache_read_tokens": None,
        "cache_write_tokens": None, "cost_usd": None, "model_time_sec": None,
        "compactions": None, "subagent_sessions": 0, "final_message": None,
        "auxiliary_calls": None, "auxiliary_tokens": None, "auxiliary_cost_usd": None,
        "edit_calls": None, "verified_after_final_edit": None,
        "reproduced_before_first_edit": None,
        "errors": [],
    }


def _number(value):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if math.isfinite(value) and value >= 0:
            return value
    return None


def _add(out: dict, key: str, value) -> None:
    value = _number(value)
    if value is not None:
        out[key] = (out[key] or 0) + value


def _mapping(value) -> dict:
    return value if isinstance(value, dict) else {}


def _records(path: Path, errors: list):
    malformed = 0
    try:
        with path.open(encoding="utf-8-sig", errors="replace") as stream:
            for line in stream:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except (ValueError, RecursionError):
                    malformed += 1
                    continue
                if isinstance(record, dict):
                    yield record
                else:
                    malformed += 1
    except OSError as exc:
        errors.append(f"Cannot read {path}: {exc}")
    if malformed:
        errors.append(f"Ignored {malformed} malformed record(s) in {path}")


def _cwd(value) -> str:
    return posixpath.normpath(str(value).replace("\\", "/")).casefold()


def _timestamp(value):
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
        except (ValueError, OverflowError, OSError):
            return None
    number = _number(value)
    return number / 1000 if number is not None and number > 1e11 else number


def _text(content) -> str | None:
    if isinstance(content, str):
        return content[:4000] if content else None
    if isinstance(content, list):
        text = "".join(b["text"] for b in content if isinstance(b, dict)
                       and b.get("type") in ("text", "output_text")
                       and isinstance(b.get("text"), str))
        return text[:4000] if text else None
    return None


def _model(out: dict, name) -> None:
    if isinstance(name, str) and name and name not in out["models"]:
        out["models"].append(name)


def _header(path: Path, record_type: str, errors: list) -> dict:
    for record in _records(path, errors):
        if record.get("type") == record_type:
            return record
    return {}


def _omp_files(workdir, session_dir, started, ended, errors, env):
    if session_dir is not None:
        root = Path(session_dir)
        files = sorted(root.rglob("*.jsonl"))
        if files:
            return [(p, p.parent != root) for p in files]
    root = state_dir("omp", env, HOME) / "sessions"
    found = []
    for path in sorted(root.glob("*/*.jsonl")):
        try:
            if not started - 60 <= path.stat().st_mtime <= ended + 60:
                continue
        except OSError as exc:
            errors.append(f"Cannot stat {path}: {exc}")
            continue
        header = _header(path, "session", errors)
        if header.get("cwd") is not None and _cwd(header["cwd"]) == _cwd(workdir):
            found.append((path, False))
            found.extend((p, True) for p in sorted(path.with_suffix("").rglob("*.jsonl")))
    return found


def _auxiliary(out, usage, cost) -> None:
    """Count side-model usage (judges, summaries); totals already include it."""
    out["auxiliary_calls"] += 1
    out["auxiliary_tokens"] += sum(_number(usage.get(k)) or 0
                                   for k in ("input", "output", "cacheRead", "cacheWrite"))
    _add(out, "auxiliary_cost_usd", cost)


def _tool_calls(calls) -> list[tuple]:
    return [(b.get("name"), args.get("command") if isinstance(args := b.get("arguments"), dict) else None)
            for b in calls]


def _verification(out, calls, check_command) -> None:
    """Did the agent run the task's check command before its first and after its last edit?"""
    needle = " ".join(check_command or [])
    edits = [i for i, (name, _) in enumerate(calls) if name in ("edit", "write")]
    checks = [i for i, (name, command) in enumerate(calls)
              if name == "bash" and isinstance(command, str) and needle in command]
    out["edit_calls"] = len(edits)
    if not check_command or not edits:
        return
    out["verified_after_final_edit"] = any(i > edits[-1] for i in checks)
    out["reproduced_before_first_edit"] = any(i < edits[0] for i in checks)


def _omp(out, files, check_command=None):
    out.update(requests=0, tool_calls=0, single_call_requests=0, compactions=0,
               auxiliary_calls=0, auxiliary_tokens=0, edit_calls=0)
    sequence = []
    histogram = Counter()
    last_time = float("-inf")
    for path, subagent in files:
        out["session_files"].append(str(path))
        out["subagent_sessions"] += int(subagent)
        for record in _records(path, out["errors"]):
            kind = record.get("type")
            msg = _mapping(record.get("message"))
            usage = msg.get("usage")
            if not isinstance(usage, dict):
                usage = record.get("usage")
            if kind == "compaction":
                out["compactions"] += 1
            if kind in ("model_change", "model_usage"):
                _model(out, record.get("model"))
            if isinstance(usage, dict):
                for source, target in (("input", "input_tokens"), ("output", "output_tokens"),
                                       ("cacheRead", "cache_read_tokens"),
                                       ("cacheWrite", "cache_write_tokens")):
                    _add(out, target, usage.get(source))
                cost = usage.get("cost")
                cost = cost.get("total") if isinstance(cost, dict) else cost
                _add(out, "cost_usd", cost)
                if kind == "model_usage":
                    _auxiliary(out, usage, cost)
                _model(out, msg.get("model") or record.get("model"))
            if kind != "message" or msg.get("role") != "assistant":
                continue
            if isinstance(usage, dict):
                out["requests"] += 1
            calls = [b for b in (msg.get("content") or []) if isinstance(b, dict)
                     and b.get("type") == "toolCall"] if isinstance(msg.get("content"), list) else []
            out["tool_calls"] += len(calls)
            if not subagent:
                sequence.extend(_tool_calls(calls))
            if isinstance(usage, dict) and len(calls) == 1:
                out["single_call_requests"] += 1
            histogram.update(str(b.get("name") or "unknown") for b in calls)
            duration = _number(msg.get("duration"))
            if duration is not None:
                _add(out, "model_time_sec", duration / 1000)
            text = _text(msg.get("content"))
            ts = _timestamp(msg.get("timestamp") or record.get("timestamp"))
            if not subagent and text and (ts is None or ts >= last_time):
                out["final_message"] = text
                if ts is not None:
                    last_time = ts
    out["tool_histogram"] = dict(histogram)
    _verification(out, sequence, check_command)


def _pi_files(workdir, session_dir, started, ended, errors, env):
    if session_dir is not None:
        found = []
        for path in sorted(Path(session_dir).rglob("*.jsonl")):
            header = _header(path, "session", errors)
            if header.get("cwd") is not None and _cwd(header["cwd"]) == _cwd(workdir):
                found.append(path)
        if found:
            return found
    override = env.get("PI_CODING_AGENT_SESSION_DIR")
    root = Path(override) if override else state_dir("pi", env, HOME) / "sessions"
    found = []
    for path in sorted(root.rglob("*.jsonl")):
        try:
            if not started - 60 <= path.stat().st_mtime <= ended + 60:
                continue
        except OSError as exc:
            errors.append(f"Cannot stat {path}: {exc}")
            continue
        header = _header(path, "session", errors)
        if header.get("cwd") is not None and _cwd(header["cwd"]) == _cwd(workdir):
            found.append(path)
    return found


def _pi_model(out, provider, model):
    if isinstance(model, str) and model:
        if isinstance(provider, str) and provider and not model.startswith(provider + "/"):
            model = provider + "/" + model
        _model(out, model)


def _stream_completion(records, label: str, terminal: str):
    last = None
    last_index = -1
    retry_failure = -1
    settled = False
    for index, record in enumerate(records):
        kind = record.get("type")
        if kind in ("agent_start", "turn_start", "message_start", "message_update",
                    "auto_retry_start"):
            settled = False
        if kind == "message_end":
            message = _mapping(record.get("message"))
            if message.get("role") == "assistant":
                last = message
                last_index = index
                settled = False
        elif kind == "auto_retry_end" and record.get("success") is False:
            retry_failure = index
            settled = False
        elif kind == terminal:
            settled = True
    if retry_failure >= last_index and retry_failure >= 0:
        return "error", [f"{label} automatic retry ended unsuccessfully"], last
    if last is not None and last.get("stopReason") in ("error", "aborted"):
        return "error", [f"{label} final assistant stopped with {last['stopReason']}"], last
    if last is None or last.get("stopReason") in (None, "pending"):
        return "incomplete", [f"{label} stream has no completed final assistant message"], last
    if not settled:
        if retry_failure >= 0:
            return "error", [f"{label} automatic retry failure has no settled recovery"], last
        return "incomplete", [f"{label} stream is missing final {terminal}"], last
    return "completed", [], last


def _file_completion(stdout_path: Path, label: str, terminal: str) -> tuple[str, list[str]]:
    errors = []
    records = list(_records(Path(stdout_path), errors))
    status, diagnostics, _ = _stream_completion(records, label, terminal)
    return status, errors + diagnostics


def pi_completion(stdout_path: Path) -> tuple[str, list[str]]:
    """Check terminal JSON events without exposing message or error contents."""
    return _file_completion(stdout_path, "Pi", "agent_settled")


def omp_completion(stdout_path: Path) -> tuple[str, list[str]]:
    """OMP `--mode json` emits the same events as Pi but ends with agent_end."""
    return _file_completion(stdout_path, "OMP", "agent_end")


def stream_retries(stdout_path: Path) -> int:
    """Number of automatic provider retries announced in a JSON event stream."""
    return sum(record.get("type") == "auto_retry_start"
               for record in _records(Path(stdout_path), []))


def _pi_usage(out, usage):
    for source, target in (("input", "input_tokens"), ("output", "output_tokens"),
                           ("cacheRead", "cache_read_tokens"),
                           ("cacheWrite", "cache_write_tokens")):
        _add(out, target, usage.get(source))
    _add(out, "cost_usd", _mapping(usage.get("cost")).get("total"))


def _pi(out, files, stdout_path, check_command=None):
    stream = list(_records(Path(stdout_path), out["errors"])) if stdout_path is not None else []
    status, diagnostics, last = _stream_completion(stream, "Pi", "agent_settled")
    if status != "completed":
        out["errors"].extend(diagnostics)
    if last is not None and last.get("stopReason") not in (None, "pending", "error", "aborted"):
        out["final_message"] = _text(last.get("content"))
    if not files and not stream:
        return
    out.update(requests=0, tool_calls=0, single_call_requests=0, compactions=0,
               auxiliary_calls=0, auxiliary_tokens=0, edit_calls=0)
    sequence = []
    histogram = Counter()
    sources = [(path, _records(path, out["errors"])) for path in files]
    if not files:
        sources = [(None, ({"type": "message", "id": record.get("id"),
                           "message": record.get("message")} for record in stream
                          if record.get("type") == "message_end"))]
    seen = set()
    for path, records in sources:
        if path is not None:
            out["session_files"].append(str(path))
        session_scope = str(path)
        for record in records:
            kind = record.get("type")
            if kind == "session":
                if isinstance(record.get("id"), str):
                    session_scope = record["id"]
                continue
            entry_id = record.get("id")
            if isinstance(entry_id, str):
                key = (session_scope, entry_id)
                if key in seen:
                    continue
                seen.add(key)
            if kind == "model_change":
                _pi_model(out, record.get("provider"), record.get("modelId"))
            if kind == "compaction":
                out["compactions"] += 1
            if kind in ("usage", "compaction", "branch_summary"):
                usage = record.get("usage")
                if isinstance(usage, dict):
                    _pi_usage(out, usage)
                    _auxiliary(out, usage, _mapping(usage.get("cost")).get("total"))
                _pi_model(out, record.get("provider"), record.get("model"))
            message = _mapping(record.get("message"))
            if kind != "message" or message.get("role") != "assistant":
                continue
            _pi_model(out, message.get("provider"), message.get("model"))
            usage = message.get("usage")
            if isinstance(usage, dict):
                _pi_usage(out, usage)
                out["requests"] += 1
            content = message.get("content")
            calls = [block for block in content if isinstance(block, dict)
                     and block.get("type") == "toolCall"] if isinstance(content, list) else []
            out["tool_calls"] += len(calls)
            sequence.extend(_tool_calls(calls))
            if isinstance(usage, dict) and len(calls) == 1:
                out["single_call_requests"] += 1
            histogram.update(str(block.get("name") or "unknown") for block in calls)
    out["tool_histogram"] = dict(histogram)
    _verification(out, sequence, check_command)


def _claude_files(workdir, session_dir, session_id, env):
    if not session_id:
        return []
    root = Path(session_dir) if session_dir is not None else state_dir("claude", env, HOME) / "projects"
    slug = re.sub(r"[^a-zA-Z0-9]", "-", str(workdir))
    preferred = [root / slug / f"{session_id}.jsonl", root / f"{session_id}.jsonl"]
    path = next((p for p in preferred if p.is_file()), None)
    mains = [path] if path else sorted(root.glob(f"*/{session_id}.jsonl"))
    found = []
    for main in mains:
        found.append((main, False))
        found.extend((p, True) for p in sorted((main.parent / session_id / "subagents").rglob("*.jsonl")))
    return found


def _claude(out, files, stdout_path):
    groups = {}
    histogram = Counter()
    last_time = float("-inf")
    if files:
        out.update(requests=0, tool_calls=0, single_call_requests=0, compactions=0)
    for path, subagent in files:
        out["session_files"].append(str(path))
        out["subagent_sessions"] += int(subagent)
        for index, record in enumerate(_records(path, out["errors"])):
            if record.get("type") == "system" and record.get("subtype") == "compact_boundary":
                out["compactions"] += 1
            if record.get("type") != "assistant":
                continue
            msg = _mapping(record.get("message"))
            _model(out, msg.get("model"))
            key = (str(path), msg.get("id") or record.get("uuid") or index)
            group = groups.setdefault(key, {"usage": {}, "calls": set()})
            for token, value in _mapping(msg.get("usage")).items():
                number = _number(value)
                if number is not None:
                    # Repeated blocks can contain progressively updated output usage.
                    group["usage"][token] = max(group["usage"].get(token, 0), number)
            content = msg.get("content")
            if isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict) or block.get("type") != "tool_use":
                        continue
                    call_id = block.get("id") or json.dumps(block, sort_keys=True)
                    if call_id not in group["calls"]:
                        group["calls"].add(call_id)
                        histogram[str(block.get("name") or "unknown")] += 1
            text = _text(content)
            ts = _timestamp(record.get("timestamp"))
            if not subagent and text and (ts is None or ts >= last_time):
                out["final_message"] = text
                if ts is not None:
                    last_time = ts
    if files:
        out["requests"] = len(groups)
        out["tool_calls"] = sum(histogram.values())
        out["single_call_requests"] = sum(len(g["calls"]) == 1 for g in groups.values())
        out["tool_histogram"] = dict(histogram)
    for group in groups.values():
        for source, target in (("input_tokens", "input_tokens"), ("output_tokens", "output_tokens"),
                               ("cache_read_input_tokens", "cache_read_tokens"),
                               ("cache_creation_input_tokens", "cache_write_tokens")):
            _add(out, target, group["usage"].get(source))
    if stdout_path is not None:
        for record in _records(Path(stdout_path), out["errors"]):
            if record.get("type") != "result":
                continue
            cost = _number(record.get("total_cost_usd"))
            if cost is not None:
                out["cost_usd"] = cost
            duration = _number(record.get("duration_api_ms"))
            if duration is not None:
                out["model_time_sec"] = duration / 1000
            if out["requests"] is None:
                out["requests"] = _number(record.get("num_turns"))
            if out["final_message"] is None:
                out["final_message"] = _text(record.get("result"))


def _codex_files(workdir, session_dir, started, ended, errors, env):
    root = Path(session_dir) if session_dir is not None else state_dir("codex", env, HOME) / "sessions"
    found = []
    for path in sorted(root.rglob("rollout-*.jsonl")):
        record = _header(path, "session_meta", errors)
        meta = _mapping(record.get("payload"))
        ts = _timestamp(meta.get("timestamp") or record.get("timestamp"))
        if meta.get("cwd") is not None and _cwd(meta["cwd"]) == _cwd(workdir):
            if ts is not None and started - 60 <= ts <= ended + 60:
                found.append((path, False))
    return found


def _codex(out, files):
    out.update(requests=0, tool_calls=0, compactions=0)
    histogram = Counter()
    last_time = float("-inf")
    for path, subagent in files:
        out["session_files"].append(str(path))
        last_usage = None
        for record in _records(path, out["errors"]):
            payload = _mapping(record.get("payload"))
            kind = payload.get("type")
            if record.get("type") == "turn_context":
                _model(out, payload.get("model"))
            if record.get("type") == "event_msg":
                if kind == "token_count" and isinstance(payload.get("info"), dict):
                    # Approximate assistant turns; not a precise HTTP request count.
                    out["requests"] += 1
                    usage = payload["info"].get("total_token_usage")
                    if isinstance(usage, dict):
                        last_usage = usage
                if kind == "context_compacted":
                    out["compactions"] += 1
                if kind == "task_complete":
                    text = _text(payload.get("last_agent_message"))
                    ts = _timestamp(record.get("timestamp"))
                    if text and (ts is None or ts >= last_time):
                        out["final_message"] = text
                        if ts is not None:
                            last_time = ts
            if record.get("type") == "response_item" and kind in (
                    "function_call", "custom_tool_call", "local_shell_call"):
                out["tool_calls"] += 1
                histogram[str(payload.get("name") or ("local_shell" if kind == "local_shell_call" else "unknown"))] += 1
        if last_usage is not None:
            cached = _number(last_usage.get("cached_input_tokens"))
            inputs = _number(last_usage.get("input_tokens"))
            if inputs is not None and cached is not None:
                _add(out, "input_tokens", max(0, inputs - cached))
            _add(out, "cache_read_tokens", cached)
            _add(out, "output_tokens", last_usage.get("output_tokens"))
    out["tool_histogram"] = dict(histogram)


def collect(kind: str, *, workdir: Path, session_dir: Path | None,
            session_id: str | None, stdout_path: Path | None,
            started: float, ended: float, env: dict[str, str] | None = None,
            check_command: list[str] | None = None) -> dict:
    """Collect normalized metrics without executing a harness or modifying files."""
    out = _empty(kind)
    try:
        env = dict(os.environ) if env is None else env
        if kind == "none":
            return out
        if kind == "omp":
            files = _omp_files(workdir, session_dir, started, ended, out["errors"], env)
            if files:
                _omp(out, files, check_command)
        elif kind == "pi":
            files = _pi_files(workdir, session_dir, started, ended, out["errors"], env)
            _pi(out, files, stdout_path, check_command)
        elif kind == "claude":
            files = _claude_files(workdir, session_dir, session_id, env)
            _claude(out, files, stdout_path)
        elif kind == "codex":
            files = _codex_files(workdir, session_dir, started, ended, out["errors"], env)
            if files:
                _codex(out, files)
        else:
            out["errors"].append(f"Unsupported harness kind: {kind}")
            return out
        if not files:
            out["errors"].append(f"No matching {kind} session files found")
        if out["requests"] and out["tool_calls"] is not None:
            out["tool_calls_per_request"] = out["tool_calls"] / out["requests"]
    except Exception as exc:
        out["errors"].append(f"Session collection failed ({type(exc).__name__}): {exc}")
    return out
