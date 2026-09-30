"""Launch native Pi/Codex with an access-only token in disposable benchmark state.

The runner obtains the token via env_commands; neither argv nor stdout contains it.
No operator auth/config is copied and no refresh token is available to rotate.
"""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind', choices=('pi', 'codex'), required=True)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command:
        parser.error('native CLI command required')
    env = dict(os.environ)
    token = env.pop('OPENAI_CODEX_OAUTH_TOKEN', '')
    state_key = 'CODEX_HOME' if args.kind == 'codex' else 'PI_CODING_AGENT_DIR'
    state = Path(env.get(state_key, '')).resolve()
    # Refuse to write credentials anywhere except the runner-owned temp directory.
    if state.parent != Path(tempfile.gettempdir()).resolve() or not state.name.startswith('hb-state-') or not state.is_dir():
        parser.error('runner-owned isolated state required')
    auth = state / 'auth.json'
    if auth.exists():
        parser.error('isolated state must not contain credentials')
    try:
        payload = token.split('.')[1]
        claims = json.loads(base64.urlsafe_b64decode(payload + '=' * (-len(payload) % 4)))
        expires = claims['exp']
        account = claims['https://api.openai.com/auth']['chatgpt_account_id']
        if expires <= time.time() or not account:
            raise ValueError()
    except (IndexError, KeyError, ValueError, TypeError):
        print('Fresh ChatGPT access token required', file=sys.stderr)
        return 2
    try:
        if args.kind == 'pi':
            auth.write_text(json.dumps({'openai-codex': {'type': 'oauth', 'access': token,
                            'refresh': '', 'expires': expires * 1000, 'accountId': account}}), encoding='utf-8')
        else:
            # Native ChatGPT TokenData parses identity claims from the access JWT.
            # https://github.com/openai/codex/blob/main/codex-rs/login/src/auth/manager.rs
            auth.write_text(json.dumps({'auth_mode': 'chatgpt', 'OPENAI_API_KEY': None,
                            'tokens': {'id_token': token, 'access_token': token,
                                       'refresh_token': '', 'account_id': account},
                            'last_refresh': datetime.now(timezone.utc).isoformat()}), encoding='utf-8')
        return subprocess.run(command, env=env, stdin=subprocess.DEVNULL).returncode
    finally:
        auth.unlink(missing_ok=True)


if __name__ == '__main__':
    raise SystemExit(main())
