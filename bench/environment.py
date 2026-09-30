"""CLI state roots resolved from the same environment used to launch them.

Harness CLIs read personal state (instructions, settings, MCP servers, memories) from
their state root. A harness can instead run against a disposable copy of a checked-in
template (`state_template`), so results do not depend on the operator's own setup.
"""
from pathlib import Path

# Environment variable that relocates each kind's state root, and its default location.
STATE_ENV = {
    'omp': ('PI_CODING_AGENT_DIR', ('.omp', 'agent')),
    'pi': ('PI_CODING_AGENT_DIR', ('.pi', 'agent')),
    'claude': ('CLAUDE_CONFIG_DIR', ('.claude',)),
    'codex': ('CODEX_HOME', ('.codex',)),
}
# A named profile overrides PI_CODING_AGENT_DIR, so isolated runs must not inherit one.
PROFILE_ENV = ('OMP_PROFILE', 'PI_PROFILE')
# Files in the state root that shape the prompt, tools or behaviour; fingerprinted per run.
CONTEXT_FILES = {
    'omp': ['config.yml', 'models.yml', 'SYSTEM.md', 'SYSTEM_TEMPLATE.md', 'AGENTS.md', 'RULES.md',
            'PERSONALITY.md', 'mcp.json', '.mcp.json'],
    'pi': ['settings.json', 'models.json'],
    'claude': ['settings.json'],
    'codex': ['config.toml'],
}
# Project-scope inputs harnesses discover by walking up from the working directory.
ANCESTOR_CONTEXT = ('AGENTS.md', 'CLAUDE.md', 'GEMINI.md', 'CODEX.md', '.mcp.json',
                    '.omp', '.pi', '.agent', '.agents', '.claude', '.codex')


def state_dir(kind: str, env: dict[str, str], home: Path) -> Path:
    key, default = STATE_ENV[kind]
    return Path(env.get(key) or home.joinpath(*default))


def isolate(kind: str, env: dict[str, str], state: Path) -> None:
    """Point a harness at `state` instead of the operator's personal state root."""
    env[STATE_ENV[kind][0]] = str(state)
    for key in PROFILE_ENV:
        env.pop(key, None)


def ancestor_context(workdir: Path, home: Path) -> list[str]:
    """Non-empty project context entries above the workdir (home is the harness user root)."""
    found = []
    for parent in Path(workdir).resolve().parents:
        if parent == home.resolve():
            continue
        for name in ANCESTOR_CONTEXT:
            path = parent / name
            if path.is_file() or (path.is_dir() and any(path.iterdir())):
                found.append(str(path))
    return found
