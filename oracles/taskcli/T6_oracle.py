from _helpers import extract_id, run_cli


def test_add_and_list_still_work_after_migration():
    run_cli("add", "Buy milk", "--priority", "high")
    result = run_cli("list")
    assert result.returncode == 0, result.stderr
    assert "Buy milk" in result.stdout
    assert "high" in result.stdout


def test_done_and_delete_still_work_after_migration():
    run_cli("add", "Temp task")
    list_before = run_cli("list").stdout
    line = next(l for l in list_before.splitlines() if "Temp task" in l)
    task_id = extract_id(line)

    done_result = run_cli("done", task_id)
    assert done_result.returncode == 0, done_result.stderr

    delete_result = run_cli("delete", task_id)
    assert delete_result.returncode == 0, delete_result.stderr
    list_after = run_cli("list").stdout
    assert "Temp task" not in list_after
