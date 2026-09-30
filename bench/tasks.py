"""Task loading, workspace materialization and grading.

Layout of `tasks/<id>/`:
  task.toml      id, title, category, timeout_sec, check (argv), check_timeout_sec (optional)
  prompt.md      exact instructions handed to the agent
  repo/          starting repository copied into the agent workdir
  hidden_tests/  overlaid onto <workdir>/test/ before grading (restores tampered visible tests too)
  solution/      reference overlay that must make every test pass (validation only)
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import stat
import subprocess
import tempfile
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from .process import group_options, kill_tree

# Files the agent is told not to touch; any change is reported as tampering.
PROTECTED_GLOBS = ("test/**/*", "package.json")


@dataclass
class Task:
    id: str
    dir: Path
    title: str
    category: str
    prompt: str
    timeout_sec: int
    check: list[str]
    check_timeout_sec: int = 120
    tags: list[str] = field(default_factory=list)

    @property
    def repo(self) -> Path:
        return self.dir / "repo"

    @property
    def hidden_tests(self) -> Path:
        return self.dir / "hidden_tests"

    @property
    def solution(self) -> Path:
        return self.dir / "solution"


def load_task(task_dir: Path) -> Task:
    meta = tomllib.loads((task_dir / "task.toml").read_text(encoding="utf-8"))
    task_id = meta.get("id", task_dir.name)
    if task_id != task_dir.name:
        raise ValueError(f"{task_dir}: task.toml id {task_id!r} != directory name")
    return Task(
        id=task_id,
        dir=task_dir,
        title=meta.get("title", task_id),
        category=meta.get("category", "misc"),
        prompt=(task_dir / "prompt.md").read_text(encoding="utf-8").strip(),
        timeout_sec=int(meta.get("timeout_sec", 600)),
        check=list(meta.get("check", ["node", "--test"])),
        check_timeout_sec=int(meta.get("check_timeout_sec", 120)),
        tags=list(meta.get("tags", [])),
    )


def load_tasks(root: Path, selected: list[str] | None = None) -> list[Task]:
    dirs = sorted(p for p in root.iterdir() if (p / "task.toml").is_file())
    tasks = [load_task(d) for d in dirs]
    if selected and selected != ["all"]:
        known = {t.id: t for t in tasks}
        missing = [s for s in selected if s not in known]
        if missing:
            raise SystemExit(f"unknown task(s): {', '.join(missing)}; known: {', '.join(known)}")
        tasks = [known[s] for s in selected]
    return tasks


def overlay(src: Path, dst: Path) -> None:
    """Copy every file under src onto dst (same relative paths), overwriting."""
    if not src.is_dir():
        return
    for path in src.rglob("*"):
        if path.is_file():
            target = dst / path.relative_to(src)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


def _force_remove(func, path, _exc):
    # git marks object files read-only; Windows refuses to delete them otherwise.
    os.chmod(path, stat.S_IWRITE)
    func(path)


def rmtree(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path, onexc=_force_remove)


def protected_hashes(workdir: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for pattern in PROTECTED_GLOBS:
        for path in workdir.glob(pattern):
            if path.is_file():
                rel = path.relative_to(workdir).as_posix()
                out[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


def tampered(before: dict[str, str], after: dict[str, str]) -> list[str]:
    keys = set(before) | set(after)
    return sorted(k for k in keys if before.get(k) != after.get(k))


_PASS = re.compile(r"^# pass (\d+)", re.M)
_FAIL = re.compile(r"^# fail (\d+)", re.M)


@dataclass
class CheckResult:
    passed: bool
    exit_code: int | None
    tests_pass: int | None
    tests_fail: int | None
    output: str
    timed_out: bool = False


def run_check(task: Task, workdir: Path, *, include_hidden: bool = True) -> CheckResult:
    """Run the grading command, optionally overlaying hidden tests first."""
    if include_hidden:
        overlay(task.hidden_tests, workdir / "test")
    exe = shutil.which(task.check[0]) or task.check[0]
    proc = subprocess.Popen(
        [exe, *task.check[1:]], cwd=workdir,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", errors="replace",
        stdin=subprocess.DEVNULL, **group_options(),
    )
    try:
        stdout, stderr = proc.communicate(timeout=task.check_timeout_sec)
    except subprocess.TimeoutExpired:
        kill_tree(proc)
        stdout, stderr = proc.communicate()
        return CheckResult(False, None, None, None, stdout + stderr + "\n[check timed out]", timed_out=True)
    output = stdout + stderr
    p, f = _PASS.findall(output), _FAIL.findall(output)
    tests_pass = int(p[-1]) if p else None
    tests_fail = int(f[-1]) if f else None
    return CheckResult(proc.returncode == 0, proc.returncode, tests_pass, tests_fail, output)


_TAP = re.compile(r"^(not )?ok \d+ - (.+?)(?:\s+#\s*(SKIP|TODO)\b.*)?$", re.M)


def tap_results(output: str) -> dict[str, bool]:
    """Top-level TAP results by test name; indented subtests and SKIP/TODO are ignored.

    Repeated names get a " (2)", " (3)" ... suffix in output order.
    """
    results: dict[str, bool] = {}
    seen: dict[str, int] = {}
    for match in _TAP.finditer(output):
        if match.group(3):
            continue
        name = match.group(2)
        seen[name] = seen.get(name, 0) + 1
        key = name if seen[name] == 1 else f"{name} ({seen[name]})"
        results[key] = match.group(1) is None
    return results


def baseline_results(task: Task) -> dict[str, bool]:
    """Per-test results of the untouched starting repository, hidden tests included."""
    with tempfile.TemporaryDirectory(prefix=f"harness-bench-baseline-{task.id}-",
                                     ignore_cleanup_errors=True) as temporary:
        workdir = Path(temporary) / "repo"
        workdir.mkdir()
        overlay(task.repo, workdir)
        check = run_check(task, workdir)
        return {} if check.timed_out else tap_results(check.output)
