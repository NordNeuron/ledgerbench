# LEDGER-META
# id: A3
# requirement: R3
# introduced_task: T3
# assumes: {storage: json_file}
# tier: correctness
from _helpers import load_tasks_json, run_cli


def test_edit_preserves_priority_in_json():
    run_cli("add", "Old title", "--priority", "high")
    tasks = load_tasks_json()
    task_id = next(t["id"] for t in tasks if t["title"] == "Old title")

    result = run_cli("edit", str(task_id), "--title", "New title")
    assert result.returncode == 0, result.stderr

    tasks = load_tasks_json()
    task = next(t for t in tasks if t["id"] == task_id)
    assert task["title"] == "New title"
    assert task["priority"] == "high"


def test_edit_preserves_done_flag_in_json():
    run_cli("add", "To finish")
    tasks = load_tasks_json()
    task_id = next(t["id"] for t in tasks if t["title"] == "To finish")
    run_cli("done", str(task_id))

    run_cli("edit", str(task_id), "--title", "Finished renamed")

    tasks = load_tasks_json()
    task = next(t for t in tasks if t["id"] == task_id)
    assert task["title"] == "Finished renamed"
    assert task["done"] is True
