from _helpers import extract_id, run_cli


def test_edit_then_list_still_shows_priority():
    run_cli("add", "Old title", "--priority", "high")
    list_before = run_cli("list").stdout
    line = next(l for l in list_before.splitlines() if "Old title" in l)
    task_id = extract_id(line)

    run_cli("edit", task_id, "--title", "New title")
    list_after = run_cli("list").stdout
    line_after = next(l for l in list_after.splitlines() if "New title" in l)
    assert "high" in line_after
    assert "Old title" not in list_after


def test_edit_changes_title_only_end_to_end():
    run_cli("add", "Task A", "--priority", "low")
    run_cli("add", "Task B", "--priority", "high")

    list_before = run_cli("list").stdout
    line_b = next(l for l in list_before.splitlines() if "Task B" in l)
    task_id = extract_id(line_b)

    run_cli("edit", task_id, "--title", "Task B Renamed")
    list_after = run_cli("list").stdout
    line_b_after = next(l for l in list_after.splitlines() if "Task B Renamed" in l)
    assert "high" in line_b_after
    assert "Task A" in list_after
