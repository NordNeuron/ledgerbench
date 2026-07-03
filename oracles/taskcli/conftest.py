import os

import pytest

from _helpers import workspace_path


@pytest.fixture(autouse=True)
def clean_storage():
    """See tasks/taskcli/assertions/conftest.py for why this is needed:
    each test must start from an empty task store, not whatever accumulated
    state prior verification/oracle runs left in the (temp-copied)
    workspace."""
    ws = workspace_path()
    for fname in ("tasks.json", "tasks.db", "config.toml"):
        path = os.path.join(ws, fname)
        if os.path.exists(path):
            os.remove(path)
    yield
