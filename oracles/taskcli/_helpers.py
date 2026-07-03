"""Shared helpers for hidden oracle test files.

Oracle files are executed by the harness against a temporary COPY of the
workspace (never the git-tracked workspace itself). The path is communicated
via the LEDGERBENCH_WORKSPACE environment variable, exactly like assertion
helpers. This file must never be imported by agent.py or included in any
prompt (see BUILD_SPEC.md section 7).
"""
import os
import re
import subprocess
import sys


def workspace_path():
    path = os.environ.get("LEDGERBENCH_WORKSPACE")
    if not path:
        raise RuntimeError("LEDGERBENCH_WORKSPACE is not set")
    return path


def run_cli(*args, cwd=None, env=None):
    cwd = cwd or workspace_path()
    full_env = dict(os.environ)
    if env:
        full_env.update(env)
    return subprocess.run(
        [sys.executable, "-m", "taskcli", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        env=full_env,
    )


def extract_id(list_line):
    """Given one line of `taskcli list` output, return the task id as a
    string. No task prompt pins the list format, so models legitimately
    vary it (seed prints "[ ] 1: Buy milk", one real run printed
    "1 [ ] Buy milk (priority: high)"); the id is the first integer on
    the line in every observed format, and oracle test titles contain no
    digits."""
    match = re.search(r"\d+", list_line)
    if match is None:
        raise AssertionError(f"no task id found in list line: {list_line!r}")
    return match.group(0)


def pin_today(date):
    """Regime-agnostic test-date override: sets both the pre-T20 mechanism
    (TASKCLI_TODAY env var) and the post-T20 one (config.toml `today` key).
    Implementations honoring either see the same date. Returns the env dict
    to pass to run_cli."""
    with open(os.path.join(workspace_path(), "config.toml"), "w", encoding="utf-8") as f:
        f.write('today = "%s"\n' % date)
    return {"TASKCLI_TODAY": date}
