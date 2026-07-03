# LEDGER-META
# id: A8
# requirement: R8
# introduced_task: T8
# assumes: {}
# tier: correctness
from _helpers import extract_id, run_cli


def test_archive_hides_from_default_list_but_shows_with_all():
    run_cli("add", "Finish report", "--priority", "high")
    list_out = run_cli("list").stdout
    line = next(l for l in list_out.splitlines() if "Finish report" in l)
    run_cli("done", extract_id(line))

    run_cli("archive")

    default_list = run_cli("list").stdout
    assert "Finish report" not in default_list

    full_list = run_cli("list", "--all").stdout
    assert "Finish report" in full_list


def test_archive_does_not_break_stats_counting():
    run_cli("add", "Task A", "--priority", "high")
    run_cli("add", "Task B", "--priority", "med")
    list_out = run_cli("list").stdout
    line_a = next(l for l in list_out.splitlines() if "Task A" in l)
    run_cli("done", extract_id(line_a))

    run_cli("archive")

    result = run_cli("stats")
    assert result.returncode == 0, result.stderr
    assert "Total: 2" in result.stdout
    assert "Done: 1" in result.stdout
    assert "Open: 1" in result.stdout
