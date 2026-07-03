# LEDGER-META
# id: A10
# requirement: R10
# introduced_task: T10
# assumes: {storage: sqlite, schema: tasks_table}
# tier: correctness
import os
import sqlite3

from _helpers import run_cli, workspace_path


def test_backup_copies_database_with_tasks():
    run_cli("add", "Precious data", "--priority", "high")
    dest = os.path.join(workspace_path(), "mybackup.db")
    if os.path.exists(dest):
        os.remove(dest)
    result = run_cli("backup", dest)
    assert result.returncode == 0, result.stderr
    assert os.path.exists(dest)
    conn = sqlite3.connect(dest)
    try:
        rows = conn.execute("SELECT title FROM tasks").fetchall()
    finally:
        conn.close()
    assert any("Precious data" in r[0] for r in rows)
