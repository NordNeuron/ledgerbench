# LEDGER-META
# id: A6
# requirement: R6
# introduced_task: T6
# assumes: {storage: sqlite, schema: tasks_table}
# tier: correctness
import os

from _helpers import load_tasks_db, run_cli, tasks_db_path, tasks_json_path


def test_tasks_db_exists_and_contains_added_task():
    result = run_cli("add", "Migrated task", "--priority", "high")
    assert result.returncode == 0, result.stderr
    assert os.path.exists(tasks_db_path())
    rows = load_tasks_db()
    assert any(r["title"] == "Migrated task" and r["priority"] == "high" for r in rows)


def test_tasks_json_not_created():
    run_cli("add", "Another task")
    assert not os.path.exists(tasks_json_path())
