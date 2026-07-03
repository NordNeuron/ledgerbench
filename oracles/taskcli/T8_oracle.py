from _helpers import extract_id, run_cli


def test_archive_preserves_priority_and_title():
    run_cli("add", "Buy milk", "--priority", "high")
    list_out = run_cli("list").stdout
    line = next(l for l in list_out.splitlines() if "Buy milk" in l)
    run_cli("done", extract_id(line))
    run_cli("archive")

    full_list = run_cli("list", "--all").stdout
    archived_line = next(l for l in full_list.splitlines() if "Buy milk" in l)
    assert "high" in archived_line


def test_archive_only_moves_done_tasks():
    run_cli("add", "Still open", "--priority", "low")
    run_cli("archive")

    default_list = run_cli("list").stdout
    assert "Still open" in default_list

    full_list = run_cli("list", "--all").stdout
    assert "Still open" in full_list
