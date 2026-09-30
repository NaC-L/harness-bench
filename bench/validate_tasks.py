"""Validate that task baselines fail and reference solutions pass, without agents."""

from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path
import sys
import tempfile

if __package__:
    from .tasks import Task, load_task, overlay, run_check
else:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from bench.tasks import Task, load_task, overlay, run_check


TIMEOUT_SEC = 120


def _check(task: Task, *, hidden: bool, solution: bool) -> dict:
    """Run one scenario in its own disposable copy of the starting repository."""
    with tempfile.TemporaryDirectory(prefix=f"harness-bench-{task.id}-") as temporary:
        workdir = Path(temporary) / "repo"
        workdir.mkdir()
        overlay(task.repo, workdir)
        if solution:
            overlay(task.solution, workdir)
        try:
            graded = run_check(
                replace(task, check_timeout_sec=TIMEOUT_SEC),
                workdir,
                include_hidden=hidden,
            )
        except OSError as error:
            return {"returncode": None, "error": str(error)}
        return {
            "returncode": graded.exit_code,
            "output": graded.output,
            "error": f"check exceeded {TIMEOUT_SEC}s" if graded.timed_out else None,
        }


def validate(task_dir: str | Path) -> dict:
    """Return id, ok, errors, and captured checks for one task directory."""
    task_dir = Path(task_dir)
    result = {"id": task_dir.name, "ok": False, "errors": [], "checks": {}}
    try:
        task = load_task(task_dir)
        command = task.check
        if not isinstance(command, list) or not command or not all(
            isinstance(part, str) and part for part in command
        ):
            raise ValueError("task.toml check must be a non-empty array of strings")
        for directory in ("repo", "hidden_tests", "solution"):
            if not (task_dir / directory).is_dir():
                raise ValueError(f"missing directory: {directory}")
        for name, hidden, solution, should_pass in (
            ("visible_baseline", False, False, False),
            ("hidden_baseline", True, False, False),
            ("solution", True, True, True),
        ):
            check = _check(task, hidden=hidden, solution=solution)
            result["checks"][name] = check
            if check["error"]:
                result["errors"].append(f"{name}: {check['error']}")
            elif (check["returncode"] == 0) != should_pass:
                expected = "pass" if should_pass else "fail with a nonzero exit code"
                result["errors"].append(
                    f"{name}: expected to {expected}, got exit {check['returncode']}"
                )
    except (OSError, ValueError, TypeError) as error:
        result["errors"].append(str(error))
    result["ok"] = not result["errors"]
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "tasks_dir",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "tasks",
    )
    args = parser.parse_args()
    if not args.tasks_dir.is_dir():
        print(f"ERROR: tasks directory does not exist: {args.tasks_dir}")
        return 1
    task_dirs = sorted(path for path in args.tasks_dir.iterdir() if path.is_dir())
    if not task_dirs:
        print("ERROR: no tasks found")
        return 1
    failed = False
    for task_dir in task_dirs:
        result = validate(task_dir)
        if result["ok"]:
            checks = result["checks"]
            print(
                f"{result['id']}: OK "
                f"(visible baseline={checks['visible_baseline']['returncode']}, "
                f"hidden baseline={checks['hidden_baseline']['returncode']}, "
                f"solution={checks['solution']['returncode']})"
            )
        else:
            failed = True
            print(f"{result['id']}: FAIL ({'; '.join(result['errors'])})")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
