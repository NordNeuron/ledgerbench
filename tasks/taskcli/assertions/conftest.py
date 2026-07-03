import os

import pytest

from _helpers import workspace_path


@pytest.fixture(autouse=True)
def clean_storage():
    """Each test starts from an empty task store. Without this, orphaned
    tasks left behind by tests that crash mid-way (e.g. a json_file
    assertion hitting FileNotFoundError after T6's sqlite migration, having
    already called `add`) would pollute every later test sharing the same
    persistent workspace storage file."""
    ws = workspace_path()
    for fname in ("tasks.json", "tasks.db", "config.toml"):
        path = os.path.join(ws, fname)
        if os.path.exists(path):
            os.remove(path)
    yield
