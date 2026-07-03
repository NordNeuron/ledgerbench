# LEDGER-META
# id: A14
# requirement: R14
# introduced_task: T14
# assumes: {storage: sqlite, schema: items_table}
# tier: correctness
import sqlite3

from _helpers import run_cli, tasks_db_path


def _table_names():
    conn = sqlite3.connect(tasks_db_path())
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        return {r[0] for r in rows}
    finally:
        conn.close()


def test_items_table_holds_tasks_with_kind():
    run_cli("add", "Normalized row", "--priority", "med")
    conn = sqlite3.connect(tasks_db_path())
    try:
        rows = conn.execute("SELECT title, kind FROM items").fetchall()
    finally:
        conn.close()
    assert any(r[0] == "Normalized row" and r[1] == "task" for r in rows)


def test_old_tasks_table_is_gone():
    run_cli("add", "Schema check")
    names = _table_names()
    assert "items" in names, f"items table missing; found {sorted(names)}"
    assert "tasks" not in names, "the old `tasks` table must no longer exist"
