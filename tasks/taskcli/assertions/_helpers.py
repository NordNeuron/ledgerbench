"""Shared helpers for reference-assertion test files.

Assertion files are executed by the harness against a workspace directory
communicated via the LEDGERBENCH_WORKSPACE environment variable. They must
never import anything from oracles/.
"""
import json
import os
import re
import sqlite3
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


def tasks_json_path(cwd=None):
    return os.path.join(cwd or workspace_path(), "tasks.json")


def load_tasks_json(cwd=None):
    path = tasks_json_path(cwd)
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f)


def tasks_db_path(cwd=None):
    return os.path.join(cwd or workspace_path(), "tasks.db")


def extract_id(list_line):
    """Given one line of `taskcli list` output, return the task id as a
    string. TRAP_DESIGN.md rule 6.2: helpers that parse output must
    tolerate any format that satisfies the actual requirements — no task
    pins the list format, so take the first integer on the line (true in
    every observed format; test titles contain no digits)."""
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


def load_tasks_db(cwd=None):
    path = tasks_db_path(cwd)
    if not os.path.exists(path):
        return []
    conn = sqlite3.connect(path)
    try:
        cols = [row[1] for row in conn.execute("PRAGMA table_info(tasks)")]
        if not cols:
            return []
        rows = conn.execute(f"SELECT {', '.join(cols)} FROM tasks ORDER BY id").fetchall()
        return [dict(zip(cols, row)) for row in rows]
    finally:
        conn.close()
