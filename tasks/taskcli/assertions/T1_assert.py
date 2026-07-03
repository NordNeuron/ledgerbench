# LEDGER-META
# id: A1
# requirement: R1
# introduced_task: T1
# assumes: {storage: json_file}
# tier: correctness
from _helpers import load_tasks_json, run_cli


def test_add_high_priority_stored_in_json():
    result = run_cli("add", "Buy milk", "--priority", "high")
    assert result.returncode == 0, result.stderr
    tasks = load_tasks_json()
    assert any(t["title"] == "Buy milk" and t["priority"] == "high" for t in tasks)


def test_add_default_priority_is_med_in_json():
    result = run_cli("add", "Water the plants")
    assert result.returncode == 0, result.stderr
    tasks = load_tasks_json()
    assert any(t["title"] == "Water the plants" and t["priority"] == "med" for t in tasks)
