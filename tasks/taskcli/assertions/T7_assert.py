# LEDGER-META
# id: A7
# requirement: R7
# introduced_task: T7
# assumes: {}
# tier: correctness
from _helpers import extract_id, run_cli


def test_stats_counts_total_done_open():
    run_cli("add", "Task 1")
    run_cli("add", "Task 2")
    list_out = run_cli("list").stdout
    line = next(l for l in list_out.splitlines() if "Task 1" in l)
    run_cli("done", extract_id(line))

    result = run_cli("stats")
    assert result.returncode == 0, result.stderr
    assert "Total: 2" in result.stdout
    assert "Done: 1" in result.stdout
    assert "Open: 1" in result.stdout


def test_stats_counts_by_priority():
    run_cli("add", "High 1", "--priority", "high")
    run_cli("add", "High 2", "--priority", "high")
    run_cli("add", "Med 1")
    run_cli("add", "Low 1", "--priority", "low")

    result = run_cli("stats")
    assert result.returncode == 0, result.stderr
    assert "Priority high: 2" in result.stdout
    assert "Priority med: 1" in result.stdout
    assert "Priority low: 1" in result.stdout
