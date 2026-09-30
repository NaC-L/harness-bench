"""Process-group lifecycle shared by agent execution and grading."""
import os
import signal
import subprocess


def group_options():
    return {'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == 'nt' else {'start_new_session': True}


def kill_tree(proc):
    try:
        if os.name == 'nt':
            subprocess.run(['taskkill', '/PID', str(proc.pid), '/T', '/F'], capture_output=True, timeout=30)
        else:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    finally:
        if proc.poll() is None:
            proc.kill()
        proc.wait(timeout=30)
