# LEDGER-META
# id: A4
# requirement: R4
# introduced_task: T4
# assumes: {storage: json_file}
# tier: correctness
from _helpers import load_tasks_json, run_cli


def test_add_with_due_date_stored_in_json():
    result = run_cli("add", "Renew passport", "--due", "2026-03-05")
    assert result.returncode == 0, result.stderr
    tasks = load_tasks_json()
    assert any(t["title"] == "Renew passport" and t["due"] == "2026-03-05" for t in tasks)


def test_add_with_invalid_due_date_rejected():
    result = run_cli("add", "Bad date task", "--due", "not-a-date")
    assert result.returncode != 0
    tasks = load_tasks_json()
    assert not any(t["title"] == "Bad date task" for t in tasks)
