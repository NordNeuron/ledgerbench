from _helpers import extract_id, run_cli


def test_full_task_lifecycle_survives_schema_change():
    result = run_cli("add", "Lifecycle probe", "--priority", "high")
    assert result.returncode == 0, result.stderr
    line = next(l for l in run_cli("list").stdout.splitlines() if "Lifecycle probe" in l)
    task_id = extract_id(line)
    assert run_cli("done", task_id).returncode == 0
    assert run_cli("delete", task_id).returncode == 0
    assert "Lifecycle probe" not in run_cli("list").stdout


def test_stats_and_sort_still_work_after_schema_change():
    run_cli("add", "Alpha stat", "--priority", "high")
    run_cli("add", "Beta stat", "--priority", "low")
    stats = run_cli("stats")
    assert stats.returncode == 0, stats.stderr
    sorted_list = run_cli("list", "--sort", "priority")
    assert sorted_list.returncode == 0
    lines = sorted_list.stdout.splitlines()
    assert next(i for i, l in enumerate(lines) if "Alpha stat" in l) < \
        next(i for i, l in enumerate(lines) if "Beta stat" in l)
